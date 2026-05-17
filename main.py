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

# --- ระบบล็อกอินอัจฉริยะแบบนิรภัย (มาตรฐานสากล Streamlit ป้องกันการทับค่า) ---
if "logged_in_user" not in st.session_state:
    st.session_state["logged_in_user"] = "admin01"

st.sidebar.title("🔐 เข้าสู่ระบบ")

# วิธีที่ถูกต้องที่สุด: ผูกกล่องเข้ากับห้องความจำโดยตรงผ่าน key ตัวเดียว (ห้ามใส่ value ซ้ำซ้อน)
# ท่านี้จะทำให้เวลาคุณกล้าพิมพ์สลับชื่อด้วยมือ ระบบจะอัปเดตความจำทันทีโดยไม่เด้งหลุด
current_id = st.sidebar.text_input(
    "ระบุ LINE User ID", 
    key="logged_in_user"
).strip()

# ดึงไอดีที่อัปเดตล่าสุดสด ๆ ไปตรวจสอบสิทธิ์บนคลาวด์ Aiven
user_role = check_permission(current_id).lower()
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
    
# --- ระบบล็อกความจำเมนู (ป้องกันหน้าจอหายจังหวะ Rerun ตัวเลือกข้างใน) ---
# 1. ตั้งค่าเริ่มต้นให้จำเมนูแรกสุดที่ดึงมาได้
if "current_menu_choice" not in st.session_state or st.session_state["current_menu_choice"] not in menu_options:
    st.session_state["current_menu_choice"] = menu_options[0] if menu_options else ""

# 2. ผูกกล่องเมนูวิทยุฝั่งซ้ายเข้ากับตู้เซฟความจำโดยตรงผ่าน key
choice = st.sidebar.radio(
    "เมนูใช้งาน", 
    options=menu_options, 
    key="current_menu_choice"
)

# --- 4. การแสดงเนื้อหาไส้ในของแต่ละเมนูตามหน้าเลือก ---

# หน้าที่ 1: Dashboard (เวอร์ชันอัปเกรด ศูนย์ควบคุมสถานการณ์เรียลไทม์)
if "Dashboard" in choice:
    st.title("🏠 หน้าแรกและภาพรวมระบบ (Dashboard)")
    st.markdown(f"สวัสดีครับคุณกล้า สถานะการเชื่อมต่อคลาวด์ **Aiven MySQL ปกติดีเยี่ยม** ครับ")
    st.write("---")

    # --- ดึงข้อมูลสถิติสด ๆ จาก Cloud ---
    try:
        db = get_connection()
        with db.cursor() as cursor:
            # 1. นับงานค้าง Pending
            cursor.execute("SELECT COUNT(*) FROM bookings WHERE status = 'Pending'")
            count_pending = cursor.fetchone()[0]
            
            # 2. นับงานที่จ่ายแล้วแต่อยู่ระหว่างดำเนินการ
            cursor.execute("SELECT COUNT(*) FROM bookings WHERE status IN ('Assigned', 'Accepted')")
            count_active = cursor.fetchone()[0]
            
            # 3. นับจำนวนคนขับรถทั้งหมดในระบบ
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'driver'")
            count_drivers = cursor.fetchone()[0]
            
            # 4. ดึงงานล่าสุด 5 รายการมาแสดง
            cursor.execute("SELECT id, passenger_name, pickup_location, dropoff_location, status FROM bookings ORDER BY id DESC LIMIT 5")
            recent_data = cursor.fetchall()
            
        df_recent = pd.DataFrame(recent_data, columns=['ใบงานที่', 'ชื่อผู้โดยสาร', 'จุดรับ', 'จุดส่ง', 'สถานะ'])
    except Exception as e:
        count_pending, count_active, count_drivers = 0, 0, 0
        df_recent = pd.DataFrame()
    finally:
        if 'db' in locals() and db.open:
            db.close()

    # --- ส่วนแสดงผลบนหน้าเว็บ ---
    # 1. แสดงกล่องสถิติ (Metrics) ด้านบน
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric(label="⏳ ใบงานรอจัดสรร (Pending)", value=count_pending, delta=f"{count_pending} งานค้าง", delta_color="inverse" if count_pending > 0 else "normal")
    with col_m2:
        st.metric(label="🚀 รถกำลังปฏิบัติงาน (Active)", value=count_active)
    with col_m3:
        st.metric(label="🚖 คนขับรถในระบบทั้งหมด", value=count_drivers)

    st.write("---")
    
    # 2. แสดงตารางงานล่าสุดและตารางสรุป
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.write("### ⏱️ รายการจองรถล่าสุด 5 รายการ")
        if not df_recent.empty:
            st.dataframe(df_recent, width='stretch')
        else:
            st.info("ยังไม่มีประวัติการจองในระบบ")
            
    with col_right:
        st.write("### 💡 แนะนำการใช้งาน")
        st.info("คุณกล้าสามารถสลับบัญชีเพื่อทดสอบระบบได้:\n\n"
                "* **admin01** : จัดสรรงานและดูภาพรวมทั้งหมด\n"
                "* **driver01** : ดูงานของตัวเองและกดรับงาน\n"
                "* **driver02** : ดูงานของคนขับคนที่ 2")

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
        
        # 1.1 แก้ไขจุดนี้: เปลี่ยนจาก pd.read_sql มาใช้ cursor ปกติ เพื่อความเสถียร
        with db.cursor() as cursor:
            query_bookings = "SELECT id, passenger_name, pickup_location, dropoff_location, booking_time, status, driver_id FROM bookings ORDER BY booking_time DESC"
            cursor.execute(query_bookings)
            bookings_data = cursor.fetchall()
            
        # แปลงข้อมูลเป็น DataFrame ด้วยมือแทน ปลอดภัยจาก UserWarning แน่นอน
        columns = ['id', 'passenger_name', 'pickup_location', 'dropoff_location', 'booking_time', 'status', 'driver_id']
        df_bookings = pd.DataFrame(bookings_data, columns=columns)
        
        # 1.2 ดึงรายชื่อผู้ใช้ที่เป็น 'driver' ทั้งหมดมาทำเป็นตัวเลือก
        with db.cursor() as cursor:
            cursor.execute("SELECT line_user_id, name FROM users WHERE role = 'driver'")
            drivers_list = cursor.fetchall()
            
        # แปลงรายชื่อคนขับเป็นดีกชันนารี
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
        st.dataframe(df_bookings, width=True)
        
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
# หน้าที่ 4: Driver (ดูงานตัวเองบน Cloud + กดรับงานเปลี่ยนสถานะเป็น Accepted)
elif "Driver" in choice:
    st.title("🚖 งานที่ได้รับมอบหมาย (Driver)")
    st.subheader(f"👤 รหัสคนขับออนไลน์: {current_id}")

    # --- ส่วนที่ 1: ดึงเฉพาะงานที่ถูกจ่ายให้คนขับคนนี้ ---
    try:
        db = get_connection()
        with db.cursor() as cursor:
            # คำสั่ง SQL ดึงงานที่ตรงกับ driver_id ของคนที่เข้าใช้งานอยู่
            query_driver = """
                SELECT id, passenger_name, pickup_location, dropoff_location, booking_time, status 
                FROM bookings 
                WHERE driver_id = %s 
                ORDER BY booking_time DESC
            """
            cursor.execute(query_driver, (current_id,))
            driver_jobs = cursor.fetchall()
            
        # แปลงข้อมูลเป็น DataFrame สวยงามเพื่อไปวาดตารางบนเว็บ
        columns = ['id', 'passenger_name', 'pickup_location', 'dropoff_location', 'booking_time', 'status']
        df_driver = pd.DataFrame(driver_jobs, columns=columns)
        
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อข้อมูลคนขับ: {e}")
        df_driver = pd.DataFrame()
    finally:
        if 'db' in locals() and db.open:
            db.close()

    # --- ส่วนที่ 2: แสดงผลตารางงานและการทำฟังก์ชันกดรับงาน ---
    if not df_driver.empty:
        st.write("### 📊 ตารางรายการงานจองของคุณในระบบ")
        st.dataframe(df_driver, width=True)
        
        st.write("---")
        
        # กรองดูว่ามีงานไหนที่จ่ายเข้ามาใหม่แล้วค้างสถานะ 'Assigned' เพื่อให้คนขับกดรับ
        assigned_jobs = df_driver[df_driver['status'] == 'Assigned']
        
        if not assigned_jobs.empty:
            st.write("### 📥 มีใบงานใหม่รอคุณกดรับทราบ")
            
            # ทำลิสต์ให้คนขับเลือกใบงานที่จะรับ (กรณีมีหลายงาน)
            driver_job_options = {
                f"🆔 ใบงานที่ {row['id']} | คุณ {row['passenger_name']} ({row['pickup_location']} ➡️ {row['dropoff_location']})": row['id']
                for _, row in assigned_jobs.iterrows()
            }
            
            col_select_job, col_btn_accept = st.columns([3, 1])
            
            with col_select_job:
                selected_driver_job = st.selectbox("เลือกใบงานที่ต้องการกดรับ", options=list(driver_job_options.keys()))
                job_id_to_accept = driver_job_options[selected_driver_job]
                
            with col_btn_accept:
                st.write(" ") # เว้นระยะช่องไฟให้ปุ่มเสมอกัน
                st.write(" ")
                btn_accept_job = st.button("✅ กดรับทราบและยอมรับงาน")
                
            # --- ส่วนที่ 3: กระบวนการหลังกดปุ่มรับงาน ---
            if btn_accept_job:
                with st.spinner("กำลังอัปเดตสถานะรับงานลงคลาวด์..."):
                    try:
                        db = get_connection()
                        with db.cursor() as cursor:
                            # สั่งอัปเดตสถานะในตาราง bookings จาก 'Assigned' ให้กลายเป็น 'Accepted'
                            sql_accept = "UPDATE bookings SET status = 'Accepted' WHERE id = %s"
                            cursor.execute(sql_accept, (job_id_to_accept,))
                            db.commit()
                            
                        st.success(f"🎉 คุณได้รับทราบและยอมรับใบงานที่ {job_id_to_accept} เรียบร้อย! ระบบแจ้งส่วนกลางแล้ว")
                        st.rerun() # รีเฟรชตารางหน้าจอเพื่อเปลี่ยนตัวหนังสือสถานะทันที
                        
                    except Exception as e:
                        st.error(f"❌ ไม่สามารถเปลี่ยนสถานะงานได้: {e}")
                    finally:
                        if 'db' in locals() and db.open:
                            db.close()
        else:
            st.success("✨ ยอดเยี่ยม! คุณได้กดรับทราบงานจองค้างหมดเรียบร้อยแล้ว ไม่มีงานใหม่ตกค้างครับ")
    else:
        st.info("ℹ️ ปัจจุบันยังไม่มีประวัติหรือใบงานจองรถที่ระบุส่งให้รหัสคนขับคนนี้ในฐานข้อมูล")

# หน้าที่ 5: Airport Staff (มอนิเตอร์ภาพรวมรถที่กำลังเดินทางมาสนามบิน)
elif "Airport Staff" in choice:
    st.title("✈️ ตรวจสอบสถานะรถ (Airport Staff)")
    st.subheader("📋 ตารางมอนิเตอร์รถยนต์และคนขับที่กำลังปฏิบัติงาน")

    try:
        db = get_connection()
        with db.cursor() as cursor:
            # คำสั่ง SQL เชื่อม 2 ตาราง (bookings และ users) เพื่อดึงชื่อคนขับออกมาโชว์ให้พนักงานสนามบินเห็นด้วย
            query_airport = """
                SELECT 
                    b.id AS 'ใบงานที่',
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

        # แปลงข้อมูลเป็น DataFrame เพื่อทำตารางสรุป
        columns = ['ใบงานที่', 'ชื่อผู้โดยสาร', 'จุดรับ', 'จุดส่ง', 'เวลาเดินทาง', 'สถานะงาน', 'คนขับรถที่รับงาน']
        df_airport = pd.DataFrame(airport_data, columns=columns)

    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการดึงข้อมูลสำหรับพนักงานสนามบิน: {e}")
        df_airport = pd.DataFrame()
    finally:
        if 'db' in locals() and db.open:
            db.close()

    # --- แสดงผลตารางมอนิเตอร์ ---
    if not df_airport.empty:
        st.write("✨ แสดงเฉพาะงานที่มีการจัดสรรคนขับแล้ว เพื่อเตรียมความพร้อมภาคพื้นสนามบิน")
        
        # ไฮไลต์สีให้ตารางอ่านง่าย (Assigned = สีส้ม, Accepted = สีเขียว)
        def highlight_status(val):
            if val == 'Accepted':
                return 'background-color: #d4edda; color: #155724; font-weight: bold;'
            elif val == 'Assigned':
                return 'background-color: #fff3cd; color: #856404;'
            return ''

        # แสดงตารางแบบจัดเต็มความกว้างหน้าจอ พร้อมใส่สีสันที่คอลัมน์สถานะงาน
        st.dataframe(df_airport.style.map(highlight_status, subset=['สถานะงาน']), width=True)
        
        # สรุปยอดจอดรอรับให้เห็นเป็นตัวเลขเข้าใจง่าย
        st.write("---")
        col_metrics1, col_metrics2 = st.columns(2)
        with col_metrics1:
            st.metric(label="🚖 จำนวนรถที่กำลังเดินทาง (Assigned)", value=len(df_airport[df_airport['สถานะงาน'] == 'Assigned']))
        with col_metrics2:
            st.metric(label="✅ จำนวนรถที่คนขับกดรับงานแล้ว (Accepted)", value=len(df_airport[df_airport['สถานะงาน'] == 'Accepted']))
            
    else:
        st.info("ℹ️ ปัจจุบันยังไม่มีรถยนต์คันไหนกำลังเดินทางมาสนามบิน (ไม่มีงานค้างในสถานะ Assigned หรือ Accepted)")
