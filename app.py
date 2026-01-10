import streamlit as st
import pandas as pd
from datetime import datetime
import math
import os

# ================= CONFIG =================
ALLOWED_DISTANCE = 300
CSV_FILE = "attendance.csv"

USERS = {
    "amit":  {"password": "1234", "lat": 28.743349, "lon": 77.116950},
    "rahul": {"password": "1111", "lat": 28.41980, "lon": 77.03850},
    "neha":  {"password": "2222", "lat": 28.41980, "lon": 77.03850}
}

ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"

# ================= CSV =================
def load_data():
    cols = ["date","name","punch_type","time","photo","lat","lon"]
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        return df[cols]
    return pd.DataFrame(columns=cols)

def save_row(row):
    df = load_data()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)

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
    photo = st.camera_input("📷 Take Photo")

    df = load_data()
    today = datetime.now().strftime("%Y-%m-%d")
    user = st.session_state.user

    already_in = ((df["name"]==user)&(df["date"]==today)&(df["punch_type"]=="IN")).any()
    already_out = ((df["name"]==user)&(df["date"]==today)&(df["punch_type"]=="OUT")).any()

    col1, col2 = st.columns(2)

    # ================= PUNCH IN =================
    with col1:
        if st.button("✅ PUNCH IN"):
            if already_in:
                st.error("Already punched IN today")
                st.stop()

            office = USERS[user]
            if distance_in_meters(lat, lon, office["lat"], office["lon"]) > ALLOWED_DISTANCE:
                st.error("Too far from office")
                st.stop()

            now = datetime.now()
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

    # ================= PUNCH OUT =================
    with col2:
        if st.button("⛔ PUNCH OUT"):
            if not already_in:
                st.error("Punch IN first")
                st.stop()
            if already_out:
                st.error("Already punched OUT")
                st.stop()

            now = datetime.now()
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
    df = load_data()
    st.dataframe(df)
    st.download_button("Download CSV", df.to_csv(index=False), "attendance.csv")

# ================= LOGOUT =================
if st.session_state.logged:
    if st.button("Logout"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()



