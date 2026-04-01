import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import init_pool
from models.medicine import search_medicines_for_billing
from models.customer import add_customer, search_customers_quick
from models.bill import create_bill, get_bill_details
from utils.helpers import format_currency, generate_customer_id
from utils.pdf_generator import generate_bill_pdf

st.set_page_config(page_title="Billing — MediShop", page_icon="🧾", layout="wide")
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

if "cart"     not in st.session_state: st.session_state.cart     = []
if "customer" not in st.session_state: st.session_state.customer = None

st.title("🧾 Billing")
left, right = st.columns([3,2])

with left:
    st.subheader("👤 Customer")
    t1, t2 = st.tabs(["Search Existing","New Customer"])
    with t1:
        q = st.text_input("Name or phone")
        if q and len(q) >= 2:
            res = search_customers_quick(q)
            if res:
                opts   = {f"{r['name']} | {r['phone']} | {r['customer_id']}":r for r in res}
                chosen = st.selectbox("Select", list(opts.keys()))
                if st.button("✅ Select", use_container_width=True):
                    st.session_state.customer = opts[chosen]
                    st.success(f"Selected: **{opts[chosen]['name']}**")
            else:
                st.info("No results.")
    with t2:
        with st.form("nc", clear_on_submit=True):
            c1,c2 = st.columns(2)
            nn = c1.text_input("Full Name *"); np = c2.text_input("Phone")
            c3,c4 = st.columns(2)
            ne = c3.text_input("Email");       na = c4.text_input("Address")
            if st.form_submit_button("➕ Create", use_container_width=True):
                if not nn.strip(): st.error("Name required.")
                else:
                    cid = generate_customer_id()
                    try:
                        add_customer({"customer_id":cid,"name":nn.strip(),"phone":np,"email":ne,"address":na})
                        st.session_state.customer = {"customer_id":cid,"name":nn,"phone":np}
                        st.success(f"Created! ID: **{cid}**")
                    except Exception as e: st.error(str(e))

    if st.session_state.customer:
        c = st.session_state.customer
        st.markdown(f'<div style="background:#e8f0fe;padding:10px;border-radius:8px;border-left:4px solid #1a73e8">👤 <b>{c["name"]}</b> | {c["customer_id"]} | 📞 {c.get("phone","")}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background:#f8f9fa;padding:10px;border-radius:8px;border-left:4px solid #dadce0">👤 Walk-in customer</div>', unsafe_allow_html=True)

    if st.button("❌ Clear Customer"): st.session_state.customer = None; st.rerun()

    st.markdown("---")
    st.subheader("🔍 Add Medicine")
    ms  = st.text_input("Search medicine")
    sel = None
    if ms and len(ms) >= 2:
        meds = search_medicines_for_billing(ms)
        if meds:
            mopts  = {f"{m['name']} | ₹{m['unit_price']} | Stock:{m['stock_quantity']}":m for m in meds}
            mch    = st.selectbox("Select medicine", list(mopts.keys()))
            sel    = mopts[mch]
        else: st.info("Not found.")
    qty = st.number_input("Quantity", min_value=1, value=1)
    if st.button("➕ Add to Cart", use_container_width=True):
        if not sel: st.warning("Select a medicine first.")
        elif qty > sel["stock_quantity"]: st.error(f"Only {sel['stock_quantity']} in stock.")
        else:
            found = False
            for item in st.session_state.cart:
                if item["medicine_id"] == sel["medicine_id"]:
                    item["quantity"] += qty
                    item["subtotal"]  = item["quantity"] * item["unit_price"]
                    found = True; break
            if not found:
                st.session_state.cart.append({"medicine_id":sel["medicine_id"],"medicine_name":sel["name"],
                    "quantity":qty,"unit_price":float(sel["unit_price"]),"subtotal":qty*float(sel["unit_price"])})
            st.success(f"Added {qty}× {sel['name']}"); st.rerun()

    st.markdown("---")
    st.subheader("🛒 Cart")
    if not st.session_state.cart: st.info("Cart is empty.")
    else:
        df = pd.DataFrame([{"#":i+1,"Medicine":it["medicine_name"],"Qty":it["quantity"],
                             "Rate":f"₹{it['unit_price']:.2f}","Amount":f"₹{it['subtotal']:.2f}"}
                            for i,it in enumerate(st.session_state.cart)])
        st.dataframe(df, use_container_width=True, hide_index=True)
        r1,r2 = st.columns([3,1])
        rem = r1.number_input("Remove item #", min_value=1, max_value=len(st.session_state.cart), step=1)
        if r2.button("🗑️ Remove"): st.session_state.cart.pop(rem-1); st.rerun()

with right:
    st.subheader("💰 Bill Summary")
    discount = st.number_input("Discount (₹)", min_value=0.0, step=1.0, format="%.2f")
    tax_pct  = st.number_input("GST %", min_value=0.0, max_value=100.0, step=0.5, format="%.2f")
    payment  = st.selectbox("Payment", ["Cash","Card","UPI","Net Banking","Cheque"])
    notes    = st.text_area("Notes", height=60)

    subtotal = sum(i["subtotal"] for i in st.session_state.cart)
    tax_amt  = round((subtotal - discount) * tax_pct / 100, 2)
    total    = round(subtotal - discount + tax_amt, 2)

    st.markdown("---")
    s1,s2 = st.columns(2)
    s1.markdown("**Subtotal**");  s2.markdown(f"**{format_currency(subtotal)}**")
    if discount > 0: s1.markdown("Discount"); s2.markdown(f"-{format_currency(discount)}")
    if tax_amt  > 0: s1.markdown(f"GST ({tax_pct}%)"); s2.markdown(format_currency(tax_amt))
    st.markdown("---")
    t1,t2 = st.columns(2)
    t1.markdown("### TOTAL"); t2.markdown(f"### {format_currency(total)}")
    st.markdown("---")

    if st.button("🧾 Generate Bill", type="primary", use_container_width=True):
        if not st.session_state.cart: st.error("Cart is empty!")
        else:
            try:
                cid = st.session_state.customer["customer_id"] if st.session_state.customer else None
                bid, bnum, btotal = create_bill(customer_id=cid, items=st.session_state.cart,
                    discount=discount, tax_percent=tax_pct, payment_method=payment, notes=notes)
                st.success(f"✅ Bill **{bnum}** created! {format_currency(btotal)}")
                bill, items = get_bill_details(bid)
                pdf_path    = generate_bill_pdf(bill, items)
                with open(pdf_path,"rb") as f: pdf_bytes = f.read()
                st.download_button("⬇️ Download PDF Receipt", data=pdf_bytes,
                                   file_name=f"{bnum}.pdf", mime="application/pdf",
                                   use_container_width=True)
                st.session_state.cart = []; st.session_state.customer = None
            except ValueError as e: st.error(f"Stock issue: {e}")
            except Exception  as e: st.error(f"Error: {e}")

    if st.button("🔄 Clear Cart", use_container_width=True):
        st.session_state.cart = []; st.session_state.customer = None; st.rerun()
