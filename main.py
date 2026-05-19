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

# --- 2. ระบบเช็คสิทธิ์ผู้ใช้งาน (เวอร์ชัน Auto-Insert พนักงานใหม่) ---
def check_permission(user_id):
    if not user_id or user_id == "admin01":  # ข้ามไอดีทดสอบพิเศษ
        return "admin"
        
    try:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT role FROM users WHERE line_user_id = %s", (user_id,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            else:
                insert_sql = """
                    INSERT INTO users (line_user_id, name, role) 
                    VALUES (%s, %s, %s)
                """
                cursor.execute(insert_sql, (user_id, f"พนักงานใหม่ ({user_id[:6]}...)", "guest"))
                db.commit()
                return "guest"
    except Exception as e:
        return "Guest"
    finally:
        if 'db' in locals() and db.open:
            db.close()

st.set_page_config(page_title="ระบบจัดการรถ Multi-Role", layout="wide")

# 🚀 [เวอร์ชันกระชับ Micro-Font] สคริปต์สยบบั๊กหน้าจอมือถือและแก้ปัญหา Font ใหญ่ล้นจอ
st.markdown("""
    <style>
    /* บีบหัวข้อหลักของแต่ละหน้าจอให้เล็กลงพอดีกับความกว้างมือถือแถวเดียว */
    h1 {
        font-size: 1.4rem !important;
        padding-top: 0.3rem !important;
        padding-bottom: 0.3rem !important;
        line-height: 1.1 !important;
    }
    /* บีบหัวข้อรองและตัวหนังสือสรุปสถิติเล็กลงตามสัดส่วน */
    h2, h3, .stSubheader {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
    }
    /* บีบขนาดฟอนต์ในฟอร์มกรอกข้อมูลและปุ่ม dropdown */
    div[data-baseweb="select"], input, label {
        font-size: 0.9rem !important;
    }
    /* จัดระยะช่องไฟด้านบนสุดของแอปไม่ให้ลอยชนขอบและไม่โดนบดบัง */
    .block-container {
        padding-top: 3.2rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    /* บังคับให้ตาราง Pandas และ DataFrame บนมือถือตัวหนังสือเล็กกระชับอ่านง่าย */
    .stDataFrame table {
        font-size: 0.8rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

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
    st.markdown(f"สวัสดีครับคุณกล้า สถานะการเชื่อมต่อ **ระบบปกติดีเยี่ยม** ครับ")
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
            # 🌟 จุดปรับปรุงที่ 1: ซ่อนดัชนีตัวเลขหน้าแดชบอร์ด
            st.dataframe(df_recent, use_container_width=True, hide_index=True)
        else:
            st.info("ยังไม่มีประวัติการจองในระบบ")
            
    with col_right:
        st.write("### 💡 แนะนำการใช้งาน")
        st.info("คุณกล้าสามารถสลับบัญชีเพื่อทดสอบระบบได้:\n\n"
                "* **admin01** : จัดสรรงานและดูภาพรวมทั้งหมด\n"
                "* **driver01** : ดูงานของตัวเองและกดรับงาน\n"
                "* **driver02** : ดูงานของคนขับคนที่ 2")

# หน้าที่ 2: Booker
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
                    now = dt_module.datetime.now()
                    year_month_str = now.strftime("%Y%m")
                    
                    with db.cursor() as cursor:
                        count_sql = "SELECT COUNT(*) FROM bookings WHERE voucher_no LIKE %s"
                        cursor.execute(count_sql, (f"VC{year_month_str}%",))
                        current_count = cursor.fetchone()[0]
                        
                        next_number = current_count + 1
                        running_no = str(next_number).zfill(5)
                        auto_voucher_no = f"VC{year_month_str}{running_no}"
                        
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

    # ✅ สั่งโชว์ตารางแบบล้ำ ๆ: ซ่อน Index ของเว็บ และ ซ่อนคอลัมน์ id ไม่ให้คนเห็น แต่หลังบ้านยังทำงานได้!
    if not df_bookings.empty:
        st.write("### 📊 ตารางสถานะงานปัจจุบัน")
        st.dataframe(
            df_bookings, 
            use_container_width=True, 
            hide_index=True,
            column_config={"id": None}  # 🚀 ไฮไลต์เด็ด: สั่งให้ Streamlit ซ่อนคอลัมน์ id ไม่ต้องโชว์บนจอ!
        )
        st.write("---")
        
        col_left_side, col_right_side = st.columns([1, 1])
        
        with col_left_side:
            st.write("### 🎯 ฟังก์ชันการจ่ายงานให้คนขับ")
            pending_jobs = df_bookings[df_bookings['status'] == 'Pending']
            
            if not pending_jobs.empty:
                job_options = {
                    f"🆔 {row['voucher_no']} | คุณ {row['passenger_name']}": row['id']
                    for _, row in pending_jobs.iterrows()
                }
                
                selected_job_text = st.selectbox("1️⃣ เลือกใบงานที่ต้องการจัดสรร", options=list(job_options.keys()), key="sb_assign")
                job_id_to_update = job_options[selected_job_text]
                selected_job_data = pending_jobs[pending_jobs['id'] == job_id_to_update].iloc[0]
                
                if driver_options:
                    selected_driver_text = st.selectbox("2️⃣ เลือกคนขับรถที่จะส่งงาน", options=list(driver_options.keys()), key="sb_drv_assign")
                    driver_id_to_assign = driver_options[selected_driver_text]
                else:
                    st.warning("⚠️ ไม่มีรายชื่อคนขับในระบบ")
                    driver_id_to_assign = None
                    
                btn_assign = st.button("🚀 กดจ่ายงานและส่ง LINE")
                
                if btn_assign and driver_id_to_assign:
                    with st.spinner("กำลังจ่ายงาน..."):
                        try:
                            db = get_connection()
                            with db.cursor() as cursor:
                                sql_update = "UPDATE bookings SET status = 'Assigned', driver_id = %s, dispatcher_id = %s WHERE id = %s"
                                cursor.execute(sql_update, (driver_id_to_assign, current_id, job_id_to_update))
                                db.commit()
                                
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
                            st.success(f"🎉 จ่ายงาน {selected_job_data['voucher_no']} สำเร็จ!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"เกิดข้อผิดพลาด: {e}")
                        finally:
                            if 'db' in locals() and db.open:
                                db.close()
            else:
                st.success("✨ ยอดเยี่ยมมาก! จ่ายงานค้างครบหมดทุกใบแล้วครับ")
                
        with col_right_side:
            st.write("### 🏁 ฟังก์ชันการปิดงาน (Completed)")
            active_jobs = df_bookings[df_bookings['status'] == 'Accepted']
            
            if not active_jobs.empty:
                complete_job_options = {
                    f"✅ {row['voucher_no']} | คุณ {row['passenger_name']}" : row['id']
                    for _, row in active_jobs.iterrows()
                }
                
                selected_complete_text = st.selectbox("🎯 เลือกใบงานที่ส่งผู้โดยสารเรียบร้อยแล้ว", options=list(complete_job_options.keys()), key="sb_complete")
                job_id_to_complete = complete_job_options[selected_complete_text]
                selected_complete_data = active_jobs[active_jobs['id'] == job_id_to_complete].iloc[0]
                
                btn_complete = st.button("🏁 ยืนยันปิดงานเสร็จสิ้น (Completed)")
                
                if btn_complete:
                    with st.spinner("กำลังบันทึกสถานะจบงาน..."):
                        try:
                            db = get_connection()
                            with db.cursor() as cursor:
                                sql_complete = "UPDATE bookings SET status = 'Completed' WHERE id = %s"
                                cursor.execute(sql_complete, (job_id_to_complete,))
                                db.commit()
                                
                            if selected_complete_data['driver_id']:
                                msg_to_driver_complete = (
                                    f"🏁 แอดมินปิดงานให้เรียบร้อยครับ!\n"
                                    f"🎫 เลข Voucher: {selected_complete_data['voucher_no']}\n"
                                    f"👤 ลูกค้า: {selected_complete_data['passenger_name']}\n"
                                    f"ระบบบันทึกผลงานลงประวัติเรียบร้อย ขอบคุณมากครับ"
                                )
                                send_line_message(msg_to_driver_complete, selected_complete_data['driver_id'])
                                
                            st.success(f"🎉 ปิดใบงาน {selected_complete_data['voucher_no']} เสร็จสมบูรณ์!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"เกิดข้อผิดพลาด: {e}")
                        finally:
                            if 'db' in locals() and db.open:
                                db.close()
            else:
                st.info("ℹ️ ปัจจุบันไม่มีรถที่กำลังวิ่งงานในระบบ")
    else:
        st.info("ℹ️ ปัจจุบันยังไม่มีประวัติการจองรถในฐานข้อมูลคลาวด์")

# หน้าที่ 4: Driver
elif "Driver" in choice:
    st.title("🚖 งานที่ได้รับมอบหมาย (Driver)")
    
    driver_name = "ไม่ระบุชื่อ"
    try:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT name FROM users WHERE line_user_id = %s", (current_id,))
            user_res = cursor.fetchone()
            if user_res:
                driver_name = user_res[0]
    except Exception as e:
        pass
    finally:
        if 'db' in locals() and db.open:
            db.close()

    st.subheader(f"👋 สวัสดีครับ: {driver_name}")

    try:
        db = get_connection()
        with db.cursor() as cursor:
            query_current = """
                SELECT id, voucher_no, passenger_name, pickup_location, dropoff_location, booking_time, status 
                FROM bookings 
                WHERE driver_id = %s AND status IN ('Assigned', 'Accepted')
                ORDER BY booking_time ASC
            """
            cursor.execute(query_current, (current_id,))
            current_jobs = cursor.fetchall()
            
            query_history = """
                SELECT id, voucher_no, passenger_name, pickup_location, dropoff_location, booking_time, status 
                FROM bookings 
                WHERE driver_id = %s AND status = 'Completed'
                ORDER BY booking_time DESC LIMIT 30
            """
            cursor.execute(query_history, (current_id,))
            history_jobs = cursor.fetchall()
            
        columns = ['id', 'voucher_no', 'passenger_name', 'pickup_location', 'dropoff_location', 'booking_time', 'status']
        df_driver_current = pd.DataFrame(current_jobs, columns=columns)
        df_driver_history = pd.DataFrame(history_jobs, columns=columns)
        
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อข้อมูลคนขับ: {e}")
        df_driver_current = pd.DataFrame()
        df_driver_history = pd.DataFrame()
    finally:
        if 'db' in locals() and db.open:
            db.close()

    st.write("---")
    st.write("### 📥 รายการงานปัจจุบันที่ต้องปฏิบัติ")
    if not df_driver_current.empty:
        # 🌟 จุดปรับปรุงที่ 3: ซ่อนดัชนีตัวเลขในตารางงานปัจจุบันของคนขับ
        st.dataframe(df_driver_current, use_container_width=True, hide_index=True)
        
        assigned_jobs = df_driver_current[df_driver_current['status'] == 'Assigned']
        if not assigned_jobs.empty:
            st.write("### 📥 มีใบงานใหม่รอคุณกดรับทราบ")
            driver_job_options = {
                f"🎫 {row['voucher_no']} | คุณ {row['passenger_name']}": row['id']
                for _, row in assigned_jobs.iterrows()
            }
            col_select_job, col_btn_accept = st.columns([1, 1])
            with col_select_job:
                selected_driver_job = st.selectbox("เลือกใบงานที่ต้องการกดรับ", options=list(driver_job_options.keys()))
                job_id_to_accept = driver_job_options[selected_driver_job]
            with col_btn_accept:
                st.write(" ")
                btn_accept_job = st.button("✅ กดรับทราบและยอมรับงาน")
                
            if btn_accept_job:
                with st.spinner("กำลังอัปเดตสถานะ..."):
                    try:
                        db = get_connection()
                        with db.cursor() as cursor:
                            info_sql = "SELECT voucher_no, dispatcher_id, passenger_name FROM bookings WHERE id = %s"
                            cursor.execute(info_sql, (job_id_to_accept,))
                            job_info = cursor.fetchone()
                            v_no = job_info[0] if job_info else "ไม่ระบุ"
                            disp_id = job_info[1] if job_info else None
                            p_name = job_info[2] if job_info else "ไม่ระบุ"

                            sql_accept = "UPDATE bookings SET status = 'Accepted' WHERE id = %s"
                            cursor.execute(sql_accept, (job_id_to_accept,))
                            db.commit()
                            
                            if disp_id:
                                msg_back_to_admin = (
                                    f"✅ คนขับกดรับงานแล้วครับ!\n"
                                    f"🎫 เลข Voucher: {v_no}\n"
                                    f"👤 ลูกค้า: {p_name}\n"
                                    f"🚖 พนักงานขับรถ: {driver_name} ได้กดรับทราบแล้ว"
                                )
                                send_line_message(msg_back_to_admin, disp_id)
                        st.success(f"🎉 คุณได้รับทราบและยอมรับใบงานเรียบร้อย!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ ไม่สามารถเปลี่ยนสถานะงานได้: {e}")
                    finally:
                        if 'db' in locals() and db.open:
                            db.close()
    else:
        st.success("✨ ไม่มีงานปัจจุบันค้างอยู่")

    st.write("---")
    st.write("### ✅ ประวัติการวิ่งงานที่เสร็จสิ้นแล้ว (Completed)")
    if not df_driver_history.empty:
        st.info(f"💡 เดือนนี้คุณวิ่งงานเสร็จสิ้นไปแล้วทั้งหมด **{len(df_driver_history)}** ใบงาน")
        # 🌟 จุดปรับปรุงที่ 4: ซ่อนดัชนีตัวเลขในตารางประวัติงานเก่าของคนขับ
        st.dataframe(df_driver_history, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ ยังไม่มีประวัติงานที่บันทึกสถานะเสร็จสิ้น")

# หน้าที่ 5: Airport Staff
elif "Airport Staff" in choice:
    st.title("✈️ ตรวจสอบสถานะรถ (Airport Staff)")
    st.subheader("📋 ตารางมอนิเตอร์รถยนต์และคนขับที่กำลังปฏิบัติงาน")

    try:
        db = get_connection()
        with db.cursor() as cursor:
            query_airport = """
                SELECT 
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

        columns = ['เลข Voucher', 'ชื่อผู้โดยสาร', 'จุดรับ', 'จุดส่ง', 'เวลาเดินทาง', 'สถานะงาน', 'คนขับรถที่รับงาน']
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

        # 🌟 จุดปรับปรุงที่ 5: ซ่อนดัชนีตัวเลขในตารางมอนิเตอร์พนักงานภาคพื้นสนามบิน
        st.dataframe(df_airport.style.map(highlight_status, subset=['สถานะงาน']), use_container_width=True, hide_index=True)
        
        st.write("---")
        col_metrics1, col_metrics2 = st.columns(2)
        with col_metrics1:
            st.metric(label="🚖 จำนวนรถที่กำลังเดินทาง (Assigned)", value=len(df_airport[df_airport['สถานะงาน'] == 'Assigned']))
        with col_metrics2:
            st.metric(label="✅ จำนวนรถที่คนขับกดรับงานแล้ว (Accepted)", value=len(df_airport[df_airport['สถานะงาน'] == 'Accepted']))
            
    else:
        st.info("ℹ️ ปัจจุบันยังไม่มีรถยนต์คันไหนกำลังเดินทางมาสนามบิน")

# --- หน้าที่ 6: เมนูพิเศษสำหรับ Admin จัดการพนักงาน (เวอร์ชันอัปเกรด แก้ไข/ลบ/ระงับสิทธิ์) ---
elif "จัดการพนักงาน" in choice:
    st.title("👥 ระบบจัดการสิทธิ์ผู้ใช้งาน (User Management)")
    st.write("---")
    
    # 🌟 1. ดึงตารางพนักงานใหม่ที่รออนุมัติสิทธิ์มาโชว์ก่อน
    st.write("### ⏳ รายชื่อพนักงานใหม่ที่รออนุมัติสิทธิ์ (Guests)")
    try:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT line_user_id, name, role FROM users WHERE role = 'guest'")
            guests_data = cursor.fetchall()
        
        if guests_data:
            df_guests = pd.DataFrame(guests_data, columns=['รหัส LINE User ID', 'ชื่อชั่วคราว', 'สถานะ'])
            st.dataframe(df_guests, use_container_width=True, hide_index=True)
            st.info("💡 คุณกล้าสามารถก๊อปปี้รหัส LINE ID จากตารางด้านบนมาวางเพื่ออัปเดตสิทธิ์ได้ครับ")
        else:
            st.success("✨ เรียบร้อยดี! ไม่มีพนักงานใหม่ค้างรออนุมัติสิทธิ์ในระบบครับ")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล Guest: {e}")
    finally:
        if 'db' in locals() and db.open:
            db.close()

    st.write("---")
    
    # 🌟 2. ดึงรายชื่อพนักงานทั้งหมดมาทำ Dropdown เพื่อเลือก "แก้ไข หรือ ลบ"
    try:
        db = get_connection()
        with db.cursor() as cursor:
            # ดึงมาทั้งหมดเพื่อทำระบบเลือกจัดการข้อมูลพนักงานเก่า
            cursor.execute("SELECT line_user_id, name, role, status FROM users")
            all_users = cursor.fetchall()
        user_list_options = {f"👤 {u[1]} ({u[2].upper()}) - [{u[3]}]": u for u in all_users}
    except Exception as e:
        user_list_options = {}
    finally:
        if 'db' in locals() and db.open:
            db.close()

    # 🏢 แบ่งสัดส่วนฟอร์มควบคุม (ซ้าย: ฟอร์มจัดการ/อัปเดตข้อมูล | ขวา: ฟอร์มสั่งลบ)
    col_form_edit, col_form_del = st.columns([2, 1])

    with col_form_edit:
        with st.form("user_management_form"):
            st.write("📝 **ฟอร์มลงทะเบียน / แก้ไข และ ปรับสถานะพนักงาน**")
            
            # ช้อยส์เสริม: ถ้าจะแก้ไขคนเก่าให้เลือกจากกล่อง หากจะเพิ่มคนใหม่ให้เลือก "➕ เพิ่ม/บันทึกด้วยแมนนวล"
            select_user_action = st.selectbox(
                "💡 เลือกพนักงานที่ต้องการแก้ไข (หรือกรอกรหัสเองด้านล่าง)", 
                options=["➕ ลงทะเบียนพนักงานใหม่ / กรอกเอง"] + list(user_list_options.keys())
            )
            
            # ค่าตั้งต้นในช่องพิมพ์
            init_id = ""
            init_name = ""
            init_role = "driver"
            init_status = "Active"
            
            # ถ้าเลือกคนขับคนเดิม ดึงค่าเก่ามาสลักลงกล่องพิมพ์ทันทีออโต้!
            if select_user_action != "➕ ลงทะเบียนพนักงานใหม่ / กรอกเอง":
                user_data = user_list_options[select_user_action]
                init_id = user_data[0]
                init_name = user_data[1]
                init_role = user_data[2].lower()
                # เช็กกรณีค่า status เก่าในเบสเป็น NULL ให้ตั้งเป็น Active
                init_status = user_data[3] if user_data[3] else "Active"

            new_line_id = st.text_input("ระบุ LINE User ID", value=init_id).strip()
            new_name = st.text_input("ระบุชื่อ-นามสกุลจริง ของพนักงาน", value=init_name).strip()
            
            roles_pool = ["admin", "booker", "dispatcher", "driver", "airportstaff", "guest"]
            new_role = st.selectbox("กำหนดตำแหน่ง (Role)", roles_pool, index=roles_pool.index(init_role) if init_role in roles_pool else 3)
            
            # 🚀 [เพิ่มใหม่] ปุ่มเลือกสถานะพนักงานใช้งาน Active / Inactive
            status_pool = ["Active", "Inactive"]
            new_status = st.radio("🚦 สถานะการใช้งานระบบ", status_pool, index=status_pool.index(init_status) if init_status in status_pool else 0, horizontal=True)
            
            submit_user = st.form_submit_button("💾 อนุมัติและบันทึกสิทธิ์")
            
            if submit_user:
                if new_line_id and new_name:
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        
                        # อัปเดตข้อมูลทับตัวเดิม พร้อมบันทึกคอลัมน์ status
                        sql = """
                            INSERT INTO users (line_user_id, name, role, status) 
                            VALUES (%s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE name = %s, role = %s, status = %s
                        """
                        cursor.execute(sql, (new_line_id, new_name, new_role, new_status, new_name, new_role, new_status))
                        conn.commit()
                        cursor.close()
                        conn.close()
                        
                        st.success(f"🎉 บันทึกข้อมูลและอัปเดตสถานะพนักงานเรียบร้อยแล้ว!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ เกิดข้อผิดพลาดทางฐานข้อมูล: {e}")
                else:
                    st.warning("⚠️ รบกวนกรอก LINE ID และชื่อพนักงานให้ครบถ้วนครับ")

    with col_form_del:
        with st.form("user_delete_form"):
            st.write("❌ **โซนอันตราย: ลบพนักงานออกจากระบบ**")
            user_to_delete = st.selectbox("เลือกรายชื่อที่จะลบทิ้งเด็ดขาด", options=list(user_list_options.keys()))
            confirm_delete = st.checkbox("⚠️ ยืนยันว่าต้องการลบข้อมูลพนักงานคนนี้จริง ๆ")
            
            btn_delete = st.form_submit_button("🗑️ ลบพนักงานออกถาวร")
            
            if btn_delete:
                if confirm_delete and user_to_delete:
                    target_del_id = user_list_options[user_to_delete][0]
                    target_del_name = user_list_options[user_to_delete][1]
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM users WHERE line_user_id = %s", (target_del_id,))
                        conn.commit()
                        cursor.close()
                        conn.close()
                        
                        st.success(f"🗑️ ลบพนักงานคุณ {target_del_name} ออกจากระบบคลาวด์เรียบร้อย!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"ไม่สามารถลบพนักงานได้: {e}")
                else:
                    st.warning("⚠️ โปรดติ๊กเครื่องหมายถูกเพื่อยืนยันก่อนกดปุ่มลบครับ")

    st.write("---")
    
    # 🌟 3. ตารางแสดงรายชื่อพนักงานทั้งหมดปัจจุบัน (เพิ่มคอลัมน์สถานะโชว์ด้วย)
    st.write("### 📋 รายชื่อพนักงานและระดับสิทธิ์ปัจจุบันในคลาวด์")
    try:
        db = get_connection()
        with db.cursor() as cursor:
            # แก้ไขสคริปต์ให้ดึงข้อมูลคอลัมน์ status ขึ้นมาโชว์บนตารางด้วย
            cursor.execute("SELECT line_user_id, name, role, status FROM users ORDER BY role ASC")
            users_data = cursor.fetchall()
            
        columns_users = ['รหัส LINE User ID', 'ชื่อ-นามสกุล พนักงาน', 'ตำแหน่ง (Role)', 'สถานะการใช้งาน']
        df_users = pd.DataFrame(users_data, columns=columns_users)
        
        if not df_users.empty:
            # ซ่อนคอลัมน์ Index สวยงามตามสูตรเดิมของคุณกล้า
            st.dataframe(df_users, use_container_width=True, hide_index=True)
        else:
            st.info("ยังไม่มีข้อมูลผู้ใช้งานในระบบ")
            
    except Exception as e:
        st.error(f"❌ ไม่สามารถดึงตารางรายชื่อพนักงานได้: {e}")
    finally:
        if 'db' in locals() and db.open:
            db.close()
