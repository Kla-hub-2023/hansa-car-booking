import streamlit as st
import pymysql
import pandas as pd

# เชื่อมต่อ DB (ใช้ตัวเดิม)
@st.cache_resource
def get_connection():
    return pymysql.connect(
        host='127.0.0.1',
        user='root',
        password='P@ssw0rd',
        database='car_booking_db',
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor
    )

st.set_page_config(page_title="จัดการงานจองรถ", layout="wide")
st.title("🖥️ หน้าจอสำหรับ Dispatcher (จัดการงาน)")

# 1. ดึงข้อมูลทั้งหมดจากฐานข้อมูล
db = get_connection()
with db.cursor() as cursor:
    cursor.execute("SELECT * FROM bookings ORDER BY pickup_date DESC, pickup_time DESC")
    data = cursor.fetchall()

# 2. แสดงตารางสรุปงาน
if data:
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
    
    st.divider()
    
    # 3. ส่วนสำหรับจ่ายงาน (Assign Driver)
    st.subheader("✍️ จ่ายงานให้คนขับ")
    with st.form("assign_form"):
        target_vc = st.selectbox("เลือก Voucher ที่ต้องการจ่ายงาน", df['voucher_no'])
        driver_name = st.text_input("ชื่อคนขับรถ (Driver Name)")
        status = st.selectbox("สถานะงาน", ["Confirmed", "On the way", "Completed", "Cancelled"])
        
        assign_btn = st.form_submit_button("อัปเดตงาน")
        
        if assign_btn:
            with db.cursor() as cursor:
                sql = "UPDATE bookings SET driver_name=%s, status=%s WHERE voucher_no=%s"
                cursor.execute(sql, (driver_name, status, target_vc))
                st.success(f"อัปเดตงาน {target_vc} ให้คุณ {driver_name} เรียบร้อย!")
                st.rerun() # รีโหลดหน้าเพื่ออัปเดตตาราง
else:
    st.info("ยังไม่มีข้อมูลการจองในระบบ")