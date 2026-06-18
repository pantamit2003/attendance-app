import streamlit as st
import pandas as pd
import pytz
from datetime import datetime
import math
from supabase.client import create_client
from streamlit_cookies_manager import EncryptedCookieManager

cookies = EncryptedCookieManager(prefix="my_app", password="super_secret_key")
if not cookies.ready():
    with st.spinner("Loading session..."):
        st.stop()

# ================= SUPABASE =================
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# ================= CONFIG =================
ALLOWED_DISTANCE = 500
IST = pytz.timezone("Asia/Kolkata")
SHIFT_HOURS = 8.5
LATE_AFTER_HOUR = 9
LATE_AFTER_MINUTE = 30

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
    "ansh": {"password": "1234"},
}
SECURE_USERS = ["ansh","rahul","ajad","ramniwas","lakshman","prempatil","mithlesh","surjesh","bittu"]
ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"

# ================= HELPERS =================
def now_ist():
    return datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(IST)

def distance_in_meters(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2)
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

@st.cache_data(ttl=300)
def get_allowed_warehouse_ids(user):
    res = supabase.table("user_warehouses").select("warehouse_id").eq("user_name", user).execute()
    return [r["warehouse_id"] for r in (res.data or []) if r["warehouse_id"]]

@st.cache_data(ttl=60)
def load_data():
    res = supabase.table("attendance").select("*").order("id", desc=True).limit(5000).execute()
    if not res.data:
        return pd.DataFrame(columns=["date","name","punch_type","time","lat","lon","warehouse_id"])
    return pd.DataFrame(res.data)

def save_row(row):
    supabase.table("attendance").insert(row).execute()
    load_data.clear()

@st.cache_data(ttl=300)
def get_warehouses_batch(warehouse_ids_tuple):
    res = supabase.table("warehouses").select("id, name, lat, lon").in_("id", list(warehouse_ids_tuple)).execute()
    return res.data or []

def get_nearest_warehouse(lat, lon, warehouse_ids):
    if not warehouse_ids:
        return None
    warehouses = get_warehouses_batch(tuple(warehouse_ids))
    nearest = None
    min_dist = float("inf")
    for wh in warehouses:
        if wh["lat"] is None or wh["lon"] is None:
            continue
        dist = distance_in_meters(lat, lon, float(wh["lat"]), float(wh["lon"]))
        if dist < min_dist:
            min_dist = dist
            nearest = {"id": wh["id"], "name": wh["name"], "distance": dist}
    return nearest

def upload_photo(photo, user):
    filename = f"{user}/{datetime.utcnow().timestamp()}.jpg"
    supabase.storage.from_("attendance-photos").upload(filename, photo.getvalue(), {"content-type": photo.type})
    return filename

@st.cache_data(ttl=60)
def load_remarks():
    res = supabase.table("attendance_remarks").select("*").order("created_at", desc=True).execute()
    return res.data or []

# ================= GPS SCRIPT =================
st.markdown("""
<script>
function getLocation(){
  navigator.geolocation.getCurrentPosition(
    function(pos){
      const lat = pos.coords.latitude;
      const lon = pos.coords.longitude;
      const url = new URL(window.location.href);
      url.searchParams.set("lat", lat);
      url.searchParams.set("lon", lon);
      window.location.href = url.toString();
    },
    function(err){ alert("Location error: " + err.message); },
    { enableHighAccuracy: true, timeout: 10000 }
  );
}
</script>
""", unsafe_allow_html=True)

# ================= GLOBAL CSS =================
st.markdown("""
<style>
/* Metric cards */
.metric-card {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 12px;
    padding: 16px 20px;
    text-align: center;
}
.metric-label {
    font-size: 12px;
    color: #6c757d;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
}
.metric-value {
    font-size: 28px;
    font-weight: 700;
    margin: 0;
}
.metric-green { color: #1a7f4b; }
.metric-red   { color: #c0392b; }
.metric-blue  { color: #1a5fa8; }
.metric-orange{ color: #d35400; }

/* Status badge */
.status-badge {
    display: inline-block;
    padding: 6px 18px;
    border-radius: 999px;
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 8px;
}
.badge-in     { background: #d4edda; color: #155724; }
.badge-out    { background: #f8d7da; color: #721c24; }
.badge-none   { background: #fff3cd; color: #856404; }

/* Progress bar */
.progress-wrap {
    background: #e9ecef;
    border-radius: 999px;
    height: 12px;
    overflow: hidden;
    margin: 8px 0 4px;
}
.progress-bar {
    height: 12px;
    border-radius: 999px;
    transition: width 0.4s ease;
}
.progress-label {
    font-size: 12px;
    color: #6c757d;
    margin-top: 2px;
}

/* Timeline */
.timeline-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid #f0f0f0;
    font-size: 14px;
}
.timeline-dot-in  { width:10px;height:10px;border-radius:50%;background:#1a7f4b;flex-shrink:0; }
.timeline-dot-out { width:10px;height:10px;border-radius:50%;background:#c0392b;flex-shrink:0; }

/* GPS distance pill */
.gps-ok   { background:#d4edda;color:#155724;padding:6px 14px;border-radius:8px;font-size:14px;font-weight:600; }
.gps-far  { background:#f8d7da;color:#721c24;padding:6px 14px;border-radius:8px;font-size:14px;font-weight:600; }

/* Chip */
.chip {
    display: inline-block;
    background: #d4edda;
    color: #155724;
    border-radius: 999px;
    padding: 4px 12px;
    font-size: 13px;
    font-weight: 500;
    margin: 3px;
}
.chip-absent {
    background: #f8d7da;
    color: #721c24;
}

/* Section header */
.section-header {
    font-size: 13px;
    font-weight: 600;
    color: #6c757d;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin: 20px 0 10px;
    border-bottom: 1px solid #e9ecef;
    padding-bottom: 6px;
}

div[data-testid="stButton"] > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
}
</style>
""", unsafe_allow_html=True)

# ================= SESSION =================
if "logged" not in st.session_state:
    st.session_state.logged = False
    st.session_state.user = None
    st.session_state.admin = False

st.title("📍 Swiss Military Attendance System")

# ================= LOGIN =================
if not st.session_state.logged:
    st.markdown("<div style='max-width:400px;margin:40px auto 0;'>", unsafe_allow_html=True)
    st.markdown("#### Sign in to continue")
    u_raw = st.text_input("Username", placeholder="Enter your username")
    p = st.text_input("Password", type="password", placeholder="Enter your password")
    if st.button("Login", use_container_width=True):
        u = (u_raw or "").strip().lower()
        p = (p or "")
        import uuid
        if "device_id" not in cookies:
            cookies["device_id"] = str(uuid.uuid4())
            cookies.save()
        current_device = cookies["device_id"]

        if u == ADMIN_USER and p == ADMIN_PASSWORD:
            st.session_state.logged = True
            st.session_state.admin = True
            st.rerun()

        if u in USERS and USERS[u]["password"] == p:
            if u in SECURE_USERS:
                res = supabase.table("user_devices").select("*").eq("user_name", u).execute()
                if not res.data:
                    supabase.table("user_devices").upsert({"user_name": u, "device_id": current_device}).execute()
                    st.success("✅ Device registered")
                else:
                    saved_device = res.data[0]["device_id"]
                    if saved_device != current_device:
                        st.error("❌ Different device detected. Aap kisi aur mobile se punch in karne ki kosis kar rahe ho.")
                        st.stop()
            st.session_state.logged = True
            st.session_state.user = u
            st.rerun()
        st.error("Invalid credentials")
    st.markdown("</div>", unsafe_allow_html=True)

# ================= USER PANEL =================
if st.session_state.logged and not st.session_state.admin:
    user = st.session_state.user
    today = now_ist().date()

    # Header
    st.markdown(f"<p style='font-size:18px;font-weight:600;margin-bottom:4px;'>👤 Welcome, {user.title()}</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#6c757d;font-size:14px;margin-top:0;'>📅 {today.strftime('%A, %d %B %Y')}</p>", unsafe_allow_html=True)

    # GPS Button
    st.markdown('<button onclick="getLocation()" style="background:#1a5fa8;color:white;border:none;padding:10px 20px;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;width:100%;margin-bottom:12px;">📍 Get My Location</button>', unsafe_allow_html=True)

    params = st.query_params
    if "lat" not in params or "lon" not in params:
        st.warning("📍 Tap the button above to get your location first.")
        st.stop()

    lat = float(params["lat"])
    lon = float(params["lon"])

    warehouse_ids = get_allowed_warehouse_ids(user)
    if not warehouse_ids:
        st.error("❌ Aap kisi warehouse ke liye allowed nahi ho")
        st.stop()

    nearest_wh = get_nearest_warehouse(lat, lon, warehouse_ids)

    # GPS distance display
    if not nearest_wh:
        st.error("❌ No warehouse found")
        st.stop()

    dist_m = int(nearest_wh["distance"])
    if nearest_wh["distance"] > ALLOWED_DISTANCE:
        st.markdown(f'<p class="gps-far">🏭 {nearest_wh["name"]} — {dist_m}m away &nbsp;|&nbsp; ❌ Too far (limit: {ALLOWED_DISTANCE}m)</p>', unsafe_allow_html=True)
        st.stop()
    else:
        st.markdown(f'<p class="gps-ok">🏭 {nearest_wh["name"]} — {dist_m}m away &nbsp;✅</p>', unsafe_allow_html=True)

    st.markdown(f'<p style="font-size:12px;color:#aaa;margin-top:2px;">GPS: {lat:.5f}, {lon:.5f}</p>', unsafe_allow_html=True)

    # Load attendance
    user_clean = user.strip().lower()
    df = load_data()
    df["name"] = df["name"].astype(str).str.strip().str.lower()
    df["punch_type"] = df["punch_type"].astype(str).str.strip().str.upper()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    today_df = df[(df["name"] == user_clean) & (df["date"] == today)]
    already_in  = (today_df["punch_type"] == "IN").any()
    already_out = (today_df["punch_type"] == "OUT").any()

    # Status badge
    st.markdown("<div class='section-header'>Today's Status</div>", unsafe_allow_html=True)
    if already_out:
        st.markdown('<span class="status-badge badge-out">🔴 Punched OUT</span>', unsafe_allow_html=True)
    elif already_in:
        st.markdown('<span class="status-badge badge-in">🟢 Currently IN</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-badge badge-none">🟡 Not Punched Yet</span>', unsafe_allow_html=True)

    # Shift progress bar + timer
    if already_in and not already_out:
        today_in_df = today_df[today_df["punch_type"] == "IN"]
        if not today_in_df.empty:
            punch_in_time = pd.to_datetime(
                today_in_df.iloc[0]["date"].strftime("%Y-%m-%d") + " " + today_in_df.iloc[0]["time"]
            ).tz_localize(IST)
            elapsed = now_ist() - punch_in_time
            worked_hours = elapsed.seconds / 3600
            hours = elapsed.seconds // 3600
            minutes = (elapsed.seconds % 3600) // 60
            pct = min(int((worked_hours / SHIFT_HOURS) * 100), 100)
            bar_color = "#1a7f4b" if pct >= 100 else "#1a5fa8"
            remaining = max(SHIFT_HOURS - worked_hours, 0)

            st.markdown(f"""
            <div style="margin:10px 0;">
              <div style="display:flex;justify-content:space-between;font-size:13px;color:#6c757d;margin-bottom:4px;">
                <span>⏱️ {hours}h {minutes}m worked</span>
                <span>{pct}% of shift</span>
              </div>
              <div class="progress-wrap">
                <div class="progress-bar" style="width:{pct}%;background:{bar_color};"></div>
              </div>
              <div class="progress-label">
                {"✅ Shift complete!" if pct >= 100 else f"⌛ {remaining:.1f} hrs remaining"}
              </div>
            </div>
            """, unsafe_allow_html=True)

    elif already_out:
        # Show total hours worked
        in_df  = today_df[today_df["punch_type"] == "IN"]
        out_df = today_df[today_df["punch_type"] == "OUT"]
        if not in_df.empty and not out_df.empty:
            t_in  = pd.to_datetime(in_df.iloc[0]["date"].strftime("%Y-%m-%d") + " " + in_df.iloc[0]["time"]).tz_localize(IST)
            t_out = pd.to_datetime(out_df.iloc[0]["date"].strftime("%Y-%m-%d") + " " + out_df.iloc[0]["time"]).tz_localize(IST)
            total_sec = (t_out - t_in).seconds
            total_h = total_sec // 3600
            total_m = (total_sec % 3600) // 60
            st.markdown(f"<p style='font-size:14px;color:#1a7f4b;font-weight:600;'>✅ Total hours worked today: {total_h}h {total_m}m</p>", unsafe_allow_html=True)

    # Today's punch timeline
    if not today_df.empty:
        st.markdown("<div class='section-header'>Today's Punch Timeline</div>", unsafe_allow_html=True)
        for _, row in today_df.sort_values("time").iterrows():
            dot_class = "timeline-dot-in" if row["punch_type"] == "IN" else "timeline-dot-out"
            label = "Punch IN" if row["punch_type"] == "IN" else "Punch OUT"
            st.markdown(f"""
            <div class="timeline-row">
              <div class="{dot_class}"></div>
              <span style="font-weight:600;">{label}</span>
              <span style="color:#6c757d;">— {row['time']}</span>
            </div>""", unsafe_allow_html=True)

    # ===== REMARK SECTION =====
    st.markdown("<div class='section-header'>Movement / Expense Remark</div>", unsafe_allow_html=True)
    remark_text = st.text_area("Where are you going?", placeholder="Enter your remarks here, then click Save.")
    if st.button("💾 Save Remark"):
        if not remark_text.strip():
            st.warning("❗ Remark empty nahi ho sakta")
            st.stop()
        try:
            supabase.table("attendance_remarks").insert({
                "user_name": user,
                "date": now_ist().date().isoformat(),
                "time": now_ist().strftime("%H:%M:%S"),
                "remark": remark_text.strip().upper()
            }).execute()
            st.success("✅ Remark saved successfully")
        except Exception as e:
            st.error(e)

    # My recent remarks
    with st.expander("📋 My Recent Remarks"):
        all_remarks = load_remarks()
        my_remarks = [r for r in all_remarks if r.get("user_name","").lower() == user_clean]
        if not my_remarks:
            st.info("No remarks yet.")
        else:
            rm_df = pd.DataFrame(my_remarks[:10])[["date","time","remark"]]
            st.dataframe(rm_df, use_container_width=True, hide_index=True)

    # ===== PHOTO & PUNCH BUTTONS =====
    st.markdown("<div class='section-header'>Attendance Punch</div>", unsafe_allow_html=True)
    photo = st.camera_input("📸 Attendance Photo (Compulsory)")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ PUNCH IN", disabled=already_in, use_container_width=True):
            if not photo:
                st.warning("📸 Punch IN ke liye photo compulsory hai")
                st.stop()
            photo_path = upload_photo(photo, user)
            save_row({
                "date": today.isoformat(), "name": user, "punch_type": "IN",
                "time": now_ist().strftime("%H:%M:%S"), "lat": lat, "lon": lon,
                "warehouse_id": nearest_wh["id"], "warehouse_name": nearest_wh["name"], "photo": photo_path,
            })
            st.success("Punch IN successful")
            st.rerun()

    with col2:
        if st.button("⛔ PUNCH OUT", disabled=(not already_in or already_out), use_container_width=True):
            if not photo:
                st.warning("📸 Punch OUT ke liye photo compulsory hai")
                st.stop()
            photo_path = upload_photo(photo, user)
            save_row({
                "date": today.isoformat(), "name": user, "punch_type": "OUT",
                "time": now_ist().strftime("%H:%M:%S"), "lat": lat, "lon": lon,
                "warehouse_id": nearest_wh["id"], "warehouse_name": nearest_wh["name"], "photo": photo_path,
            })
            st.success("Punch OUT successful")
            st.rerun()

    # My last 7 days summary
    with st.expander("📅 My Last 7 Days"):
        from datetime import timedelta
        week_ago = today - timedelta(days=6)
        my_df = df[(df["name"] == user_clean) & (df["date"] >= week_ago)]
        if my_df.empty:
            st.info("No records found.")
        else:
            summary_rows = []
            for d in pd.date_range(week_ago, today).date:
                day_df = my_df[my_df["date"] == d]
                has_in  = (day_df["punch_type"] == "IN").any()
                has_out = (day_df["punch_type"] == "OUT").any()
                in_time  = day_df[day_df["punch_type"]=="IN"]["time"].values[0]  if has_in  else "-"
                out_time = day_df[day_df["punch_type"]=="OUT"]["time"].values[0] if has_out else "-"
                if has_in and has_out:
                    t_in  = pd.to_datetime(str(d) + " " + in_time).tz_localize(IST)
                    t_out = pd.to_datetime(str(d) + " " + out_time).tz_localize(IST)
                    hrs = round((t_out - t_in).seconds / 3600, 1)
                else:
                    hrs = "-"
                status = "Present" if has_in else "Absent"
                summary_rows.append({"Date": d.strftime("%d %b"), "Status": status, "IN": in_time, "OUT": out_time, "Hours": hrs})
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

# ================= ADMIN PANEL =================
if st.session_state.logged and st.session_state.admin:
    st.markdown("#### 🛡️ Admin Dashboard")

    df = load_data()
    df["date"] = pd.to_datetime(df["date"])
    today = now_ist().date()

    date_filter = st.selectbox("📅 Date Filter", ["Today", "Yesterday", "Last 7 Days", "Custom Date Range"])
    if date_filter == "Today":
        filtered_df = df[df["date"].dt.date == today]
    elif date_filter == "Yesterday":
        filtered_df = df[df["date"].dt.date == today - pd.Timedelta(days=1)]
    elif date_filter == "Last 7 Days":
        filtered_df = df[(df["date"].dt.date >= today - pd.Timedelta(days=7)) & (df["date"].dt.date <= today)]
    else:
        s, e = st.columns(2)
        start = s.date_input("Start", today - pd.Timedelta(days=7))
        end   = e.date_input("End", today)
        filtered_df = df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end)]

    # ── Stat cards ──
    all_users = list(USERS.keys())
    today_df_admin = df[df["date"].dt.date == today].copy()
    today_df_admin["name"] = today_df_admin["name"].astype(str).str.strip().str.lower()
    punched_today = today_df_admin["name"].unique().tolist()
    currently_in  = today_df_admin.groupby("name")["punch_type"].apply(
        lambda x: (x.str.upper() == "IN").any() and not (x.str.upper() == "OUT").any()
    )
    in_count     = int(currently_in.sum())
    absent_today = [u for u in all_users if u not in punched_today]
    absent_count = len(absent_today)
    present_count = len(punched_today)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Present Today</div><div class="metric-value metric-green">{present_count}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Currently IN</div><div class="metric-value metric-blue">{in_count}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Absent Today</div><div class="metric-value metric-red">{absent_count}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Total Records</div><div class="metric-value metric-orange">{len(filtered_df)}</div></div>', unsafe_allow_html=True)

    st.markdown("")

    # ── Who is IN right now ──
    if in_count > 0:
        in_names = currently_in[currently_in].index.tolist()
        chips = "".join([f'<span class="chip">✅ {n.title()}</span>' for n in in_names])
        st.markdown(f"<div class='section-header'>Currently Punched IN</div>{chips}", unsafe_allow_html=True)

    # ── Absent list ──
    if absent_count > 0:
        with st.expander(f"🔴 Absent Today ({absent_count} employees)"):
            chips = "".join([f'<span class="chip chip-absent">❌ {n.title()}</span>' for n in absent_today])
            st.markdown(chips, unsafe_allow_html=True)

    st.markdown("")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Attendance Table",
        "⏱️ Hours Worked",
        "📸 Photos",
        "📝 Remarks",
        "📥 Export"
    ])

    with tab1:
        if filtered_df.empty:
            st.warning("⚠️ No data found")
        else:
            # Employee filter
            emp_names = sorted(filtered_df["name"].astype(str).str.strip().str.lower().unique().tolist())
            sel_emp = st.selectbox("Filter by employee", ["All"] + emp_names)
            display_df = filtered_df if sel_emp == "All" else filtered_df[filtered_df["name"].str.lower().str.strip() == sel_emp]

            # Late arrival flag
            display_df = display_df.copy()
            display_df["name_clean"] = display_df["name"].astype(str).str.strip().str.lower()
            display_df["punch_type_clean"] = display_df["punch_type"].astype(str).str.strip().str.upper()

            def flag_late(row):
                if row["punch_type_clean"] != "IN":
                    return ""
                try:
                    t = datetime.strptime(str(row["time"]), "%H:%M:%S")
                    if t.hour > LATE_AFTER_HOUR or (t.hour == LATE_AFTER_HOUR and t.minute >= LATE_AFTER_MINUTE):
                        return "⚠️ Late"
                except:
                    pass
                return ""

            display_df["flag"] = display_df.apply(flag_late, axis=1)
            st.dataframe(display_df.drop(columns=["name_clean","punch_type_clean"], errors="ignore"), use_container_width=True)

    with tab2:
        if filtered_df.empty:
            st.info("No data for selected range.")
        else:
            hours_df = filtered_df.copy()
            hours_df["name"]       = hours_df["name"].astype(str).str.strip().str.lower()
            hours_df["punch_type"] = hours_df["punch_type"].astype(str).str.strip().str.upper()
            hours_df["date_only"]  = pd.to_datetime(hours_df["date"]).dt.date

            rows = []
            for (name, date_val), grp in hours_df.groupby(["name","date_only"]):
                in_rows  = grp[grp["punch_type"]=="IN"]
                out_rows = grp[grp["punch_type"]=="OUT"]
                if not in_rows.empty and not out_rows.empty:
                    try:
                        t_in  = pd.to_datetime(str(date_val)+" "+in_rows.iloc[0]["time"]).tz_localize(IST)
                        t_out = pd.to_datetime(str(date_val)+" "+out_rows.iloc[0]["time"]).tz_localize(IST)
                        hrs   = round((t_out - t_in).seconds / 3600, 2)
                        overtime = round(max(hrs - SHIFT_HOURS, 0), 2)
                        rows.append({"Employee": name.title(), "Date": date_val, "IN": in_rows.iloc[0]["time"], "OUT": out_rows.iloc[0]["time"], "Hours Worked": hrs, "Overtime": overtime})
                    except:
                        pass

            if not rows:
                st.info("No complete IN-OUT pairs found.")
            else:
                hw_df = pd.DataFrame(rows).sort_values(["Date","Employee"])
                st.dataframe(hw_df, use_container_width=True, hide_index=True)
                total_hrs = hw_df["Hours Worked"].sum()
                st.markdown(f"<p style='font-size:14px;font-weight:600;'>Total hours across all employees: {round(total_hrs,1)} hrs</p>", unsafe_allow_html=True)

    with tab3:
        if filtered_df.empty:
            st.info("📸 No photos to display")
        else:
            for _, row in filtered_df.iterrows():
                if "photo" in filtered_df.columns and row.get("photo"):
                    url = supabase.storage.from_("attendance-photos").get_public_url(row["photo"])
                    st.image(url, caption=f"{row['name']} | {row['punch_type']}", width=220)

    with tab4:
        remarks_data = load_remarks()
        if not remarks_data:
            st.info("📝 No remarks found")
        else:
            remarks_df = pd.DataFrame(remarks_data)
            # Employee filter for remarks
            rem_names = sorted(remarks_df["user_name"].astype(str).str.lower().unique().tolist())
            sel_rem = st.selectbox("Filter remarks by employee", ["All"] + rem_names, key="rem_filter")
            show_rem = remarks_df if sel_rem == "All" else remarks_df[remarks_df["user_name"].str.lower() == sel_rem]
            st.dataframe(show_rem[["user_name","date","time","remark"]], use_container_width=True, hide_index=True)

    with tab5:
        st.markdown("#### Download attendance data")
        if filtered_df.empty:
            st.warning("No data to export.")
        else:
            csv = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"attendance_{today}.csv",
                mime="text/csv",
                use_container_width=True
            )
            # Hours worked export
            hours_df2 = filtered_df.copy()
            hours_df2["name"]       = hours_df2["name"].astype(str).str.strip().str.lower()
            hours_df2["punch_type"] = hours_df2["punch_type"].astype(str).str.strip().str.upper()
            hours_df2["date_only"]  = pd.to_datetime(hours_df2["date"]).dt.date
            hw_rows = []
            for (name, date_val), grp in hours_df2.groupby(["name","date_only"]):
                in_rows  = grp[grp["punch_type"]=="IN"]
                out_rows = grp[grp["punch_type"]=="OUT"]
                if not in_rows.empty and not out_rows.empty:
                    try:
                        t_in  = pd.to_datetime(str(date_val)+" "+in_rows.iloc[0]["time"]).tz_localize(IST)
                        t_out = pd.to_datetime(str(date_val)+" "+out_rows.iloc[0]["time"]).tz_localize(IST)
                        hrs   = round((t_out - t_in).seconds / 3600, 2)
                        hw_rows.append({"Employee": name.title(), "Date": date_val, "IN": in_rows.iloc[0]["time"], "OUT": out_rows.iloc[0]["time"], "Hours Worked": hrs})
                    except:
                        pass
            if hw_rows:
                hw_csv = pd.DataFrame(hw_rows).to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Download Hours Summary as CSV",
                    data=hw_csv,
                    file_name=f"hours_summary_{today}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

# ================= LOGOUT =================
if st.session_state.logged:
    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
