import streamlit as st
import pymysql
import pandas as pd
import requests
import datetime as dt_module

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
        st.error(f"❌ ไม่สามารถเชื่อมต่อฐานข้อมูลได้: (Error: {e})")
        st.stop()

# --- 2. ตรวจสอบสิทธิ์ ---
def check_permission(user_id):
    if not user_id or user_id.startswith("GUEST_") or "*" in user_id: return "guest"
    uid = user_id.strip().lower()
    mapping = {
        "admin01": "admin", "booker01": "booker", "dispatcher01": "dispatcher", 
        "driver01": "driver", "staff01": "airportstaff", "airportstaff01": "airportstaff"
    }
    if uid in mapping: return mapping[uid]
    db = None
    try:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT role, status FROM users WHERE line_user_id = %s", (user_id,))
            res = cursor.fetchone()
            if res and res[1] == "Active": return str(res[0]).lower()
            return "guest"
    except: return "guest"
    finally:
        if db and db.open: db.close()

st.set_page_config(page_title="ระบบจัดการรถ Hunsa", layout="wide")

# =================================================================
# 🎨 💡 ข้อ 1: สไตล์ CSS บีบปรับขนาดหัวข้อทุกหน้าจอให้เล็กลง สวยงาม พอดีจอมือถือ
# =================================================================
st.markdown("""
    <style>
    /* จำกัดขนาดตัวอักษรของ Title และ Subheader ทุกหน้าจอ */
    h1, .stTitle, [data-testid="stHeader"] h1 {
        font-size: 24px !important;
        font-weight: 700 !important;
        color: #1e293b !important;
        margin-top: 5px !important;
        margin-bottom: 5px !important;
    }
    h2, h3, .stSubheader {
        font-size: 18px !important;
        font-weight: 600 !important;
        color: #334155 !important;
    }
    /* บีบขนาดบนหน้าจอมือถือความกว้างไม่เกิน 768px */
    @media (max-width: 768px) {
        h1, .stTitle {
            font-size: 20px !important;
        }
        h2, h3, .stSubheader {
            font-size: 16px !important;
        }
        .stButton button {
            font-size: 13px !important;
            padding: 4px 8px !important;
        }
        .stDataFrame div, table th, table td {
            font-size: 12px !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# จัดทำตัวแปร Session State สำหรับคุมสถานะเปิด-ปิดหน้าระบบย่อย/ปุ่มลิงก์
if "booker_mode" not in st.session_state: st.session_state.booker_mode = "list"
if "selected_booking_id" not in st.session_state: st.session_state.selected_booking_id = None
if "dispatcher_mode" not in st.session_state: st.session_state.dispatcher_mode = "list"

# ดักรับ LINE User ID จาก URL
q_params = st.query_params
line_id_from_url = q_params.get("user") or q_params.get("lineidtoemp")
if line_id_from_url:
    st.session_state.default_user_id = str(line_id_from_url[0] if isinstance(line_id_from_url, list) else line_id_from_url).strip()

current_id = st.sidebar.text_input("ระบุ LINE User ID", value=st.session_state.get("default_user_id", "")).strip()
st.session_state.default_user_id = current_id

user_role = check_permission(current_id)
if not current_id or user_role == "guest": user_role = "guest"
st.sidebar.info(f"สิทธิ์ผู้ใช้งาน: {user_role.upper()}")

# ตั้งค่าแท็บเมนู
menu_options = []
if user_role == "admin": menu_options = ["🏠 Dashboard", "➕ Booker", "🖥️ Dispatcher", "🚖 งานของฉัน (Driver)", "✈️ Airport Staff", "📝 ลงทะเบียนพนักงานใหม่"]
elif user_role == "booker": menu_options = ["➕ Booker"]
elif user_role == "dispatcher": menu_options = ["🖥️ Dispatcher"]
elif user_role == "driver": menu_options = ["🚖 งานของฉัน (Driver)"]
elif user_role == "airportstaff": menu_options = ["✈️ Airport Staff"]
else: menu_options = ["📝 ลงทะเบียนพนักงานใหม่"]

if user_role == "guest": menu_options = ["📝 ลงทะเบียนพนักงานใหม่"]
choice = st.sidebar.radio("เมนูใช้งาน", options=menu_options)

# --- 3. ส่วนควบคุมการแสดงหน้าจอแต่ละบทบาท ---

# =================================================================
# 🏠 0. หน้าสำหรับ DASHBOARD & USER MANAGEMENT (เวอร์ชันอัปเดตช่องเบอร์โทรศัพท์พนักงาน)
# =================================================================
if choice == "🏠 Dashboard" and user_role in ["admin", "dispatcher"]:
    st.title("🏠 Dashboard ระบบจัดการรถ Hunsa")
    st.write("---")
    
    # ส่วนสรุปจำนวนงาน (Metrics)
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
        col_m1.metric("⏳ งานรอจัดสรร (Pending)", count_pending)
        col_m2.metric("🚀 รถกำลังวิ่ง (Active)", count_active)
        col_m3.metric("🚖 คนขับในระบบทั้งหมด", count_drivers)
    except Exception as e: 
        st.error(f"Error Metric: {e}")
    finally: 
        if db and db.open: db.close()

    # แสดงโซนจัดการสิทธิ์พนักงาน เฉพาะผู้ใช้ระดับ Admin เท่านั้น
    if user_role == "admin":
        st.write("<br><br>", unsafe_allow_html=True)
        st.title("👥 ระบบจัดการสิทธิ์ผู้ใช้งาน (User Management)")
        st.write("---")
        
        st.subheader("⏳ รายชื่อพนักงานใหม่ที่รออนุมัติสิทธิ์ (Guests)")
        db = None
        try:
            db = get_connection()
            with db.cursor() as cursor:
                # 💡 ดึงฟิลด์เบอร์โทรศัพท์พนักงานออกมาแสดงในตารางตรวจสอบด้วย
                cursor.execute("SELECT line_user_id, name, phone_no, DATE_FORMAT(createdate, '%d/%m/%Y %H:%M') FROM users WHERE role = 'guest'")
                guests_data = cursor.fetchall()
            if guests_data:
                df_guests = pd.DataFrame(guests_data, columns=['รหัส LINE User ID', 'ชื่อรายงานตัวพนักงาน', 'เบอร์โทรศัพท์', 'วันที่สมัครเข้ามา'])
                st.dataframe(df_guests, use_container_width=True, hide_index=True)
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
                # 💡 ดึงฟิลด์ phone_no ของทุกคนออกมาร่วมเตรียมหยอดลงกล่องอินพุต
                cursor.execute("SELECT line_user_id, name, role, status, phone_no FROM users")
                all_users = cursor.fetchall()
            user_list_options = {f"👤 {u[1]} ({u[2].upper()}) - [{u[3] if u[3] else 'Active'}]": u for u in all_users}
        except Exception as e: 
            st.error(f"ดึงข้อมูลผู้ใช้ล้มเหลว: {e}")
        finally:
            if db and db.open: db.close()

        col_form_edit, col_form_del = st.columns([2, 1])
        with col_form_edit:
            st.write("📝 **ระบบลงทะเบียน / แก้ไข และ ปรับสถานะพนักงาน**")
            select_user_action = st.selectbox("💡 เลือกพนักงานที่ต้องการแก้ไข", options=["➕ ลงทะเบียนพนักงานใหม่ / กรอกเอง"] + list(user_list_options.keys()))
            init_id, init_name, init_role, init_status, init_phone = "", "", "driver", "Active", ""
            
            if select_user_action != "➕ ลงทะเบียนพนักงานใหม่ / กรอกเอง":
                user_data = user_list_options[select_user_action]
                init_id = user_data[0]
                init_name = user_data[1]
                init_role = user_data[2].lower() if user_data[2] else "driver"
                init_status = user_data[3] if user_data[3] else "Active"
                init_phone = user_data[4] if user_data[4] else "" # ดึงค่าเบอร์โทรเดิมจาก DB

            with st.form("user_management_form", clear_on_submit=False):
                new_line_id = st.text_input("ระบุ LINE User ID", value=init_id).strip()
                new_name = st.text_input("ระบุชื่อ-นามสกุลจริง ของพนักงาน", value=init_name).strip()
                
                # 💡 [เพิ่มใหม่] ช่องระบุเบอร์โทรศัพท์มือถือ สำหรับกรณีคนขับรถต้องการสลับสับเปลี่ยนเบอร์โทรในระบบ
                new_phone = st.text_input("📱 เบอร์โทรศัพท์มือถือพนักงาน", value=init_phone, placeholder="เช่น 0812345678").strip()
                
                roles_pool = ["admin", "booker", "dispatcher", "driver", "airportstaff", "guest"]
                new_role = st.selectbox("กำหนดตำแหน่ง (Role)", roles_pool, index=roles_pool.index(init_role) if init_role in roles_pool else 3)
                status_pool = ["Active", "Inactive"]
                new_status = st.radio("🚦 Status การใช้งานระบบ", status_pool, index=status_pool.index(init_status) if init_status in status_pool else 0, horizontal=True)
                submit_user = st.form_submit_button("💾 อนุมัติและบันทึกสิทธิ์พนักงาน")
                
                if submit_user:
                    if new_line_id and new_name:
                        try:
                            conn = get_connection()
                            now_time = dt_module.datetime.now()
                            with conn.cursor() as cursor:
                                # 💡 ทำการอัปเดตคอลัมน์ phone_no เพิ่มเติมเข้าคำสั่ง SQL ด้วยระบบ ON DUPLICATE KEY UPDATE
                                sql = """
                                    INSERT INTO users (line_user_id, name, role, status, phone_no, createdate, updatedate) 
                                    VALUES (%s, %s, %s, %s, %s, %s, %s) 
                                    ON DUPLICATE KEY UPDATE name = %s, role = %s, status = %s, phone_no = %s, updatedate = %s
                                """
                                cursor.execute(sql, (new_line_id, new_name, new_role, new_status, new_phone, now_time, now_time, 
                                                     new_name, new_role, new_status, new_phone, now_time))
                            conn.commit(); conn.close()
                            st.success(f"🎉 บันทึกข้อมูลพนักงานและอัปเดตเบอร์โทรศัพท์เรียบร้อยแล้ว!")
                            st.rerun()
                        except Exception as e: 
                            st.error(f"❌ เกิดข้อผิดพลาดทางฐานข้อมูล: {e}")
                    else: 
                        st.warning("⚠️ รบกวนกรอก LINE ID และชื่อพนักงานให้ครบถ้วนครับ")

        with col_form_del:
            st.write("❌ **โซนอันตราย**")
            with st.form("user_delete_form"):
                user_to_delete = st.selectbox("เลือกรายชื่อที่จะลบทิ้งเด็ดขาด", options=list(user_list_options.keys()))
                confirm_delete = st.checkbox("⚠️ ยืนยันว่าต้องการลบข้อมูลพนักงานคนนี้จริง ๆ")
                btn_delete = st.form_submit_button("🗑️ ลบพนักงานออกถาวร")
                
                if btn_delete:
                    if confirm_delete and user_to_delete:
                        target_del_id = user_list_options[user_to_delete][0]
                        try:
                            conn = get_connection()
                            with conn.cursor() as cursor:
                                cursor.execute("SELECT COUNT(*) FROM bookings WHERE driver_id = %s", (target_del_id,))
                                if cursor.fetchone()[0] > 0: 
                                    st.error("❌ ไม่สามารถลบได้ เนื่องจากมีประวัติการวิ่งงานในระบบแล้ว")
                                else:
                                    cursor.execute("DELETE FROM users WHERE line_user_id = %s", (target_del_id,))
                                    conn.commit()
                                    st.success("🗑️ ลบข้อมูลพนักงานเรียบร้อยแล้ว!")
                                    st.rerun()
                            conn.close()
                        except Exception as e: 
                            st.error(f"เกิดข้อผิดพลาด: {e}")
                    else: 
                        st.warning("⚠️ โปรดติ๊กเครื่องหมายถูกเพื่อยืนยันก่อนกดปุ่มลบครับ")

# =================================================================
# ➕ 1. หน้าสำหรับ BOOKER (เวอร์ชันเสถียรที่สุด 100% แก้บั๊กลูปค้าง)
# =================================================================
elif choice == "➕ Booker":
    st.title("📋 ระบบจัดการงานจองรถ (ฝั่ง Booker)")
    
    # 1. ดึงรายการ Pending ทั้งหมดมาทำระบบเลือกดึงข้อมูลแก้ไขแบบไร้บั๊ก
    booking_dropdown_options = {}
    try:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT id, voucher_no, passenger_name FROM bookings WHERE status = 'Pending' ORDER BY id DESC")
            all_b_pending = cursor.fetchall()
            booking_dropdown_options = {f"🔗 [แก้ไข] {b[1]} - คุณ {b[2]}": b[0] for b in all_b_pending}
    except Exception as e:
        st.error(f"โหลดตัวเลือกแก้ไขผิดพลาด: {e}")
    finally:
        if db and db.open: db.close()

    if st.session_state.booker_mode == "list":
        st.subheader("รายการงานจองรอดำเนินการ (Status = 'Pending')")
        
        # 1.3 ปุ่มสร้างรายการใหม่ (New Button)
        col_btn_new, col_select_edit = st.columns([1, 2])
        with col_btn_new:
            if st.button("➕ New (สร้างรายการใหม่)", use_container_width=True):
                st.session_state.booker_mode = "create"
                st.session_state.selected_booking_id = None
                
                # ล้างค่า State เที่ยวบินเก่าออกให้สะอาดก่อนคีย์งานใหม่
                if "bk_flight_upper" in st.session_state: del st.session_state.bk_flight_upper
                if "bk_flight_raw" in st.session_state: del st.session_state.bk_flight_raw
                st.rerun()
                
        with col_select_edit:
            # 💡 ระบบสลับหน้าไปโหมดแก้ไขข้อมูลแบบปลอดภัย ไม่ผ่านการคลิกตารางให้พัง
            if booking_dropdown_options:
                chosen_edit = st.selectbox(
                    "🎯 เลือกใบงานจองที่ต้องการแก้ไขข้อมูลด้านล่าง", 
                    options=["-- เลือกใบงานเพื่อแก้ไข --"] + list(booking_dropdown_options.keys())
                )
                if chosen_edit != "-- เลือกใบงานเพื่อแก้ไข --":
                    st.session_state.selected_booking_id = booking_dropdown_options[chosen_edit]
                    st.session_state.booker_mode = "edit"
                    
                    # ล้างค่า State ชั่วคราวเพื่อให้ระบบโหลดค่าใหม่จากฐานข้อมูลมาใช้งาน
                    if "bk_flight_upper" in st.session_state: del st.session_state.bk_flight_upper
                    if "bk_flight_raw" in st.session_state: del st.session_state.bk_flight_raw
                    st.rerun()

        # 2. แสดงตารางสรุปผลข้อมูลหน้ารายการของ Booker
        db = get_connection()
        df_booker = pd.read_sql("""
            SELECT voucher_no AS 'Voucher', passenger_name AS 'Guest Name', 
                   hotel_group AS 'Hotel', DATE_FORMAT(booking_time, '%d/%m/%Y') AS 'Service Date',
                   DATE_FORMAT(booking_time, '%H:%M') AS 'Service Time'
            FROM bookings WHERE status = 'Pending' ORDER BY id DESC
        """, db)
        db.close()
        
        if not df_booker.empty:
            st.dataframe(df_booker, use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ ไม่มีใบงานสถานะ Pending ค้างอยู่ในระบบขณะนี้ครับ")
            
    elif st.session_state.booker_mode in ["create", "edit"]:
        st.subheader("📝 ฟอร์มบันทึกข้อมูลใบงานจองรถ")
        
        init_pass, init_pick, init_dest = "", "", ""
        init_date = dt_module.date.today()
        init_time = dt_module.time(12, 0)
        init_car_type = "Camry"
        init_remark = ""
        
        elif st.session_state.booker_mode in ["create", "edit"]:
        st.subheader("📝 ฟอร์มบันทึกข้อมูลใบงานจองรถ")
        
        init_pass, init_pick, init_dest = "", "", ""
        init_date = dt_module.date.today()
        init_time = dt_module.time(12, 0)
        init_car_type = "Camry"
        init_remark = ""
        init_flight = ""
        
        if st.session_state.booker_mode == "edit":
            db = get_connection()
            with db.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("SELECT * FROM bookings WHERE id = %s", (st.session_state.selected_booking_id,))
                curr_b = cursor.fetchone()
            db.close()
            if curr_b:
                init_pass = curr_b['passenger_name']
                init_pick = curr_b['pickup_location']
                init_dest = curr_b['dropoff_location']
                init_car_type = curr_b['car_type'] if curr_b['car_type'] else "Camry"
                init_remark = curr_b['job_remark'] if curr_b['job_remark'] else ""
                init_flight = curr_b['flight_no'] if curr_b['flight_no'] else ""
                if curr_b['booking_time']:
                    init_date = curr_b['booking_time'].date()
                    init_time = curr_b['booking_time'].time()

        # ฟอร์ม Booker (ถอด on_change และ Callback ออกทั้งหมดเพื่อแก้ Error จากรูป 114134.jpg)
        with st.form("booker_form"):
            p_name = st.text_input("Guest Name (ชื่อผู้โดยสาร)", value=init_pass)
            
            car_choices = ["Camry", "Commuter", "E-Class", "S-Class", "V-Class", "Alphard", "BMW"]
            p_car_type = st.selectbox("Car Types. 🔽", options=car_choices, index=car_choices.index(init_car_type) if init_car_type in car_choices else 0)
            
            # 💡 เปลี่ยนเป็นช่องข้อความปกติ ไม่ใส่ Callback ในฟอร์มตามกฎ Streamlit
            p_flight = st.text_input("Flight no. (เที่ยวบิน)", value=init_flight)
            
            p_pickup = st.text_input("Pickup (จุดรับ)", value=init_pick)
            p_dest = st.text_input("Destination (จุดส่ง)", value=init_dest)
            
            c_date = st.date_input("Service Date (วันที่เดินทาง)", value=init_date)
            c_time = st.time_input("Time. (เวลาเดินทาง)", value=init_time, step=60)
            
            p_remark = st.text_area("Remark (หมายเหตุ)", value=init_remark)
            
            col_frm_b1, col_frm_b2 = st.columns(2)
            with col_frm_b1: btn_save = st.form_submit_button("💾 บันทึกข้อมูล")
            with col_frm_b2: btn_cancel = st.form_submit_button("❌ ยกเลิกรายการ")
            
            if btn_save:
                if not p_name or not p_pickup or not p_dest:
                    st.error("⚠️ กรุณากรอกข้อมูลหลักให้ครบถ้วนก่อนส่งบันทึกครับ")
                else:
                    db = get_connection()
                    now = dt_module.datetime.now()
                    comb_dt = dt_module.datetime.combine(c_date, c_time)
                    
                    # 💡 [ทางออกชี้ขาด] ทำการแปลง Flight No. เป็นตัวพิมพ์ใหญ่ที่บรรทัดนี้ตอนกดบันทึกแทน! สะอาด ปลอดภัย ชัวร์ 100%
                    final_flight_no = p_flight.upper().strip() if p_flight else ""
                    
                    with db.cursor() as cursor:
                        if st.session_state.booker_mode == "create":
                            year_month_str = now.strftime("%Y%m")
                            cursor.execute("SELECT COUNT(*) FROM bookings WHERE voucher_no LIKE %s", (f"BK{year_month_str}%",))
                            auto_voucher_no = f"BK{year_month_str}{str(cursor.fetchone()[0] + 1).zfill(5)}"
                            
                            cursor.execute("""
                                INSERT INTO bookings (voucher_no, passenger_name, car_type, flight_no, pickup_location, dropoff_location, booking_time, job_remark, status, createdate, updatedate)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Pending', %s, %s)
                            """, (auto_voucher_no, p_name, p_car_type, final_flight_no, p_pickup, p_dest, comb_dt, p_remark, now, now))
                        else:
                            cursor.execute("""
                                UPDATE bookings SET passenger_name = %s, car_type = %s, flight_no = %s, pickup_location = %s, dropoff_location = %s, booking_time = %s, job_remark = %s, updatedate = %s
                                WHERE id = %s
                            """, (p_name, p_car_type, final_flight_no, p_pickup, p_dest, comb_dt, p_remark, now, st.session_state.selected_booking_id))
                    db.commit(); db.close()
                    st.success("บันทึกข้อมูลเรียบร้อยแล้ว!")
                    st.session_state.booker_mode = "list"
                    st.rerun()
                    
            if btn_cancel:
                st.session_state.booker_mode = "list"
                st.rerun()
                
# =================================================================
# 🖥️ 2. หน้าสำหรับ DISPATCHER (เวอร์ชันซ่อมแซมระบดึงเบอร์โทรศัพท์อัตโนมัติ)
# =================================================================
elif choice == "🖥️ Dispatcher" and user_role in ["admin", "dispatcher"]:
    st.title("🎛️ แผงควบคุมงานสำหรับ Dispatcher")
    
    if st.session_state.dispatcher_mode == "list":
        st.subheader("2.1 รายการใบงานจองจาก Booker (Status = 'Pending')")
        
        db = get_connection()
        df_disp = pd.read_sql("""
            SELECT id, voucher_no AS 'Voucher', hotel_group AS 'Group Agency', pickup_location AS 'Hotel',
                   DATE_FORMAT(booking_time, '%d/%m/%Y') AS 'Service Date', DATE_FORMAT(booking_time, '%H:%M') AS 'Service Time',
                   car_type AS 'Car Type', passenger_name AS 'Guest Name', pickup_location AS 'Pickup',
                   dropoff_location AS 'Destination', job_type AS 'Service Type', job_remark AS 'Remark',
                   driver_name_text AS 'Driver Name', mobile_no AS 'Tel.', car_plate AS 'Plate No.'
            FROM bookings WHERE status = 'Pending' ORDER BY id DESC
        """, db)
        db.close()
        
        if not df_disp.empty:
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1: f_agency = st.selectbox("🔽 คัดกรอง Group Agency", ["ทั้งหมด"] + list(df_disp['Group Agency'].dropna().unique()))
            with col_f2: f_car = st.selectbox("🔽 คัดกรอง Car Type", ["ทั้งหมด"] + list(df_disp['Car Type'].dropna().unique()))
            with col_f3: f_service = st.selectbox("🔽 คัดกรอง Service Type", ["ทั้งหมด"] + list(df_disp['Service Type'].dropna().unique()))
                
            if f_agency != "ทั้งหมด": df_disp = df_disp[df_disp['Group Agency'] == f_agency]
            if f_car != "ทั้งหมด": df_disp = df_disp[df_disp['Car Type'] == f_car]
            if f_service != "ทั้งหมด": df_disp = df_disp[df_disp['Service Type'] == f_service]
            
            for index, row in df_disp.iterrows():
                with st.expander(f"🎫 บัตรงาน Voucher: {row['Voucher']} - คุณ {row['Guest Name']}"):
                    st.write(f"**โรงแรม:** {row['Hotel']} -> **ปลายทาง:** {row['Destination']}")
                    st.write(f"**เวลาปฏิบัติงาน:** {row['Service Date']} ตอน {row['Service Time']} ({row['Car Type']})")
                    
                    phone_num = row['Tel.'] if row['Tel.'] else "ไม่มีเบอร์"
                    st.markdown(f"📱 **เบอร์โทรคนขับ:** <a href='tel:{phone_num}'>{phone_num}</a>", unsafe_allow_html=True)
                    
                    if st.button("🛠️ จัดการคีย์ข้อมูล / แก้ไขใบงาน", key=f"dp_edit_{row['id']}"):
                        st.session_state.selected_booking_id = int(row['id'])
                        st.session_state.dispatcher_mode = "edit"
                        
                        # เคลียร์ state เก่าของคนขับออกเมื่อกดเปิดงานชิ้นใหม่
                        if "selected_driver_name" in st.session_state: del st.session_state.selected_driver_name
                        st.rerun()
        else:
            st.info("✨ ไม่มีรายการงานรอดำเนินการตกค้างในระบบ")
            
    elif st.session_state.dispatcher_mode == "edit":
        st.subheader("🛠️ หน้าแก้ไขและมอบหมายคนขับโดยละเอียด (Dispatcher)")
        
        db = get_connection()
        with db.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM bookings WHERE id = %s", (st.session_state.selected_booking_id,))
            b_data = cursor.fetchone()
            cursor.execute("SELECT name, phone_no FROM users WHERE role = 'driver' AND status = 'Active'")
            drivers_list = cursor.fetchall()
        db.close()
        
        driver_phones = {d['name']: (d['phone_no'] if d['phone_no'] else "") for d in drivers_list}
        driver_names_pool = ["-- โปรดเลือกคนขับรถ --"] + list(driver_phones.keys())
        
        if b_data:
            init_driver_idx = 0
            if b_data['driver_name_text'] in driver_names_pool:
                init_driver_idx = driver_names_pool.index(b_data['driver_name_text'])

            # 💡 1. สร้างฟังก์ชันแปลงเที่ยวบินเป็นตัวใหญ่แบบ Callback ป้องกัน Infinite Rerun ลูปพัง
            def uppercase_flight_dispatcher():
                if "dp_flight_raw" in st.session_state and st.session_state.dp_flight_raw:
                    st.session_state.dp_flight_upper = st.session_state.dp_flight_raw.upper().strip()

            # ตั้งค่าเริ่มต้นประทับลง Session State ความปลอดภัย
            if "dp_flight_upper" not in st.session_state:
                st.session_state.dp_flight_upper = b_data['flight_no'] if b_data['flight_no'] else ""

            # ================= Group 1: ข้อมูลใบงานหลักและการเดินทาง =================
            with st.form("dispatcher_group_1"):
                st.markdown("### 🎫 1. ข้อมูลใบงานหลักและการเดินทาง")
                agency_choices = ["Bell transport", "VIG", "Courtyard SVB", "137 Pillars", "Trikaya", "อื่นๆ / คีย์ระบุเอง"]
                init_agency = b_data['hotel_group'] if b_data['hotel_group'] else "Bell transport"
                sel_agency = st.selectbox("Group Agency", options=agency_choices, index=agency_choices.index(init_agency) if init_agency in agency_choices else 5)
                
                custom_agency = ""
                if sel_agency == "อื่นๆ / คีย์ระบุเอง": 
                    custom_agency = st.text_input("ระบุ Group Agency เพิ่มเติม")
                    
                in_hotel = st.text_input("Hotel", value=b_data['pickup_location'] if b_data['pickup_location'] else "")
                in_s_date = st.date_input("Service Date", value=b_data['booking_time'].date() if b_data['booking_time'] else dt_module.date.today())
                in_s_time = st.time_input("Service Time", value=b_data['booking_time'].time() if b_data['booking_time'] else dt_module.time(12,0), step=60)
                
                car_choices = ["Camry", "Commuter", "E-Class", "S-Class", "V-Class", "Alphard", "BMW"]
                in_car_type = st.selectbox("Car Type 🔽", options=car_choices, index=car_choices.index(b_data['car_type']) if b_data['car_type'] in car_choices else 0)
                
                in_guest = st.text_input("Guest Name", value=b_data['passenger_name'])
                in_pickup = st.text_input("Pickup", value=b_data['pickup_location'])
                in_dest = st.text_input("Destination", value=b_data['dropoff_location'])
                st.form_submit_button("⏩ ถัดไป (ข้อมูลเที่ยวบิน)")

            # ================= Group 2: ข้อมูลสนามบินและหมายเหตุ =================
            with st.form("dispatcher_group_2"):
                st.markdown("### 🛫 2. ข้อมูลสนามบินและหมายเหตุเพิ่มเติม")
                in_1st = st.text_input("1st Call", value=b_data['first_call'] if b_data['first_call'] else "")
                in_2nd = st.text_input("2nd Call", value=b_data['second_call'] if b_data['second_call'] else "")
                
                service_type_options = ["1. From Airport", "2. To Airport", "3. One Way", "4. Round Trip", "5. By Hour"]
                init_service_idx = 0
                if b_data['job_type'] in service_type_options:
                    init_service_idx = service_type_options.index(b_data['job_type'])
                sel_service_type = st.selectbox("Service Type 🔽", options=service_type_options, index=init_service_idx)
                
                in_airport = st.text_input("🛫 Airport", value=b_data['airport_name'] if b_data['airport_name'] else "")
                
                # 💡 2. ผูกช่องรับข้อมูลเข้ากับระบบ Callback และ Key เพื่อดักเปลี่ยนตัวพิมพ์ใหญ่ทันทีโดยไม่ค้าง
                st.text_input(
                    "✈️ Flight No.", 
                    value=st.session_state.dp_flight_upper,
                    key="dp_flight_raw",
                    on_change=uppercase_flight_dispatcher
                )
                final_disp_flight = st.session_state.dp_flight_upper
                
                in_room = st.text_input("🔑 Room No.", value=b_data['room_no'] if b_data['room_no'] else "")
                in_remark = st.text_area("Remark (หมายเหตุ)", value=b_data['job_remark'] if b_data['job_remark'] else "")
                in_vc_remark = st.text_area("VC Remark", value=b_data['vc_remark'] if b_data['vc_remark'] else "")
                st.form_submit_button("⏩ ถัดไป (จัดสรรคนขับ)")

            st.write("---")
            # ตัวเลือก Driver Name วางอยู่นอกกลุ่มฟอร์มสุดท้ายเพื่อทำระบบดึงเบอร์โทรศัพท์ตามชื่อออโต้
            selected_driver = st.selectbox(
                "🧑 เลือก Driver Name (พนักงานคนขับรถ)", 
                options=driver_names_pool, 
                index=init_driver_idx,
                key="dispatcher_select_driver_final_widget"
            )
            
            if selected_driver != "-- โปรดเลือกคนขับรถ --":
                auto_phone_val = driver_phones.get(selected_driver, "")
            else:
                auto_phone_val = b_data['mobile_no'] if b_data['mobile_no'] else ""

            # ================= Group 3: จัดสรรคนขับยานพาหนะ =================
            with st.form("dispatcher_group_3"):
                st.markdown("### 🚖 3. จัดสรรคนขับยานพาหนะ")
                in_tel = st.text_input("Tel. (ดึงจากฐานข้อมูลให้อัตโนมัติ)", value=auto_phone_val, key=f"tel_final_field_{selected_driver}")
                in_plate = st.text_input("Plate No. (ทะเบียนรถ)", value=b_data['car_plate'] if b_data['car_plate'] else "")
                
                col_dp_f1, col_dp_f2 = st.columns(2)
                with col_dp_f1: 
                    submit_disp = st.form_submit_button("💾 บันทึกจัดสรรงานและส่งมอบ")
                with col_dp_f2: 
                    cancel_disp = st.form_submit_button("🔙 ยกเลิก/ย้อนกลับ")
                    
                if submit_disp:
                    final_agency = custom_agency if sel_agency == "อื่นๆ / คีย์ระบุเอง" else sel_agency
                    db_save = get_connection()
                    now_t = dt_module.datetime.now()
                    comb_dt = dt_module.datetime.combine(in_s_date, in_s_time)
                    final_driver_name = selected_driver if selected_driver != "-- โปรดเลือกคนขับรถ --" else ""
                    
                    with db_save.cursor() as cursor_up:
                        cursor_up.execute("""
                            UPDATE bookings SET 
                                hotel_group = %s, pickup_location = %s, booking_time = %s, car_type = %s, passenger_name = %s, 
                                dropoff_location = %s, first_call = %s, second_call = %s, job_type = %s, airport_name = %s, 
                                flight_no = %s, room_no = %s, job_remark = %s, vc_remark = %s, driver_name_text = %s, 
                                mobile_no = %s, car_plate = %s, status = 'Assigned', updatedate = %s
                            WHERE id = %s
                        """, (final_agency, in_hotel, comb_dt, in_car_type, in_guest, in_dest, in_1st, in_2nd, sel_service_type, 
                              in_airport, final_disp_flight, in_room, in_remark, in_vc_remark, final_driver_name, in_tel, in_plate, now_t, st.session_state.selected_booking_id))
                    db_save.commit(); db_save.close()
                    
                    # ล้างเคลียร์ State ข้อมูลเที่ยวบินเก่าออกเพื่อป้องกันการค้างไปงานชิ้นอื่น
                    if "dp_flight_upper" in st.session_state: del st.session_state.dp_flight_upper
                    if "dp_flight_raw" in st.session_state: del st.session_state.dp_flight_raw
                    
                    st.success("📝 อัปเดตข้อมูลและกระจายงานเข้าสมาร์ทโฟนเสร็จสิ้น!")
                    st.session_state.dispatcher_mode = "list"
                    st.rerun()
                    
                if cancel_disp:
                    if "dp_flight_upper" in st.session_state: del st.session_state.dp_flight_upper
                    if "dp_flight_raw" in st.session_state: del st.session_state.dp_flight_raw
                    st.session_state.dispatcher_mode = "list"
                    st.rerun()

# =================================================================
# ✈️ 4. หน้าสำหรับ AIRPORT REPRENSENTATIVE
# =================================================================
elif choice == "✈️ Airport Staff":
    st.title("✈️ หน้าแผงควบคุมสำหรับเจ้าหน้าที่สนามบิน (Airport Staff)")
    st.write("---")
    
    db = get_connection()
    # 💡 ปรับเงื่อนไข WHERE ให้ดึงเฉพาะใบงานที่มอบหมายระบุคนขับรถยนต์เรียบร้อยแล้วเท่านั้น
    df_airport = pd.read_sql("""
        SELECT voucher_no AS 'Voucher', passenger_name AS 'Guest Name',
               car_type AS 'Car Type', flight_no AS 'Flight No.',
               DATE_FORMAT(booking_time, '%d/%m/%Y %H:%M') AS 'Service Date/Time',
               driver_name_text AS 'Driver Name', mobile_no AS 'Driver Tel.', car_plate AS 'Plate No.',
               status AS 'Status'
        FROM bookings 
        WHERE driver_name_text IS NOT NULL 
          AND driver_name_text != '' 
          AND driver_name_text != '-- โปรดเลือกคนขับรถ --'
        ORDER BY booking_time ASC
    """, db)
    db.close()
    
    if not df_airport.empty:
        st.subheader("📋 รายการรถและคนขับพร้อมปฏิบัติงาน")
        st.dataframe(df_airport, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ ไม่มีข้อมูลใบงานจองที่คีย์ระบุชื่อคนขับค้างในระบบขณะนี้ครับ")

# =================================================================
# 🚖 5. หน้าออกแบบโมเดลการ์ดตารางงานสำหรับ DRIVER
# =================================================================
elif choice == "🚖 งานของฉัน (Driver)":
    st.title("🚖 บอร์ดงานคิวรถสำหรับพนักงานขับรถ (Driver)")
    
    db = get_connection()
    df_drv_jobs = pd.read_sql("""
        SELECT id, voucher_no, passenger_name, pickup_location, dropoff_location,
               DATE_FORMAT(booking_time, '%H:%M') AS s_time, DATE_FORMAT(booking_time, '%d-%m-%Y') AS s_date,
               flight_no, status, hotel_group
        FROM bookings WHERE status IN ('Assigned', 'Accepted') ORDER BY booking_time ASC
    """, db)
    db.close()
    
    if not df_drv_jobs.empty:
        for index, row in df_drv_jobs.iterrows():
            # 💡 ข้อ 3: ตรวจสอบและแมตช์สถานะดิบหลังบ้านอย่างถูกต้อง เพื่อควบคุมป้ายบนหน้าการ์ดมือถือคนขับ
            is_pending_accept = (row['status'] == 'Assigned')
            status_tag = "รอดำเนินการ" if is_pending_accept else "รับทราบงานแล้ว"
            
            st.markdown(f"""
            <div style="background-color: #212529; border-radius: 12px; padding: 15px; margin-bottom: 5px; border-left: 8px solid #ffc107; color: white;">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #6c757d; padding-bottom: 5px;">
                    <span style="font-size: 16px; font-weight: bold; color: #ffc107;">⏰ {row['s_time']} | 📅 {row['s_date']}</span>
                    <span style="background-color: #ff9800; color: black; font-size: 11px; padding: 3px 8px; border-radius: 6px; font-weight: bold;">{status_tag}</span>
                </div>
                <div style="margin-top: 10px; font-size: 14px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span><b style="color: #64b5f6;">HOTELS:</b> {row['pickup_location']}</span>
                        <span><b style="color: #64b5f6;">VOUCHER:</b> {row['voucher_no']}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-top: 5px;">
                        <span><b style="color: #e57373;">DESTINATION:</b> {row['dropoff_location']}</span>
                        <span><b style="color: #e57373;">FLIGHT:</b> {row['flight_no'] if row['flight_no'] else 'N/A'}</span>
                    </div>
                    <div style="margin-top: 10px; font-size: 18px; font-weight: bold; color: #ffffff;">
                        👤 {row['passenger_name']}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 💡 ข้อ 3: คืนค่าและติดตั้งปุ่มกดรับงานสีเขียวเด่นใต้กล่องการ์ดงานของคนขับรถแต่ละชิ้นอย่างสมบูรณ์แบบ
            if is_pending_accept:
                if st.button(f"✅ กดรับทราบและยอมรับงานใบงาน {row['voucher_no']}", key=f"drv_ack_{row['id']}", use_container_width=True):
                    db_ack = get_connection()
                    with db_ack.cursor() as c_ack:
                        c_ack.execute("UPDATE bookings SET status = 'Accepted', updatedate = NOW() WHERE id = %s", (row['id'],))
                    db_ack.commit(); db_ack.close()
                    st.success(f"รับทราบงานใบงาน {row['voucher_no']} เรียบร้อย!")
                    st.rerun()
                st.write("<br>", unsafe_allow_html=True)
    else: st.info("✨ ปัจจุบันยังไม่มีคิวงานค้างส่งมอบในกระดานบอร์ดครับ")

# =================================================================
# 📝 3. หน้าลงทะเบียน (REGISTER)
# =================================================================
elif choice == "📝 ลงทะเบียนพนักงานใหม่":
    st.title("📝 ลงทะเบียนพนักงานใหม่ เข้าสู่ระบบ")
    st.write("---")
    
    with st.form("register_form_new_patch"):
        reg_name = st.text_input("กรุณากรอก ชื่อ - นามสกุลจริงของคุณ")
        reg_line_id = st.text_input("รหัส LINE User ID ของคุณ", value=current_id, disabled=True)
        reg_phone = st.text_input("ระบุเบอร์โทรศัพท์มือถือสายตรงของคุณ (ฟิลด์ใหม่ 📞)", placeholder="เช่น 089-xxxxxxx")
        
        btn_reg_submit = st.form_submit_button("🚀 บันทึกส่งข้อมูลสมัครเข้าตารางระบบ")
        
        if btn_reg_submit:
            if not reg_name or not reg_phone: st.error("⚠️ กรุณากรอกชื่อและเบอร์โทรศัพท์ให้เรียบร้อยครับ")
            else:
                db_reg = get_connection()
                now_t = dt_module.datetime.now()
                with db_reg.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM users WHERE line_user_id = %s", (current_id,))
                    if cursor.fetchone()[0] > 0: st.warning("คุณเคยลงทะเบียนเรียบร้อยแล้ว!")
                    else:
                        cursor.execute("""
                            INSERT INTO users (line_user_id, name, role, status, phone_no, createdate, updatedate) 
                            VALUES (%s, %s, 'guest', 'Active', %s, %s, %s)
                        """, (current_id, reg_name, reg_phone, now_t, now_t))
                        db_reg.commit()
                        st.success("🎉 สมัครสมาชิกข้อมูลเรียบร้อยแล้ว!")
                db_reg.close()
