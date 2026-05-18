import streamlit as st
import pymysql
import pandas as pd
import requests
from datetime import datetime
import io
import datetime as dt_module

# --- 1. การตั้งค่าพื้นฐานและการเชื่อมต่อ DB ---
def get_connection():
    return pymysql.connect(
        host='mysql-22653bef-kla-e55d.c.aivencloud.com',
        user='avnadmin',
        password='AVNS_W4Huwc3abQww6NKNlG2',
        database='defaultdb',
        port=23986
    )

def send_line_message(message, target_id):
    token = 'X8ogM3D2GxzZ3z5EBMdOxWTa4BjTlqP1H/bYv+fwqLGNiKhhxuiPQR5bakcgXfEZBUPNDImDlvLrDMvtqN0/8XTlrcqfIvti2m2RpY/wrbQ9xl95HJd+slpzHCM9Vs5SxNS5e9gBG4MSE71UUNhXrQdB04t89/1O/w1cDnyilFU='
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    data = {'to': target_id, 'messages': [{'type': 'text', 'text': message}]}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            st.sidebar.error(f"⚠️ LINE API Error: {response.status_code} - {response.text}")
    except Exception as e:
        st.sidebar.error(f"❌ ระบบส่ง LINE ขัดข้อง: {e}")

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

# --- ระบบล็อกอินอัจฉริยะ (เวอร์ชันเสถียร ล็อก ID เข้าฐานข้อมูลตรงจุด) ---
query_params = st.query_params

if "default_user_id" not in st.session_state:
    st.session_state["default_user_id"] = "admin01"

if "user" in query_params:
    url_user = query_params["user"].strip()
    if st.session_state["default_user_id"] != url_user:
        st.session_state["default_user_id"] = url_user

st.sidebar.title("🔐 เข้าสู่ระบบ")

current_id = st.sidebar.text_input(
    "ระบุ LINE User ID", 
    value=st.session_state["default_user_id"]
).strip()

st.session_state["default_user_id"] = current_id

user_role = check_permission(current_id).strip().lower()
st.sidebar.info(f"สิทธิ์ของคุณคือ: {user_role}")

# --- 3. จัดการรายการเมนูฝั่งซ้ายตามระดับสิทธิ์ ---
menu_options = []
current_role = user_role.strip().lower()

if current_role == "admin":
    # เพิ่ม "👥 จัดการพนักงาน" เข้าไปต่อท้ายหรือแทรกกลางได้เลยครับ
    menu_options = ["🏠 Dashboard", "➕ Booker", "🖥️ Dispatcher", "👥 จัดการพนักงาน", "🚖 งานของฉัน (Driver)", "✈️ Airport Staff"]
elif current_role == "booker":
    menu_options = ["➕ Booker"]
elif current_role == "dispatcher":
    menu_options = ["🖥️ Dispatcher"]
elif current_role == "driver":
    menu_options = ["🚖 งานของฉัน (Driver)"]
elif current_role in ["airportstaff", "airport staff"]:
    menu_options = ["✈️ Airport Staff"]
else:
    st.warning("⚠️ คุณไม่มีสิทธิ์เข้าถึงระบบ หรือยังไม่ได้ระบุรหัส LINE User ID ที่ถูกต้องบนฐานข้อมูล")
    st.info(f"💡 รหัสที่ระบบตรวจพบตอนนี้คือ: `{current_id}` (ระดับสิทธิ์: `{user_role}`)")
    st.stop()

if "current_menu_choice" not in st.session_state or st.session_state["current_menu_choice"] not in menu_options:
    st.session_state["current_menu_choice"] = menu_options[0] if menu_options else ""

choice = st.sidebar.radio(
    "เมนูใช้งาน", 
    options=menu_options, 
    key="current_menu_choice"
)

# --- 4. การแสดงเนื้อหาไส้ในของแต่ละเมนูตามหน้าเลือก ---

# หน้าที่ 1: Dashboard
if "Dashboard" in choice:
    st.title("🏠 หน้าแรกและภาพรวมระบบ (Dashboard)")
    st.markdown(f"สวัสดีครับคุณกล้า สถานะการเชื่อมต่อคลาวด์ **Aiven MySQL ปกติดีเยี่ยม** ครับ")
    st.write("---")

    try:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM bookings WHERE status = 'Pending'")
            count_pending = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bookings WHERE status IN ('Assigned', 'Accepted')")
            count_active = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'driver'")
            count_drivers = cursor.fetchone()[0]
            
            # ปรับปรุง SQL หน้าแดชบอร์ดให้ดึงรหัส Voucher No มาโชว์ด้วย
            cursor.execute("SELECT id, voucher_no, passenger_name, pickup_location, dropoff_location, status FROM bookings ORDER BY id DESC LIMIT 5")
            recent_data = cursor.fetchall()
            
        df_recent = pd.DataFrame(recent_data, columns=['ใบงานที่', 'เลข Voucher', 'ชื่อผู้โดยสาร', 'จุดรับ', 'จุดส่ง', 'สถานะ'])
    except Exception as e:
        count_pending, count_active, count_drivers = 0, 0, 0
        df_recent = pd.DataFrame()
    finally:
        if 'db' in locals() and db.open:
            db.close()

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric(label="⏳ ใบงานรอจัดสรร (Pending)", value=count_pending, delta=f"{count_pending} งานค้าง", delta_color="inverse" if count_pending > 0 else "normal")
    with col_m2:
        st.metric(label="🚀 รถกำลังปฏิบัติงาน (Active)", value=count_active)
    with col_m3:
        st.metric(label="🚖 คนขับรถในระบบทั้งหมด", value=count_drivers)

    st.write("---")
    
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.write("### ⏱️ รายการจองรถล่าสุด 5 รายการ")
        if not df_recent.empty:
            st.dataframe(df_recent, use_container_width=True)
        else:
            st.info("ยังไม่มีประวัติการจองในระบบ")
            
    with col_right:
        st.write("### 💡 แนะนำการใช้งาน")
        st.info("คุณกล้าสามารถสลับบัญชีเพื่อทดสอบระบบได้:\n\n"
                "* **admin01** : จัดสรรงานและดูภาพรวมทั้งหมด\n"
                "* **driver01** : ดูงานของตัวเองและกดรับงาน\n"
                "* **driver02** : ดูงานของคนขับคนที่ 2")

# หน้าที่ 2: Booker (ฟังก์ชันรันระบบเลข Voucher อัตโนมัติ)
elif "Booker" in choice:
    st.title("📋 แบบฟอร์มจองรถ (Booker)")
    st.subheader("กรอกรายละเอียดการเดินทางเพื่อส่งงานให้ผู้จัดสรรรถ")

    with st.form(key="car_booking_form", clear_on_submit=True):
        st.write("### 🚗 ข้อมูลการเดินทาง")
        
        passenger_name = st.text_input("👤 ชื่อผู้โดยสาร / คณะเดินทาง", placeholder="เช่น คุณสมชาย สายลุย")
        locations = ["สนามบินสุวรรณภูมิ", "สนามบินดอนเมือง", "โรงแรมฮันซ่า", "ตัวเมืองกรุงเทพฯ", "พัทยา", "หัวหิน"]
        pickup_location = st.selectbox("📍 จุดรับ (Pickup)", options=locations)
        dropoff_location = st.selectbox("🏁 จุดส่ง (Dropoff)", options=locations)
        
        st.write("📅 วันและเวลาเดินทาง")
        col1, col2 = st.columns(2)
        with col1:
            booking_date = st.date_input("เลือกวันที่")
        with col2:
            booking_time_input = st.time_input("เลือกเวลา")
        
        combined_datetime = dt_module.datetime.combine(booking_date, booking_time_input)
        submit_button = st.form_submit_button("💾 บันทึกข้อมูลการจอง")

    if submit_button:
        if not passenger_name.strip():
            st.error("⚠️ กรุณากรอกชื่อผู้โดยสารก่อนกดบันทึกครับ")
        elif pickup_location == dropoff_location:
            st.error("⚠️ จุดรับและจุดส่งห้ามเป็นสถานที่เดียวกันครับ")
        else:
            with st.spinner("กำลังคำนวณรหัสและบันทึกข้อมูลลงระบบคลาวด์..."):
                try:
                    db = get_connection()
                    
                    # 🚀 คำนวณรันนิ่งนัมเบอร์อัตโนมัติ (ฟอร์แมต VC + ปีเดือนปัจจุบัน + 5หลัก)
                    now = dt_module.datetime.now()
                    year_month_str = now.strftime("%Y%m") # ผลลัพธ์: '202605'
                    
                    with db.cursor() as cursor:
                        # ค้นหาจำนวนงานของเดือนนี้เพื่อนำมาบวกต่อยอดเลขถัดไป
                        count_sql = "SELECT COUNT(*) FROM bookings WHERE voucher_no LIKE %s"
                        cursor.execute(count_sql, (f"VC{year_month_str}%",))
                        current_count = cursor.fetchone()[0]
                        
                        next_number = current_count + 1
                        running_no = str(next_number).zfill(5) # เติมศูนย์หน้าให้ครบ 5 หลัก
                        auto_voucher_no = f"VC{year_month_str}{running_no}" # ประกอบร่างเป็น 'VC20260500001'
                        
                        # บันทึกลงตารางฐานข้อมูลคลาวด์
                        sql = """
                            INSERT INTO bookings (voucher_no, passenger_name, pickup_location, dropoff_location, booking_time, status)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        val = (auto_voucher_no, passenger_name, pickup_location, dropoff_location, combined_datetime, 'Pending')
                        cursor.execute(sql, val)
                        db.commit()
                        
                    st.success(f"🎉 บันทึกการจองสำเร็จ! เลขใบงานของคุณคือ: **{auto_voucher_no}** ข้อมูลอัปเดตเรียลไทม์")
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาดระหว่างบันทึกข้อมูล: {e}")
                finally:
                    if 'db' in locals() and db.open:
                        db.close()

# หน้าที่ 3: Dispatcher
elif "Dispatcher" in choice:
    st.title("🖥️ หน้าจัดการงาน (Dispatcher)")
    st.subheader("📋 รายการจองรถทั้งหมดที่รอจัดสรรคนขับ")

    try:
        db = get_connection()
        with db.cursor() as cursor:
            # เพิ่มคอลัมน์ voucher_no เข้าไปใน SQL แสดงผล
            query_bookings = "SELECT id, voucher_no, passenger_name, pickup_location, dropoff_location, booking_time, status, driver_id FROM bookings ORDER BY booking_time DESC"
            cursor.execute(query_bookings)
            bookings_data = cursor.fetchall()
            
        columns = ['id', 'voucher_no', 'passenger_name', 'pickup_location', 'dropoff_location', 'booking_time', 'status', 'driver_id']
        df_bookings = pd.DataFrame(bookings_data, columns=columns)
        
        with db.cursor() as cursor:
            cursor.execute("SELECT line_user_id, name FROM users WHERE role = 'driver'")
            drivers_list = cursor.fetchall()
            
        driver_options = {f"🚖 {d[1]} ({d[0]})": d[0] for d in drivers_list}
        
    except Exception as e:
        st.error(f"❌ ไม่สามารถดึงข้อมูลจากฐานข้อมูลได้: {e}")
        df_bookings = pd.DataFrame()
        driver_options = {}
    finally:
        if 'db' in locals() and db.open:
            db.close()

    if not df_bookings.empty:
        st.write("### 📊 ตารางสถานะงานปัจจุบัน")
        st.dataframe(df_bookings, use_container_width=True)
        
        st.write("---")
        st.write("### 🎯 ฟังก์ชันการจ่ายงานให้คนขับ")
        
        pending_jobs = df_bookings[df_bookings['status'] == 'Pending']
        
        if not pending_jobs.empty:
            # ดึงเลขรหัส Voucher No มาสลักบนกล่อง Dropdown ให้เห็นเด่นชัด
            job_options = {
                f"🆔 {row['voucher_no']} | คุณ {row['passenger_name']} ({row['pickup_location']} ➡️ {row['dropoff_location']})": row['id']
                for _, row in pending_jobs.iterrows()
            }
            
            col_job, col_drv, col_btn = st.columns([2, 1, 1])
            
            with col_job:
                selected_job_text = st.selectbox("1️⃣ เลือกใบงานที่ต้องการจัดสรร", options=list(job_options.keys()))
                job_id_to_update = job_options[selected_job_text]
                selected_job_data = pending_jobs[pending_jobs['id'] == job_id_to_update].iloc[0]
            
            with col_drv:
                if driver_options:
                    selected_driver_text = st.selectbox("2️⃣ เลือกคนขับรถที่จะส่งงาน", options=list(driver_options.keys()))
                    driver_id_to_assign = driver_options[selected_driver_text]
                else:
                    st.warning("⚠️ ไม่มีรายชื่อคนขับในระบบ")
                    driver_id_to_assign = None
                    
            with col_btn:
                st.write(" ")
                st.write(" ")
                btn_assign = st.button("🚀 กดจ่ายงานและส่ง LINE")
                
            if btn_assign:
                if not driver_id_to_assign:
                    st.error("❌ ไม่สามารถจ่ายงานได้ เนื่องจากไม่ได้เลือกคนขับรถครับ")
                else:
                    with st.spinner("กำลังอัปเดตสถานะงานและส่งข้อความเข้า LINE..."):
                        try:
                            db = get_connection()
                            with db.cursor() as cursor:
                                sql_update = """
                                    UPDATE bookings 
                                    SET status = 'Assigned', driver_id = %s, dispatcher_id = %s 
                                    WHERE id = %s
                                """
                                cursor.execute(sql_update, (driver_id_to_assign, current_id, job_id_to_update))
                                db.commit()
                                
                            # แนบข้อมูลเลขรหัส Voucher อัตโนมัติส่งแจ้งเตือนเข้าแอป LINE ไปหาคนขับรถ
                            msg_to_line = (
                                f"🔔 มีงานใหม่เข้าครับ!\n"
                                f"🎫 Voucher No: {selected_job_data['voucher_no']}\n"
                                f"👤 ลูกค้า: {selected_job_data['passenger_name']}\n"
                                f"📍 จุดรับ: {selected_job_data['pickup_location']}\n"
                                f"🏁 จุดส่ง: {selected_job_data['dropoff_location']}\n"
                                f"📅 เวลาเดินทาง: {selected_job_data['booking_time']}\n"
                                f"รบกวนตรวจสอบและเข้าหน้าเว็บเพื่อกดรับงานด้วยครับ"
                            )
                            send_line_message(msg_to_line, driver_id_to_assign)
                            
                            st.success(f"🎉 จ่ายงานใบงาน {selected_job_data['voucher_no']} เรียบร้อย! ส่งแจ้งเตือน LINE เรียบร้อย")
                            st.rerun()
                            
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
    st.subheader(f"👤 รหัสคนขับออนไลน์: {current_id}")

    try:
        db = get_connection()
        with db.cursor() as cursor:
            # เพิ่มคอลัมน์ voucher_no เข้าไปในตารางงานคนขับ
            query_driver = """
                SELECT id, voucher_no, passenger_name, pickup_location, dropoff_location, booking_time, status 
                FROM bookings 
                WHERE driver_id = %s 
                ORDER BY booking_time DESC
            """
            cursor.execute(query_driver, (current_id,))
            driver_jobs = cursor.fetchall()
            
        columns = ['id', 'voucher_no', 'passenger_name', 'pickup_location', 'dropoff_location', 'booking_time', 'status']
        df_driver = pd.DataFrame(driver_jobs, columns=columns)
        
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อข้อมูลคนขับ: {e}")
        df_driver = pd.DataFrame()
    finally:
        if 'db' in locals() and db.open:
            db.close()

    if not df_driver.empty:
        st.write("### 📊 ตารางรายการงานจองของคุณในระบบ")
        st.dataframe(df_driver, use_container_width=True)
        
        st.write("---")
        
        assigned_jobs = df_driver[df_driver['status'] == 'Assigned']
        
        if not assigned_jobs.empty:
            st.write("### 📥 มีใบงานใหม่รอคุณกดรับทราบ")
            
            driver_job_options = {
                f"🎫 {row['voucher_no']} | คุณ {row['passenger_name']} ({row['pickup_location']} ➡️ {row['dropoff_location']})": row['id']
                for _, row in assigned_jobs.iterrows()
            }
            
            col_select_job, col_btn_accept = st.columns([3, 1])
            
            with col_select_job:
                selected_driver_job = st.selectbox("เลือกใบงานที่ต้องการกดรับ", options=list(driver_job_options.keys()))
                job_id_to_accept = driver_job_options[selected_driver_job]
                
            with col_btn_accept:
                st.write(" ")
                st.write(" ")
                btn_accept_job = st.button("✅ กดรับทราบและยอมรับงาน")
                
            # --- ส่วนที่ 3: กระบวนการหลังกดปุ่มรับงาน (เวอร์ชันยิง LINE กลับหาแอดมิน) ---
            if btn_accept_job:
                with st.spinner("กำลังอัปเดตสถานะรับงานและแจ้งเตือนแอดมิน..."):
                    try:
                        db = get_connection()
                        with db.cursor() as cursor:
                            # 1. ก่อนจะอัปเดต ขอแอบดึงเลข Voucher และรหัส dispatcher_id ผู้จ่ายงานออกมาก่อน
                            info_sql = "SELECT voucher_no, dispatcher_id, passenger_name FROM bookings WHERE id = %s"
                            cursor.execute(info_sql, (job_id_to_accept,))
                            job_info = cursor.fetchone()
                            
                            v_no = job_info[0] if job_info else "ไม่ระบุ"
                            disp_id = job_info[1] if job_info else None
                            p_name = job_info[2] if job_info else "ไม่ระบุ"

                            # 2. สั่งอัปเดตสถานะในตาราง bookings จาก 'Assigned' ให้กลายเป็น 'Accepted'
                            sql_accept = "UPDATE bookings SET status = 'Accepted' WHERE id = %s"
                            cursor.execute(sql_accept, (job_id_to_accept,))
                            db.commit()
                            
                            # 3. ถ้างานนี้มีรหัสแอดมินผู้จ่ายงานผูกอยู่ ให้ส่ง LINE เด้งกลับไปบอกเขาทันที!
                            if disp_id:
                                msg_back_to_admin = (
                                    f"✅ คนขับกดรับงานแล้วครับ!\n"
                                    f"🎫 เลข Voucher: {v_no}\n"
                                    f"👤 ลูกค้า: {p_name}\n"
                                    f"🚖 พนักงานขับรถ: {current_id} ได้กดรับทราบและกำลังเตรียมออกปฏิบัติงานครับ"
                                )
                                send_line_message(msg_back_to_admin, disp_id)
                            
                        st.success(f"🎉 คุณได้รับทราบและยอมรับใบงานเรียบร้อย! ระบบส่งสัญญาณแจ้งเตือนเข้า LINE แอดมินผู้จ่ายงานแล้ว")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ ไม่สามารถเปลี่ยนสถานะงานได้: {e}")
                    finally:
                        if 'db' in locals() and db.open:
                            db.close()
        else:
            st.success("✨ ยอดเยี่ยม! คุณได้กดรับทราบงานจองค้างหมดเรียบร้อยแล้ว ไม่มีงานใหม่ตกค้างครับ")
    else:
        st.info("ℹ️ ปัจจุบันยังไม่มีประวัติหรือใบงานจองรถที่ระบุส่งให้รหัสคนขับคนนี้ในฐานข้อมูล")

# หน้าที่ 5: Airport Staff
elif "Airport Staff" in choice:
    st.title("✈️ ตรวจสอบสถานะรถ (Airport Staff)")
    st.subheader("📋 ตารางมอนิเตอร์รถยนต์และคนขับที่กำลังปฏิบัติงาน")

    try:
        db = get_connection()
        with db.cursor() as cursor:
            # ดึงรหัสคอลัมน์ b.voucher_no ขึ้นตารางเพื่อให้แผนกสนามบินตรวจสอบรหัสรถ
            query_airport = """
                SELECT 
                    b.id AS 'ใบงานที่',
                    b.voucher_no AS 'เลข Voucher',
                    b.passenger_name AS 'ชื่อผู้โดยสาร',
                    b.pickup_location AS 'จุดรับ',
                    b.dropoff_location AS 'จุดส่ง',
                    b.booking_time AS 'เวลาเดินทาง',
                    b.status AS 'สถานะงาน',
                    u.name AS 'คนขับรถที่รับงาน'
                FROM bookings b
                LEFT JOIN users u ON b.driver_id = u.line_user_id
                WHERE b.status IN ('Assigned', 'Accepted')
                ORDER BY b.booking_time ASC
            """
            cursor.execute(query_airport)
            airport_data = cursor.fetchall()

        columns = ['ใบงานที่', 'เลข Voucher', 'ชื่อผู้โดยสาร', 'จุดรับ', 'จุดส่ง', 'เวลาเดินทาง', 'สถานะงาน', 'คนขับรถที่รับงาน']
        df_airport = pd.DataFrame(airport_data, columns=columns)

    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการดึงข้อมูลสำหรับพนักงานสนามบิน: {e}")
        df_airport = pd.DataFrame()
    finally:
        if 'db' in locals() and db.open:
            db.close()

    if not df_airport.empty:
        st.write("✨ แสดงเฉพาะงานที่มีการจัดสรรคนขับแล้ว เพื่อเตรียมความพร้อมภาคพื้นสนามบิน")
        
        def highlight_status(val):
            if val == 'Accepted':
                return 'background-color: #d4edda; color: #155724; font-weight: bold;'
            elif val == 'Assigned':
                return 'background-color: #fff3cd; color: #856404;'
            return ''

        st.dataframe(df_airport.style.map(highlight_status, subset=['สถานะงาน']), use_container_width=True)
        
        st.write("---")
        col_metrics1, col_metrics2 = st.columns(2)
        with col_metrics1:
            st.metric(label="🚖 จำนวนรถที่กำลังเดินทาง (Assigned)", value=len(df_airport[df_airport['สถานะงาน'] == 'Assigned']))
        with col_metrics2:
            st.metric(label="✅ จำนวนรถที่คนขับกดรับงานแล้ว (Accepted)", value=len(df_airport[df_airport['สถานะงาน'] == 'Accepted']))
            
    else:
        st.info("ℹ️ ปัจจุบันยังไม่มีรถยนต์คันไหนกำลังเดินทางมาสนามบิน (ไม่มีงานค้างในสถานะ Assigned หรือ Accepted)")
# --- หน้าที่ 6: เมนูพิเศษสำหรับ Admin จัดการพนักงาน ---
elif "จัดการพนักงาน" in choice:
    st.title("👥 ระบบจัดการสิทธิ์ผู้ใช้งาน (User Management)")
    st.write("---")
    
    with st.form("user_management_form"):
        st.write("📝 ลงทะเบียนและกำหนดสิทธิ์พนักงานใหม่")
        new_line_id = st.text_input("ระบุ LINE User ID").strip()
        new_name = st.text_input("ระบุชื่อ-นามสกุล พนักงาน").strip()
        new_role = st.selectbox(
            "กำหนดตำแหน่ง (Role)", 
            ["admin", "booker", "dispatcher", "driver", "airportstaff"]
        )
        
        submit_user = st.form_submit_button("💾 บันทึกสิทธิ์เข้าระบบ")
        
        if submit_user:
            if new_line_id and new_name:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    sql = """
                        INSERT INTO users (line_user_id, name, role) 
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE name = %s, role = %s
                    """
                    cursor.execute(sql, (new_line_id, new_name, new_role, new_name, new_role))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    st.success(f"🎉 บันทึกสิทธิ์คุณ {new_name} เป็น {new_role} เรียบร้อยแล้ว!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาดทางฐานข้อมูล: {e}")
            else:
                st.warning("⚠️ รบกวนกรอก LINE ID และชื่อพนักงานให้ครบถ้วนครับ")
                
# 💡 [โค้ดเสริมเพิ่มความโปร] ดึงตารางรายชื่อพนักงานทั้งหมดในระบบมาโชว์ให้ Admin ตรวจสอบ
    st.write("---")
    st.write("### 📋 รายชื่อพนักงานและระดับสิทธิ์ปัจจุบันในคลาวด์")
    
    try:
        db = get_connection()
        with db.cursor() as cursor:
            # ดึงข้อมูลพนักงานทั้งหมดเรียงตามตำแหน่ง
            cursor.execute("SELECT line_user_id, name, role FROM users ORDER BY role ASC")
            users_data = cursor.fetchall()
            
        columns_users = ['รหัส LINE User ID', 'ชื่อ-นามสกุล พนักงาน', 'ตำแหน่ง (Role)']
        df_users = pd.DataFrame(users_data, columns=columns_users)
        
        if not df_users.empty:
            st.dataframe(df_users, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลผู้ใช้งานในระบบ")
            
    except Exception as e:
        st.error(f"❌ ไม่สามารถดึงตารางรายชื่อพนักงานได้: {e}")
    finally:
        if 'db' in locals() and db.open:
            db.close()                
