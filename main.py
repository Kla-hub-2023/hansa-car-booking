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
            password='AVNS_W4Huwc3abQww6NKNlG2',
            database='defaultdb',
            port=23986,
            connect_timeout=5
        )
    except pymysql.MySQLError as e:
        st.error(f"❌ ไม่สามารถเชื่อมต่อฐานข้อมูลได้: กรุณาตรวจสอบรหัสผ่านหรือสถานะบน Aiven (Error: {e})")
        st.stop()

# --- 2. ฟังก์ชันตรวจสอบสิทธิ์ ---
def check_permission(user_id):
    if not user_id or user_id.startswith("GUEST_") or "*" in user_id: 
        return "guest"
    uid = user_id.strip().lower()
    mapping = {
        "admin01": "admin", "booker01": "booker", "dispatcher01": "dispatcher", 
        "driver01": "driver", "staff01": "airportstaff", "airportstaff01": "airportstaff"
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
        if db and db.open: db.close()

st.set_page_config(page_title="ระบบจัดการรถ Hunsa", layout="wide")

# =================================================================
# 🎨 สไตล์ CSS ปรับขนาดตัวอักษรให้พอเหมาะกับหน้าจอมือถือ
# =================================================================
st.markdown("""
    <style>
    @media (max-width: 768px) {
        .stHtmlBlock h1, h1 { font-size: 22px !important; font-weight: 700 !important; margin-bottom: 10px !important; }
        .stHtmlBlock h2, h2, .stHtmlBlock h3, h3 { font-size: 18px !important; font-weight: 600 !important; }
        [data-testid="stMetricLabel"] { font-size: 13px !important; }
        [data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 700 !important; }
        .stButton button, .stSelectbox label, .stTextInput label, p { font-size: 14px !important; }
        .stDataFrame div, table th, table td { font-size: 12px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- ฟังก์ชันส่งข้อความแจ้งเตือนผ่าน LINE ---
def send_line_message(message, target_line_id):
    if not target_line_id or target_line_id.startswith("GUEST_"): return 
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer X8ogM3D2GxzZ3z5EBMdOxWTa4BjTlqP1H/bYv+fwqLGNiKhhxuiPQR5bakcgXfEZBUPNDImDlvLrDMvtqN0/8XTlrcqfIvti2m2RpY/wrbQ9xl95HJd+slpzHCM9Vs5SxNS5e9gBG4MSE71UUNhXrQdB04t89/1O/w1cDnyilFU='
    }
    data = {'to': target_line_id, 'messages': [{'type': 'text', 'text': message}]}
    try: requests.post(url, headers=headers, json=data, timeout=5)
    except: pass
        
# --- 3. จัดการสถานะและเมนู ---
q_params = st.query_params
line_id_from_url = q_params.get("user") or q_params.get("lineidtoemp")

if not line_id_from_url and "liff.state" in q_params:
    liff_state = q_params.get("liff.state")
    if isinstance(liff_state, list): liff_state = liff_state[0]
    if "user=" in liff_state:
        line_id_from_url = liff_state.split("user=")[1].split("&")[0]

if line_id_from_url:
    if isinstance(line_id_from_url, list): st.session_state.default_user_id = str(line_id_from_url[0]).strip()
    else: st.session_state.default_user_id = str(line_id_from_url).strip()

current_id = st.sidebar.text_input("ระบุ LINE User ID", value=st.session_state.get("default_user_id", "")).strip()
st.session_state.default_user_id = current_id

user_role = check_permission(current_id)
if not current_id or user_role == "guest": user_role = "guest"

st.sidebar.info(f"สิทธิ์: {user_role.upper()}")

menu_options = []
if user_role == "admin": menu_options = ["🏠 Dashboard", "➕ Booker", "🖥️ Dispatcher", "🚖 งานของฉัน (Driver)", "✈️ Airport Staff", "📝 ลงทะเบียนพนักงานใหม่"]
elif user_role == "booker": menu_options = ["➕ Booker"]
elif user_role == "dispatcher": menu_options = ["🖥️ Dispatcher"]
elif user_role == "driver": menu_options = ["🚖 งานของฉัน (Driver)"]
elif user_role == "airportstaff": menu_options = ["✈️ Airport Staff"]
else: menu_options = ["📝 ลงทะเบียนพนักงานใหม่"]

if user_role == "guest":
    st.session_state["current_menu_choice"] = "📝 ลงทะเบียนพนักงานใหม่"
    menu_options = ["📝 ลงทะเบียนพนักงานใหม่"]
elif "current_menu_choice" not in st.session_state or st.session_state["current_menu_choice"] not in menu_options: 
    st.session_state["current_menu_choice"] = menu_options[0]

try: menu_index = menu_options.index(st.session_state["current_menu_choice"])
except ValueError: menu_index = 0

choice = st.sidebar.radio("เมนูใช้งาน", options=menu_options, index=menu_index)
st.session_state["current_menu_choice"] = choice

if choice not in menu_options:
    st.sidebar.error("❌ ขออภัย คุณไม่มีสิทธิ์เข้าใช้งานเมนูนี้")
    st.session_state["current_menu_choice"] = menu_options[0]
    st.rerun()

if user_role == "driver" and choice != "🚖 งานของฉัน (Driver)":
    st.session_state["current_menu_choice"] = "🚖 งานของฉัน (Driver)"
    st.rerun()
    
# --- 4. แยกหน้าแสดงผลตามตัวเลือกเมนู ---
if choice == "🏠 Dashboard" and user_role in ["admin", "dispatcher"]:
    st.title("🏠 Dashboard")
    st.write("---")
    
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
    except Exception as e: st.error(f"Error Metric: {e}")
    finally: 
        if db and db.open: db.close()

    if user_role == "admin":
        st.title("👥 ระบบจัดการสิทธิ์ผู้ใช้งาน (User Management)")
        st.write("---")
        st.write("### ⏳ รายชื่อพนักงานใหม่ที่รออนุมัติสิทธิ์ (Guests)")
        db = None
        try:
            db = get_connection()
            with db.cursor() as cursor:
                cursor.execute("SELECT line_user_id, name, role, createdate FROM users WHERE role = 'guest'")
                guests_data = cursor.fetchall()
            if guests_data:
                df_guests = pd.DataFrame(guests_data, columns=['รหัส LINE User ID', 'ชื่อรายงานตัวพนักงาน', 'สถานะ', 'วันที่สมัครเข้ามา'])
                st.dataframe(df_guests, width='stretch', hide_index=True)
            else: st.success("✨ เรียบร้อยดี! ไม่มีพนักงานใหม่ค้างรออนุมัติสิทธิ์ในระบบครับ")
        except Exception as e: st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล Guest: {e}")
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
        except Exception as e: st.error(f"ดึงข้อมูลผู้ใช้ล้มเหลว: {e}")
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
                            now_time = dt_module.datetime.now()
                            with conn.cursor() as cursor:
                                # 💡 แก้ไขข้อ 3: เมื่อแอดมินแก้ไขหรือระบุสิทธิ์ ให้ทำการอัปเดตลงฟิลด์ updatedate ด้วย
                                sql = """
                                    INSERT INTO users (line_user_id, name, role, status, createdate, updatedate) 
                                    VALUES (%s, %s, %s, %s, %s, %s) 
                                    ON DUPLICATE KEY UPDATE name = %s, role = %s, status = %s, updatedate = %s
                                """
                                cursor.execute(sql, (new_line_id, new_name, new_role, new_status, now_time, now_time, new_name, new_role, new_status, now_time))
                            conn.commit()
                            conn.close()
                            st.success(f"🎉 บันทึกข้อมูลและอัปเดตสถานะ (พร้อมแสตมป์เวลา updatedate) เรียบร้อยแล้ว!")
                            st.rerun()
                        except Exception as e: st.error(f"❌ เกิดข้อผิดพลาดทางฐานข้อมูล: {e}")
                    else: st.warning("⚠️ รบกวนกรอก LINE ID และชื่อพนักงานให้ครบถ้วนครับ")

        with col_form_del:
            st.write("❌ **โซนอันตราย: ลบพนักงานออกจากระบบ**")
            with st.form("user_delete_form"):
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
                                if cursor.fetchone()[0] > 0:
                                    st.error(f"❌ ไม่สามารถลบคุณ {target_del_name} ได้ เนื่องจากมีประวัติงานวิ่งงานแล้ว")
                                else:
                                    cursor.execute("DELETE FROM users WHERE line_user_id = %s", (target_del_id,))
                                    conn.commit()
                                    st.success(f"🗑️ ลบข้อมูลพนักงานเรียบร้อยแล้ว!")
                                    st.rerun()
                            conn.close()
                        except Exception as e: st.error(f"เกิดข้อผิดพลาด: {e}")
                    else: st.warning("⚠️ โปรดติ๊กเครื่องหมายถูกเพื่อยืนยันก่อนกดปุ่มลบครับ")

elif choice == "➕ Booker" and user_role in ["admin", "booker"]:
    st.title("📋 ระบบจัดการการจองรถ (Booker)")
    
    # 💡 เพิ่มโหมดการทำงาน
    mode = st.radio("โหมดการทำงาน", ["สร้างรายการใหม่", "แก้ไขรายการที่มีอยู่"], horizontal=True)
    st.write("---")

    # ดึงข้อมูลมาแสดงเป็นตัวเลือกถ้าเลือกโหมดแก้ไข
    booking_options = {}
    if mode == "แก้ไขรายการที่มีอยู่":
        db = None
        try:
            db = get_connection()
            df_list = pd.read_sql("SELECT id, voucher_no, passenger_name FROM bookings WHERE status != 'Completed' ORDER BY id DESC", db)
            booking_options = {f"{row['voucher_no']} - {row['passenger_name']}": row['id'] for _, row in df_list.iterrows()}
        finally:
            if db and db.open: db.close()
        
        selected_booking_label = st.selectbox("เลือกใบงานที่ต้องการแก้ไข", list(booking_options.keys()))
        selected_id = booking_options[selected_booking_label]
    else:
        selected_id = None

    # ดึงข้อมูลเก่ามาแสดงในฟอร์ม (ถ้ามี)
    edit_data = None
    if selected_id:
        db = get_connection()
        edit_data = pd.read_sql("SELECT * FROM bookings WHERE id = %s", db, params=(selected_id,)).iloc[0]
        db.close()

    # --- ฟอร์มบันทึกข้อมูล ---
    with st.form(key="car_booking_form"):
        st.write("### 🚗 ข้อมูลการเดินทาง")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            passenger_name = st.text_input("👤 ชื่อผู้โดยสาร", value=edit_data['passenger_name'] if edit_data is not None else "")
            pickup = st.text_input("📍 จุดรับ", value=edit_data['pickup_location'] if edit_data is not None else "")
        with col_c2:
            dropoff = st.text_input("🏁 จุดส่ง", value=edit_data['dropoff_location'] if edit_data is not None else "")
            v_no = st.text_input("🎫 เลข Voucher (ห้ามแก้ไข)", value=edit_data['voucher_no'] if edit_data is not None else "ระบบสร้างให้อัตโนมัติ", disabled=True)
        
        st.write("📅 วันและเวลาเดินทาง")
        col_d1, col_d2 = st.columns(2)
        with col_d1: booking_date = st.date_input("วันที่", value=edit_data['booking_time'] if edit_data is not None else dt_module.date.today())
        with col_d2: booking_time = st.time_input("เวลา", value=edit_data['booking_time'] if edit_data is not None else dt_module.time(12, 0))
        
        st.write("---")
        st.write("### 📝 รายละเอียดเพิ่มเติม")
        c1, c2 = st.columns(2)
        with c1:
            in_group = st.text_input("🏨 Group/โรงแรม", value=edit_data['hotel_group'] if edit_data is not None else "")
            in_flight = st.text_input("✈️ Flight", value=edit_data['flight_no'] if edit_data is not None else "")
            in_time = st.time_input("🕒 เวลาบิน", value=edit_data['flight_time'] if edit_data is not None else dt_module.time(12, 0))
            in_room = st.text_input("🔑 Room", value=edit_data['room_no'] if edit_data is not None else "")
        with c2:
            in_type = st.text_input("🚘 Type", value=edit_data['car_type'] if edit_data is not None else "")
            in_plate = st.text_input("🎫 Plate", value=edit_data['car_plate'] if edit_data is not None else "")
            in_driver = st.text_input("👤 Driver Name", value=edit_data['driver_name_text'] if edit_data is not None else "")
            in_mobile = st.text_input("📱 Mobile No.", value=edit_data['mobile_no'] if edit_data is not None else "")
        
        in_1st = st.text_input("📞 1st call", value=edit_data['first_call'] if edit_data is not None else "")
        in_2nd = st.text_input("📞 2nd call", value=edit_data['second_call'] if edit_data is not None else "")
        in_vc_rem = st.text_area("🗒️ VC Remark", value=edit_data['vc_remark'] if edit_data is not None else "")
        in_job_rem = st.text_area("🗒️ Job Remark", value=edit_data['job_remark'] if edit_data is not None else "")
        
        submit_button = st.form_submit_button("💾 บันทึกข้อมูล")

    if submit_button:
        db = None
        try:
            db = get_connection()
            now = dt_module.datetime.now()
            combined_dt = dt_module.datetime.combine(booking_date, booking_time)
            
            with db.cursor() as cursor:
                if selected_id: # อัปเดตข้อมูลเดิม
                    sql = """UPDATE bookings SET passenger_name=%s, pickup_location=%s, dropoff_location=%s, booking_time=%s, 
                             hotel_group=%s, flight_no=%s, flight_time=%s, room_no=%s, car_type=%s, car_plate=%s, 
                             driver_name_text=%s, mobile_no=%s, first_call=%s, second_call=%s, vc_remark=%s, 
                             job_remark=%s, updatedate=%s WHERE id=%s"""
                    cursor.execute(sql, (passenger_name, pickup, dropoff, combined_dt, in_group, in_flight, in_time, in_room, 
                                         in_type, in_plate, in_driver, in_mobile, in_1st, in_2nd, in_vc_rem, in_job_rem, now, selected_id))
                    st.success("✅ อัปเดตข้อมูลเรียบร้อย!")
                else: # สร้างใหม่
                    year_month = now.strftime("%Y%m")
                    cursor.execute("SELECT COUNT(*) FROM bookings WHERE voucher_no LIKE %s", (f"VC{year_month}%",))
                    auto_v = f"VC{year_month}{str(cursor.fetchone()[0] + 1).zfill(5)}"
                    sql = """INSERT INTO bookings (voucher_no, passenger_name, pickup_location, dropoff_location, booking_time, 
                             status, hotel_group, flight_no, flight_time, room_no, car_type, car_plate, driver_name_text, 
                             mobile_no, first_call, second_call, vc_remark, job_remark, createdate, updatedate) 
                             VALUES (%s, %s, %s, %s, %s, 'Pending', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                    cursor.execute(sql, (auto_v, passenger_name, pickup, dropoff, combined_dt, in_group, in_flight, in_time, 
                                         in_room, in_type, in_plate, in_driver, in_mobile, in_1st, in_2nd, in_vc_rem, in_job_rem, now, now))
                    st.success(f"🎉 บันทึกใบงานใหม่สำเร็จ: {auto_v}")
            db.commit()
            st.rerun()
        except Exception as e: st.error(f"❌ Error: {e}")
        finally: 
            if db and db.open: db.close()

elif choice == "🖥️ Dispatcher" and user_role in ["admin", "dispatcher"]:
    st.title("🎛️ แผงควบคุมสำหรับ Dispatcher")
    st.write("---")
    db = None
    try:
        db = get_connection()
        cursor = db.cursor()
        cursor.execute("SELECT line_user_id, name FROM users WHERE role = 'driver' AND status = 'Active'")
        drivers_data = cursor.fetchall()
        driver_options = {f"🚗 {d[1]} ({d[0][:6]}...)": d[0] for d in drivers_data}
        
        df_bookings = pd.read_sql("""
            SELECT id, voucher_no, passenger_name, pickup_location, dropoff_location, status, driver_id 
            FROM bookings WHERE status IN ('Pending', 'Assigned') ORDER BY id DESC
        """, db)
        
        if not df_bookings.empty:
            df_bookings['คนขับที่รับงาน'] = df_bookings['driver_id'].map(lambda x: dict(drivers_data).get(x, "ยังไม่ได้จ่ายงาน") if x else "ยังไม่ได้จ่ายงาน")
            st.write("### 📊 ตารางสถานะงาน")
            st.dataframe(df_bookings[['voucher_no', 'passenger_name', 'status', 'คนขับที่รับงาน']], width='stretch', hide_index=True)
            
            col_assign, col_complete = st.columns(2)
            with col_assign:
                st.write("### 🚖 จ่ายงานใหม่")
                job_map = {f"🎫 {row['voucher_no']} ({row['passenger_name']})": row['id'] for _, row in df_bookings.iterrows()}
                sel_job = st.selectbox("เลือกงาน", list(job_map.keys()))
                sel_driver = st.selectbox("เลือกคนขับ", list(driver_options.keys()))
                
                if st.button("💾 บันทึกการมอบหมาย"):
                    now_time = dt_module.datetime.now()
                    cursor.execute("UPDATE bookings SET driver_id = %s, status = 'Assigned', updatedate = %s WHERE id = %s", 
                                   (driver_options[sel_driver], now_time, job_map[sel_job]))
                    db.commit()
                    send_line_message(f"🚖 มีงานใหม่มอบหมายถึงคุณ!\nเลขใบงาน: {sel_job}\nกรุณาเข้าแอปเพื่อกดรับงานครับ", driver_options[sel_driver])
                    st.success("จ่ายงานเรียบร้อย!")
                    st.rerun()

            with col_complete:
                st.write("### 🏁 ปิดงาน")
                active_jobs = df_bookings[df_bookings['status'] == 'Assigned']
                if not active_jobs.empty:
                    job_opts = {f"✅ {row['voucher_no']}": row['id'] for _, row in active_jobs.iterrows()}
                    sel_done = st.selectbox("เลือกงานปิดสถานะ", list(job_opts.keys()))
                    if st.button("🏁 ยืนยันปิดงาน"):
                        now_time = dt_module.datetime.now()
                        cursor.execute("UPDATE bookings SET status = 'Completed', updatedate = %s WHERE id = %s", (now_time, job_opts[sel_done]))
                        db.commit()
                        st.success("ปิดงานสำเร็จ!")
                        st.rerun()
                else: st.info("ไม่มีงานที่กำลังวิ่งอยู่ให้กดปิด")
        else: st.info("✨ ไม่มีงานค้างในระบบ")
    except Exception as e: st.error(f"Error: {e}")
    finally: 
        if db and db.open: db.close()

elif choice == "🚖 งานของฉัน (Driver)" and user_role in ["admin", "driver"]:
    st.title("🚖 งานของฉัน (Driver)")
    driver_name = "คนขับรถ"
    db = None
    try:
        db = get_connection()
        cursor = db.cursor() 
        cursor.execute("SELECT name FROM users WHERE line_user_id = %s", (current_id,))
        res = cursor.fetchone()
        if res: driver_name = res[0]
        st.subheader(f"👋 สวัสดีคุณ: {driver_name}")
        st.write("---")
        
        df_driver = pd.read_sql("""
            SELECT id, voucher_no, passenger_name, pickup_location, dropoff_location, status,
                   hotel_group, flight_no, room_no, car_plate, mobile_no, vc_remark, job_remark
            FROM bookings WHERE driver_id = %s AND status IN ('Assigned', 'Accepted') ORDER BY booking_time ASC
        """, db, params=(current_id,))
        
        if not df_driver.empty:
            st.write("### 📥 รายการงานที่ได้รับมอบหมาย")
            st.dataframe(df_driver[['voucher_no', 'passenger_name', 'pickup_location', 'dropoff_location', 'hotel_group', 'flight_no', 'car_plate', 'status']], width='stretch', hide_index=True)
            
            # เปิดให้คนขับดูข้อมูลสายโทรศัพท์และข้อมูลใบงานจาก Booker ได้ละเอียดผ่านหน้าต่างแอป
            st.write("🔍 **รายละเอียดงานจองของคุณโดยละเอียด:**")
            for _, r in df_driver.iterrows():
                with st.expander(f"📋 ใบงาน {r['voucher_no']} - คุณ {r['passenger_name']}"):
                    st.write(f"🏨 **โรงแรม (Group):** {r['hotel_group']} | **ห้องพัก:** {r['room_no']}")
                    st.write(f"✈️ **เที่ยวบิน:** {r['flight_no']} | **ทะเบียนรถ:** {r['car_plate']}")
                    st.write(f"📱 **เบอร์โทรติดต่อ:** {r['mobile_no']}")
                    st.write(f"💬 **หมายเหตุ Voucher:** {r['vc_remark']}")
                    st.write(f"💬 **หมายเหตุงาน:** {r['job_remark']}")

            assigned_jobs = df_driver[df_driver['status'] == 'Assigned']
            if not assigned_jobs.empty:
                st.write("---")
                st.write("### 📥 งานใหม่รอรับทราบ")
                job_map = {f"🎫 {row['voucher_no']} | ลูกค้า {row['passenger_name']}": (row['id'], row['voucher_no']) for _, row in assigned_jobs.iterrows()}
                selected_job = st.selectbox("เลือกงานที่ต้องการรับ", list(job_map.keys()))
                
                if st.button("✅ กดรับทราบและยอมรับงาน"):
                    target_job_id = job_map[selected_job][0]
                    target_voucher = job_map[selected_job][1]
                    now_time = dt_module.datetime.now()
                    
                    cursor.execute("UPDATE bookings SET status = 'Accepted', updatedate = %s WHERE id = %s", (now_time, target_job_id))
                    db.commit()
                    send_line_message(f"✅ คนขับ '{driver_name}' กดรับทราบงาน Voucher: {target_voucher} เรียบร้อยแล้วครับ!", current_id)
                    st.success("รับงานเรียบร้อย!")
                    st.rerun()
        else: st.info("✨ ปัจจุบันคุณยังไม่มีงานค้างที่ต้องปฏิบัติครับ")
    except Exception as e: st.error(f"Error Driver Page: {e}")
    finally: 
        if db and db.open: db.close()

elif choice == "✈️ Airport Staff" and user_role in ["admin", "airportstaff"]:
    st.title("✈️ ตรวจสอบสถานะรถ (Airport Staff)")
    st.subheader("📋 ตารางมอนิเตอร์รถยนต์และคนขับที่กำลังปฏิบัติงาน")

    db = None
    try:
        db = get_connection()
        # 💡 ปรับปรุงคิวรี: ดึงฟิลด์ใหม่ทั้งหมดออกมาร่วมแสดงผลบนหน้าจอ Airport Staff
        query = """
            SELECT b.voucher_no AS 'เลข Voucher', 
                   b.passenger_name AS 'ชื่อผู้โดยสาร', 
                   b.hotel_group AS 'Group (โรงแรม)',
                   b.flight_no AS 'Flight',
                   b.flight_time AS 'เวลาบิน',
                   b.room_no AS 'ห้อง',
                   b.car_type AS 'ประเภทรถ',
                   b.car_plate AS 'ทะเบียนรถ',
                   b.mobile_no AS 'เบอร์โทร',
                   b.status AS 'สถานะงาน', 
                   u.name AS 'คนขับระบบ (LINE)',
                   b.driver_name_text AS 'ชื่อคนขับ (ระบุ)'
            FROM bookings b 
            LEFT JOIN users u ON b.driver_id = u.line_user_id
            WHERE b.status IN ('Assigned', 'Accepted') 
            ORDER BY b.booking_time ASC
        """
        df_airport = pd.read_sql(query, db)
        
        if not df_airport.empty:
            st.write("✨ แสดงงานคิวรถที่กำลังดำเนินการภาคพื้นสนามบินในขณะนี้")
            
            # ฟังก์ชันทำไฮไลท์สีแยกสถานะงานเพื่อความสบายตา (Assigned = เหลือง, Accepted = เขียว)
            def highlight_status(row):
                color = '#fff3cd' if row['สถานะงาน'] == 'Assigned' else '#d4edda'
                return [f'background-color: {color}'] * len(row)
            
            # 💡 แสดงผลตารางตัวเต็มกางออกหน้าจอแบบ stretch พร้อมซ่อน index
            st.dataframe(df_airport.style.apply(highlight_status, axis=1), width='stretch', hide_index=True)
            
            st.write("---")
            col1, col2 = st.columns(2)
            with col1: 
                st.metric(label="🚖 กำลังเดินทาง (Assigned)", value=len(df_airport[df_airport['สถานะงาน'] == 'Assigned']))
            with col2: 
                st.metric(label="✅ คนขับรับทราบงานแล้ว (Accepted)", value=len(df_airport[df_airport['สถานะงาน'] == 'Accepted']))
        else:
            st.info("ℹ️ ปัจจุบันยังไม่มีรถยนต์หรือใบงานใดอยู่ในสถานะกำลังปฏิบัติงานครับ")
            
    except Exception as e: 
        st.error(f"❌ เกิดข้อผิดพลาดในการดึงข้อมูลหน้า Airport Staff: {e}")
    finally: 
        if db and db.open: db.close()

elif choice == "📝 ลงทะเบียนพนักงานใหม่":
    st.title("📝 ลงทะเบียนพนักงานใหม่")
    st.write("---")
    st.markdown("### 👤 กรอกข้อมูลรายงานตัวเพื่อส่งให้แอดมินอนุมัติ")
    
    with st.form("guest_register_form", clear_on_submit=True):
        reg_name = st.text_input("1. กรุณากรอก ชื่อ - นามสกุลจริงของคุณ").strip()
        reg_line_id = st.text_input("2. ระบุรหัส LINE User ID ของคุณ", value=current_id if current_id else "")
        submit_reg = st.form_submit_button("🚀 ส่งข้อมูลลงทะเบียนระบบคิวรถ")
        
        if submit_reg:
            if not reg_name or not reg_line_id: st.error("⚠️ กรุณากรอกชื่อและรหัส LINE ID ให้ครบถ้วนก่อนกดส่งข้อมูลครับ")
            else:
                db_reg = None
                try:
                    db_reg = get_connection()
                    now_time = dt_module.datetime.now()
                    with db_reg.cursor() as cursor:
                        cursor.execute("SELECT COUNT(*) FROM users WHERE line_user_id = %s", (reg_line_id,))
                        if cursor.fetchone()[0] > 0:
                            st.warning("⚠️ ขออภัยครับ! คุณเคยลงทะเบียนในระบบเรียบร้อยแล้ว ไม่ต้องลงทะเบียนซ้ำครับ")
                        else:
                            # 💡 แก้ไขข้อ 2: เมื่อกดส่งสิทธิ์พนักงานใหม่ทางหน้าเว็บตรง ๆ ให้บันทึกระบุ createdate, updatedate ไปด้วย
                            sql = "INSERT INTO users (line_user_id, name, role, status, createdate, updatedate) VALUES (%s, %s, 'guest', 'Active', %s, %s)"
                            cursor.execute(sql, (reg_line_id, reg_name, now_time, now_time))
                            db_reg.commit()
                            st.success(f"🎉 ส่งข้อมูลรายงานตัวของคุณ '{reg_name}' (พร้อมระบุประทับเวลาสมัคร) เรียบร้อย!")
                except Exception as e: st.error(f"❌ เกิดข้อผิดพลาดทางฐานข้อมูล: {e}")
                finally:
                    if db_reg and db_reg.open: db_reg.close()

# --- 🚪 ประตูลับ (API Endpoint สำหรับรับข้อมูลจากเว็บ GitHub Pages) ---
if "action" in q_params and q_params.get("action") == "api_register":
    api_name = q_params.get("name")[0] if isinstance(q_params.get("name"), list) else q_params.get("name")
    api_line_id = q_params.get("line_id")[0] if isinstance(q_params.get("line_id"), list) else q_params.get("line_id")
    
    if api_name and api_line_id:
        db_api = None
        try:
            db_api = get_connection()
            now_time = dt_module.datetime.now()
            with db_api.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM users WHERE line_user_id = %s", (api_line_id,))
                if cursor.fetchone()[0] > 0:
                    st.write('{"status": "duplicate", "message": "คุณเคยลงทะเบียนในระบบเรียบร้อยแล้วครับ"}')
                else:
                    # 💡 แก้ไขข้อ 2: ระบุประทับเวลาผ่านท่อประตูลับ API ลงตัวแปรคู่ทั้งสองตัวให้เรียบร้อยครับ
                    sql_api = "INSERT INTO users (line_user_id, name, role, status, createdate, updatedate) VALUES (%s, %s, 'guest', 'Active', %s, %s)"
                    cursor.execute(sql_api, (api_line_id, api_name, now_time, now_time))
                    db_api.commit()
                    st.write('{"status": "success", "message": "Register complete"}')
            st.stop()
        except Exception as e:
            st.write(f'{{"status": "error", "message": "{str(e)}"}}')
            st.stop()
        finally:
            if db_api and db_api.open: db_api.close()
