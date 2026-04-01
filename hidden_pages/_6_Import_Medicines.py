import streamlit as st
import psycopg2, psycopg2.extras
import pandas as pd
import os, sys, random, time
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="Import — MediShop", page_icon="📥", layout="centered")
st.markdown("""<style>#MainMenu{visibility:hidden}footer{visibility:hidden}
.stButton>button{border-radius:8px;font-weight:700}h1,h2,h3{color:#1e2a3a!important}</style>""", unsafe_allow_html=True)

PRICE_RANGES = {
    "antibiotic":(20,250),"analgesic":(5,80),"antacid":(8,120),"antidiabetic":(10,200),
    "antihypertensive":(15,180),"cholesterol":(20,300),"antihistamine":(5,100),
    "supplement":(20,500),"antifungal":(30,400),"antiviral":(50,800),
    "steroid":(15,300),"antidepressant":(30,500),"general":(5,150),
}

def get_conn():
    url = os.environ.get("DATABASE_URL","")
    if url:
        if url.startswith("postgres://"): url = url.replace("postgres://","postgresql://",1)
        return psycopg2.connect(url, sslmode="require")
    from config import DB_CONFIG
    return psycopg2.connect(**DB_CONFIG)

def get_count():
    try:
        conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT COUNT(*) AS n FROM medicines"); n = cur.fetchone()["n"]
        cur.close(); conn.close(); return n
    except: return 0

def detect_csv():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"data")
    if os.path.exists(data_dir):
        for f in sorted(os.listdir(data_dir)):
            if f.endswith(".csv"): return os.path.join(data_dir,f), f
    return None, None

def price_for(cat):
    c = cat.lower()
    for k,(lo,hi) in PRICE_RANGES.items():
        if k in c: return round(random.uniform(lo,hi),2)
    return round(random.uniform(5,150),2)

def rnd_expiry():
    today = date.today(); r = random.random()
    if r < 0.10: return today - timedelta(days=random.randint(1,180))
    if r < 0.20: return today + timedelta(days=random.randint(1,29))
    return today + timedelta(days=random.randint(180,1095))

def combine(row, prefix, max_n):
    vals = []
    for i in range(max_n):
        v = row.get(f"{prefix}{i}","")
        if pd.notna(v) and str(v).strip() not in ("","nan","NaN"): vals.append(str(v).strip())
    return ", ".join(vals)

def run_import(csv_path, limit=None, progress_cb=None):
    df    = pd.read_csv(csv_path, nrows=limit, low_memory=False)
    total = len(df)
    se_max  = len([c for c in df.columns if c.startswith("sideEffect")])
    sub_max = len([c for c in df.columns if c.startswith("substitute")])
    imported = skipped = errors = 0
    batch = []; BATCH = 5000; start = time.time()
    conn = get_conn(); cur = conn.cursor()
    for idx, row in df.iterrows():
        try:
            name = str(row.get("name","")).strip()
            if not name or name.lower() in ("nan",""): skipped += 1; continue
            cat = str(row.get("use0","General")).strip()
            if not cat or cat.lower()=="nan": cat = "General"
            batch.append((name[:300],"Unknown",cat[:100],price_for(cat),
                          random.randint(10,500),10,rnd_expiry(),
                          combine(row,"sideEffect",se_max)[:3000],
                          combine(row,"substitute",sub_max)[:1000]))
            if len(batch) >= BATCH:
                psycopg2.extras.execute_values(cur,"""
                    INSERT INTO medicines (name,manufacturer,category,unit_price,stock_quantity,
                        reorder_level,expiry_date,side_effects,substitutes)
                    VALUES %s ON CONFLICT DO NOTHING""", batch, page_size=BATCH)
                conn.commit()
                imported += cur.rowcount if cur.rowcount>=0 else len(batch)
                batch = []
        except: errors += 1
        if (idx+1)%5000==0 or (idx+1)==total:
            done = imported+skipped+errors
            pct  = int(done/total*100) if total else 0
            elapsed = time.time()-start
            eta  = int((total-done)/max(done/elapsed,1)) if done else 0
            if progress_cb: progress_cb(pct, f"{pct}% | {done:,}/{total:,} | ETA {eta}s")
    if batch:
        psycopg2.extras.execute_values(cur,"""
            INSERT INTO medicines (name,manufacturer,category,unit_price,stock_quantity,
                reorder_level,expiry_date,side_effects,substitutes)
            VALUES %s ON CONFLICT DO NOTHING""", batch, page_size=BATCH)
        conn.commit()
        imported += cur.rowcount if cur.rowcount>=0 else len(batch)
    cur.close(); conn.close()
    return {"imported":imported,"skipped":skipped,"errors":errors,
            "elapsed":round(time.time()-start,1),"total":total}

st.title("📥 Import Kaggle Medicines")
st.caption("Load 250,000+ medicines from your Kaggle CSV")

st.metric("💊 Current medicines in DB", f"{get_count():,}")
st.markdown("---")

csv_path, csv_name = detect_csv()
if csv_path:
    with open(csv_path,"r",encoding="utf-8",errors="ignore") as f:
        row_count = sum(1 for _ in f)-1
    st.success(f"✅ CSV found: **{csv_name}** — {row_count:,} rows")
else:
    st.error("No CSV found in the `data/` folder.")
    st.info("Place your Kaggle CSV file inside the `data/` folder then restart the app.")
    st.stop()

st.markdown("---")
c1,c2 = st.columns(2)
mode  = c1.radio("How many?",["All medicines (recommended)","Limited number"])
limit = None
if mode == "Limited number":
    limit = c2.number_input("Row limit", min_value=100, max_value=300000, value=10000, step=1000)
else:
    c2.info(f"Will import all **{row_count:,}** medicines")

st.info("Prices auto-assigned by category · Random stock (10–500) · Random expiry dates · Duplicates skipped")

st.markdown("---")
if st.button("🚀 Start Import", type="primary", use_container_width=True):
    prog = st.progress(0,"Starting...")
    stat = st.empty()
    try:
        def cb(pct, msg): prog.progress(min(pct,99),msg); stat.caption(msg)
        result = run_import(csv_path, limit=limit, progress_cb=cb)
        prog.progress(100,"✅ Done!")
        st.balloons()
        st.success(f"🎉 Done in {result['elapsed']}s! Imported: {result['imported']:,} | Skipped: {result['skipped']:,} | Errors: {result['errors']}")
        m1,m2,m3 = st.columns(3)
        m1.metric("Total in DB", f"{get_count():,}")
        m2.metric("Imported",    f"{result['imported']:,}")
        m3.metric("Time",        f"{result['elapsed']}s")
        st.success("Go to 💊 Inventory or 📊 Dashboard to see your medicines!")
    except Exception as e:
        prog.empty(); st.error(f"Import failed: {e}")

with st.expander("💡 Tips"):
    st.markdown("""
    - Place your Kaggle CSV inside the `data/` folder before starting
    - If import times out, use **Limited number** and import in batches (e.g. 50,000 at a time)
    - Re-running is safe — duplicates are always skipped
    - Run ⚙️ Setup first if you get a table not found error
    """)
