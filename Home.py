import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database.db import init_pool
from models.medicine import get_dashboard_stats, get_expiry_alerts, get_low_stock_alerts
from models.bill import get_revenue_stats
from utils.helpers import format_currency, format_date

st.set_page_config(page_title="MediShop Manager", page_icon="💊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
#MainMenu{visibility:hidden}footer{visibility:hidden}
[data-testid="metric-container"]{background:#fff;border:1px solid #dadce0;
    border-radius:12px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,0.08)}
[data-testid="stMetricValue"]{font-size:2rem!important;font-weight:700}
.stButton>button{border-radius:8px;font-weight:600}
h1,h2,h3{color:#1e2a3a!important}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def init_db():
    try:
        init_pool()
        return True
    except Exception as e:
        return str(e)


db_ok = init_db()
if db_ok is not True:
    st.error(f"❌ Cannot connect to database: {db_ok}")
    st.info("Go to **⚙️ Setup** in the sidebar and check your database connection.")
    st.stop()

with st.sidebar:
    st.markdown("## 💊 MediShop Manager")
    st.markdown("---")
    st.markdown("Navigate using the pages below.")

st.title("📊 Dashboard")
st.caption("Live overview of your medical shop")

try:
    med = get_dashboard_stats()
    rev = get_revenue_stats()
except Exception as e:
    st.error(f"Error loading stats: {e}")
    st.stop()

if med["total_medicines"] < 20:
    st.info("💡 Only a few medicines loaded. Go to **📥 Import Medicines** to load your Kaggle dataset.")

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("💊 Medicines",     med["total_medicines"])
c2.metric("💰 Today",         format_currency(rev["today_revenue"]))
c3.metric("📈 This Month",    format_currency(rev["month_revenue"]))
c4.metric("🧾 Total Bills",   rev["total_bills"])
c5.metric("⚠️ Low Stock",     med["low_stock_count"])
c6.metric("⏰ Expiring Soon", med["expiring_count"])

st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.subheader("⏰ Expiring / Expired Medicines")
    alerts = get_expiry_alerts()
    if alerts:
        df = pd.DataFrame([{
            "Medicine":    a["name"],
            "Stock":       a["stock_quantity"],
            "Expiry Date": format_date(a["expiry_date"]),
            "Status":      a["status"],
        } for a in alerts])
        def hl(row):
            c = "#fce8e6" if row["Status"] == "EXPIRED" else "#fef3cd"
            return [f"background-color:{c}"] * len(row)
        st.dataframe(df.style.apply(hl, axis=1),
                     use_container_width=True, hide_index=True, height=280)
    else:
        st.success("✅ No expiry alerts!")

with col2:
    st.subheader("📦 Low Stock Medicines")
    stock = get_low_stock_alerts()
    if stock:
        df2 = pd.DataFrame([{
            "Medicine":   s["name"],
            "Stock":      s["stock_quantity"],
            "Reorder At": s["reorder_level"],
            "Status":     s["status"],
        } for s in stock])
        def hl2(row):
            c = "#fce8e6" if row["Stock"] == 0 else "#fef3cd"
            return [f"background-color:{c}"] * len(row)
        st.dataframe(df2.style.apply(hl2, axis=1),
                     use_container_width=True, hide_index=True, height=280)
    else:
        st.success("✅ All medicines well stocked!")

st.markdown("---")
g1, g2 = st.columns(2)

with g1:
    st.subheader("💰 Revenue Overview")
    fig = go.Figure(go.Bar(
        x=["Today", "This Month", "All Time"],
        y=[float(rev["today_revenue"]),
           float(rev["month_revenue"]),
           float(rev["total_revenue"])],
        marker_color=["#1a73e8", "#34a853", "#fbbc04"],
        text=[format_currency(rev["today_revenue"]),
              format_currency(rev["month_revenue"]),
              format_currency(rev["total_revenue"])],
        textposition="outside",
    ))
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                      margin=dict(t=20, b=20, l=0, r=0),
                      height=280, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with g2:
    st.subheader("🏥 Inventory Health")
    total    = int(med["total_medicines"]) or 1
    low      = int(med["low_stock_count"])
    expiring = int(med["expiring_count"])
    expired  = int(med["expired_count"])
    healthy  = max(0, total - low - expiring - expired)
    fig2 = go.Figure(go.Pie(
        labels=["Healthy", "Low Stock", "Expiring", "Expired"],
        values=[healthy, low, expiring, expired],
        hole=0.45,
        marker_colors=["#34a853", "#fbbc04", "#ff9800", "#ea4335"],
    ))
    fig2.update_layout(margin=dict(t=20, b=20, l=0, r=0), height=280)
    st.plotly_chart(fig2, use_container_width=True)
