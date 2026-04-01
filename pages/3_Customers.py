import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import init_pool
from models.customer import (get_all_customers, get_customer_by_id, add_customer,
                              update_customer, delete_customer, get_customer_purchase_history)
from utils.helpers import format_currency, format_datetime, generate_customer_id

st.set_page_config(page_title="Customers — MediShop", page_icon="👥", layout="wide")
st.markdown("""<style>#MainMenu{visibility:hidden}footer{visibility:hidden}
.stButton>button{border-radius:8px;font-weight:600}h1,h2,h3{color:#1e2a3a!important}</style>""", unsafe_allow_html=True)

@st.cache_resource
def init_db(): init_pool()
init_db()

st.title("👥 Customers")
search = st.text_input("🔍 Search by name, phone or ID")
custs  = get_all_customers(search)
st.caption(f"{len(custs):,} customers")

if custs:
    df = pd.DataFrame([{"ID":c["customer_id"],"Name":c["name"],"Phone":c["phone"] or "",
                         "Email":c["email"] or "","Bills":c["total_bills"],
                         "Total Spent":format_currency(c["total_spent"]),
                         "Since":format_datetime(c["created_at"],"%d-%m-%Y")} for c in custs])
    st.dataframe(df, use_container_width=True, hide_index=True, height=300)
else:
    st.info("No customers yet.")

st.markdown("---")
t1,t2,t3,t4 = st.tabs(["➕ Add","✏️ Edit","📋 History","🗑️ Delete"])

with t1:
    with st.form("ac", clear_on_submit=True):
        a1,a2 = st.columns(2); an=a1.text_input("Full Name *"); ap=a2.text_input("Phone")
        a3,a4 = st.columns(2); ae=a3.text_input("Email");       aa=a4.text_input("Address")
        if st.form_submit_button("💾 Add", use_container_width=True):
            if not an.strip(): st.error("Name required.")
            else:
                cid = generate_customer_id()
                try:
                    add_customer({"customer_id":cid,"name":an.strip(),"phone":ap,"email":ae,"address":aa})
                    st.success(f"✅ Added! ID: **{cid}**"); st.rerun()
                except Exception as e: st.error(str(e))

with t2:
    eid = st.text_input("Customer ID", key="eid")
    if st.button("🔍 Load", key="el"):
        c = get_customer_by_id(eid)
        st.session_state["ec"] = dict(c) if c else None
        if not c: st.error("Not found.")
    if st.session_state.get("ec"):
        c = st.session_state["ec"]
        st.info(f"Editing: **{c['name']}**")
        with st.form("ecc"):
            e1,e2=st.columns(2); en=e1.text_input("Name",value=c["name"]); ep=e2.text_input("Phone",value=c["phone"] or "")
            e3,e4=st.columns(2); ee=e3.text_input("Email",value=c["email"] or ""); ea=e4.text_input("Address",value=c["address"] or "")
            if st.form_submit_button("💾 Save", use_container_width=True):
                try:
                    update_customer(c["customer_id"],{"name":en,"phone":ep,"email":ee,"address":ea})
                    st.success("✅ Updated!"); del st.session_state["ec"]; st.rerun()
                except Exception as e: st.error(str(e))

with t3:
    hid = st.text_input("Customer ID for history")
    if st.button("📋 Load History", use_container_width=True) and hid:
        cust = get_customer_by_id(hid)
        if not cust: st.error("Not found.")
        else:
            hist = get_customer_purchase_history(hid)
            st.markdown(f"**{cust['name']}** — {len(hist)} records")
            if hist:
                df_h = pd.DataFrame([{"Bill":h["bill_number"],"Date":format_datetime(h["created_at"],"%d-%m-%Y"),
                    "Medicine":h["medicine_name"],"Qty":h["quantity"],"Amount":format_currency(h["subtotal"]),
                    "Bill Total":format_currency(h["total_amount"])} for h in hist])
                st.dataframe(df_h, use_container_width=True, hide_index=True)
            else: st.info("No purchases yet.")

with t4:
    did = st.text_input("Customer ID to delete", key="did")
    if st.button("🔍 Load", key="dl"):
        c = get_customer_by_id(did)
        st.session_state["dc"] = dict(c) if c else None
        if not c: st.error("Not found.")
    if st.session_state.get("dc"):
        c = st.session_state["dc"]
        st.warning(f"Delete **{c['name']}** ({c['customer_id']})?")
        d1,d2 = st.columns(2)
        if d1.button("🗑️ Confirm", type="primary", use_container_width=True):
            try:
                delete_customer(c["customer_id"]); st.success("Deleted.")
                del st.session_state["dc"]; st.rerun()
            except Exception as e: st.error(str(e))
        if d2.button("Cancel", use_container_width=True):
            del st.session_state["dc"]; st.rerun()
