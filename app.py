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
ALLOWED_DISTANCE = 800  # meters
IST = pytz.timezone("Asia/Kolkata")

USERS = {
    "ajad": {"password": "1234"},
    "jitender": {"password": "1234"},
    "ramniwas": {"password": "1234"},
    "lakshman": {"password": "1234"},
    "prempatil": {"password": "1234"},
    "mithlesh": {"password": "1234"},
    "dharmendra": {"password": "1234"},
    "deepak": {"password": "1234"},
    "rajan": {"password": "1234"},
    "shyamjeesharma": {"password": "1234"},
    "surjesh": {"password": "1234"},
    "bittu": {"password": "1234"},
    "prakashkumarjha": {"password": "1234"},
    "amit": {"password": "1234"},
    "himanshu": {"password": "1234"},
    "rahul": {"password": "1234"},
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

def get_allowed_warehouse_ids(user):
    res = (
        supabase.table("user_warehouses")
        .select("warehouse_id")
        .eq("user_name", user)
        .execute()
    )
    return [r["warehouse_id"] for r in (res.data or []) if r["warehouse_id"]]

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
        u = u_raw.strip().lower()

        if u == ADMIN_USER and p == ADMIN_PASSWORD:
            st.session_state.logged = True
            st.session_state.admin = True
            st.rerun()

        if u in USERS and USERS[u]["password"] == p:
            st.session_state.logged = True
            st.session_state.user = u
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

    # ===== WAREHOUSE CHECK =====
    warehouse_ids = get_allowed_warehouse_ids(user)
    if not warehouse_ids:
        st.error("❌ Aap kisi warehouse ke liye allowed nahi ho")
        st.stop()

    valid_location = False

    for wid in warehouse_ids:
        res = (
            supabase.table("warehouses")
            .select("lat, lon")
            .eq("id", wid)
            .execute()
        )

        if not res.data:
            continue

        wh = res.data[0]
        if wh["lat"] is None or wh["lon"] is None:
            continue

        dist = distance_in_meters(lat, lon, float(wh["lat"]), float(wh["lon"]))
        if dist <= ALLOWED_DISTANCE:
            valid_location = True
            break

    if not valid_location:
        st.error("❌ Aap allowed warehouse location par nahi ho")
        st.stop()

    # ===== ATTENDANCE LOGIC =====
    df = load_data()
    today = now_ist().date()

    already_in = (
        (df["name"].str.lower() == user)
        & (pd.to_datetime(df["date"]).dt.date == today)
        & (df["punch_type"] == "IN")
    ).any()

    already_out = (
        (df["name"].str.lower() == user)
        & (pd.to_datetime(df["date"]).dt.date == today)
        & (df["punch_type"] == "OUT")
    ).any()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ PUNCH IN", disabled=already_in):
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
        if st.button("⛔ PUNCH OUT", disabled=not already_in or already_out):
            save_row({
                "date": today.isoformat(),
                "name": user,
                "punch_type": "OUT",
                "time": now_ist().strftime("%H:%M:%S"),
                "lat": lat,
                "lon": lon,
            })
            st.success("Punch OUT successful")


# ================= ADMIN PANEL =================
if st.session_state.logged and st.session_state.admin:

    df = load_data()
    df["date"] = pd.to_datetime(df["date"])
    today = now_ist().date()

    # ---- COMMON FILTER ----
    filter = st.selectbox(
        "📅 Date Filter",
        ["Today", "Yesterday", "Last 7 Days", "Custom Date Range"],
    )

    if filter == "Today":
        filtered_df = df[df["date"].dt.date == today]
    elif filter == "Yesterday":
        filtered_df = df[df["date"].dt.date == today - pd.Timedelta(days=1)]
    elif filter == "Last 7 Days":
        filtered_df = df[
            (df["date"].dt.date >= today - pd.Timedelta(days=7)) &
            (df["date"].dt.date <= today)
        ]
    else:
        s, e = st.columns(2)
        start = s.date_input("Start", today - pd.Timedelta(days=7))
        end = e.date_input("End", today)
        filtered_df = df[
            (df["date"].dt.date >= start) &
            (df["date"].dt.date <= end)
        ]

    tab1, tab2 = st.tabs(["📊 Attendance Table", "📸 Attendance Photos"])

    with tab1:
        if filtered_df.empty:
            st.warning("⚠️ No data found")
        else:
            st.dataframe(filtered_df)

    with tab2:
        if filtered_df.empty:
            st.info("📸 No photos to display")
        else:
            for _, row in filtered_df.iterrows():
                if "photo" in filtered_df.columns and row.get("photo"):
                    url = supabase.storage.from_("attendance-photos").get_public_url(row["photo"])
                    st.image(
                        url,
                        caption=f"{row['name']} | {row['punch_type']}",
                        width=220,
                    )


# ================= LOGOUT =================
if st.session_state.logged:
    if st.button("Logout"):
        st.session_state.clear()
        st.experimental_set_query_params()
        st.rerun()

