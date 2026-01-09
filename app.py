import streamlit as st
import pandas as pd
from datetime import datetime
import math
import os
import mysql.connector

# ================= CONFIG =================
ALLOWED_DISTANCE = 100  # meters

USERS = {
    "amit":  {"password": "1234", "lat": 28.65880, "lon": 77.14402},   # Moti Nagar
    "rahul": {"password": "1111", "lat": 28.41933, "lon": 77.03814},   # Gurgaon
    "neha":  {"password": "2222", "lat": 28.41933, "lon": 77.03814}
}

ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"

# ================= DATABASE =================
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

# ================= GPS FROM BROWSER =================
st.markdown("""
<script>
navigator.geolocation.getCurrentPosition(
  function(pos){
    const params = new URLSearchParams(window.location.search);
    params.set("lat", pos.coords.latitude);
    params.set("lon", pos.coords.longitude);
    window.history.replaceState({}, "", `${location.pathname}?${params}`);
  },
  function(){
    alert("❌ Location permission required");
  }
);
</script>
""", unsafe_allow_html=True)

# ================= SESSION =================
if "logged" not in st.session_state:
    st.session_state.logged = False
    st.session_state.user = None
    st.session_state.admin = False

# ================= UI =================
st.title("📸 ATTENDANCE SYSTEM")

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

# ================= USER =================
if st.session_state.logged and not st.session_state.admin:
    st.subheader(f"👤 Welcome {st.session_state.user}")

    params = st.query_params

    # 🔍 LOCATION STATUS
    if "lat" in params and "lon" in params:
        user_lat = float(params["lat"])
        user_lon = float(params["lon"])
        st.success("📍 Location detected")
        st.caption(f"Lat: {user_lat} | Lon: {user_lon}")
    else:
        st.warning("📍 Waiting for location… allow location & refresh page")
        st.stop()

    photo = st.camera_input("Take Photo")

    if st.button("PUNCH ATTENDANCE"):
        if photo is None:
            st.warning("Photo required")
            st.stop()

        office_lat = USERS[st.session_state.user]["lat"]
        office_lon = USERS[st.session_state.user]["lon"]

        dist = distance_in_meters(user_lat, user_lon, office_lat, office_lon)

        if dist > ALLOWED_DISTANCE:
            st.error(f"❌ Outside allowed location ({int(dist)} meters)")
            st.stop()

        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")

        if not os.path.exists("photos"):
            os.mkdir("photos")

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
            st.error("❌ Already punched today")
        else:
            cur.execute(
                "INSERT INTO attendance (date,name,time,photo) VALUES (%s,%s,%s,%s)",
                (date, st.session_state.user, time, path)
            )
            conn.commit()
            st.success("✅ Attendance punched successfully")

        conn.close()

# ================= ADMIN =================
if st.session_state.logged and st.session_state.admin:
    st.subheader("👨‍💼 Admin Dashboard")

    option = st.selectbox("📅 View Attendance", ["Today", "Last 7 Days", "Last 30 Days"])

    today = datetime.now().date()
    if option == "Today":
        start = end = today
    elif option == "Last 7 Days":
        start = today - pd.Timedelta(days=6)
        end = today
    else:
        start = today - pd.Timedelta(days=29)
        end = today

    conn = get_db_connection()
    df = pd.read_sql(
        "SELECT * FROM attendance WHERE date BETWEEN %s AND %s ORDER BY date DESC",
        conn, params=(start, end)
    )
    conn.close()

    st.dataframe(df, use_container_width=True)

    st.download_button(
        "⬇️ Download CSV",
        df.to_csv(index=False),
        f"attendance_{start}_to_{end}.csv",
        "text/csv"
    )

# ================= LOGOUT =================
if st.session_state.logged:
    if st.button("Logout"):
        st.session_state.logged = False
        st.session_state.user = None
        st.session_state.admin = False
        st.rerun()
