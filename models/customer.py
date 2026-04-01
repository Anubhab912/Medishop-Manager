import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_cursor


def get_all_customers(search=""):
    with get_cursor() as cur:
        q      = """
            SELECT c.*,
                COUNT(b.bill_id)                     AS total_bills,
                COALESCE(SUM(b.total_amount), 0)     AS total_spent
            FROM customers c
            LEFT JOIN bills b ON b.customer_id = c.customer_id
            WHERE 1=1
        """
        params = []
        if search:
            q += " AND (LOWER(c.name) LIKE %s OR c.phone LIKE %s OR LOWER(c.customer_id) LIKE %s)"
            params += [f"%{search.lower()}%", f"%{search}%", f"%{search.lower()}%"]
        q += " GROUP BY c.customer_id ORDER BY c.name"
        cur.execute(q, params)
        return cur.fetchall()


def get_customer_by_id(customer_id):
    with get_cursor() as cur:
        cur.execute("SELECT * FROM customers WHERE customer_id = %s", (customer_id,))
        return cur.fetchone()


def search_customers_quick(search):
    with get_cursor() as cur:
        cur.execute("""
            SELECT customer_id, name, phone FROM customers
            WHERE LOWER(name) LIKE %s OR phone LIKE %s
            ORDER BY name LIMIT 10
        """, (f"%{search.lower()}%", f"%{search}%"))
        return cur.fetchall()


def add_customer(data):
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO customers (customer_id, name, phone, email, address)
            VALUES (%(customer_id)s, %(name)s, %(phone)s, %(email)s, %(address)s)
        """, data)


def update_customer(customer_id, data):
    with get_cursor() as cur:
        cur.execute("""
            UPDATE customers SET name=%(name)s, phone=%(phone)s,
                email=%(email)s, address=%(address)s
            WHERE customer_id=%(customer_id)s
        """, {**data, "customer_id": customer_id})


def delete_customer(customer_id):
    with get_cursor() as cur:
        cur.execute("DELETE FROM customers WHERE customer_id = %s", (customer_id,))


def get_customer_purchase_history(customer_id):
    with get_cursor() as cur:
        cur.execute("""
            SELECT b.bill_number, b.created_at, b.total_amount, b.payment_method,
                bi.medicine_name, bi.quantity, bi.unit_price, bi.subtotal
            FROM bills b
            JOIN bill_items bi ON bi.bill_id = b.bill_id
            WHERE b.customer_id = %s
            ORDER BY b.created_at DESC
        """, (customer_id,))
        return cur.fetchall()
