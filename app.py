import streamlit as st
import pandas as pd
import pytz
from datetime import datetime
import math
import os
import uuid
from PIL import Image

# ================= CONFIG =================
ALLOWED_DISTANCE = 300
CSV_FILE = "attendance.csv"
PHOTO_DIR = "photos"

USERS = {
    "amit":  {"password": "1234", "lat": 28.743349, "lon": 77.116950},
    "rahul": {"password": "1111", "lat": 28.419466, "lon": 77.038072},
    "neha":  {"password": "2222", "lat": 28.419466, "lon": 77.038072}
}

ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"

IST = pytz.timezone("Asia/Kolkata")

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

# ================= PHOTO SAVE =================
def save_photo(photo):
    if photo is None:
        return ""
    os.makedirs(PHOTO_DIR, exist_ok=True)
    img = Image.open(photo)
    filename = f"{uuid.uuid4()}.jpg"
    img.save(os.path.join(PHOTO_DIR, filename))
    return filename

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
    today = datetime.now(IST).strftime("%Y-%m-%d")
    user = st.session_state.user

    already_in = ((df["name"] == user) & (df["date"] == today) & (df["punch_type"] == "IN")).any()
    already_out = ((df["name"] == user) & (df["date"] == today) & (df["punch_type"] == "OUT")).any()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ PUNCH IN"):
            if already_in:
                st.error("Already punched IN")
                st.stop()
            if distance_in_meters(lat, lon, USERS[user]["lat"], USERS[user]["lon"]) > ALLOWED_DISTANCE:
                st.error("Too far from office")
                st.stop()

            save_row({
                "date": today,
                "name": user,
                "punch_type": "IN",
                "time": datetime.now(IST).strftime("%H:%M:%S"),
                "photo": save_photo(photo),
                "lat": lat,
                "lon": lon
            })
            st.success("Punch IN successful")

    with col2:
        if st.button("⛔ PUNCH OUT"):
            if not already_in or already_out:
                st.error("Invalid Punch OUT")
                st.stop()

            save_row({
                "date": today,
                "name": user,
                "punch_type": "OUT",
                "time": datetime.now(IST).strftime("%H:%M:%S"),
                "photo": save_photo(photo),
                "lat": lat,
                "lon": lon
            })
            st.success("Punch OUT successful")

# ================= ADMIN =================
if st.session_state.logged and st.session_state.admin:
    df = load_data()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    today = datetime.now(IST).date()

    tab1, tab2 = st.tabs(["📊 Attendance Table", "📸 Attendance Photos"])

    # ---------- TABLE TAB ----------
    with tab1:
        filter_type = st.selectbox("📅 Date Filter",
            ["Today", "Last 1 Day", "Last 7 Days", "Custom Date Range"])

        if filter_type == "Today":
            filtered_df = df[df["date"].dt.date == today]
        elif filter_type == "Last 1 Day":
            filtered_df = df[df["date"].dt.date == (today - pd.Timedelta(days=1))]
        elif filter_type == "Last 7 Days":
            filtered_df = df[(df["date"].dt.date >= today - pd.Timedelta(days=7)) & (df["date"].dt.date <= today)]
        else:
            c1, c2 = st.columns(2)
            start = c1.date_input("Start Date", today - pd.Timedelta(days=7))
            end = c2.date_input("End Date", today)
            filtered_df = df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end)]

        st.dataframe(filtered_df)
        st.download_button("⬇️ Download CSV", filtered_df.to_csv(index=False), "attendance.csv")

    # ---------- PHOTOS TAB ----------
    with tab2:
        st.subheader("📸 Attendance Photos")
        punch_filter = st.selectbox("Punch Type", ["All", "IN", "OUT"])

        photo_df = filtered_df.copy()
        if punch_filter != "All":
            photo_df = photo_df[photo_df["punch_type"] == punch_filter]

        if photo_df.empty:
            st.info("No photos found")
        else:
            for _, row in photo_df.iterrows():
                img_path = os.path.join(PHOTO_DIR, row["photo"])
                if row["photo"] and os.path.exists(img_path):
                    with st.container(border=True):
                        st.markdown(
                            f"**👤 {row['name']}**  \n"
                            f"📅 {row['date'].date()} | 🕒 {row['time']} | 🔖 {row['punch_type']}"
                        )
                        st.image(img_path, width=220)

# ================= LOGOUT =================
if st.session_state.logged:
    if st.button("Logout"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
