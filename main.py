import streamlit as st
import pymysql
import pandas as pd
import requests
from datetime import datetime
import io
import datetime as dt_module
import streamlit.components.v1 as components

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
def check_permission(user_id, line_name=None):
    if not user_id or user_id.strip() == "" or user_id.strip().lower() == "none" or user_id.startswith("GUEST_") or "line.me" in user_id.lower() or "http" in user_id.lower() or "*" in user_id:
        return "guest"
        
    if user_id == "admin01":
        return "admin"
        
    try:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT role, status FROM users WHERE line_user_id = %s", (user_id,))
            result = cursor.fetchone()
            
            if result:
                role_res = result[0]
                status_res = result[1] if result[1] else "Active"
                if status_res == "Inactive":
                    return "guest"
                return role_res
            else:
                return "guest"
    except Exception as e:
        return "guest"
    finally:
        if 'db' in locals() and db.open:
            db.close()

st.set_page_config(page_title="ระบบจัดการรถ Multi-Role", layout="wide")

st.markdown("""
    <style>
    h1 { font-size: 1.4rem !important; padding-top: 0.3rem !important; padding-bottom: 0.3rem !important; line-height: 1.1 !important; }
    h2, h3, .stSubheader { font-size: 1.05rem !important; font-weight: 600 !important; }
    div[data-baseweb="select"], input, label { font-size: 0.9rem !important; }
    .block-container { padding-top: 3.2rem !important; padding-bottom: 1rem !important; padding-left: 0.8rem !important; padding-right: 0.8rem !important; }
    .stDataFrame table { font-size: 0.8rem !important; }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    div[data-testid="stDecoration"] {display: none;}
    .stAppDeployButton {display: none !important;}
    div[data-testid="stStatusWidget"] {display: none !important;}
    iframe[title="streamlit_runtime.auth_user_nav"] {display: none !important;}
    div.stAppToolbar {display: none !important;}
    button[data-testid="stViewerBadge"] {display: none !important;}
    .viewerBadge {display: none !important;}
    </style>
    """, unsafe_allow_html=True)

if "default_user_id" not in st.session_state:
    st.session_state["default_user_id"] = ""

# 📌 ดักจับแกะรอยค่าพารามิเตอร์ลับสิทธิ์ 'lineidtoemp' ไอเดียแอดมินเพื่อหนีดอกจันเซ็นเซอร์
query_params = st.query_params
extracted_id = ""

if "lineidtoemp" in query_params:
    raw_val = query_params["lineidtoemp"].strip()
    if "*" not in raw_val and len(raw_val) > 15:
        extracted_id = raw_val

if extracted_id:
    st.session_state.default_user_id = extracted_id

st.sidebar.title("🔐 เข้าสู่ระบบ")

current_id = st.sidebar.text_input(
    "ระบุ LINE User ID", 
    value=st.session_state["default_user_id"]
).strip()

if "http" in current_id.lower() or "line.me" in current_id.lower() or "*" in current_id:
    current_id = ""

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
    menu_options = ["📝 ลงทะเบียนพนักงานใหม่"]

if "current_menu_choice" not in st.session_state or st.session_state["current_menu_choice"] not in menu_options:
    st.session_state["current_menu_choice"] = menu_options[0] if menu_options else ""

choice = st.sidebar.radio(
    "เมนูใช้งาน", 
    options=menu_options, 
    key="current_menu_choice"
)

# --- 4. การแสดงเนื้อหาไส้ในของแต่ละเมนูตามหน้าเลือก ---
if "ลงทะเบียนพนักงานใหม่" in choice:
    st.title("📝 ฟอร์มรายงานตัวและลงทะเบียนพนักงานใหม่")
    st.warning("⚠️ บัญชีของคุณกำลังรอแอดมินอนุมัติสิทธิ์เข้าใช้งานระบบคิวรถครับ")
    st.write("---")
    
    has_real_id = current_id and current_id.strip() != "" and len(current_id) > 15
    
    if has_real_id:
        st.success(f"💚 **ระบบดักจับรหัสเครื่องของคุณสำเร็จ!**")
        st.info(f"นี่คือรหัส LINE User ID ของคุณ: **{current_id}** (ระบบล็อกรหัสใส่ช่องสมัครด้านล่างให้เรียบร้อยแล้วครับ)")
        st.write("---")
    else:
        st.markdown("### 🔍 วิธีระบบดักจับรหัสเครื่องพนักงานใหม่อัตโนมัติ")
        st.info("กรุณากดที่ปุ่มสีเขียวด้านล่างนี้ 1 ครั้ง เพื่อเชื่อมต่อโปรไฟล์และล็อกรหัสตัว U ของคุณเข้าสู่ฟอร์มสมัครครับ 👇")

        # 🚀 [ท่อเหล็กสยบบล็อก] ใช้คำสั่ง window.open พ่วง target '_top' ดีดทะลวงหน้าต่างค้างเติ่งให้ขยับทันที 100%
        liff_html = """
        <script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
        <div style="background-color:#f8f9fa; padding:16px; border-radius:8px; border:1px solid #e9ecef; text-align:center; font-family:sans-serif;">
            <button id="btn-liff" style="background-color:#28a745; color:white; border:none; padding:14px 28px; font-size:16px; font-weight:bold; border-radius:6px; cursor:pointer; width:100%; max-width:320px; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                🟢 คลิกเพื่อดึงรหัสประจำเครื่องของฉัน
            </button>
            <div id="status-msg" style="margin-top:12px; font-size:14px; color:#495057; font-weight:bold;">กรุณากดปุ่มเพื่อเปิดท่อดึงรหัสประจำเครื่อง</div>
        </div>

        <script>
        document.getElementById('btn-liff').addEventListener('click', function() {
            document.getElementById('status-msg').innerHTML = "⏳ กำลังเชื่อมต่อระบบโปรไฟล์ LINE...";
            
            liff.init({ liffId: "2010148491-zYBksiiv" }).then(() => {
                if (liff.isLoggedIn()) {
                    liff.getProfile().then(profile => {
                        const uId = profile.userId;
                        document.getElementById('status-msg').innerHTML = "✅ ตรวจพบรหัสสำเร็จ! กำลังพาวาร์ปกรอกฟอร์ม...";
                        
                        // ปรับเป็นคำสั่งวาร์ปหน้าหลักระดับสูงสุดเพื่อไม่ให้เบราเซอร์สั่งบล็อกค่าค้างเติ่ง
                        window.open("https://hansa-car-booking-mmvs3r3jbrdwbuu7x5vecw.streamlit.app/?lineidtoemp=" + uId, "_top");
                    }).catch(err => {
                        document.getElementById('status-msg').innerHTML = "❌ ดึงโปรไฟล์ล้มเหลว: " + err;
                    });
                } else {
                    liff.login();
                }
            }).catch(err => {
                document.getElementById('status-msg').innerHTML = "❌ ระบบ LIFF ไม่ตอบสนอง: " + err;
            });
        });
        </script>
        """
        components.html(liff_html, height=140)
        st.write("---")
        
    st.write("### 👤 กรุณากรอกข้อมูลรายงานตัวเพื่อส่งให้แอดมินอนุมัติ")
    
    with st.form("guest_register_form", clear_on_submit=True):
        reg_name = st.text_input("1. ระบุ ชื่อ - นามสกุลจริงของคุณ", placeholder="เช่น นายสมชาย ใจดีมาก").strip()
        reg_line_id = st.text_input("2. ระบุรหัส LINE User ID ของคุณ (รหัสตัว U 33 หลัก)", value=current_id if current_id else "", placeholder="รหัสตัว U ของคุณจะล็อกโชว์ที่นี่หลังจากกดปุ่มสีเขียวด้านบน")
            
        submit_reg = st.form_submit_button("🚀 ส่งข้อมูลลงทะเบียนระบบคิวรถ")
        
        if submit_reg:
            cleaned_target_id = reg_line_id.strip() if reg_line_id else ""
            if "http" in cleaned_target_id.lower() or "line.me" in cleaned_target_id.lower() or len(cleaned_target_id) < 10 or "*" in cleaned_target_id:
                st.error("⚠️ รหัส LINE User ID ไม่ถูกต้อง! กรุณากดปุ่มสีเขียวดึงข้อมูลด้านบน หรือติดต่อแอดมินเพื่อขอรหัสครับ")
            elif not reg_name:
                st.error("⚠️ กรุณากรอกชื่อ-นามสกุลจริงก่อนกดส่งข้อมูลครับ")
            else:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO users (line_user_id, name, role, status)
                        VALUES (%s, %s, 'guest', 'Active')
                        ON DUPLICATE KEY UPDATE name = %s, role = 'guest', status = 'Active'
                    """, (cleaned_target_id, reg_name, reg_name))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success(f"🎉 ส่งข้อมูลรายงานตัวของพนักงานคุณ '{reg_name}' เรียบร้อย! รบกวนแจ้งแอดมินให้กดยอมรับสิทธิ์ในระบบหลังบ้านครับ")
                    st.rerun()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดทางฐานข้อมูล: {e}")

# --- หน้าระบบเมนูอื่น ๆ คงไว้เหมือนเดิมทั้งหมดเพื่อความเสถียรของฐานข้อมูลอู่รถ ---
elif "Dashboard" in choice:
    if current_role == "admin":
        st.success("👑 ยินดีต้อนรับกลับเข้าสู่ระบบครับ แอดมินกล้า (Admin Level Max) | ระบบความปลอดภัยยืนยันสิทธิ์ถูกต้องเรียบร้อย")

    st.title("🏠 หน้าแรกและภาพรวมระบบ (Dashboard)")
    st.markdown(f"สวัสดีครับแอดมิน Status การเชื่อมต่อ **ระบบปกติดีเยี่ยม** ครับ")
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
            st.dataframe(df_recent, width='stretch', hide_index=True)
        else:
            st.info("ยังไม่มีประวัติการจองในระบบ")
            
    with col_right:
        st.write("### 💡 แนะนำการใช้งาน")
        st.info("แอดมินสามารถสลับบัญชีเพื่อทดสอบระบบได้:\n\n"
                "* **admin01** : จัดสรรงานและดูภาพรวมทั้งหมด\n"
                "* **driver01** : ดูงานของตัวเองและกดรับงาน\n"
                "* **driver02** : ดูงานของคนขับคนที่ 2")

elif "Booker" in choice:
    st.title("📋 แบบฟอร์มจองรถ (Booker)")
    st.subheader("กรอกรายละเอียดการเดินทางเพื่อส่งงานให้ผู้จัดสรรรถ")

    with st.form(key="car_booking_form", clear_on_submit=True):
        st.write("### 🚗 ข้อมูลการเดินทาง")
        passenger_name = st.text_input("👤 ชื่อผู้โดยสาร / คณะเดินทาง", placeholder="เช่น คุณสมชาย สายลุย")
        pickup_location = st.text_input("📍 จุดรับ (Pickup)", placeholder="กรอกจุดรับ เช่น สนามบินสุวรรณภูมิ, โรงแรมฮันซ่า, พัทยา").strip()
        dropoff_location = st.text_input("🏁 จุดส่ง (Dropoff)", placeholder="กรอกจุดส่ง เช่น ตัวเมืองกรุงเทพฯ, หัวหิน, คอนโด A").strip()
        
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
        elif not pickup_location or not dropoff_location:
            st.error("⚠️ กรุณาระบุข้อมูลจุดรับและจุดส่งให้ครบถ้วนก่อนบันทึกครับ")
        elif pickup_location.lower() == dropoff_location.lower():
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
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาดระหว่างบันทึกข้อมูล: {e}")
                finally:
                    if 'db' in locals() and db.open:
                        db.close()

    st.write("---")
    st.write("### 🕒 รายการงานจองปัจจุบันที่คุณคีย์ในระบบ")
    try:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT voucher_no, passenger_name, pickup_location, dropoff_location, booking_time, status 
                FROM bookings 
                WHERE status IN ('Pending', 'Assigned')
                ORDER BY booking_time ASC
            """)
            booker_jobs = cursor.fetchall()
        columns_booker = ['Voucher No.', 'ชื่อผู้โดยสาร', 'จุดรับ', 'จุดส่ง', 'เวลาเดินทาง', 'สถานะงาน']
        df_booker = pd.DataFrame(booker_jobs, columns=columns_booker)
        if not df_booker.empty:
            st.dataframe(df_booker, width='stretch', hide_index=True)
        else:
            st.info("💡 ปัจจุบันยังไม่มีรายการงานค้างในระบบครับ")
    except Exception as e:
        st.error(f"❌ ไม่สามารถดึงรายการข้อมูลการจองมาแสดงได้: {e}")
    finally:
        if 'db' in locals() and db.open:
            db.close()

elif "Dispatcher" in choice:
    st.title("🎛️ แผงควบคุมสำหรับ Dispatcher")
    st.write("---")
    
    drivers_dict = {}
    driver_options = {}
    try:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT line_user_id, name FROM users WHERE role = 'driver' AND status = 'Active'")
            drivers_data = cursor.fetchall()
            for d in drivers_data:
                drivers_dict[d[0]] = d[1]
                driver_options[f"🚗 {d[1]} ({d[0][:6]}...)"] = d[0]
    except Exception as e:
        st.sidebar.error(f"ไม่สามารถดึงรายชื่อคนขับได้: {e}")
    finally:
        if 'db' in locals() and db.open:
            db.close()

    try:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT id, voucher_no, passenger_name, pickup_location, dropoff_location, booking_time, status, driver_id 
                FROM bookings 
                WHERE status IN ('Pending', 'Assigned')
                ORDER BY booking_time ASC
            """)
            bookings_data = cursor.fetchall()
        columns = ['id', 'Voucher No.', 'ชื่อผู้โดยสาร', 'จุดรับ', 'จุดส่ง', 'เวลาจอง', 'สถานะงาน', 'รหัสคนขับ']
        df_bookings = pd.DataFrame(bookings_data, columns=columns)
        
        if not df_bookings.empty:
            df_bookings['คนขับที่รับงาน'] = df_bookings['รหัสคนขับ'].map(lambda x: drivers_dict.get(x, "ยังไม่ได้จ่ายงาน") if x else "ยังไม่ได้จ่ายงาน")
            display_cols = ['id', 'Voucher No.', 'ชื่อผู้โดยสาร', 'จุดรับ', 'จุดส่ง', 'เวลาจอง', 'สถานะงาน', 'คนขับที่รับงาน']
            df_display = df_bookings[display_cols]
            st.write("### 📊 ตารางสถานะงานปัจจุบัน (กำลังรอรับ/กำลังเดินทาง)")
            st.dataframe(df_display, width='stretch', hide_index=True, column_config={"id": None})
        else:
            st.info("✨ ไม่มีงานค้างในระบบปัจจุบัน")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงตารางงาน: {e}")
    finally:
        if 'db' in locals() and db.open:
            db.close()

    st.write("---")
    col_assign, col_complete = st.columns(2)
    
    with col_assign:
        st.write("### 🚖 จ่ายงานใหม่ / สลับเปลี่ยนคนขับกรณีฉุกเฉิน")
        if not df_bookings.empty:
            job_options = {}
            for index, row in df_bookings.iterrows():
                current_driver = row['คนขับที่รับงาน']
                job_options[f"🎫 {row['Voucher No.']} - {row['ชื่อผู้โดยสาร']} [{row['สถานะงาน']}] (ปัจจุบัน: {current_driver})"] = row['id']
                
            selected_job_text = st.selectbox("เลือกงานที่ต้องการจัดการ", options=list(job_options.keys()))
            selected_driver_text = st.selectbox("เลือกคนขับรถที่จะมอบหมายงานให้", options=list(driver_options.keys()))
            
            if st.button("💾 บันทึกการมอบหมายงาน", type="primary", use_container_width=True):
                job_id_to_update = job_options[selected_job_text]
                driver_id_target = driver_options[selected_driver_text]
                driver_name_target = next(name for name, d_id in driver_options.items() if d_id == driver_id_target)
                
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT voucher_no, passenger_name, status, driver_id FROM bookings WHERE id = %s", (job_id_to_update,))
                    old_job_data = cursor.fetchone()
                    
                    cursor.execute("UPDATE bookings SET driver_id = %s, status = 'Assigned' WHERE id = %s", (driver_id_target, job_id_to_update))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    st.success(f"🎉 มอบหมายงาน {old_job_data[0]} ให้กับ {driver_name_target} เรียบร้อยแล้ว!")
                    push_msg = f"🔔 คุณมีงานเข้าใหม่/สลับงานฉุกเฉิน\n🎫 Voucher: {old_job_data[0]}\n👤 ผู้โดยสาร: {old_job_data[1]}\n📊 โปรดตรวจสอบที่หน้างานของฉันบนระบบ"
                    send_line_message(push_msg, driver_id_target)
                    
                    if old_job_data[2] == 'Assigned' and old_job_data[3] != driver_id_target:
                        cancel_msg = f"⚠️ แจ้งเตือนฉุกเฉิน:\n🎫 งาน Voucher: {old_job_data[0]} ของผู้โดยสารคุณ {old_job_data[1]} ได้ถูกโอนย้ายให้คนขับท่านอื่นดูแลแทนแล้วครับ"
                        send_line_message(cancel_msg, old_job_data[3])
                    st.rerun()
                except Exception as e:
                    st.error(f"ไม่สามารถมอบหมายงานได้: {e}")
        else:
            st.info("ไม่มีรายการงานที่สามารถจ่ายหรือสลับได้ในขณะนี้")

    with col_complete:
        st.write("### 🏁 บันทึกปิดงานเสร็จสิ้น (Completed)")
        if not df_bookings.empty:
            active_jobs = df_bookings[df_bookings['status'] == 'Assigned']
            if not active_jobs.empty:
                active_job_options = {f"✅ {row['Voucher No.']} - {row['ชื่อผู้โดยสาร']} ({row['คนขับที่รับงาน']})": row['id'] for index, row in active_jobs.iterrows()}
                selected_active_job = st.selectbox("เลือกงานที่ต้องการปิดสถานะ", options=list(active_job_options.keys()))
                if st.button("🏁 ยืนยันปิดงานนี้ (Completed)", use_container_width=True):
                    job_id_to_complete = active_job_options[selected_active_job]
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE bookings SET status = 'Completed' WHERE id = %s", (job_id_to_complete,))
                        conn.commit()
                        cursor.close()
                        conn.close()
                        st.success("🎉 ปิดงานเรียบร้อย ตารางจะถูกเคลียร์ออกครับ")
                        st.rerun()
                    except Exception as e:
                        st.error(f"ไม่สามารถปิดงานได้: {e}")
            else:
                st.info("ไม่มีงานที่กำลังวิ่งอยู่ (Assigned) ให้กดปิดสถานะครับ")
        else:
            st.info("ไม่มีรายการงานในระบบ")

elif "Driver" in choice:
    st.title("𚖖 งานที่ได้รับมอบหมาย (Driver)")
    driver_name = "ไม่ระบุชื่อ"
    try:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT name FROM users WHERE line_user_id = %s", (current_id,))
            user_res = cursor.fetchone()
            if user_res: driver_name = user_res[0]
    except Exception as e: pass
    finally:
        if 'db' in locals() and db.open: db.close()

    st.subheader(f"👋 สวัสดีครับ: {driver_name}")

    try:
        db = get_connection()
        with db.cursor() as cursor:
            query_current = "SELECT id, voucher_no, passenger_name, pickup_location, dropoff_location, booking_time, status FROM bookings WHERE driver_id = %s AND status IN ('Assigned', 'Accepted') ORDER BY booking_time ASC"
            cursor.execute(query_current, (current_id,))
            current_jobs = cursor.fetchall()
            query_history = "SELECT id, voucher_no, passenger_name, pickup_location, dropoff_location, booking_time, status FROM bookings WHERE driver_id = %s AND status = 'Completed' ORDER BY booking_time DESC LIMIT 30"
            cursor.execute(query_history, (current_id,))
            history_jobs = cursor.fetchall()
        columns = ['id', 'voucher_no', 'passenger_name', 'pickup_location', 'dropoff_location', 'booking_time', 'status']
        df_driver_current = pd.DataFrame(current_jobs, columns=columns)
        df_driver_history = pd.DataFrame(history_jobs, columns=columns)
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อข้อมูลคนขับ: {e}")
        df_driver_current, df_driver_history = pd.DataFrame(), pd.DataFrame()
    finally:
        if 'db' in locals() and db.open: db.close()

    st.write("---")
    st.write("### 📥 รายการงานปัจจุบันที่ต้องปฏิบัติ")
    if not df_driver_current.empty:
        st.dataframe(df_driver_current, width='stretch', hide_index=True)
        assigned_jobs = df_driver_current[df_driver_current['status'] == 'Assigned']
        if not assigned_jobs.empty:
            st.write("### 📥 มีใบงานใหม่รอคุณกดรับทราบ")
            driver_job_options = { f"🎫 {row['voucher_no']} | คุณ {row['passenger_name']}": row['id'] for _, row in assigned_jobs.iterrows() }
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

                            cursor.execute("UPDATE bookings SET status = 'Accepted' WHERE id = %s", (job_id_to_accept,))
                            db.commit()
                            if disp_id:
                                msg_back_to_admin = f"✅ คนขับกดรับงานแล้วครับ!\n🎫 เลข Voucher: {v_no}\n👤 ลูกค้า: {p_name}\n🚖 พนักงานขับรถ: {driver_name} ได้กดรับทราบแล้ว"
                                send_line_message(msg_back_to_admin, disp_id)
                        st.success(f"🎉 คุณได้รับทราบและยอมรับใบงานเรียบร้อย!")
                        st.rerun()
                    except Exception as e: st.error(f"❌ ไม่สามารถเปลี่ยนสถานะงานได้: {e}")
                    finally:
                        if 'db' in locals() and db.open: db.close()
    else: st.success("✨ ไม่มีงานปัจจุบันค้างอยู่")

    st.write("---")
    st.write("### ✅ ประวัติการวิ่งงานที่เสร็จสิ้นแล้ว (Completed)")
    if not df_driver_history.empty:
        st.info(f"💡 เดือนนี้คุณวิ่งงานเสร็จสิ้นไปแล้วทั้งหมด **{len(df_driver_history)}** ใบงาน")
        st.dataframe(df_driver_history, width='stretch', hide_index=True)
    else: st.info("ℹ️ ยังไม่มีประวัติงานที่บันทึกสถานะเสร็จสิ้น")

elif "Airport Staff" in choice:
    st.title("✈️ ตรวจสอบสถานะรถ (Airport Staff)")
    st.subheader("📋 ตารางมอนิเตอร์รถยนต์และคนขับที่กำลังปฏิบัติงาน")

    try:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT b.voucher_no AS 'เลข Voucher', b.passenger_name AS 'ชื่อผู้โดยสาร', b.pickup_location AS 'จุดรับ', b.dropoff_location AS 'จุดส่ง', b.booking_time AS 'เวลาเดินทาง', b.status AS 'สถานะงาน', u.name AS 'คนขับรถที่รับงาน'
                FROM bookings b LEFT JOIN users u ON b.driver_id = u.line_user_id
                WHERE b.status IN ('Assigned', 'Accepted') ORDER BY b.booking_time ASC
            """)
            airport_data = cursor.fetchall()
        columns = ['เลข Voucher', 'ชื่อผู้โดยสาร', 'จุดรับ', 'จุดส่ง', 'เวลาเดินทาง', 'สถานะงาน', 'คนขับรถที่รับงาน']
        df_airport = pd.DataFrame(airport_data, columns=columns)
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการดึงข้อมูลสำหรับพนักงานสนามบิน: {e}")
        df_airport = pd.DataFrame()
    finally:
        if 'db' in locals() and db.open: db.close()

    if not df_airport.empty:
        st.write("✨ แสดงเฉพาะงานที่มีการจัดสรรคนขับแล้ว เพื่อเตรียมความพร้อมภาคพื้นสนามบิน")
        def highlight_status(val):
            if val == 'Accepted': return 'background-color: #d4edda; color: #155724; font-weight: bold;'
            elif val == 'Assigned': return 'background-color: #fff3cd; color: #856404;'
            return ''
        st.dataframe(df_airport.style.map(highlight_status, subset=['สถานะงาน']), width='stretch', hide_index=True)
        st.write("---")
        col_metrics1, col_metrics2 = st.columns(2)
        with col_metrics1: st.metric(label="🚖 จำนวนรถที่กำลังเดินทาง (Assigned)", value=len(df_airport[df_airport['สถานะงาน'] == 'Assigned']))
        with col_metrics2: st.metric(label="✅ จำนวนรถที่คนขับกดรับงานแล้ว (Accepted)", value=len(df_airport[df_airport['สถานะงาน'] == 'Accepted']))
    else: st.info("ℹ️ ปัจจุบันยังไม่มีรถยนต์คันไหนกำลังเดินทางมาสนามบิน")

elif "จัดการพนักงาน" in choice:
    st.title("👥 ระบบจัดการสิทธิ์ผู้ใช้งาน (User Management)")
    st.write("---")
    
    st.write("### ⏳ รายชื่อพนักงานใหม่ที่รออนุมัติสิทธิ์ (Guests)")
    try:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT line_user_id, name, role FROM users WHERE role = 'guest'")
            guests_data = cursor.fetchall()
        if guests_data:
            df_guests = pd.DataFrame(guests_data, columns=['รหัส LINE User ID', 'ชื่อรายงานตัวพนักงาน', 'สถานะ'])
            st.dataframe(df_guests, width='stretch', hide_index=True)
            st.sidebar.info("💡 แอดมินสามารถก๊อปปี้รหัส LINE ID จากตารางด้านบนมาวางในกล่องแก้ไขเพื่ออัปเดตตำแหน่งได้ครับ")
        else: st.success("✨ เรียบร้อยดี! ไม่มีพนักงานใหม่ค้างรออนุมัติสิทธิ์ในระบบครับ")
    except Exception as e: st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล Guest: {e}")
    finally:
        if 'db' in locals() and db.open: db.close()

    st.write("---")
    try:
        db = get_connection()
        with db.cursor() as cursor: cursor.execute("SELECT line_user_id, name, role, status FROM users")
        all_users = cursor.fetchall()
        user_list_options = {f"👤 {u[1]} ({u[2].upper()}) - [{u[3] if u
