import streamlit as st
import pymysql
import pandas as pd
import requests
import datetime as dt_module
import streamlit.components.v1 as components

# --- 1. เชื่อมต่อฐานข้อมูล ---
def get_connection():
    try:
        return pymysql.connect(
            host='mysql-22653bef-kla-e55d.c.aivencloud.com',
            user='avnadmin',
            password='AVNS_W4Huwc3abQww6NKNlG2', # เปลี่ยนเป็นรหัสผ่านล่าสุดที่ก๊อปปี้มาจากเว็บ Aiven
            database='defaultdb',
            port=23986,
            connect_timeout=5 # ตั้งเวลา Timeout ไว้ 5 วินาทีไม่ให้หน้าเว็บค้าง
        )
    except pymysql.MySQLError as e:
        st.error(f"❌ ไม่สามารถเชื่อมต่อฐานข้อมูลได้: กรุณาตรวจสอบรหัสผ่านหรือสถานะของฐานข้อมูลบน Aiven (Error: {e})")
        st.stop() # สั่งให้ Streamlit หยุดทำงานตรงนี้ ไม่ให้รันโค้ดส่วนอื่นต่อจนพัง

# --- 2. ฟังก์ชันตรวจสอบสิทธิ์ ---
def check_permission(user_id):
    if not user_id or user_id.startswith("GUEST_") or "*" in user_id: 
        return "guest"
    uid = user_id.strip().lower()
    mapping = {
        "admin01": "admin", 
        "booker01": "booker", 
        "dispatcher01": "dispatcher", 
        "driver01": "driver", 
        "staff01": "airportstaff", 
        "airportstaff01": "airportstaff"
    }
    if uid in mapping: 
        return mapping[uid]
    
    db = None
    try:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT role, status FROM users WHERE line_user_id = %s", (user_id,))
            res = cursor.fetchone()
            if res and res[1] == "Active": 
                return str(res[0]).lower()
            return "guest"
    except: 
        return "guest"
    finally: 
        if db and db.open:
            db.close()

st.set_page_config(page_title="ระบบจัดการรถ Hunsa", layout="wide")

# --- 3. จัดการสถานะและเมนู ---
q_params = st.query_params

# 💡 อัปเกรดดักจับ: เช็คทั้งจาก ?user= , ?lineidtoemp= และดักจับจากค่า state ของ LINE LIFF
line_id_from_url = q_params.get("user") or q_params.get("lineidtoemp")

# ดักจับเพิ่มกรณีเปิดผ่าน LINE LIFF URL แล้วค่าหลุดไปอยู่ใน liff.state
if not line_id_from_url and "liff.state" in q_params:
    liff_state = q_params.get("liff.state")
    if isinstance(liff_state, list): liff_state = liff_state[0]
    # ค้นหาคำว่า ?user= หรือ &user= ใน state ของ LIFF
    if "user=" in liff_state:
        line_id_from_url = liff_state.split("user=")[1].split("&")[0]

if line_id_from_url:
    if isinstance(line_id_from_url, list):
        st.session_state.default_user_id = str(line_id_from_url[0]).strip()
    else:
        st.session_state.default_user_id = str(line_id_from_url).strip()

current_id = st.sidebar.text_input("ระบุ LINE User ID", value=st.session_state.get("default_user_id", "")).strip()
st.session_state.default_user_id = current_id

# ตรวจสอบสิทธิ์จากฟังก์ชันเดิม
user_role = check_permission(current_id)

# หากไม่มีการกรอก ID หรือเป็นสิทธิ์อื่นที่หาไม่เจอ ให้ปรับสถานะเป็น guest เสมอ
if not current_id or user_role == "guest":
    user_role = "guest"

st.sidebar.info(f"สิทธิ์: {user_role.upper()}")

# สร้างรายการเมนูตามระดับสิทธิ์แบบปลอดภัย
menu_options = []
if user_role == "admin": 
    menu_options = ["🏠 Dashboard", "➕ Booker", "🖥️ Dispatcher", "🚖 งานของฉัน (Driver)", "✈️ Airport Staff", "📝 ลงทะเบียนพนักงานใหม่"]
elif user_role == "booker": 
    menu_options = ["➕ Booker"]
elif user_role == "dispatcher": 
    menu_options = ["🖥️ Dispatcher"]
elif user_role == "driver": 
    menu_options = ["🚖 งานของฉัน (Driver)"]
elif user_role == "airportstaff": 
    menu_options = ["✈️ Airport Staff"]
else: 
    menu_options = ["📝 ลงทะเบียนพนักงานใหม่"]

# ป้องกันบั๊กกรณีเมนูเก่าค้างใน session_state ของระดับสิทธิ์อื่น
if "current_menu_choice" not in st.session_state or st.session_state["current_menu_choice"] not in menu_options: 
    st.session_state["current_menu_choice"] = menu_options[0]

choice = st.sidebar.radio(
    "เมนูใช้งาน", 
    options=menu_options, 
    index=menu_options.index(st.session_state["current_menu_choice"])
)
st.session_state["current_menu_choice"] = choice

# เช็คตัดหน้ากลับเฉพาะผู้ใช้งานที่เป็น Driver เท่านั้น เพื่อป้องกันเมนูค้างหน้าอื่น
if user_role == "driver" and choice != "🚖 งานของฉัน (Driver)":
    st.session_state["current_menu_choice"] = "🚖 งานของฉัน (Driver)"
    st.rerun()
    
# --- 4. แยกหน้าแสดงผลตามตัวเลือกเมนู ---
if choice == "🏠 Dashboard":
    st.title("🏠 Dashboard")
    st.write("---")
    
    # 1. ส่วน Metric สรุปงาน
    db = None
    try:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM bookings WHERE status = 'Pending'")
            count_pending = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM bookings WHERE status IN ('Assigned', 'Accepted')")
            count_active = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'driver'")
            count_drivers = cursor.fetchone()[0]
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("⏳ งานรอจัดสรร", count_pending)
        col_m2.metric("🚀 รถกำลังวิ่ง", count_active)
        col_m3.metric("🚖 คนขับทั้งหมด", count_drivers)
    except Exception as e: 
        st.error(f"Error Metric: {e}")
    finally: 
        if db and db.open: db.close()

    # 2. ส่วนจัดการพนักงาน (เฉพาะ Admin เท่านั้น)
    if user_role == "admin":
        st.title("👥 ระบบจัดการสิทธิ์ผู้ใช้งาน (User Management)")
        st.write("---")
    
        st.write("### ⏳ รายชื่อพนักงานใหม่ที่รออนุมัติสิทธิ์ (Guests)")
        db = None
        try:
            db = get_connection()
            with db.cursor() as cursor:
                cursor.execute("SELECT line_user_id, name, role FROM users WHERE role = 'guest'")
                guests_data = cursor.fetchall()
            if guests_data:
                df_guests = pd.DataFrame(guests_data, columns=['รหัส LINE User ID', 'ชื่อรายงานตัวพนักงาน', 'สถานะ'])
                st.dataframe(df_guests, width='stretch', hide_index=True)
                st.sidebar.info("💡 แอดมินสามารถก๊อปปี้รหัส LINE ID จากตารางด้านบนมาวางในกล่องแก้ไขเพื่ออัปเดตตำแหน่งได้ครับ")
            else: 
                st.success("✨ เรียบร้อยดี! ไม่มีพนักงานใหม่ค้างรออนุมัติสิทธิ์ในระบบครับ")
        except Exception as e: 
            st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล Guest: {e}")
        finally:
            if db and db.open: db.close()

        st.write("---")
        user_list_options = {}
        try:
            db = get_connection()
            with db.cursor() as cursor: 
                cursor.execute("SELECT line_user_id, name, role, status FROM users")
                all_users = cursor.fetchall()
            user_list_options = {f"👤 {u[1]} ({u[2].upper()}) - [{u[3] if u[3] else 'Active'}]": u for u in all_users}
        except Exception as e: 
            st.error(f"ดึงข้อมูลผู้ใช้ล้มเหลว: {e}")
        finally:
            if db and db.open: db.close()

        col_form_edit, col_form_del = st.columns([2, 1])

        with col_form_edit:
            st.write("📝 **ระบบลงทะเบียน / แก้ไข และ ปรับสถานะพนักงาน**")
            select_user_action = st.selectbox("💡 เลือกพนักงานที่ต้องการแก้ไข (หรือเลือกเพิ่มคนใหม่)", options=["➕ ลงทะเบียนพนักงานใหม่ / กรอกเอง"] + list(user_list_options.keys()))
            init_id, init_name, init_role, init_status = "", "", "driver", "Active"
            
            if select_user_action != "➕ ลงทะเบียนพนักงานใหม่ / กรอกเอง":
                user_data = user_list_options[select_user_action]
                init_id, init_name = user_data[0], user_data[1]
                init_role = user_data[2].lower() if user_data[2] else "driver"
                init_status = user_data[3] if user_data[3] else "Active"

            with st.form("user_management_form", clear_on_submit=False):
                new_line_id = st.text_input("ระบุ LINE User ID", value=init_id).strip()
                new_name = st.text_input("ระบุชื่อ-นามสกุลจริง ของพนักงาน", value=init_name).strip()
                roles_pool = ["admin", "booker", "dispatcher", "driver", "airportstaff", "guest"]
                new_role = st.selectbox("กำหนดตำแหน่ง (Role)", roles_pool, index=roles_pool.index(init_role) if init_role in roles_pool else 3)
                status_pool = ["Active", "Inactive"]
                new_status = st.radio("🚦 Status การใช้งานระบบ", status_pool, index=status_pool.index(init_status) if init_status in status_pool else 0, horizontal=True)
                submit_user = st.form_submit_button("💾 อนุมัติและบันทึกสิทธิ์")
                
                if submit_user:
                    if new_line_id and new_name:
                        try:
                            conn = get_connection()
                            with conn.cursor() as cursor:
                                sql = "INSERT INTO users (line_user_id, name, role, status) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE name = %s, role = %s, status = %s"
                                cursor.execute(sql, (new_line_id, new_name, new_role, new_status, new_name, new_role, new_status))
                            conn.commit()
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
                            with conn.cursor() as cursor:
                                cursor.execute("SELECT COUNT(*) FROM bookings WHERE driver_id = %s", (target_del_id,))
                                has_history = cursor.fetchone()[0]
                                if has_history > 0:
                                    st.error(f"❌ ไม่สามารถลบคุณ {target_del_name} ได้ เนื่องจากมีประวัติการวิ่งงานในระบบแล้ว (แนะนำให้เปลี่ยนสถานะเป็น Inactive แทน)")
                                else:
                                    cursor.execute("DELETE FROM users WHERE line_user_id = %s", (target_del_id,))
                                    conn.commit()
                                    st.success(f"🗑️ ลบข้อมูลพนักงานทดสอบคุณ {target_del_name} เรียบร้อยแล้ว!")
                                    st.rerun()
                            conn.close()
                        except Exception as e: 
                            st.error(f"เกิดข้อผิดพลาด: {e}")
                    else: 
                        st.warning("⚠️ โปรดติ๊กเครื่องหมายถูกเพื่อยืนยันก่อนกดปุ่มลบครับ")

elif choice == "➕ Booker":
    st.title("📋 แบบฟอร์มจองรถ (Booker)")
    st.subheader("กรอกรายละเอียดการเดินทางเพื่อส่งงานให้ผู้จัดสรรรถ")

    with st.form(key="car_booking_form", clear_on_submit=True):
        st.write("### 🚗 ข้อมูลการเดินทาง")
        passenger_name = st.text_input("👤 ชื่อผู้โดยสาร / คณะเดินทาง", placeholder="เช่น คุณสมชาย ใจดี")
        pickup_location = st.text_input("📍 จุดรับ (Pickup)", placeholder="กรอกจุดรับ เช่น สนามบินสุวรรณภูมิ").strip()
        dropoff_location = st.text_input("🏁 จุดส่ง (Dropoff)", placeholder="กรอกจุดส่ง เช่น โรงแรมฮันซ่า").strip()
        
        st.write("📅 วันและเวลาเดินทาง")
        col1, col2 = st.columns(2)
        with col1:
            booking_date = st.date_input("เลือกวันที่")
        with col2:
            booking_time_input = st.time_input("เลือกเวลา")
        
        combined_datetime = dt_module.datetime.combine(booking_date, booking_time_input)
        submit_button = st.form_submit_button("💾 บันทึกข้อมูลการจอง")

    if submit_button:
        if not passenger_name.strip() or not pickup_location or not dropoff_location:
            st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนก่อนบันทึกครับ")
        else:
            with st.spinner("กำลังบันทึกข้อมูลลงระบบ..."):
                db = None
                try:
                    db = get_connection()
                    now = dt_module.datetime.now()
                    year_month_str = now.strftime("%Y%m")
                    
                    with db.cursor() as cursor:
                        # สร้างเลข Voucher อัตโนมัติ
                        cursor.execute("SELECT COUNT(*) FROM bookings WHERE voucher_no LIKE %s", (f"VC{year_month_str}%",))
                        next_number = cursor.fetchone()[0] + 1
                        auto_voucher_no = f"VC{year_month_str}{str(next_number).zfill(5)}"
                        
                        sql = "INSERT INTO bookings (voucher_no, passenger_name, pickup_location, dropoff_location, booking_time, status) VALUES (%s, %s, %s, %s, %s, %s)"
                        cursor.execute(sql, (auto_voucher_no, passenger_name, pickup_location, dropoff_location, combined_datetime, 'Pending'))
                    db.commit()
                    st.success(f"🎉 บันทึกการจองสำเร็จ! เลขใบงาน: **{auto_voucher_no}**")
                    st.rerun()
                except Exception as e: 
                    st.error(f"❌ เกิดข้อผิดพลาด: {e}")
                finally: 
                    if db and db.open: db.close()

    st.write("---")
    st.write("### 🚗 รายการงานจองปัจจุบันที่คุณคีย์ในระบบ")
    db = None
    try:
        db = get_connection()
        df_booker = pd.read_sql("""
            SELECT voucher_no AS 'Voucher', passenger_name AS 'ชื่อผู้โดยสาร', pickup_location AS 'จุดรับ', 
                   dropoff_location AS 'จุดส่ง', booking_time AS 'เวลาเดินทาง', status AS 'สถานะงาน' 
            FROM bookings WHERE status IN ('Pending', 'Assigned') ORDER BY booking_time ASC
        """, db)
        if not df_booker.empty: 
            st.dataframe(df_booker, width='stretch', hide_index=True)
        else: 
            st.info("💡 ปัจจุบันยังไม่มีรายการงานค้างในระบบครับ")
    except Exception as e: 
        st.error(f"❌ ไม่สามารถดึงข้อมูลได้: {e}")
    finally: 
        if db and db.open: db.close()

elif choice == "🖥️ Dispatcher":
    st.title("🎛️ แผงควบคุมสำหรับ Dispatcher")
    st.write("---")
    
    db = None
    try:
        db = get_connection()
        # 1. ดึงข้อมูลคนขับ
        cursor = db.cursor()
        cursor.execute("SELECT line_user_id, name FROM users WHERE role = 'driver' AND status = 'Active'")
        drivers_data = cursor.fetchall()
        driver_options = {f"🚗 {d[1]} ({d[0][:6]}...)": d[0] for d in drivers_data}
        
        # 2. ดึงข้อมูลงาน
        df_bookings = pd.read_sql("""
            SELECT id, voucher_no, passenger_name, pickup_location, dropoff_location, status, driver_id 
            FROM bookings 
            WHERE status IN ('Pending', 'Assigned')
            ORDER BY id DESC
        """, db)
        
        if not df_bookings.empty:
            df_bookings['คนขับที่รับงาน'] = df_bookings['driver_id'].map(lambda x: dict(drivers_data).get(x, "ยังไม่ได้จ่ายงาน") if x else "ยังไม่ได้จ่ายงาน")
            
            st.write("### 📊 ตารางสถานะงาน")
            st.dataframe(df_bookings[['voucher_no', 'passenger_name', 'status', 'คนขับที่รับงาน']], width='stretch', hide_index=True)
            
            # 3. ส่วนการจ่ายงานและปิดงาน
            col_assign, col_complete = st.columns(2)
            
            with col_assign:
                st.write("### 🚖 จ่ายงานใหม่")
                job_map = {f"🎫 {row['voucher_no']} ({row['passenger_name']})": row['id'] for _, row in df_bookings.iterrows()}
                sel_job = st.selectbox("เลือกงาน", list(job_map.keys()))
                sel_driver = st.selectbox("เลือกคนขับ", list(driver_options.keys()))
                
                if st.button("💾 บันทึกการมอบหมาย"):
                    cursor.execute("UPDATE bookings SET driver_id = %s, status = 'Assigned' WHERE id = %s", 
                                   (driver_options[sel_driver], job_map[sel_job]))
                    db.commit()
                    st.success("จ่ายงานเรียบร้อย!")
                    st.rerun()

            with col_complete:
                st.write("### 🏁 ปิดงาน")
                active_jobs = df_bookings[df_bookings['status'] == 'Assigned']
                if not active_jobs.empty:
                    job_opts = {f"✅ {row['voucher_no']}": row['id'] for _, row in active_jobs.iterrows()}
                    sel_done = st.selectbox("เลือกงานปิดสถานะ", list(job_opts.keys()))
                    if st.button("🏁 ยืนยันปิดงาน"):
                        cursor.execute("UPDATE bookings SET status = 'Completed' WHERE id = %s", (job_opts[sel_done],))
                        db.commit()
                        st.success("ปิดงานสำเร็จ!")
                        st.rerun()
                else:
                    st.info("ไม่มีงานที่กำลังวิ่งอยู่ให้กดปิด")
        else:
            st.info("✨ ไม่มีงานค้างในระบบ")
            
    except Exception as e: 
        st.error(f"Error: {e}")
    finally: 
        if db and db.open: db.close()

elif choice == "🚖 งานของฉัน (Driver)":
    st.title("🚖 งานของฉัน (Driver)")
    
    driver_name = "คนขับรถ"
    db = None
    try:
        db = get_connection()
        cursor = db.cursor() # 💡 แก้ไข: เพิ่มคำสั่งประกาศสิทธิ์ cursor ป้องกันบั๊กตอนกดรับงานย่อหน้าด้านล่าง
        
        # 1. ดึงชื่อคนขับ
        cursor.execute("SELECT name FROM users WHERE line_user_id = %s", (current_id,))
        res = cursor.fetchone()
        if res: driver_name = res[0]
        st.subheader(f"👋 สวัสดีคุณ: {driver_name}")
        st.write("---")
        
        # 2. ดึงงานปัจจุบัน
        df_driver = pd.read_sql("""
            SELECT id, voucher_no, passenger_name, pickup_location, dropoff_location, status 
            FROM bookings 
            WHERE driver_id = %s AND status IN ('Assigned', 'Accepted')
            ORDER BY booking_time ASC
        """, db, params=(current_id,))
        
        if not df_driver.empty:
            st.write("### 📥 รายการงานที่ได้รับมอบหมาย")
            st.dataframe(df_driver, width='stretch', hide_index=True)
            
            assigned_jobs = df_driver[df_driver['status'] == 'Assigned']
            if not assigned_jobs.empty:
                st.write("---")
                st.write("### 📥 งานใหม่รอรับทราบ")
                job_map = {f"🎫 {row['voucher_no']} | ลูกค้า {row['passenger_name']}": row['id'] for _, row in assigned_jobs.iterrows()}
                selected_job = st.selectbox("เลือกงานที่ต้องการรับ", list(job_map.keys()))
                
                if st.button("✅ กดรับทราบและยอมรับงาน"):
                    cursor.execute("UPDATE bookings SET status = 'Accepted' WHERE id = %s", (job_map[selected_job],))
                    db.commit()
                    st.success("รับงานเรียบร้อย!")
                    st.rerun()
        else:
            st.info("✨ ปัจจุบันคุณยังไม่มีงานค้างที่ต้องปฏิบัติครับ")
            
    except Exception as e: 
        st.error(f"Error Driver Page: {e}")
    finally: 
        if db and db.open: db.close()

    # 3. ส่วนประวัติการวิ่งงาน
    st.write("---")
    st.write("### ✅ ประวัติการวิ่งงาน (Completed)")
    db = None
    try:
        db = get_connection()
        df_history = pd.read_sql("SELECT voucher_no, passenger_name, status FROM bookings WHERE driver_id = %s AND status = 'Completed' ORDER BY id DESC LIMIT 20", db, params=(current_id,))
        if not df_history.empty:
            st.dataframe(df_history, width='stretch', hide_index=True)
        else:
            st.info("ยังไม่มีประวัติการวิ่งงานครับ")
    except Exception as e: 
        st.error(f"Error History: {e}")
    finally: 
        if db and db.open: db.close()

elif choice == "✈️ Airport Staff":
    st.title("✈️ ตรวจสอบสถานะรถ (Airport Staff)")
    st.subheader("📋 ตารางมอนิเตอร์รถยนต์และคนขับที่กำลังปฏิบัติงาน")

    db = None
    try:
        db = get_connection()
        query = """
            SELECT b.voucher_no AS 'เลข Voucher', b.passenger_name AS 'ชื่อผู้โดยสาร', 
                   b.pickup_location AS 'จุดรับ', b.dropoff_location AS 'จุดส่ง', 
                   b.booking_time AS 'เวลาเดินทาง', b.status AS 'สถานะงาน', 
                   u.name AS 'คนขับรถที่รับงาน'
            FROM bookings b 
            LEFT JOIN users u ON b.driver_id = u.line_user_id
            WHERE b.status IN ('Assigned', 'Accepted') 
            ORDER BY b.booking_time ASC
        """
        df_airport = pd.read_sql(query, db)
        
        if not df_airport.empty:
            st.write("✨ แสดงงานที่กำลังดำเนินการภาคพื้นสนามบิน")
            
            def highlight_status(row):
                color = '#fff3cd' if row['สถานะงาน'] == 'Assigned' else '#d4edda'
                return [f'background-color: {color}'] * len(row)
            
            st.dataframe(df_airport.style.apply(highlight_status, axis=1), width='stretch', hide_index=True)
            
            st.write("---")
            col1, col2 = st.columns(2)
            with col1: 
                st.metric(label="🚖 กำลังเดินทาง (Assigned)", value=len(df_airport[df_airport['สถานะงาน'] == 'Assigned']))
            with col2: 
                st.metric(label="✅ คนขับรับทราบงานแล้ว (Accepted)", value=len(df_airport[df_airport['สถานะงาน'] == 'Accepted']))
        else:
            st.info("ℹ️ ปัจจุบันยังไม่มีรถยนต์ที่อยู่ในสถานะรับงานครับ")
            
    except Exception as e: 
        st.error(f"❌ เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
    finally: 
        if db and db.open: db.close()

elif choice == "📝 ลงทะเบียนพนักงานใหม่":
    st.title("📝 ลงทะเบียนพนักงานใหม่")
    st.write("---")
    
    st.markdown("### 👤 กรอกข้อมูลรายงานตัวเพื่อส่งให้แอดมินอนุมัติ")
    st.info("💡 กรุณากดปุ่มดึงรหัสในแอป LINE (Rich Menu หรือข้อความปักหมุด) แล้วนำรหัสตัว U 33 หลักมาวางด้านล่างนี้ครับ")
    
    with st.form("guest_register_form", clear_on_submit=True):
        reg_name = st.text_input("1. กรุณากรอก ชื่อ - นามสกุลจริงของคุณ", placeholder="เช่น นายสมชาย ใจดีมาก").strip()
        reg_line_id = st.text_input("2. ระบุรหัส LINE User ID ของคุณ (รหัสตัว U 33 หลัก)", value=current_id if current_id else "", placeholder="วางรหัสตัว U ที่คัดลอกมาที่นี่ครับ")
        
        submit_reg = st.form_submit_button("🚀 ส่งข้อมูลลงทะเบียนระบบคิวรถ")
        
        if submit_reg:
            if not reg_name or not reg_line_id:
                st.error("⚠️ กรุณากรอกชื่อและรหัส LINE ID ให้ครบถ้วนก่อนกดส่งข้อมูลครับ")
            elif "http" in reg_line_id.lower() or "line.me" in reg_line_id.lower() or len(reg_line_id) < 10 or "*" in reg_line_id:
                st.error("⚠️ รหัส LINE User ID ไม่ถูกต้อง! กรุณานำเฉพาะรหัสตัว U มาวางให้ถูกต้องครับ")
            else:
                db_reg = None
                try:
                    db_reg = get_connection()
                    with db_reg.cursor() as cursor:
                        sql = """
                            INSERT INTO users (line_user_id, name, role, status)
                            VALUES (%s, %s, 'guest', 'Active')
                            ON DUPLICATE KEY UPDATE name = %s, role = 'guest', status = 'Active'
                        """
                        cursor.execute(sql, (reg_line_id, reg_name, reg_name))
                    db_reg.commit()
                    st.success(f"🎉 ส่งข้อมูลรายงานตัวของพนักงานคุณ '{reg_name}' เรียบร้อย! รบกวนแจ้งแอดมินอนุมัติในหน้าหลังบ้านครับ")
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาดทางฐานข้อมูล: {e}")
                finally:
                    if db_reg and db_reg.open: db_reg.close()
