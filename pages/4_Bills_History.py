import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import init_pool
from models.bill import get_all_bills, get_bill_details
from utils.helpers import format_currency, format_datetime
from utils.pdf_generator import generate_bill_pdf

st.set_page_config(page_title="Bills — MediShop", page_icon="📄", layout="wide")
st.markdown("""<style>#MainMenu{visibility:hidden}footer{visibility:hidden}
.stButton>button{border-radius:8px;font-weight:600}h1,h2,h3{color:#1e2a3a!important}</style>""", unsafe_allow_html=True)

@st.cache_resource
def init_db(): init_pool()
init_db()

st.title("📄 Bills History")
f1,f2,f3 = st.columns([3,2,2])
search    = f1.text_input("🔍 Search")
from_date = f2.date_input("From", value=None)
to_date   = f3.date_input("To",   value=None)

bills = get_all_bills(search=search, from_date=from_date, to_date=to_date)
st.caption(f"{len(bills):,} bills")

if bills:
    df = pd.DataFrame([{"ID":b["bill_id"],"Bill No":b["bill_number"],
                         "Date":format_datetime(b["created_at"]),"Customer":b["customer_name"] or "Walk-in",
                         "Total":format_currency(b["total_amount"]),"Payment":b["payment_method"]} for b in bills])
    st.dataframe(df, use_container_width=True, hide_index=True, height=380)
else:
    st.info("No bills yet.")

st.markdown("---")
st.subheader("🖨️ Download Bill PDF")
bid = st.number_input("Enter Bill ID", min_value=1, step=1)
if st.button("📄 Load Bill", use_container_width=True):
    bill, items = get_bill_details(bid)
    if not bill: st.error("Not found.")
    else:
        st.markdown(f"### {bill['bill_number']}")
        i1,i2,i3,i4 = st.columns(4)
        i1.metric("Customer", bill.get("customer_name") or "Walk-in")
        i2.metric("Total",    format_currency(bill["total_amount"]))
        i3.metric("Payment",  bill["payment_method"])
        i4.metric("Date",     format_datetime(bill["created_at"],"%d-%m-%Y"))
        df_i = pd.DataFrame([{"Medicine":i["medicine_name"],"Qty":i["quantity"],
                               "Rate":format_currency(i["unit_price"]),"Amount":format_currency(i["subtotal"])} for i in items])
        st.dataframe(df_i, use_container_width=True, hide_index=True)
        pdf_path = generate_bill_pdf(bill, items)
        with open(pdf_path,"rb") as f: pdf_data = f.read()
        st.download_button("⬇️ Download PDF", data=pdf_data,
                           file_name=f"{bill['bill_number']}.pdf",
                           mime="application/pdf", use_container_width=True)
