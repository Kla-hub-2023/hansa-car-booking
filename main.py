import streamlit as st
import pymysql
import pandas as pd
import requests
import datetime as dt_module
import streamlit.components.v1 as components

def get_connection():
    return pymysql.connect(host='mysql-22653bef-kla-e55d.c.aivencloud.com', user='avnadmin', password='AVNS_W4Huwc3abQww6NKNlG2', database='defaultdb', port=23986)

def check_permission(user_id):
    if not user_id or user_id.startswith("GUEST_") or "*" in user_id: return "guest"
    try:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT role, status FROM users WHERE line_user_id = %s", (user_id,))
            res = cursor.fetchone()
            if res and res[1] == "Active": return str(res[0]).lower()
            return "guest"
    finally: db.close()

st.set_page_config(page_title="ระบบจัดการรถ Hunsa", layout="wide")

query_params = st.query_params
if "lineidtoemp" in query_params: st.session_state.default_user_id = query_params["lineidtoemp"].strip()
elif "user" in query_params: st.session_state.default_user_id = query_params["user"].strip()

current_id = st.sidebar.text_input("ระบุ LINE User ID", value=st.session_state.get("default_user_id", "")).strip()
st.session_state.default_user_id = current_id
user_role = check_permission(current_id)
st.sidebar.info(f"สิทธิ์: {user_role.upper()}")

menu_options = ["🏠 Dashboard", "➕ Booker", "🖥️ Dispatcher", "𚖖 งานของฉัน (Driver)", "✈️ Airport Staff", "📝 ลงทะเบียนพนักงานใหม่", "👥 จัดการพนักงาน"]
if "current_menu_choice" not in st.session_state: st.session_state["current_menu_choice"] = menu_options[0]

# Logic วาร์ป Admin
if user_role == "admin" and "user" in query_params:
    cmd = query_params["user"].strip().lower()
    if cmd == "admin01": st.session_state["current_menu_choice"] = "🏠 Dashboard"

choice = st.sidebar.radio("เมนูใช้งาน", options=menu_options, index=menu_options.index(st.session_state["current_menu_choice"]) if st.session_state["current_menu_choice"] in menu_options else 0)
st.session_state["current_menu_choice"] = choice

if user_role == "driver" and choice != "𚖖 งานของฉัน (Driver)":
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
    
