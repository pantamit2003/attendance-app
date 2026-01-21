import streamlit as st
import pandas as pd
import pytz
from datetime import datetime
import math
from supabase.client import create_client

# ================= SUPABASE =================
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ================= CONFIG =================
ALLOWED_DISTANCE = 800
IST = pytz.timezone("Asia/Kolkata")

USERS = {
    "Ajad": {"password": "1234"},
    "Jitender": {"password": "1234"},
    "RamNiwas": {"password": "1234"},
    "Lakshman": {"password": "1234"},
    "premPatil": {"password": "1234"},
    "Mithlesh": {"password": "1234"},
    "Dharmendra": {"password": "1234"},
    "Deepak": {"password": "1234"},
    "Rajan": {"password": "1234"},
    "Shyamjeesharma": {"password": "1234"},
    "Surjesh": {"password": "1234"},
    "Bittu": {"password": "1234"},
    "Prakashkumarjha": {"password": "1234"},
    "amit": {"password": "1234"},
    "Himanshu": {"password": "1234"},
    "Rahul": {"password": "1234"},
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
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def get_allowed_warehouses(user):
    res = (
        supabase.table("user_warehouses")
        .select("warehouse_id")
        .eq("user_name", user)
        .execute()
    )
    return res.data or []

def load_data():
    res = supabase.table("attendance").select("*").execute()
    if not res.data:
        return pd.DataFrame(columns=["date","name","punch_type","time","lat","lon"])
    return pd.DataFrame(res.data)

def save_row(row):
    supabase.table("attendance").insert(row).execute()

# ================= GPS SCRIPT =================
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

st.title("📍 SWISS MILITARY ATTENDANCE SYSTEM (NO PHOTO)")

# ================= LOGIN =================
if not st.session_state.logged:
    u_raw = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        u_clean = u_raw.strip().lower()

        if u_clean == ADMIN_USER and p == ADMIN_PASSWORD:
            st.session_state.logged = True
            st.session_state.admin = True
            st.rerun()

        for real_user in USERS:
            if real_user.lower() == u_clean and USERS[real_user]["password"] == p:
                st.session_state.logged = True
                st.session_state.user = real_user.lower()
                st.rerun()

        st.error("Invalid credentials")

# ================= USER PANEL =================
if st.session_state.logged and not st.session_state.admin:
    user = st.session_state.user
    st.subheader(f"👤 Welcome {user}")

    st.markdown('<button onclick="getLocation()">📍 Get My Location</button>', unsafe_allow_html=True)

    params = st.experimental_get_query_params()
    if "lat" not in params or "lon" not in params:
        st.warning("📍 Get location first")
        st.stop()

    lat = float(params["lat"][0])
    lon = float(params["lon"][0])
    st.write("GPS:", lat, lon)

    allowed = get_allowed_warehouses(user)
    if not allowed:
        st.error("❌ Aap kisi warehouse ke liye allowed nahi ho")
        st.stop()

    valid_location = False
    for row in allowed:
        warehouse_id = row["warehouse_id"]
        res = supabase.table("warehouses").select("lat, lon").eq("id", warehouse_id).single().execute()
        wh = res.data

        dist = distance_in_meters(lat, lon, wh["lat"], wh["lon"])
        if dist <= ALLOWED_DISTANCE:
            valid_location = True
            break

    if not valid_location:
        st.error("❌ Aap allowed warehouse location par nahi ho")
        st.stop()

    df = load_data()
    today = now_ist().date()

    already_in = ((df["name"] == user) & (pd.to_datetime(df["date"]).dt.date == today) & (df["punch_type"] == "IN")).any()
    already_out = ((df["name"] == user) & (pd.to_datetime(df["date"]).dt.date == today) & (df["punch_type"] == "OUT")).any()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ PUNCH IN"):
            if already_in:
                st.error("Already punched IN")
                st.stop()

            save_row({
                "date": today.isoformat(),
                "name": user,
                "punch_type": "IN",
                "time": now_ist().strftime("%H:%M:%S"),
                "lat": lat,
                "lon": lon,
            })
            st.success("Punch IN successful")

    with col2:
        if st.button("⛔ PUNCH OUT"):
            if not already_in or already_out:
                st.error("Invalid Punch OUT")
                st.stop()

            save_row({
                "date": today.isoformat(),
                "name": user,
                "punch_type": "OUT",
                "time": now_ist().strftime("%H:%M:%S"),
                "lat": lat,
                "lon": lon,
            })
            st.success("Punch OUT successful")

# ================= LOGOUT =================
if st.session_state.logged:
    if st.button("Logout"):
        st.session_state.clear()
        st.experimental_set_query_params()
        st.rerun()
