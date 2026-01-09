import streamlit as st
import pandas as pd
from datetime import datetime
import math
import os

# ================= CONFIG =================
ALLOWED_DISTANCE = 100  # meters
CSV_FILE = "attendance.csv"

USERS = {
    "amit":  {"password": "1234", "lat": 28.65880, "lon": 77.14402},
    "rahul": {"password": "1111", "lat": 28.41933, "lon": 77.03814},
    "neha":  {"password": "2222", "lat": 28.41933, "lon": 77.03814}
}

ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"

# ================= DISTANCE =================
def distance_in_meters(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ================= CSV HELPERS =================
def load_data():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    else:
        return pd.DataFrame(columns=["date","name","time","photo","lat","lon"])

def save_attendance(row):
    df = load_data()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)

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

    params = st.query_params
    if "lat" not in params or "lon" not in params:
        st.error("📍 Location not received. Please open GPS link first.")
        st.stop()

    user_lat = float(params["lat"])
    user_lon = float(params["lon"])

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

        df = load_data()
        if not df.empty and ((df["name"] == st.session_state.user) & (df["date"] == date)).any():
            st.error("❌ Attendance already punched today")
            st.stop()

        os.makedirs("photos", exist_ok=True)
        path = f"photos/{st.session_state.user}_{time.replace(':','')}.jpg"
        with open(path, "wb") as f:
            f.write(photo.getbuffer())

        save_attendance({
            "date": date,
            "name": st.session_state.user,
            "time": time,
            "photo": path,
            "lat": user_lat,
            "lon": user_lon
        })

        st.success("✅ Attendance punched successfully")

# ================= ADMIN PANEL =================
if st.session_state.logged and st.session_state.admin:
    st.subheader("👨‍💼 Admin Dashboard")

    df = load_data()
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
        st.query_params.clear()
        st.rerun()
