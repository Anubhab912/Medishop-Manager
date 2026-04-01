import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_cursor, get_conn
from utils.helpers import generate_bill_number


def create_bill(customer_id, items, discount=0, tax_percent=0, payment_method="Cash", notes=""):
    subtotal = sum(i["quantity"] * i["unit_price"] for i in items)
    tax_amt  = round((subtotal - discount) * tax_percent / 100, 2)
    total    = round(subtotal - discount + tax_amt, 2)
    bill_num = generate_bill_number()

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO bills (bill_number, customer_id, subtotal, discount,
                tax_percent, tax_amount, total_amount, payment_method, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING bill_id
        """, (bill_num, customer_id, subtotal, discount,
              tax_percent, tax_amt, total, payment_method, notes))
        bill_id = cur.fetchone()[0]

        for item in items:
            cur.execute("""
                SELECT stock_quantity FROM medicines
                WHERE medicine_id = %s FOR UPDATE
            """, (item["medicine_id"],))
            row = cur.fetchone()
            if not row or row[0] < item["quantity"]:
                raise ValueError(f"Not enough stock for {item['medicine_name']}")
            cur.execute("""
                INSERT INTO bill_items
                    (bill_id, medicine_id, medicine_name, quantity, unit_price, subtotal)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (bill_id, item["medicine_id"], item["medicine_name"],
                  item["quantity"], item["unit_price"],
                  item["quantity"] * item["unit_price"]))
            cur.execute("""
                UPDATE medicines SET stock_quantity = stock_quantity - %s
                WHERE medicine_id = %s
            """, (item["quantity"], item["medicine_id"]))
        cur.close()
    return bill_id, bill_num, total


def get_all_bills(search="", from_date=None, to_date=None):
    with get_cursor() as cur:
        q      = """
            SELECT b.*, c.name AS customer_name
            FROM bills b
            LEFT JOIN customers c ON c.customer_id = b.customer_id
            WHERE 1=1
        """
        params = []
        if search:
            q += " AND (LOWER(b.bill_number) LIKE %s OR LOWER(c.name) LIKE %s)"
            params += [f"%{search.lower()}%", f"%{search.lower()}%"]
        if from_date:
            q += " AND b.created_at >= %s"
            params.append(from_date)
        if to_date:
            q += " AND b.created_at <= %s"
            params.append(to_date)
        q += " ORDER BY b.created_at DESC"
        cur.execute(q, params)
        return cur.fetchall()


def get_bill_details(bill_id):
    with get_cursor() as cur:
        cur.execute("""
            SELECT b.*, c.name AS customer_name
            FROM bills b
            LEFT JOIN customers c ON c.customer_id = b.customer_id
            WHERE b.bill_id = %s
        """, (bill_id,))
        bill  = cur.fetchone()
        cur.execute("SELECT * FROM bill_items WHERE bill_id = %s", (bill_id,))
        items = cur.fetchall()
    return bill, items


def get_revenue_stats():
    with get_cursor() as cur:
        cur.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN DATE(created_at) = CURRENT_DATE
                    THEN total_amount END), 0)                                       AS today_revenue,
                COALESCE(SUM(CASE WHEN DATE_TRUNC('month', created_at) =
                    DATE_TRUNC('month', NOW()) THEN total_amount END), 0)            AS month_revenue,
                COALESCE(SUM(total_amount), 0)                                       AS total_revenue,
                COUNT(*)                                                             AS total_bills
            FROM bills
        """)
        return cur.fetchone()
