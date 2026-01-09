import streamlit as st
import pandas as pd
from datetime import datetime
import math
import os

# ================= CONFIG =================
ALLOWED_DISTANCE = 100  # meters
CSV_FILE = "attendance.csv"

USERS = {
    "amit":  {"password": "1234", "lat": 28.62591, "lon": 77.20905},
    "rahul": {"password": "1111", "lat": 28.41933, "lon": 77.03814},
    "neha":  {"password": "2222", "lat": 28.41933, "lon": 77.03814}
}

ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"

# ================= CSV HELPERS =================
def load_data():
    cols = ["date", "name", "time", "photo", "lat", "lon"]
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

# ================= JS GPS =================
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
    function(){
      alert("❌ Location permission denied");
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
st.title("📸 SWISS MILITARY ATTENDANCE SYSTEM")

# ================= LOGIN =================
if not st.session_state.logged:
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

    st.markdown(
        '<button onclick="getLocation()" style="padding:10px 20px;font-size:16px;">📍 Get My Location</button>',
        unsafe_allow_html=True
    )

    params = st.query_params
    if "lat" not in params or "lon" not in params:
        st.warning("📍 Please click **Get My Location**")
        st.stop()

    lat = float(params["lat"])
    lon = float(params["lon"])

    photo = st.camera_input("📷 Take Photo")

    if st.button("✅ PUNCH ATTENDANCE"):
        if photo is None:
            st.error("❌ Photo required")
            st.stop()

        office = USERS[st.session_state.user]
        dist = distance_in_meters(lat, lon, office["lat"], office["lon"])

        # 🔔 TOO FAR POPUP + MESSAGE
        if dist > ALLOWED_DISTANCE:
            st.markdown(f"""
            <script>
              alert("❌ Sorry, you are too far from your desired location. Distance: {int(dist)} meters");
            </script>
            """, unsafe_allow_html=True)

            st.error("❌ Sorry, you are too far from your desired location")
            st.stop()

        now = datetime.now()
        date = now.strftime("%Y-%m-%d")

        df = load_data()
        if not df.empty and ((df["name"] == st.session_state.user) & (df["date"] == date)).any():
            st.error("❌ Attendance already punched today")
            st.stop()

        os.makedirs("photos", exist_ok=True)
        path = f"photos/{st.session_state.user}_{now.strftime('%H%M%S')}.jpg"
        with open(path, "wb") as f:
            f.write(photo.getbuffer())

        save_row({
            "date": date,
            "name": st.session_state.user,
            "time": now.strftime("%H:%M:%S"),
            "photo": path,
            "lat": lat,
            "lon": lon
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
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()


