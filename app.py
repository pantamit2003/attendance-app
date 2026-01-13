import streamlit as st
import pandas as pd
import pytz
from datetime import datetime
import math
import uuid
from supabase import create_client

# ================= SUPABASE =================
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ================= CONFIG =================
ALLOWED_DISTANCE = 300  # meters
IST = pytz.timezone("Asia/Kolkata")

USERS = {
    "amit":  {"password": "1234", "lat": 28.743349, "lon": 77.116950},
    "rahul": {"password": "1111", "lat": 28.419466, "lon": 77.038072},
    "neha":  {"password": "2222", "lat": 28.419466, "lon": 77.038072},
    "dep":   {"password": "1456", "lat": 28.502959, "lon": 77.185798}
}

ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"

# ================= HELPERS =================
def now_ist():
    return datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(IST)

def distance_in_meters(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def save_photo(photo):
    if photo is None:
        return ""

    filename = f"{uuid.uuid4()}.jpg"
    supabase.storage.from_("attendance-photos").upload(
        filename,
        photo.getvalue(),
        {"content-type": "image/jpeg"}
    )
    return filename

def save_row(row):
    supabase.table("attendance").insert(row).execute()

def load_data():
    res = supabase.table("attendance").select("*").execute()
    return pd.DataFrame(res.data)

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

# ================= USER PANEL =================
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
    today = now_ist().date()
    user = st.session_state.user

    already_in = ((df["name"] == user) & (pd.to_datetime(df["date"]).dt.date == today) & (df["punch_type"] == "IN")).any()
    already_out = ((df["name"] == user) & (pd.to_datetime(df["date"]).dt.date == today) & (df["punch_type"] == "OUT")).any()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ PUNCH IN"):
            if photo is None:
                st.error("📷 Photo compulsory hai")
                st.stop()

            if already_in:
                st.error("Already punched IN today")
                st.stop()

            dist = distance_in_meters(lat, lon, USERS[user]["lat"], USERS[user]["lon"])
            if dist > ALLOWED_DISTANCE:
                st.error(f"❌ Location mismatch ({int(dist)} m)")
                st.stop()

            save_row({
                "date": today.isoformat(),
                "name": user,
                "punch_type": "IN",
                "time": now_ist().strftime("%H:%M:%S"),
                "photo": save_photo(photo),
                "lat": lat,
                "lon": lon
            })
            st.success("Punch IN successful")

    with col2:
        if st.button("⛔ PUNCH OUT"):
            if photo is None:
                st.error("📷 Photo compulsory hai")
                st.stop()

            if not already_in or already_out:
                st.error("Invalid Punch OUT")
                st.stop()

            dist = distance_in_meters(lat, lon, USERS[user]["lat"], USERS[user]["lon"])
            if dist > ALLOWED_DISTANCE:
                st.error(f"❌ Location mismatch ({int(dist)} m)")
                st.stop()

            save_row({
                "date": today.isoformat(),
                "name": user,
                "punch_type": "OUT",
                "time": now_ist().strftime("%H:%M:%S"),
                "photo": save_photo(photo),
                "lat": lat,
                "lon": lon
            })
            st.success("Punch OUT successful")

# ================= ADMIN PANEL =================
if st.session_state.logged and st.session_state.admin:
    df = load_data()
    df["date"] = pd.to_datetime(df["date"])
    today = now_ist().date()

    tab1, tab2 = st.tabs(["📊 Attendance Table", "📸 Attendance Photos"])

    with tab1:
        filter = st.selectbox("📅 Date Filter",
            ["Today", "Last 1 Day", "Last 7 Days", "Custom Date Range"])

        if filter == "Today":
            filtered_df = df[df["date"].dt.date == today]
        elif filter == "Last 1 Day":
            filtered_df = df[df["date"].dt.date == today - pd.Timedelta(days=1)]
        elif filter == "Last 7 Days":
            filtered_df = df[(df["date"].dt.date >= today - pd.Timedelta(days=7)) & (df["date"].dt.date <= today)]
        else:
            s, e = st.columns(2)
            start = s.date_input("Start", today - pd.Timedelta(days=7))
            end = e.date_input("End", today)
            filtered_df = df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end)]

        st.dataframe(filtered_df)

    with tab2:
        for _, row in filtered_df.iterrows():
            if row["photo"]:
                url = supabase.storage.from_("attendance-photos").get_public_url(row["photo"])
                st.image(url, caption=f"{row['name']} | {row['date'].date()} | {row['punch_type']}", width=220)

# ================= LOGOUT =================
if st.session_state.logged:
    if st.button("Logout"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
