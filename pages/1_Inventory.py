import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import init_pool
from models.medicine import (get_all_medicines, get_medicine_by_id, add_medicine,
                              update_medicine, delete_medicine, get_categories)
from utils.helpers import format_currency, format_date

st.set_page_config(page_title="Inventory — MediShop", page_icon="💊", layout="wide")
st.markdown("""
<style>
#MainMenu{visibility:hidden}footer{visibility:hidden}
.stButton>button{border-radius:8px;font-weight:600}
h1,h2,h3{color:#1e2a3a!important}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_db(): init_pool()
init_db()

CATS = ["Analgesic","Antibiotic","Antacid","Antidiabetic","Antihypertensive","Cholesterol",
        "Antihistamine","Antiplatelet","Supplement","Antifungal","Antiviral","Antiseptic",
        "Hormone","Steroid","Antidepressant","Antiasthmatic","Diuretic","Expectorant",
        "Antiemetic","General","Other"]

st.title("💊 Inventory")

f1,f2,f3,f4 = st.columns([3,2,1,1])
search    = f1.text_input("🔍 Search")
cats      = ["All"] + get_categories()
category  = f2.selectbox("Category", cats)
low_only  = f3.checkbox("Low Stock Only")
exp_only  = f4.checkbox("Expiring Soon")

meds = get_all_medicines(search=search, category=category,
                          low_stock_only=low_only, expiring_only=exp_only)
st.caption(f"{len(meds):,} medicines found")

if meds:
    rows = []
    for m in meds:
        ss = str(m["stock_status"])
        es = str(m["expiry_status"])
        rows.append({
            "ID":          m["medicine_id"],
            "Name":        m["name"],
            "Manufacturer":m["manufacturer"] or "",
            "Category":    m["category"] or "",
            "Price":       float(m["unit_price"]),
            "Stock":       m["stock_quantity"],
            "Reorder":     m["reorder_level"],
            "Expiry":      format_date(m["expiry_date"]),
            "Stock":       "OUT" if ss=="out_of_stock" else ("LOW" if ss=="low_stock" else "OK"),
            "Expiry Stat": "EXPIRED" if es=="expired" else ("SOON" if es=="expiring_soon" else "OK"),
        })
    df = pd.DataFrame(rows)
    def cr(row):
        if "EXPIRED" in str(row["Expiry Stat"]) or row["Stock"] == "OUT":
            return ["background-color:#fce8e6"]*len(row)
        if "SOON" in str(row["Expiry Stat"]) or row["Stock"] == "LOW":
            return ["background-color:#fef3cd"]*len(row)
        return [""]*len(row)
    st.dataframe(df.style.apply(cr, axis=1).format({"Price": lambda x: f"₹{x:,.2f}"}),
                 use_container_width=True, height=400, hide_index=True)
else:
    st.info("No medicines found.")

st.markdown("---")
t_add, t_edit, t_del = st.tabs(["➕ Add", "✏️ Edit", "🗑️ Delete"])

with t_add:
    with st.form("add", clear_on_submit=True):
        a1,a2 = st.columns(2)
        name  = a1.text_input("Medicine Name *")
        mfr   = a2.text_input("Manufacturer")
        a3,a4 = st.columns(2)
        cat   = a3.selectbox("Category", CATS)
        price = a4.number_input("Price (₹)", min_value=0.0, step=0.5, format="%.2f")
        a5,a6 = st.columns(2)
        stock = a5.number_input("Stock", min_value=0, step=1)
        reord = a6.number_input("Reorder Level", min_value=0, step=1, value=10)
        exp   = st.date_input("Expiry Date", value=None)
        se    = st.text_area("Side Effects")
        subs  = st.text_area("Substitutes")
        if st.form_submit_button("💾 Add Medicine", use_container_width=True):
            if not name.strip():
                st.error("Name is required.")
            else:
                try:
                    add_medicine({"name":name.strip(),"manufacturer":mfr.strip(),"category":cat,
                                  "unit_price":float(price),"stock_quantity":int(stock),
                                  "reorder_level":int(reord),"expiry_date":exp,
                                  "side_effects":se,"substitutes":subs})
                    st.success(f"✅ '{name}' added!")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

with t_edit:
    mid = st.number_input("Medicine ID to edit", min_value=1, step=1, key="eid")
    if st.button("🔍 Load", key="el"):
        m = get_medicine_by_id(mid)
        st.session_state["em"] = dict(m) if m else None
        if not m: st.error("Not found.")
    if st.session_state.get("em"):
        m = st.session_state["em"]
        st.info(f"Editing: **{m['name']}**")
        with st.form("edit"):
            e1,e2 = st.columns(2)
            en = e1.text_input("Name",         value=m["name"])
            em = e2.text_input("Manufacturer", value=m["manufacturer"] or "")
            e3,e4 = st.columns(2)
            idx   = CATS.index(m["category"]) if m["category"] in CATS else 0
            ec    = e3.selectbox("Category", CATS, index=idx)
            ep    = e4.number_input("Price", value=float(m["unit_price"]), min_value=0.0, format="%.2f")
            e5,e6 = st.columns(2)
            es_   = e5.number_input("Stock",        value=int(m["stock_quantity"]), min_value=0)
            er    = e6.number_input("Reorder Level", value=int(m["reorder_level"]),  min_value=0)
            ee    = st.date_input("Expiry", value=m["expiry_date"])
            ese   = st.text_area("Side Effects", value=m["side_effects"] or "")
            esu   = st.text_area("Substitutes",  value=m["substitutes"]  or "")
            if st.form_submit_button("💾 Save", use_container_width=True):
                try:
                    update_medicine(m["medicine_id"],
                                    {"name":en,"manufacturer":em,"category":ec,"unit_price":float(ep),
                                     "stock_quantity":int(es_),"reorder_level":int(er),
                                     "expiry_date":ee,"side_effects":ese,"substitutes":esu})
                    st.success("✅ Updated!")
                    del st.session_state["em"]
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

with t_del:
    did = st.number_input("Medicine ID to delete", min_value=1, step=1, key="did")
    if st.button("🔍 Load", key="dl"):
        m = get_medicine_by_id(did)
        st.session_state["dm"] = dict(m) if m else None
        if not m: st.error("Not found.")
    if st.session_state.get("dm"):
        m = st.session_state["dm"]
        st.warning(f"Delete **{m['name']}** (ID {m['medicine_id']})?")
        d1,d2 = st.columns(2)
        if d1.button("🗑️ Confirm", type="primary", use_container_width=True):
            try:
                delete_medicine(m["medicine_id"])
                st.success("Deleted.")
                del st.session_state["dm"]
                st.rerun()
            except Exception as e:
                st.error(str(e))
        if d2.button("Cancel", use_container_width=True):
            del st.session_state["dm"]
            st.rerun()
