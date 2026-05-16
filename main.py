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
current_id = st.sidebar.text_input("ระบุ LINE User ID", value="admin01", placeholder="พิมพ์รหัสของคุณที่นี่")

# จัดการแปลงเป็นตัวพิมพ์เล็กเพื่อลดความผิดพลาดในการค้นหาในฐานข้อมูล
user_role = check_permission(current_id.strip()).lower()
st.sidebar.info(f"สิทธิ์ของคุณคือ: {user_role}")

# --- 3. จัดการรายการเมนูฝั่งซ้ายตามระดับสิทธิ์ ---
menu_options = []
# เช็กสิทธิ์โดยตัดช่องว่าง และแปลงเป็นตัวพิมพ์เล็กทั้งหมดเพื่อความปลอดภัย
current_role = user_role.strip().lower()

if current_role == "admin":
    menu_options = ["🏠 Dashboard", "➕ Booker", "🖥️ Dispatcher", "🚖 Driver", "✈️ Airport Staff"]
elif current_role == "dispatcher":
    menu_options = ["➕ Booker", "🖥️ Dispatcher", "🚖 Driver", "✈️ Airport Staff"]
elif current_role == "driver":
    menu_options = ["🚖 งานของฉัน (Driver)"]
elif current_role == "passenger":
    menu_options = ["➕ Booker"]
elif current_role == "airportstaff" or current_role == "airport staff":
    menu_options = ["✈️ Airport Staff"]
else:
    # หากยังเป็น Guest หรือหาชื่อไม่เจอในฐานข้อมูล
    st.warning("⚠️ คุณไม่มีสิทธิ์เข้าถึงระบบ หรือยังไม่ได้ระบุรหัส LINE User ID ที่ถูกต้องบนฐานข้อมูล")
    st.info("💡 รหัสที่ระบบตรวจพบตอนนี้คือ: " + f"`{current_id}`" + f" (ระดับสิทธิ์: `{user_role}`)")
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
        submit_button = st.form_submit_button("💾 บันทึกข้อมูลการจอง")

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

# หน้าที่ 3: Dispatcher (ดึงงานมาโชว์ + เลือกคนขับ + กดจ่ายงานลง Cloud)
elif "Dispatcher" in choice:
    st.title("🖥️ หน้าจัดการงาน (Dispatcher)")
    st.subheader("📋 รายการจองรถทั้งหมดที่รอจัดสรรคนขับ")

    # --- ส่วนที่ 1: ดึงงานจากคลาวด์มาแสดงผล ---
    try:
        db = get_connection()
        
        # 1.1 ดึงงานจองรถทั้งหมด
        query_bookings = "SELECT id, passenger_name, pickup_location, dropoff_location, booking_time, status, driver_id FROM bookings ORDER BY booking_time DESC"
        df_bookings = pd.read_sql(query_bookings, db)
        
        # 1.2 ดึงรายชื่อผู้ใช้ที่เป็น 'driver' ทั้งหมดมาทำเป็นตัวเลือก
        with db.cursor() as cursor:
            cursor.execute("SELECT line_user_id, name FROM users WHERE role = 'driver'")
            drivers_list = cursor.fetchall()
            
        # แปลงรายชื่อคนขับเป็นดีกชันนารี { 'ชื่อคนขับ (ID)': 'ID' } เพื่อเอาไปใส่ใน Selectbox
        driver_options = {f"🚖 {d[1]} ({d[0]})": d[0] for d in drivers_list}
        
    except Exception as e:
        st.error(f"❌ ไม่สามารถดึงข้อมูลจากฐานข้อมูลได้: {e}")
        df_bookings = pd.DataFrame()
        driver_options = {}
    finally:
        if 'db' in locals() and db.open:
            db.close()

    # แสดงตารางงานปัจจุบันให้ Dispatcher เห็นบนหน้าจอ
    if not df_bookings.empty:
        st.write("### 📊 ตารางสถานะงานปัจจุบัน")
        # ตกแต่งหน้าตาตารางของ Pandas ก่อนโชว์
        st.dataframe(df_bookings, use_container_width=True)
        
        st.write("---")
        st.write("### 🎯 ฟังก์ชันการจ่ายงานให้คนขับ")
        
        # กรองเอาเฉพาะงานที่ยังค้างสถานะ 'Pending' เพื่อเอามาเข้าเมนูจ่ายงาน
        pending_jobs = df_bookings[df_bookings['status'] == 'Pending']
        
        if not pending_jobs.empty:
            # สร้างลิสต์รายการงานเพื่อให้เลือกจากรหัส ID จอง เช่น "ID: 1 | คุณหรรษา (สนามบินสุวรรณภูมิ -> โรงแรมฮันซ่า)"
            job_options = {
                f"🆔 ใบงานที่ {row['id']} | คุณ {row['passenger_name']} ({row['pickup_location']} ➡️ {row['dropoff_location']})": row['id']
                for _, row in pending_jobs.iterrows()
            }
            
            # วางกล่องคอนโทรลในรูปแบบคอลัมน์ซ้ายขวาให้สวยงาม
            col_job, col_drv, col_btn = st.columns([2, 1, 1])
            
            with col_job:
                selected_job_text = st.selectbox("1️⃣ เลือกใบงานที่ต้องการจัดสรร", options=list(job_options.keys()))
                job_id_to_update = job_options[selected_job_text]
                
                # ดึงข้อมูลของงานที่เลือกไว้เตรียมไปส่ง LINE
                selected_job_data = pending_jobs[pending_jobs['id'] == job_id_to_update].iloc[0]
            
            with col_drv:
                if driver_options:
                    selected_driver_text = st.selectbox("2️⃣ เลือกคนขับรถที่จะส่งงาน", options=list(driver_options.keys()))
                    driver_id_to_assign = driver_options[selected_driver_text]
                else:
                    st.warning("⚠️ ไม่มีรายชื่อคนขับในระบบ")
                    driver_id_to_assign = None
                    
            with col_btn:
                st.write(" ") # เว้นช่องว่างให้ปุ่มตรงกับกล่องเลือก
                st.write(" ")
                btn_assign = st.button("🚀 กดจ่ายงานและส่ง LINE")
                
            # --- ส่วนที่ 2: เมื่อกดปุ่มจ่ายงาน ---
            if btn_assign:
                if not driver_id_to_assign:
                    st.error("❌ ไม่สามารถจ่ายงานได้ เนื่องจากไม่ได้เลือกคนขับรถครับ")
                else:
                    with st.spinner("กำลังอัปเดตสถานะงานและส่งข้อความเข้า LINE..."):
                        try:
                            db = get_connection()
                            with db.cursor() as cursor:
                                # SQL สำหรับอัปเดตสถานะเป็น 'Assigned' และบันทึกรหัสคนขับลงไป
                                sql_update = """
                                    UPDATE bookings 
                                    SET status = 'Assigned', driver_id = %s, dispatcher_id = %s 
                                    WHERE id = %s
                                """
                                # current_id คือ ID ของ Dispatcher/Admin ที่กำลังกดปุ่มนี้อยู่
                                cursor.execute(sql_update, (driver_id_to_assign, current_id, job_id_to_update))
                                db.commit()
                                
                            # ยิงข้อความแจ้งเตือนเข้า LINE Push API หาคนขับคนนั้นทันที
                            msg_to_line = (
                                f"🔔 มีงานใหม่เข้าครับ!\n"
                                f"📋 ใบงานที่: {job_id_to_update}\n"
                                f"👤 ลูกค้า: {selected_job_data['passenger_name']}\n"
                                f"📍 จุดรับ: {selected_job_data['pickup_location']}\n"
                                f"🏁 จุดส่ง: {selected_job_data['dropoff_location']}\n"
                                f"📅 เวลาเดินทาง: {selected_job_data['booking_time']}\n"
                                f"รบกวนตรวจสอบและเข้าหน้าเว็บเพื่อกดรับงานด้วยครับ"
                            )
                            send_line_message(msg_to_line, driver_id_to_assign)
                            
                            st.success(f"🎉 จ่ายงานใบงานที่ {job_id_to_update} ให้คนขับเรียบร้อย! อัปเดตคลาวด์และส่ง LINE แจ้งเตือนแล้ว")
                            st.rerun() # สั่งรีเฟรชหน้าจอทันทีเพื่ออัปเดตตัวเลขตาราง
                            
                        except Exception as e:
                            st.error(f"❌ เกิดข้อผิดพลาดระหว่างจ่ายงาน: {e}")
                        finally:
                            if 'db' in locals() and db.open:
                                db.close()
        else:
            st.success("✨ ยอดเยี่ยมมาก! ตอนนี้ไม่มีงานจองค้างสถานะ Pending (จ่ายงานครบหมดทุกใบแล้วครับ)")
    else:
        st.info("ℹ️ ปัจจุบันยังไม่มีประวัติการจองรถในฐานข้อมูลคลาวด์")

# หน้าที่ 4: Driver
elif "Driver" in choice:
    st.title("🚖 งานที่ได้รับมอบหมาย (Driver)")
    st.write("แสดงรายการงานจองรถทั้งหมดที่เจาะจงมอบหมายให้ไอดี LINE ของคนขับคนนี้")

# หน้าที่ 5: Airport Staff
elif "Airport Staff" in choice:
    st.title("✈️ ตรวจสอบสถานะรถ (Airport Staff)")
    st.write("หน้าตารางรายงานสำหรับพนักงานภาคพื้นสนามบิน เพื่อมอนิเตอร์ดูว่ารถจองกำลังเดินทางมาถึงในเวลาใดบ้าง")
