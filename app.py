import streamlit as st
import pandas as pd
import pytz
from datetime import datetime
import math
import mysql.connector

# ================= CONFIG =================
ALLOWED_DISTANCE = 300

USERS = {
    "amit":  {"password": "1234", "lat": 28.743349, "lon": 77.116950},
    "rahul": {"password": "1111", "lat": 28.419466, "lon": 77.038072},
    "neha":  {"password": "2222", "lat": 28.419466, "lon": 77.038072}
}

ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"

# ================= IST TIMEZONE =================
IST = pytz.timezone("Asia/Kolkata")

# ================= MYSQL CONNECTION =================
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root@123",      # 🔴 change if needed
        database="attendance_db",
        port=3306
    )

# ================= DB FUNCTIONS =================
def save_row(row):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO attendance
        (date, name, punch_type, time, photo, lat, lon)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        row["date"],
        row["name"],
        row["punch_type"],
        row["time"],
        row["photo"],
        row["lat"],
        row["lon"]
    ))
    conn.commit()
    cursor.close()
    conn.close()

def load_data():
    conn = get_db_connection()
    df = pd.read_sql(
        "SELECT date, name, punch_type, time, photo, lat, lon FROM attendance",
        conn
    )
    conn.close()
    return df

# ================= DISTANCE =================
def distance_in_meters(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ================= GPS =================
st.markdown("""
<script>
function getLocation(){
  navigator.geolocation.getCurrentPosition(
    function(pos){
      const p = new URLSearchParams(window.location.search);
      p.set("lat", pos.coords.latitude);
      p.set("lon", pos.coords.longitude);
      window.location.search = p.toString();
    },
    function(){ alert("Location denied"); }
  );
}
</script>
""", unsafe_allow_html=True)

# ================= SESSION =================
if "logged" not in st.session_state:
    st.session_state.logged = False
    st.session_state.user = None
    st.session_state.admin = False

# ================= UI =================
st.title("📸 SWISS MILITARY ATTENDANCE SYSTEM")

# ================= LOGIN =================
if not st.session_state.logged:
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u == ADMIN_USER and p == ADMIN_PASSWORD:
            st.session_state.logged = True
            st.session_state.admin = True
            st.rerun()

        elif u in USERS and USERS[u]["password"] == p:
            st.session_state.logged = True
            st.session_state.user = u
            st.rerun()

        else:
            st.error("Invalid credentials")

# ================= USER =================
if st.session_state.logged and not st.session_state.admin:
    st.subheader(f"👤 Welcome {st.session_state.user}")

    st.markdown('<button onclick="getLocation()">📍 Get My Location</button>', unsafe_allow_html=True)

    params = st.query_params
    if "lat" not in params:
        st.warning("Get location first")
        st.stop()

    lat = float(params["lat"])
    lon = float(params["lon"])
    st.camera_input("📷 Take Photo")

    df = load_data()
    now = datetime.now(IST)
    today = now.strftime("%Y-%m-%d")
    user = st.session_state.user

    already_in = ((df["name"] == user) & (df["date"] == today) & (df["punch_type"] == "IN")).any()
    already_out = ((df["name"] == user) & (df["date"] == today) & (df["punch_type"] == "OUT")).any()

    col1, col2 = st.columns(2)

    # ===== PUNCH IN =====
    with col1:
        if st.button("✅ PUNCH IN"):
            if already_in:
                st.error("Already punched IN today")
                st.stop()

            office = USERS[user]
            if distance_in_meters(lat, lon, office["lat"], office["lon"]) > ALLOWED_DISTANCE:
                st.error("Too far from office")
                st.stop()

            now = datetime.now(IST)
            save_row({
                "date": today,
                "name": user,
                "punch_type": "IN",
                "time": now.strftime("%H:%M:%S"),
                "photo": "photo",
                "lat": lat,
                "lon": lon
            })
            st.success("Punch IN successful")

    # ===== PUNCH OUT =====
    with col2:
        if st.button("⛔ PUNCH OUT"):
            if not already_in:
                st.error("Punch IN first")
                st.stop()

            if already_out:
                st.error("Already punched OUT")
                st.stop()

            now = datetime.now(IST)
            save_row({
                "date": today,
                "name": user,
                "punch_type": "OUT",
                "time": now.strftime("%H:%M:%S"),
                "photo": "photo",
                "lat": lat,
                "lon": lon
            })
            st.success("Punch OUT successful")

# ================= ADMIN =================
if st.session_state.logged and st.session_state.admin:
    st.subheader("🧑‍💼 Admin Attendance Dashboard")

    df = load_data()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    today = datetime.now(IST).date()

    filter_type = st.selectbox(
        "📅 Select Filter",
        ["Today", "Last 1 Day", "Last 7 Days", "Custom Date Range"]
    )

    if filter_type == "Today":
        filtered_df = df[df["date"].dt.date == today]

    elif filter_type == "Last 1 Day":
        filtered_df = df[df["date"].dt.date == (today - pd.Timedelta(days=1))]

    elif filter_type == "Last 7 Days":
        filtered_df = df[
            (df["date"].dt.date >= (today - pd.Timedelta(days=7))) &
            (df["date"].dt.date <= today)
        ]

    else:
        c1, c2 = st.columns(2)
        with c1:
            start_date = st.date_input("Start Date", today - pd.Timedelta(days=7))
        with c2:
            end_date = st.date_input("End Date", today)

        filtered_df = df[
            (df["date"].dt.date >= start_date) &
            (df["date"].dt.date <= end_date)
        ]

    st.dataframe(filtered_df)

    st.download_button(
        "⬇️ Download CSV",
        filtered_df.to_csv(index=False),
        "attendance_filtered.csv"
    )

# ================= LOGOUT =================
if st.session_state.logged:
    if st.button("Logout"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
