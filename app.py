import streamlit as st
import pandas as pd
from datetime import datetime
import math
import os
import mysql.connector

# ================= CONFIG =================
ALLOWED_DISTANCE = 100  # meters

USERS = {
    "amit":  {"password": "1234", "lat": 28.65880, "lon": 77.14402},
    "rahul": {"password": "1111", "lat": 28.41933, "lon": 77.03814},
    "neha":  {"password": "2222", "lat": 28.41933, "lon": 77.03814}
}

ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"

# ================= DB =================
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root@123",
        database="attendance_db",
        port=3306
    )

# ================= DISTANCE =================
def distance_in_meters(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ================= JS GPS (MANUAL BUTTON) =================
st.markdown("""
<script>
window.getLocation = function(){
  if (!navigator.geolocation) {
    alert("GPS not supported");
    return;
  }

  navigator.geolocation.getCurrentPosition(
    function(pos){
      const params = new URLSearchParams(window.location.search);
      params.set("lat", pos.coords.latitude);
      params.set("lon", pos.coords.longitude);
      window.location.href = window.location.pathname + "?" + params.toString();
    },
    function(){
      alert("❌ Location permission denied. Enable GPS.");
    },
    { enableHighAccuracy: true, timeout: 10000 }
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
st.title("📸 GPS BASED ATTENDANCE SYSTEM")

# ================= LOGIN =================
if not st.session_state.logged:
    st.subheader("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == ADMIN_USER and password == ADMIN_PASSWORD:
            st.session_state.logged = True
            st.session_state.admin = True
            st.rerun()

        elif username in USERS and USERS[username]["password"] == password:
            st.session_state.logged = True
            st.session_state.user = username
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

# ================= USER PANEL =================
if st.session_state.logged and not st.session_state.admin:
    st.subheader(f"👤 Welcome {st.session_state.user}")

    # 🔘 GET LOCATION BUTTON
    st.markdown(
        '<button onclick="getLocation()" style="padding:10px 20px;font-size:16px;">📍 Get My Location</button>',
        unsafe_allow_html=True
    )

    params = st.experimental_get_query_params()

    if "lat" not in params or "lon" not in params:
        st.warning("📍 Click **Get My Location** to continue")
        st.stop()

    user_lat = float(params["lat"][0])
    user_lon = float(params["lon"][0])

    photo = st.camera_input("📷 Take Photo")

    if st.button("✅ PUNCH ATTENDANCE"):
        if photo is None:
            st.error("❌ Photo required")
            st.stop()

        office_lat = USERS[st.session_state.user]["lat"]
        office_lon = USERS[st.session_state.user]["lon"]

        dist = distance_in_meters(user_lat, user_lon, office_lat, office_lon)

        if dist > ALLOWED_DISTANCE:
            st.error(f"❌ You are {int(dist)} meters away from allowed location")
            st.stop()

        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")

        os.makedirs("photos", exist_ok=True)
        path = f"photos/{st.session_state.user}_{time.replace(':','')}.jpg"
        with open(path, "wb") as f:
            f.write(photo.getbuffer())

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT COUNT(*) FROM attendance WHERE name=%s AND date=%s",
            (st.session_state.user, date)
        )

        if cur.fetchone()[0] > 0:
            st.error("❌ Attendance already punched today")
        else:
            cur.execute(
                "INSERT INTO attendance (date,name,time,photo) VALUES (%s,%s,%s,%s)",
                (date, st.session_state.user, time, path)
            )
            conn.commit()
            st.success("✅ Attendance punched successfully")

        conn.close()

# ================= ADMIN PANEL =================
if st.session_state.logged and st.session_state.admin:
    st.subheader("👨‍💼 Admin Dashboard")

    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM attendance ORDER BY date DESC", conn)
    conn.close()

    st.dataframe(df, use_container_width=True)

    st.download_button(
        "⬇️ Download CSV",
        df.to_csv(index=False),
        "attendance.csv",
        "text/csv"
    )

# ================= LOGOUT =================
if st.session_state.logged:
    if st.button("🚪 Logout"):
        st.session_state.logged = False
        st.session_state.user = None
        st.session_state.admin = False
        st.experimental_set_query_params()
        st.rerun()
