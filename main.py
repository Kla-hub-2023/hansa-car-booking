import streamlit as st
import pymysql
import pandas as pd
import requests
from datetime import datetime
import io

# --- 1. การตั้งค่าพื้นฐานและการเชื่อมต่อ DB ---
@st.cache_resource
def get_connection():
    return pymysql.connect(
        host='127.0.0.1',
        user='root',
        password='P@ssw0rd', # ⚠️ แก้จุดนี้
        database='car_booking_db',
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor
    )

def send_line_message(message, target_id):
    token = 'X8ogM3D2GxzZ3z5EBMdOxWTa4BjTlqP1H/bYv+fwqLGNiKhhxuiPQR5bakcgXfEZBUPNDImDlvLrDMvtqN0/8XTlrcqfIvti2m2RpY/wrbQ9xl95HJd+slpzHCM9Vs5SxNS5e9gBG4MSE71UUNhXrQdB04t89/1O/w1cDnyilFU=' # ⚠️ แก้จุดนี้
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    data = {'to': target_id, 'messages': [{'type': 'text', 'text': message}]}
    requests.post(url, headers=headers, json=data)

# --- 2. ระบบเช็คสิทธิ์ผู้ใช้งาน ---
def check_permission(user_id):
    db = get_connection()
    with db.cursor() as cursor:
        cursor.execute("SELECT role FROM users WHERE line_user_id = %s", (user_id,))
        result = cursor.fetchone()
    return result['role'] if result else "Guest"

st.set_page_config(page_title="ระบบจัดการรถ Multi-Role", layout="wide")

# จำลองการดึง ID จาก LINE (ตอนนี้ให้พิมพ์ใส่เองเพื่อทดสอบ)
st.sidebar.title("🔐 เข้าสู่ระบบ")
current_id = st.sidebar.text_input("ระบุ LINE User ID", value="วาง_รหัส_U_ของคุณที่นี่")
user_role = check_permission(current_id)
st.sidebar.info(f"สิทธิ์ของคุณคือ: {user_role}")

# --- 3. จัดการเมนูตามสิทธิ์ (Spec: Admin เห็นหมด, Dispatcher เห็น 3 กลุ่ม) ---
menu_options = []
if user_role == "Admin":
    menu_options = ["🏠 Dashboard", "➕ Booker", "🖥️ Dispatcher", "🚖 Driver", "✈️ Airport Staff"]
elif user_role == "Dispatcher":
    menu_options = ["➕ Booker", "🖥️ Dispatcher", "🚖 Driver", "✈️ Airport Staff"]
elif user_role == "Driver":
    menu_options = ["🚖 งานของฉัน (Driver)"]
elif user_role == "Booker":
    menu_options = ["➕ คีย์งานจองรถ (Booker)"]
elif user_role == "AirportStaff":
    menu_options = ["✈️ ตรวจสอบคิวรถ (Airport Staff)"]
else:
    st.warning("คุณไม่มีสิทธิ์เข้าถึงระบบ กรุณาติดต่อ Admin")
    st.stop()

choice = st.sidebar.radio("เมนูใช้งาน", menu_options)

# --- 4. ไส้ในของแต่ละเมนู (ดึงโค้ดเดิมมาใส่ที่นี่) ---

if "Booker" in choice:
    st.title("📋 แบบฟอร์มจองรถ (Booker)")
    with st.form("book_form"):
        # ... (ใส่โค้ด Input ต่างๆ จาก app.py เดิมของคุณตรงนี้) ...
        vc = st.text_input("Voucher No.")
        # [ย่อโค้ดเพื่อประหยัดพื้นที่]
        btn = st.form_submit_button("บันทึก")
        if btn: st.success("บันทึกสำเร็จ")

elif "Dispatcher" in choice:
    st.title("🖥️ หน้าจัดการงาน (Dispatcher)")
    # ... (ใส่โค้ดตาราง Search/Export และปุ่มจ่ายงานเข้า LINE ตรงนี้) ...
    st.write("ตารางงานทั้งหมดและการจ่ายงานให้คนขับ")

elif "Driver" in choice:
    st.title("🚖 งานที่ได้รับมอบหมาย (Driver)")
    # ดึงงานเฉพาะที่ระบุชื่อ Driver คนนี้
    st.write("แสดงรายการงานที่คุณต้องไปรับลูกค้าวันนี้")

elif "Airport Staff" in choice:
    st.title("✈️ ตรวจสอบสถานะรถ (Airport Staff)")
    # แสดงตารางเพื่อให้พนักงานสนามบินรู้ว่ารถคันไหนกำลังมา
    st.write("ตารางรถที่จะมาถึงสนามบินเร็วๆ นี้")