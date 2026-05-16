import streamlit as st
import pymysql
import pandas as pd
import requests
from datetime import datetime
import io

# --- 1. การตั้งค่าพื้นฐานและการเชื่อมต่อ DB ---
@st.cache_resource
def get_connection():
    return pymysql.connect(
        host='mysql-22653bef-kla-e55d.c.aivencloud.com',
        user='avnadmin',
        password='AVNS_W4Huwc3abQww6NKNlG2', # ⚠️ แก้จุดนี้
        database='defaultdb',
        port=23986
    )

def send_line_message(message, target_id):
    token = 'X8ogM3D2GxzZ3z5EBMdOxWTa4BjTlqP1H/bYv+fwqLGNiKhhxuiPQR5bakcgXfEZBUPNDImDlvLrDMvtqN0/8XTlrcqfIvti2m2RpY/wrbQ9xl95HJd+slpzHCM9Vs5SxNS5e9gBG4MSE71UUNhXrQdB04t89/1O/w1cDnyilFU=' # ⚠️ แก้จุดนี้
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    data = {'to': target_id, 'messages': [{'type': 'text', 'text': message}]}
    requests.post(url, headers=headers, json=data)

# --- 2. ระบบเช็คสิทธิ์ผู้ใช้งาน ---
def check_permission(user_id):
    db = get_connection()
    with db.cursor() as cursor:
        cursor.execute("SELECT role FROM users WHERE line_user_id = %s", (user_id,))
        result = cursor.fetchone()
    return result[0] if result else "Guest"

st.set_page_config(page_title="ระบบจัดการรถ Multi-Role", layout="wide")

# จำลองการดึง ID จาก LINE (ตอนนี้ให้พิมพ์ใส่เองเพื่อทดสอบ)
st.sidebar.title("🔐 เข้าสู่ระบบ")
current_id = st.sidebar.text_input("ระบุ LINE User ID", value="วาง_รหัส_U_ของคุณที่นี่")
user_role = check_permission(current_id)
st.sidebar.info(f"สิทธิ์ของคุณคือ: {user_role}")

# --- 3. จัดการเมนูตามสิทธิ์ (Spec: Admin เห็นหมด, Dispatcher เห็น 3 กลุ่ม) ---
menu_options = []
if user_role == "admin":
    menu_options = ["🏠 Dashboard", "➕ Booker", "🖥️ Dispatcher", "🚖 Driver", "✈️ Airport Staff"]
elif user_role == "Dispatcher":
    menu_options = ["➕ Booker", "🖥️ Dispatcher", "🚖 Driver", "✈️ Airport Staff"]
elif user_role == "Driver":
    menu_options = ["🚖 งานของฉัน (Driver)"]
elif menu == "Booker":
    st.title("📋 แบบฟอร์มจองรถ (Booker)")
    st.subheader("กรอกรายละเอียดการเดินทางเพื่อส่งงานให้ผู้จัดสรรรถ")

    # สร้างกล่องฟอร์มสีขาวล้อมรอบให้ดูเป็นระเบียบ
    with st.form(key="car_booking_form", clear_on_submit=True):
        st.write("### 🚗 ข้อมูลการเดินทาง")
        
        # 1. ช่องกรอกชื่อผู้โดยสาร
        passenger_name = st.text_input("👤 ชื่อผู้โดยสาร / คณะเดินทาง", placeholder="เช่น คุณสมชาย สายลุย")
        
        # 2. ช่องเลือกจุดรับ-จุดส่ง (ปรับเปลี่ยนรายชื่อสถานที่ได้ตามใจชอบเลยครับ)
        locations = ["สนามบินสุวรรณภูมิ", "สนามบินดอนเมือง", "โรงแรมฮันซ่า", "ตัวเมืองกรุงเทพฯ", "พัทยา", "หัวหิน"]
        pickup_location = st.selectbox("📍 จุดรับ (Pickup)", options=locations)
        dropoff_location = st.selectbox("🏁 จุดส่ง (Dropoff)", options=locations)
        
        # 3. ช่องเลือกวันและเวลาเดินทาง
        st.write("📅 วันและเวลาเดินทาง")
        col1, col2 = st.columns(2)
        with col1:
            booking_date = st.date_input("เลือกวันที่")
        with col2:
            booking_time_input = st.time_input("เลือกเวลา")
        
        # รวมวันและเวลาเข้าด้วยกันเป็นฟอร์แมตที่ MySQL เข้าใจ (YYYY-MM-DD HH:MM:SS)
        import datetime
        combined_datetime = datetime.datetime.combine(booking_date, booking_time_input)

        # 4. ปุ่มกดบันทึกข้อมูล
        submit_button = st.form_submit_with_button("💾 บันทึกข้อมูลการจอง")

    # --- ส่วนของการกดปุ่มเพื่อบันทึกลงฐานข้อมูล Aiven ---
    if submit_button:
        # ตรวจเช็กเบื้องต้นก่อนว่าไม่ได้ปล่อยช่องชื่อให้ว่างไว้
        if not passenger_name.strip():
            st.error("⚠️ กรุณากรอกชื่อผู้โดยสารก่อนกดบันทึกครับ")
        elif pickup_location == dropoff_location:
            st.error("⚠️ จุดรับและจุดส่งห้ามเป็นสถานที่เดียวกันครับ")
        else:
            with st.spinner("กำลังเชื่อมต่อฐานข้อมูลและบันทึกข้อมูล..."):
                try:
                    # เรียกใช้ฟังก์ชันเชื่อมต่อ DB ที่เราเซ็ตค่าไว้ตอนแรก
                    db = get_connection()
                    cursor = db.cursor()
                    
                    # คำสั่ง SQL สำหรับยิงข้อมูลเข้าคลาวด์
                    sql = """
                        INSERT INTO bookings (passenger_name, pickup_location, dropoff_location, booking_time, status)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    val = (passenger_name, pickup_location, dropoff_location, combined_datetime, 'Pending')
                    
                    cursor.execute(sql, val)
                    db.commit() # ยืนยันการบันทึกข้อมูลลงแผ่นดิสก์บนคลาวด์
                    
                    # แจ้งเตือนความสำเร็จสีเขียวสวยงาม
                    st.success(f"🎉 บันทึกการจองสำหรับคุณ {passenger_name} เรียบร้อยแล้ว! ข้อมูลถูกส่งเข้าฐานข้อมูลออนไลน์แล้ว")
                    
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาดระหว่างบันทึกข้อมูล: {e}")
                finally:
                    # ปิดสัญญานการเชื่อมต่อเพื่อไม่ให้ฐานข้อมูลค้าง
                    if 'db' in locals() and db.open:
                        cursor.close()
                        db.close()
elif user_role == "AirportStaff":
    menu_options = ["✈️ ตรวจสอบคิวรถ (Airport Staff)"]
else:
    st.warning("คุณไม่มีสิทธิ์เข้าถึงระบบ กรุณาติดต่อ Admin")
    st.stop()

choice = st.sidebar.radio("เมนูใช้งาน", menu_options)

# --- 4. ไส้ในของแต่ละเมนู (ดึงโค้ดเดิมมาใส่ที่นี่) ---

if "Booker" in choice:
    st.title("📋 แบบฟอร์มจองรถ (Booker)")
    with st.form("book_form"):
        # ... (ใส่โค้ด Input ต่างๆ จาก app.py เดิมของคุณตรงนี้) ...
        vc = st.text_input("Voucher No.")
        # [ย่อโค้ดเพื่อประหยัดพื้นที่]
        btn = st.form_submit_button("บันทึก")
        if btn: st.success("บันทึกสำเร็จ")

elif "Dispatcher" in choice:
    st.title("🖥️ หน้าจัดการงาน (Dispatcher)")
    # ... (ใส่โค้ดตาราง Search/Export และปุ่มจ่ายงานเข้า LINE ตรงนี้) ...
    st.write("ตารางงานทั้งหมดและการจ่ายงานให้คนขับ")

elif "Driver" in choice:
    st.title("🚖 งานที่ได้รับมอบหมาย (Driver)")
    # ดึงงานเฉพาะที่ระบุชื่อ Driver คนนี้
    st.write("แสดงรายการงานที่คุณต้องไปรับลูกค้าวันนี้")

elif "Airport Staff" in choice:
    st.title("✈️ ตรวจสอบสถานะรถ (Airport Staff)")
    # แสดงตารางเพื่อให้พนักงานสนามบินรู้ว่ารถคันไหนกำลังมา
    st.write("ตารางรถที่จะมาถึงสนามบินเร็วๆ นี้")
