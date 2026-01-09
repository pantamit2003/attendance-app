import streamlit as st
import pandas as pd
from datetime import datetime
import os
import math

# 📍 OFFICE LOCATION (CHANGE THIS)
OFFICE_LAT = 28.41979
OFFICE_LON = 77.03858
ALLOWED_DISTANCE = 100  # meters

# 🔹 PWA ENABLE
st.markdown("""
<link rel="manifest" href="/static/manifest.json">
<script>
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/service-worker.js');
}

navigator.geolocation.getCurrentPosition(
  function(position) {
    document.cookie = "lat=" + position.coords.latitude;
    document.cookie = "lon=" + position.coords.longitude;
  },
  function(error) {
    alert("❌ Location permission is required");
  }
);
</script>
""", unsafe_allow_html=True)

def distance_in_meters(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# folders
if not os.path.exists("photos"):
    os.mkdir("photos")

FILE = "attendance.csv"

if not os.path.exists(FILE):
    pd.DataFrame(columns=["DATE", "NAME", "TIME", "PHOTO"]).to_csv(FILE, index=False)

st.title("📸 PHOTO ATTENDANCE SYSTEM")

name = st.text_input("Enter Your Name")
photo = st.camera_input("Take Photo")

if st.button("PUNCH ATTENDANCE"):
    if name == "" or photo is None:
        st.warning("Name aur Photo dono required hai")
    else:
        # 🔐 LOCATION CHECK
        lat = st.experimental_get_query_params().get("lat")
        lon = st.experimental_get_query_params().get("lon")

        if lat is None or lon is None:
            st.error("❌ Location not detected. Please refresh and allow location.")
            st.stop()

        user_lat = float(lat[0])
        user_lon = float(lon[0])

        dist = distance_in_meters(user_lat, user_lon, OFFICE_LAT, OFFICE_LON)

        if dist > ALLOWED_DISTANCE:
            st.error("❌ You are outside the allowed 10 meter location. Attendance blocked.")
            st.stop()

        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")

        photo_name = f"photos/{name}_{time.replace(':','')}.jpg"
        with open(photo_name, "wb") as f:
            f.write(photo.getbuffer())

        df = pd.read_csv(FILE)

        if ((df["NAME"] == name) & (df["DATE"] == date)).any():
            st.error("Aaj already punch ho chuka hai")
        else:
            df = df._append({
                "DATE": date,
                "NAME": name,
                "TIME": time,
                "PHOTO": photo_name
            }, ignore_index=True)
            df.to_csv(FILE, index=False)

            st.success("✅ Your punch is successful")

# ================= ADMIN =================
st.divider()
st.subheader("🔐 Admin Login")

admin_password = st.text_input("Enter Admin Password", type="password")
if admin_password == "admin123":
    df = pd.read_csv(FILE)
    st.download_button(
        "⬇️ Download Attendance CSV",
        df.to_csv(index=False),
        "attendance.csv",
        "text/csv"
    )

