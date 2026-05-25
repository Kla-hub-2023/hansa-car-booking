import streamlit as st
import pymysql
import pandas as pd
import requests
import datetime as dt_module
import streamlit.components.v1 as components

# --- 1. เชื่อมต่อฐานข้อมูล ---
def get_connection():
    return pymysql.connect(
        host='mysql-22653bef-kla-e55d.c.aivencloud.com',
        user='avnadmin',
        password='AVNS_W4Huwc3abQww6NKNlG2',
        database='defaultdb',
        port=23986
    )

# --- 2. ฟังก์ชันตรวจสอบสิทธิ์ ---
def check_permission(user_id):
    if not user_id or user_id.startswith("GUEST_") or "*" in user_id: return "guest"
    uid = user_id.strip().lower()
    mapping = {"admin01": "admin", "booker01": "booker", "dispatcher01": "dispatcher", "driver01": "driver", "staff01": "airportstaff", "airportstaff01": "airportstaff"}
    if uid in mapping: return mapping[uid]
    try:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT role, status FROM users WHERE line_user_id = %s", (user_id,))
            res = cursor.fetchone()
            if res and res[1] == "Active": return str(res[0]).lower()
            return "guest"
    except: return "guest"
    finally: db.close()

st.set_page_config(page_title="ระบบจัดการรถ Hunsa", layout="wide")

# --- 3. จัดการสถานะและเมนู ---
query_params = st.query_params
if "lineidtoemp" in query_params: st.session_state.default_user_id = query_params["lineidtoemp"].strip()
elif "user" in query_params: st.session_state.default_user_id = query_params["user"].strip()

current_id = st.sidebar.text_input("ระบุ LINE User ID", value=st.session_state.get("default_user_id", "")).strip()
st.session_state.default_user_id = current_id
user_role = check_permission(current_id)
st.sidebar.info(f"สิทธิ์: {user_role.upper()}")

menu_options = []
if user_role == "admin": menu_options = ["🏠 Dashboard", "➕ Booker", "🖥️ Dispatcher", "🚖 งานของฉัน (Driver)", "✈️ Airport Staff"]
elif user_role == "booker": menu_options = ["➕ Booker"]
elif user_role == "dispatcher": menu_options = ["🖥️ Dispatcher"]
elif user_role == "driver": menu_options = ["𚖖 งานของฉัน (Driver)"]
elif user_role == "airportstaff": menu_options = ["✈️ Airport Staff"]
else: menu_options = ["📝 ลงทะเบียนพนักงานใหม่"]

if "current_menu_choice" not in st.session_state: st.session_state["current_menu_choice"] = menu_options[0]

choice = st.sidebar.radio("เมนูใช้งาน", options=menu_options, index=menu_options.index(st.session_state["current_menu_choice"]) if st.session_state["current_menu_choice"] in menu_options else 0)
st.session_state["current_menu_choice"] = choice

if user_role == "driver" and choice != "🚖 งานของฉัน (Driver)":
    st.session_state["current_menu_choice"] = "𚖖 งานของฉัน (Driver)"
    st.rerun()
    
if choice == "🏠 Dashboard":
    st.title("🏠 หน้าแรกและภาพรวมระบบ (Dashboard)")
    st.write("---")
    
    # 1. ส่วน Metric สรุปงาน
    db = get_connection()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM bookings WHERE status = 'Pending'")
            count_pending = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM bookings WHERE status IN ('Assigned', 'Accepted')")
            count_active = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'driver'")
            count_drivers = cursor.fetchone()[0]
            
            # ดึงข้อมูลการจองล่าสุด
            cursor.execute("SELECT id, voucher_no, passenger_name, pickup_location, dropoff_location, status FROM bookings ORDER BY id DESC LIMIT 5")
            recent_data = cursor.fetchall()
            
            # ดึงข้อมูลพนักงาน
            cursor.execute("SELECT line_user_id, name, role, status FROM users ORDER BY role ASC")
            users_data = cursor.fetchall()
            
        df_recent = pd.DataFrame(recent_data, columns=['ใบงานที่', 'เลข Voucher', 'ชื่อผู้โดยสาร', 'จุดรับ', 'จุดส่ง', 'สถานะ'])
        df_users = pd.DataFrame(users_data, columns=['LINE User ID', 'ชื่อ-นามสกุล', 'ตำแหน่ง', 'สถานะ'])

        # แสดง Metric
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("⏳ งานรอจัดสรร", count_pending)
        col_m2.metric("🚀 รถกำลังวิ่ง", count_active)
        col_m3.metric("🚖 คนขับทั้งหมด", count_drivers)

        st.write("---")
        
        # 2. ส่วนจัดการพนักงาน (เฉพาะ Admin)
        if user_role == "admin":
            st.write("### 👥 ระบบจัดการสิทธิ์พนักงาน (Quick Access)")
            st.dataframe(df_users, width='stretch', hide_index=True)
            
            # ทำ Selectbox เลือกรายชื่อมาแก้ไข
            user_options = {f"{row['ชื่อ-นามสกุล']} ({row['LINE User ID']})": row for _, row in df_users.iterrows()}
            selected_user = st.selectbox("เลือกพนักงานเพื่อแก้ไขข้อมูล", ["-- เลือกพนักงาน --"] + list(user_options.keys()))
            
            # ค่าเริ่มต้น
            def_id, def_name, def_role, def_status = "", "", "driver", "Active"
            if selected_user != "-- เลือกพนักงาน --":
                u = user_options[selected_user]
                def_id, def_name, def_role, def_status = u['LINE User ID'], u['ชื่อ-นามสกุล'], u['ตำแหน่ง'], u['สถานะ']

            with st.expander("➕ เพิ่ม/แก้ไขสิทธิ์พนักงาน"):
                with st.form("quick_user_mgmt"):
                    e_id = st.text_input("LINE User ID", value=def_id)
                    e_name = st.text_input("ชื่อ-นามสกุล", value=def_name)
                    e_role = st.selectbox("ตำแหน่ง", ["admin", "booker", "dispatcher", "driver", "airportstaff", "guest"], 
                                          index=["admin", "booker", "dispatcher", "driver", "airportstaff", "guest"].index(def_role) if def_role in ["admin", "booker", "dispatcher", "driver", "airportstaff", "guest"] else 3)
                    e_status = st.radio("สถานะ", ["Active", "Inactive"], index=0 if def_status=="Active" else 1, horizontal=True)
                    
                    if st.form_submit_button("💾 บันทึกสิทธิ์"):
                        cursor.execute("INSERT INTO users VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE name=%s, role=%s, status=%s", 
                                       (e_id, e_name, e_role, e_status, e_name, e_role, e_status))
                        db.commit()
                        st.success("บันทึกเรียบร้อย!")
                        st.rerun()

        st.write("---")
        st.write("### ⏱️ รายการจองรถล่าสุด 5 รายการ")
        if not df_recent.empty:
            st.dataframe(df_recent, width='stretch', hide_index=True)
        else:
            st.info("ยังไม่มีประวัติการจองในระบบ")
            
    except Exception as e: st.error(f"Error: {e}")
    finally: db.close()

elif choice == "➕ Booker":
    st.title("📋 แบบฟอร์มจองรถ (Booker)")
    st.subheader("กรอกรายละเอียดการเดินทางเพื่อส่งงานให้ผู้จัดสรรรถ")

    with st.form(key="car_booking_form", clear_on_submit=True):
        st.write("### 🚗 ข้อมูลการเดินทาง")
        passenger_name = st.text_input("👤 ชื่อผู้โดยสาร / คณะเดินทาง", placeholder="เช่น คุณสมชาย สายลุย")
        pickup_location = st.text_input("📍 จุดรับ (Pickup)", placeholder="กรอกจุดรับ เช่น สนามบินสุวรรณภูมิ, โรงแรมฮันซ่า").strip()
        dropoff_location = st.text_input("🏁 จุดส่ง (Dropoff)", placeholder="กรอกจุดส่ง เช่น ตัวเมืองกรุงเทพฯ, หัวหิน").strip()
        
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
                except Exception as e: st.error(f"❌ เกิดข้อผิดพลาด: {e}")
                finally: db.close()

    st.write("---")
    st.write("### 🕒 รายการงานจองปัจจุบันของคุณ")
    try:
        db = get_connection()
        df_booker = pd.read_sql("""
            SELECT voucher_no AS 'Voucher', passenger_name AS 'ชื่อผู้โดยสาร', pickup_location AS 'จุดรับ', 
                   dropoff_location AS 'จุดส่ง', booking_time AS 'เวลาเดินทาง', status AS 'สถานะ' 
            FROM bookings WHERE status IN ('Pending', 'Assigned') ORDER BY booking_time ASC
        """, db)
        if not df_booker.empty: st.dataframe(df_booker, width='stretch', hide_index=True)
        else: st.info("💡 ยังไม่มีรายการงานค้างในระบบ")
    except Exception as e: st.error(f"❌ ไม่สามารถดึงข้อมูลได้: {e}")
    finally: db.close()
elif choice == "🖥️ Dispatcher":
    st.title("🎛️ แผงควบคุมสำหรับ Dispatcher")
    st.write("---")
    
    db = get_connection()
    try:
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
            # เพิ่มคอลัมน์ชื่อคนขับแบบปลอดภัย
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
            
    except Exception as e: st.error(f"Error: {e}")
    finally: db.close()
elif choice == "🚖 งานของฉัน (Driver)":
    st.title("🚖 งานของฉัน (Driver)")
    
    # 1. ดึงชื่อคนขับเพื่อความ Friendly
    driver_name = "คนขับรถ"
    db = get_connection()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT name FROM users WHERE line_user_id = %s", (current_id,))
            res = cursor.fetchone()
            if res: driver_name = res[0]
        st.subheader(f"👋 สวัสดีคุณ: {driver_name}")
        st.write("---")
        
        # 2. ดึงงานปัจจุบัน (ที่สถานะ Assigned หรือ Accepted)
        df_driver = pd.read_sql("""
            SELECT id, voucher_no, passenger_name, pickup_location, dropoff_location, status 
            FROM bookings 
            WHERE driver_id = %s AND status IN ('Assigned', 'Accepted')
            ORDER BY booking_time ASC
        """, db, params=(current_id,))
        
        if not df_driver.empty:
            st.write("### 📥 รายการงานที่ได้รับมอบหมาย")
            st.dataframe(df_driver, width='stretch', hide_index=True)
            
            # ระบบกดรับงาน (เฉพาะงานที่ status เป็น Assigned)
            assigned_jobs = df_driver[df_driver['status'] == 'Assigned']
            if not assigned_jobs.empty:
                st.write("---")
                st.write("### 📥 งานใหม่รอรับทราบ")
                job_map = {f"🎫 {row['voucher_no']} | ลูกค้า {row['passenger_name']}": row['id'] for _, row in assigned_jobs.iterrows()}
                selected_job = st.selectbox("เลือกงานที่ต้องการรับ", list(job_map.keys()))
                
                if st.button("✅ กดรับทราบและยอมรับงาน"):
                    cursor.execute("UPDATE bookings SET status = 'Accepted' WHERE id = %s", (job_map[selected_job],))
                    db.commit()
                    # ส่งข้อความกลับไปหา Dispatcher (ถ้ามี)
                    send_line_message(f"✅ คนขับ {driver_name} กดรับงานแล้ว!", "dispatcher01") 
                    st.success("รับงานเรียบร้อย!")
                    st.rerun()
        else:
            st.info("✨ ปัจจุบันคุณยังไม่มีงานค้างที่ต้องปฏิบัติครับ")
            
    except Exception as e: st.error(f"Error: {e}")
    finally: db.close()

    # 3. ส่วนประวัติการวิ่งงาน
    st.write("---")
    st.write("### ✅ ประวัติการวิ่งงาน (Completed)")
    try:
        db = get_connection()
        df_history = pd.read_sql("SELECT voucher_no, passenger_name, status FROM bookings WHERE driver_id = %s AND status = 'Completed' ORDER BY id DESC LIMIT 20", db, params=(current_id,))
        if not df_history.empty:
            st.dataframe(df_history, width='stretch', hide_index=True)
        else:
            st.info("ยังไม่มีประวัติการวิ่งงานครับ")
    except Exception as e: st.error(f"Error: {e}")
    finally: db.close()
elif choice == "✈️ Airport Staff":
    st.title("✈️ ตรวจสอบสถานะรถ (Airport Staff)")
    st.subheader("📋 ตารางมอนิเตอร์รถยนต์และคนขับที่กำลังปฏิบัติงาน")

    try:
        db = get_connection()
        # ดึงงานที่ Assigned (กำลังไปรับ) หรือ Accepted (คนขับรับทราบแล้ว)
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
            
            # ใส่สีสถานะงาน
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
        if 'db' in locals() and db.open: db.close()
elif choice == "📝 ลงทะเบียนพนักงานใหม่":
    st.title("📝 ลงทะเบียนพนักงานใหม่")
    
    # ส่วนดึง LINE ID ด้วย LIFF
    st.markdown("### 🔍 วิธีการดึงรหัสประจำตัวเครื่อง")
    st.info("กรุณากดปุ่มด้านล่างเพื่อดึงรหัส LINE User ID อัตโนมัติ แล้วนำไปวางในช่องสมัครครับ 👇")

    pure_js_html = """
    <div style="background-color:#ffffff; padding:15px; border-radius:8px; border:2px dashed #28a745; text-align:center;">
        <button id="btn-scan" style="background-color:#28a745; color:white; border:none; padding:12px 24px; font-size:16px; font-weight:bold; border-radius:5px; cursor:pointer; width:100%; max-width:320px;">
            🟢 ดึง LINE ID ของคุณ
        </button>
        <div id="display-output" style="display:none; margin-top:15px;">
            <input type="text" id="id-box" style="width:100%; max-width:320px; padding:10px; text-align:center; border:1px solid #ced4da; border-radius:4px;" readonly>
            <br><br>
            <button onclick="navigator.clipboard.writeText(document.getElementById('id-box').value); alert('คัดลอกรหัสแล้วครับ');" style="background-color:#007bff; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">
                📋 คัดลอกรหัส
            </button>
        </div>
    </div>
    <script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
    <script>
    document.getElementById('btn-scan').addEventListener('click', function() {
        liff.init({ liffId: "2010148491-zYBksiiv" }).then(() => {
            liff.getProfile().then(p => {
                document.getElementById('btn-scan').style.display = 'none';
                document.getElementById('display-output').style.display = 'block';
                document.getElementById('id-box').value = p.userId;
            });
        });
    });
    </script>
    """
    components.html(pure_js_html, height=180)
    
    st.write("---")
    st.write("### 👤 กรอกข้อมูลรายงานตัว")
    
    with st.form("guest_register_form", clear_on_submit=True):
        reg_name = st.text_input("ชื่อ - นามสกุลจริง", placeholder="เช่น นายสมชาย ใจดีมาก").strip()
        reg_line_id = st.text_input("LINE User ID", value=current_id, placeholder="กดดึงรหัสด้านบนแล้วนำมาวางที่นี่")
        
        if st.form_submit_button("🚀 ส่งข้อมูลลงทะเบียน"):
            if not reg_name or not reg_line_id:
                st.error("⚠️ กรุณากรอกชื่อและรหัส LINE ID ให้ครบถ้วนครับ")
            else:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO users (line_user_id, name, role, status)
                        VALUES (%s, %s, 'guest', 'Active')
                        ON DUPLICATE KEY UPDATE name = %s, role = 'guest', status = 'Active'
                    """, (reg_line_id, reg_name, reg_name))
                    conn.commit()
                    conn.close()
                    st.success("🎉 ส่งข้อมูลเรียบร้อย! โปรดรอแอดมินอนุมัติสิทธิ์ครับ")
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาดทางฐานข้อมูล: {e}")
