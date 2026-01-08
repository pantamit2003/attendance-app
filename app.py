import streamlit as st
import pandas as pd
from datetime import datetime
import os

# 🔹 PWA ENABLE
st.markdown("""
<link rel="manifest" href="/static/manifest.json">
<script>
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/service-worker.js');
}
</script>
""", unsafe_allow_html=True)

# folders
if not os.path.exists("photos"):
    os.mkdir("photos")

FILE = "attendance.csv"

# create file if not exists
if not os.path.exists(FILE):
    df = pd.DataFrame(columns=["DATE", "NAME", "TIME", "PHOTO"])
    df.to_csv(FILE, index=False)

st.title("📸 PHOTO ATTENDANCE SYSTEM")

# ================= USER SECTION =================
name = st.text_input("Enter Your Name")
photo = st.camera_input("Take Photo")

if st.button("PUNCH ATTENDANCE"):
    if name == "" or photo is None:
        st.warning("Name aur Photo dono required hai")
    else:
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
            new_row = {
                "DATE": date,
                "NAME": name,
                "TIME": time,
                "PHOTO": photo_name
            }
            df = df._append(new_row, ignore_index=True)
            df.to_csv(FILE, index=False)

            # ✅ USER KO SIRF MESSAGE
            st.success("✅ Your punch is successful")

# ================= ADMIN SECTION =================
st.divider()
st.subheader("🔐 Admin Login")

admin_password = st.text_input("Enter Admin Password", type="password")

# 🔑 CHANGE PASSWORD HERE
if admin_password == "admin123":
    st.success("Admin Access Granted")

    df = pd.read_csv(FILE)

    st.download_button(
        label="⬇️ Download Attendance CSV",
        data=df.to_csv(index=False),
        file_name="attendance.csv",
        mime="text/csv"
    )
