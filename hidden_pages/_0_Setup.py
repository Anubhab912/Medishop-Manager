import streamlit as st
import psycopg2
import psycopg2.extras
import os, sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="Setup — MediShop", page_icon="⚙️", layout="centered")
st.markdown("""
<style>
#MainMenu{visibility:hidden}footer{visibility:hidden}
.stButton>button{border-radius:8px;font-weight:700}
h1,h2,h3{color:#1e2a3a!important}
</style>
""", unsafe_allow_html=True)


def get_conn():
    url = os.environ.get("DATABASE_URL", "")
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(url, sslmode="require")
    from config import DB_CONFIG
    return psycopg2.connect(**DB_CONFIG)


SCHEMA = """
DROP TABLE IF EXISTS bill_items CASCADE;
DROP TABLE IF EXISTS bills CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS medicines CASCADE;

CREATE TABLE medicines (
    medicine_id     SERIAL PRIMARY KEY,
    name            VARCHAR(300) NOT NULL,
    manufacturer    VARCHAR(255) DEFAULT 'Unknown',
    category        VARCHAR(100) DEFAULT 'General',
    unit_price      NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    stock_quantity  INTEGER NOT NULL DEFAULT 0,
    reorder_level   INTEGER NOT NULL DEFAULT 10,
    expiry_date     DATE,
    side_effects    TEXT DEFAULT '',
    substitutes     TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_medicines_name_unique ON medicines(LOWER(name));
CREATE INDEX idx_medicines_expiry   ON medicines(expiry_date);
CREATE INDEX idx_medicines_stock    ON medicines(stock_quantity);
CREATE INDEX idx_medicines_category ON medicines(category);

CREATE TABLE customers (
    customer_id VARCHAR(12) PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    phone       VARCHAR(15)  DEFAULT '',
    email       VARCHAR(255) DEFAULT '',
    address     TEXT         DEFAULT '',
    created_at  TIMESTAMP    DEFAULT NOW()
);
CREATE INDEX idx_customers_name  ON customers(name);
CREATE INDEX idx_customers_phone ON customers(phone);

CREATE TABLE bills (
    bill_id        SERIAL PRIMARY KEY,
    bill_number    VARCHAR(25)    UNIQUE NOT NULL,
    customer_id    VARCHAR(12)    REFERENCES customers(customer_id) ON DELETE SET NULL,
    subtotal       NUMERIC(10,2)  DEFAULT 0.00,
    discount       NUMERIC(10,2)  DEFAULT 0.00,
    tax_percent    NUMERIC(5,2)   DEFAULT 0.00,
    tax_amount     NUMERIC(10,2)  DEFAULT 0.00,
    total_amount   NUMERIC(10,2)  DEFAULT 0.00,
    payment_method VARCHAR(50)    DEFAULT 'Cash',
    notes          TEXT           DEFAULT '',
    created_at     TIMESTAMP      DEFAULT NOW()
);
CREATE INDEX idx_bills_customer ON bills(customer_id);
CREATE INDEX idx_bills_date     ON bills(created_at);
CREATE INDEX idx_bills_number   ON bills(bill_number);

CREATE TABLE bill_items (
    item_id       SERIAL PRIMARY KEY,
    bill_id       INTEGER REFERENCES bills(bill_id)         ON DELETE CASCADE,
    medicine_id   INTEGER REFERENCES medicines(medicine_id) ON DELETE SET NULL,
    medicine_name VARCHAR(300)   NOT NULL,
    quantity      INTEGER        NOT NULL,
    unit_price    NUMERIC(10,2)  NOT NULL,
    subtotal      NUMERIC(10,2)  NOT NULL
);
CREATE INDEX idx_bill_items_bill     ON bill_items(bill_id);
CREATE INDEX idx_bill_items_medicine ON bill_items(medicine_id);

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER medicines_updated_at
    BEFORE UPDATE ON medicines
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
"""

SAMPLE_MEDICINES = [
    ("Paracetamol 500mg","Sun Pharma","Analgesic",5.50,200,50,480,"Nausea, liver damage on overdose","Crocin, Calpol"),
    ("Amoxicillin 250mg","Cipla","Antibiotic",12.00,8,20,300,"Diarrhea, rash","Mox, Novamox"),
    ("Metformin 500mg","Mankind","Antidiabetic",8.75,150,30,400,"Nausea, vomiting","Glyciphage, Gluconorm"),
    ("Atorvastatin 10mg","Ranbaxy","Cholesterol",18.50,5,15,-10,"Muscle pain","Lipitor, Sortis"),
    ("Omeprazole 20mg","Dr Reddys","Antacid",9.25,80,25,520,"Headache, diarrhea","Prilosec, Omez"),
    ("Cetirizine 10mg","Alkem","Antihistamine",4.00,120,40,700,"Drowsiness, dry mouth","Zyrtec, Cetzine"),
    ("Aspirin 75mg","Bayer","Antiplatelet",3.50,7,20,-30,"GI bleeding, nausea","Ecosprin, Disprin"),
    ("Azithromycin 500mg","Pfizer","Antibiotic",45.00,60,15,450,"Nausea, diarrhea","Zithromax, Azee"),
    ("Pantoprazole 40mg","Torrent","Antacid",11.00,90,20,580,"Headache, flatulence","Pantop, Pan"),
    ("Vitamin D3 60000 IU","Abbott","Supplement",35.00,3,10,-15,"Hypercalcemia on excess","D-Rise, Calcirol"),
    ("Ibuprofen 400mg","Cipla","Analgesic",7.00,180,40,500,"Stomach upset","Brufen, Advil"),
    ("Amlodipine 5mg","Sun Pharma","Antihypertensive",14.00,90,20,600,"Ankle swelling","Norvasc, Amlopin"),
    ("Losartan 50mg","Lupin","Antihypertensive",22.00,75,15,550,"Dizziness","Cozaar, Losar"),
    ("Levothyroxine 50mcg","Abbott","Hormone",28.00,65,15,730,"Palpitations","Eltroxin, Thyronorm"),
    ("Ciprofloxacin 500mg","Bayer","Antibiotic",22.00,70,15,450,"Nausea, dizziness","Ciplox, Cifran"),
    ("Ranitidine 150mg","GSK","Antacid",6.00,100,25,600,"Headache","Aciloc, Rantac"),
    ("Ondansetron 4mg","Cipla","Antiemetic",15.00,60,15,500,"Headache","Zofran, Emeset"),
    ("Fluconazole 150mg","Pfizer","Antifungal",25.00,55,15,500,"Nausea","Diflucan, Forcan"),
    ("Sertraline 50mg","Pfizer","Antidepressant",38.00,50,10,500,"Nausea, insomnia","Zoloft, Serta"),
    ("Prednisolone 5mg","Cipla","Steroid",10.00,70,20,450,"Weight gain","Omnacortil"),
    ("Ambroxol 30mg","Boehringer","Expectorant",8.00,110,25,600,"Nausea","Mucosolvan"),
    ("Doxycycline 100mg","Cipla","Antibiotic",18.00,45,10,400,"Photosensitivity","Doxt, Doxrid"),
    ("Metoprolol 25mg","Cipla","Antihypertensive",18.00,55,10,490,"Fatigue, bradycardia","Betaloc, Metolar"),
    ("Montelukast 10mg","MSD","Antiasthmatic",32.00,50,10,400,"Headache","Singulair, Montair"),
    ("Glimepiride 1mg","Sanofi","Antidiabetic",12.00,40,10,25,"Hypoglycemia","Amaryl, Glimpid"),
]

SAMPLE_CUSTOMERS = [
    ("CUST-ABC123","Rahul Sharma","9876543210","rahul@email.com","Mumbai"),
    ("CUST-XYZ789","Priya Patel","8765432109","priya@email.com","Delhi"),
    ("CUST-DEF456","Arjun Singh","7654321098","arjun@email.com","Bangalore"),
    ("CUST-GHI012","Sneha Reddy","6543210987","sneha@email.com","Hyderabad"),
]


def seed(conn):
    today = date.today()
    cur   = conn.cursor()
    nm = nc = 0
    for m in SAMPLE_MEDICINES:
        name,mfr,cat,price,stock,reorder,exp_days,se,subs = m
        cur.execute("""
            INSERT INTO medicines (name,manufacturer,category,unit_price,stock_quantity,
                reorder_level,expiry_date,side_effects,substitutes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING
        """, (name,mfr,cat,price,stock,reorder,today+timedelta(days=exp_days),se,subs))
        nm += cur.rowcount
    for c in SAMPLE_CUSTOMERS:
        cur.execute("""
            INSERT INTO customers (customer_id,name,phone,email,address)
            VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING
        """, c)
        nc += cur.rowcount
    conn.commit()
    cur.close()
    return nm, nc


def get_counts(conn):
    cur    = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    counts = {}
    for tbl in ["medicines","customers","bills","bill_items"]:
        try:
            cur.execute(f"SELECT COUNT(*) AS n FROM {tbl}")
            counts[tbl] = cur.fetchone()["n"]
        except Exception:
            counts[tbl] = "—"
    cur.close()
    return counts


st.title("⚙️ Setup")
st.caption("Run this once to initialise your database")

st.subheader("1️⃣ Connection")
try:
    conn = get_conn()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT version()")
    ver  = cur.fetchone()["version"]
    cur.close()
    conn.close()
    st.success("✅ Connected to PostgreSQL!")
    st.caption(ver[:80])
except Exception as e:
    st.error(f"❌ Connection failed: {e}")
    st.markdown("""
    **Fix:**
    - Make sure PostgreSQL is running
    - Open your `.env` file and check `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
    - Make sure the database `medishop` exists
    """)
    st.stop()

st.subheader("2️⃣ Current Database")
try:
    conn   = get_conn()
    counts = get_counts(conn)
    conn.close()
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("💊 Medicines",  counts.get("medicines",  0))
    c2.metric("👥 Customers",  counts.get("customers",  0))
    c3.metric("🧾 Bills",      counts.get("bills",      0))
    c4.metric("📦 Bill Items", counts.get("bill_items", 0))
except Exception:
    st.info("Tables do not exist yet — run Full Setup below.")

st.markdown("---")
st.subheader("3️⃣ Run Setup")
st.warning("Full Setup deletes all existing data and starts fresh. Only run once on first use!")

b1, b2 = st.columns(2)

if b1.button("🚀 Full Setup (Fresh Start)", type="primary", use_container_width=True):
    prog = st.progress(0, "Creating tables...")
    try:
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute(SCHEMA)
        conn.commit()
        cur.close()
        prog.progress(60, "Adding sample data...")
        nm, nc = seed(conn)
        conn.close()
        prog.progress(100, "Done!")
        st.success(f"✅ Done! {nm} medicines and {nc} customers added.")
        st.balloons()
    except Exception as e:
        st.error(f"Setup failed: {e}")

if b2.button("➕ Add Sample Data Only", use_container_width=True):
    try:
        conn    = get_conn()
        nm, nc  = seed(conn)
        conn.close()
        st.success(f"✅ Added {nm} medicines and {nc} customers!")
    except Exception as e:
        st.error(f"Error: {e}")

st.markdown("---")
st.subheader("4️⃣ Next steps")
st.markdown("""
1. 📊 Go to **Home** → see your dashboard  
2. 💊 Go to **Inventory** → browse and manage medicines  
3. 📥 Go to **Import Medicines** → load your Kaggle CSV (250k+ medicines)  
4. 🧾 Go to **Billing** → create your first bill  
5. 🔔 Go to **Alerts** → see expiry and stock alerts  
""")

with st.expander("🔴 Danger Zone"):
    st.error("This permanently deletes ALL medicines, customers and bills.")
    confirm = st.text_input("Type RESET to confirm")
    if st.button("🗑️ Reset Database") and confirm == "RESET":
        try:
            conn = get_conn()
            cur  = conn.cursor()
            cur.execute(SCHEMA)
            conn.commit()
            cur.close()
            conn.close()
            st.success("Database reset.")
            st.rerun()
        except Exception as e:
            st.error(str(e))
