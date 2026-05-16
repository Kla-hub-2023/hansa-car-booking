import streamlit as st
import pymysql
import pandas as pd
import requests
from datetime import datetime
import io
import datetime as dt_module

# --- 1. การตั้งค่าพื้นฐานและการเชื่อมต่อ DB ---
@st.cache_resource
def get_connection():
    return pymysql.connect(
        host='mysql-22653bef-kla-e55d.c.aivencloud.com',
        user='avnadmin',
        password='AVNS_W4Huwc3abQww6NKNlG2',
        database='defaultdb',
        port=23986
    )

def send_line_message(message, target_id):
    token = 'X8ogM3D2GxzZ3z5EBMdOxWTa4BjTlqP1H/bYv+fwqLGNiKhhxuiPQR5bakcgXfEZBUPNDImDlvLrDMvtqN0/8XTlrcqfIvti2m2RpY/wrbQ9xl95HJd+slpzHCM9Vs5SxNS5e9gBG4MSE71UUNhXrQdB04t89/1O/w1cDnyilFU=' # ⚠️ Token LINE ของคุณกล้า
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    data = {'to': target_id, 'messages': [{'type': 'text', 'text': message}]}
    try:
        requests.post(url, headers=headers, json=data)
    except Exception as e:
        pass

# --- 2. ระบบเช็คสิทธิ์ผู้ใช้งาน ---
def check_permission(user_id):
    try:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT role FROM users WHERE line_user_id = %s", (user_id,))
            result = cursor.fetchone()
        return result[0] if result else "Guest"
    except Exception as e:
        return "Guest"

st.set_page_config(page_title="ระบบจัดการรถ Multi-Role", layout="wide")

# แถบเมนูด้านซ้ายสำหรับเข้าสู่ระบบ
st.sidebar.title("🔐 เข้าสู่ระบบ")
current_id = st.sidebar.text_input("ระบุ LINE User ID", value="วาง_รหัส_U_ของคุณที่นี่")

# จัดการแปลงเป็นตัวพิมพ์เล็กเพื่อลดความผิดพลาดในการค้นหาในฐานข้อมูล
user_role = check_permission(current_id.strip()).lower()
st.sidebar.info(f"สิทธิ์ของคุณคือ: {user_role}")

# --- 3. จัดการรายการเมนูฝั่งซ้ายตามระดับสิทธิ์ ---
menu_options = []
if user_role == "admin":
    menu_options = ["🏠 Dashboard", "➕ Booker", "🖥️ Dispatcher", "🚖 Driver", "✈️ Airport Staff"]
elif user_role == "dispatcher":
    menu_options = ["➕ Booker", "🖥️ Dispatcher", "🚖 Driver", "✈️ Airport Staff"]
elif user_role == "driver":
    menu_options = ["🚖 งานของฉัน (Driver)"]
elif user_role == "passenger":
    menu_options = ["➕ Booker"]
elif user_role == "airportstaff" or user_role == "airport staff":
    menu_options = ["✈️ Airport Staff"]
else:
    # หากเป็น Guest หรือยังไม่ล็อกอิน
    st.warning("⚠️ คุณไม่มีสิทธิ์เข้าถึงระบบ หรือยังไม่ได้ระบุรหัส LINE User ID ที่ถูกต้องบนฐานข้อมูล")
    st.info("💡 ทดสอบระบบ: กรุณากรอก 'admin01' ในช่องระบุ LINE User ID ด้านซ้ายมือเพื่อปลดล็อก")
    st.stop()

# แสดงปุ่มเลือกเมนูตามรายการสิทธิ์ที่ได้รับกรองแล้วด้านบน
choice = st.sidebar.radio("เมนูใช้งาน", menu_options)

# --- 4. การแสดงเนื้อหาไส้ในของแต่ละเมนูตามหน้าเลือก ---

# หน้าที่ 1: Dashboard
if "Dashboard" in choice:
    st.title("🏠 หน้าแรกและภาพรวมระบบ (Dashboard)")
    st.write(f"สวัสดีครับคุณกล้า สถานะการเชื่อมต่อระบบฐานข้อมูลคลาวด์ Aiven MySQL ปกติดีเยี่ยมครับ")

# หน้าที่ 2: Booker (แบบฟอร์มบันทึกการจองรถ เชื่อมต่อ Aiven DB ตัวเต็ม)
elif "Booker" in choice:
    st.title("📋 แบบฟอร์มจองรถ (Booker)")
    st.subheader("กรอกรายละเอียดการเดินทางเพื่อส่งงานให้ผู้จัดสรรรถ")

    with st.form(key="car_booking_form", clear_on_submit=True):
        st.write("### 🚗 ข้อมูลการเดินทาง")
        
        # 1. ช่องกรอกข้อมูล
        passenger_name = st.text_input("👤 ชื่อผู้โดยสาร / คณะเดินทาง", placeholder="เช่น คุณสมชาย สายลุย")
        
        locations = ["สนามบินสุวรรณภูมิ", "สนามบินดอนเมือง", "โรงแรมฮันซ่า", "ตัวเมืองกรุงเทพฯ", "พัทยา", "หัวหิน"]
        pickup_location = st.selectbox("📍 จุดรับ (Pickup)", options=locations)
        dropoff_location = st.selectbox("🏁 จุดส่ง (Dropoff)", options=locations)
        
        # 2. วันและเวลาเดินทาง
        st.write("📅 วันและเวลาเดินทาง")
        col1, col2 = st.columns(2)
        with col1:
            booking_date = st.date_input("เลือกวันที่")
        with col2:
            booking_time_input = st.time_input("เลือกเวลา")
        
        combined_datetime = dt_module.datetime.combine(booking_date, booking_time_input)
        submit_button = st.form_submit_with_button("💾 บันทึกข้อมูลการจอง")

    # ส่วนของการประมวลผลเมื่อกดปุ่มบันทึก
    if submit_button:
        if not passenger_name.strip():
            st.error("⚠️ กรุณากรอกชื่อผู้โดยสารก่อนกดบันทึกครับ")
        elif pickup_location == dropoff_location:
            st.error("⚠️ จุดรับและจุดส่งห้ามเป็นสถานที่เดียวกันครับ")
        else:
            with st.spinner("กำลังเชื่อมต่อฐานข้อมูลและบันทึกข้อมูล..."):
                try:
                    db = get_connection()
                    with db.cursor() as cursor:
                        sql = """
                            INSERT INTO bookings (passenger_name, pickup_location, dropoff_location, booking_time, status)
                            VALUES (%s, %s, %s, %s, %s)
                        """
                        val = (passenger_name, pickup_location, dropoff_location, combined_datetime, 'Pending')
                        cursor.execute(sql, val)
                        db.commit()
                    st.success(f"🎉 บันทึกการจองสำหรับคุณ {passenger_name} เรียบร้อยแล้ว! ข้อมูลยิงเข้าไปบันทึกบนระบบคลาวด์เรียลไทม์")
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาดระหว่างบันทึกข้อมูล: {e}")
                finally:
                    if 'db' in locals() and db.open:
                        db.close()

# หน้าที่ 3: Dispatcher
elif "Dispatcher" in choice:
    st.title("🖥️ หน้าจัดการงาน (Dispatcher)")
    st.write("🔧 กำลังเตรียมโครงสร้างตารางแสดงรายการข้อมูล เพื่อให้คัดเลือกคนขับรถและส่งข้อความแจ้งเตือนผ่าน LINE")

# หน้าที่ 4: Driver
elif "Driver" in choice:
    st.title("🚖 งานที่ได้รับมอบหมาย (Driver)")
    st.write("แสดงรายการงานจองรถทั้งหมดที่เจาะจงมอบหมายให้ไอดี LINE ของคนขับคนนี้")

# หน้าที่ 5: Airport Staff
elif "Airport Staff" in choice:
    st.title("✈️ ตรวจสอบสถานะรถ (Airport Staff)")
    st.write("หน้าตารางรายงานสำหรับพนักงานภาคพื้นสนามบิน เพื่อมอนิเตอร์ดูว่ารถจองกำลังเดินทางมาถึงในเวลาใดบ้าง")
