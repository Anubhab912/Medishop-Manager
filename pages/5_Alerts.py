import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import init_pool
from models.medicine import get_expiry_alerts, get_low_stock_alerts
from utils.helpers import format_date

st.set_page_config(page_title="Alerts — MediShop", page_icon="🔔", layout="wide")
st.markdown("""<style>#MainMenu{visibility:hidden}footer{visibility:hidden}
h1,h2,h3{color:#1e2a3a!important}</style>""", unsafe_allow_html=True)

@st.cache_resource
def init_db(): init_pool()
init_db()

st.title("🔔 Alerts")
if st.button("🔄 Refresh"): st.rerun()

expiry = get_expiry_alerts()
stock  = get_low_stock_alerts()

m1,m2,m3,m4 = st.columns(4)
m1.metric("❌ Expired",       sum(1 for a in expiry if a["status"]=="EXPIRED"))
m2.metric("⏰ Expiring Soon", sum(1 for a in expiry if a["status"]=="EXPIRING SOON"))
m3.metric("📦 Out of Stock",  sum(1 for a in stock  if a["stock_quantity"]==0))
m4.metric("⚠️ Low Stock",     sum(1 for a in stock  if a["stock_quantity"]>0))

st.markdown("---")
te, ts = st.tabs([f"⏰ Expiry ({len(expiry)})", f"📦 Stock ({len(stock)})"])

with te:
    if expiry:
        df = pd.DataFrame([{"ID":a["medicine_id"],"Medicine":a["name"],"Stock":a["stock_quantity"],
                             "Expiry":format_date(a["expiry_date"]),"Status":a["status"]} for a in expiry])
        def h1(row):
            c = "#fce8e6" if row["Status"]=="EXPIRED" else "#fef3cd"
            return [f"background-color:{c}"]*len(row)
        st.dataframe(df.style.apply(h1,axis=1), use_container_width=True, hide_index=True, height=400)
    else:
        st.success("✅ No expiry alerts!")

with ts:
    if stock:
        df2 = pd.DataFrame([{"ID":a["medicine_id"],"Medicine":a["name"],"Manufacturer":a.get("manufacturer",""),
                              "Stock":a["stock_quantity"],"Reorder":a["reorder_level"],"Status":a["status"]} for a in stock])
        def h2(row):
            c = "#fce8e6" if row["Stock"]==0 else "#fef3cd"
            return [f"background-color:{c}"]*len(row)
        st.dataframe(df2.style.apply(h2,axis=1), use_container_width=True, hide_index=True, height=400)
    else:
        st.success("✅ All medicines well stocked!")
