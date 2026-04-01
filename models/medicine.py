import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_cursor
from config import EXPIRY_ALERT_DAYS


def get_all_medicines(search="", category="All", low_stock_only=False, expiring_only=False):
    with get_cursor() as cur:
        q      = """
            SELECT *,
                CASE
                    WHEN stock_quantity = 0             THEN 'out_of_stock'
                    WHEN stock_quantity <= reorder_level THEN 'low_stock'
                    ELSE 'ok'
                END AS stock_status,
                CASE
                    WHEN expiry_date < CURRENT_DATE                                    THEN 'expired'
                    WHEN expiry_date <= CURRENT_DATE + INTERVAL '{days} days'          THEN 'expiring_soon'
                    ELSE 'ok'
                END AS expiry_status
            FROM medicines WHERE 1=1
        """.format(days=EXPIRY_ALERT_DAYS)
        params = []
        if search:
            q += " AND (LOWER(name) LIKE %s OR LOWER(manufacturer) LIKE %s)"
            params += [f"%{search.lower()}%", f"%{search.lower()}%"]
        if category and category != "All":
            q += " AND category = %s"
            params.append(category)
        if low_stock_only:
            q += " AND stock_quantity <= reorder_level"
        if expiring_only:
            q += " AND expiry_date <= CURRENT_DATE + INTERVAL '{days} days'".format(days=EXPIRY_ALERT_DAYS)
        q += " ORDER BY name LIMIT 500"
        cur.execute(q, params)
        return cur.fetchall()


def get_medicine_by_id(medicine_id):
    with get_cursor() as cur:
        cur.execute("SELECT * FROM medicines WHERE medicine_id = %s", (medicine_id,))
        return cur.fetchone()


def search_medicines_for_billing(search):
    with get_cursor() as cur:
        cur.execute("""
            SELECT medicine_id, name, unit_price, stock_quantity
            FROM medicines
            WHERE LOWER(name) LIKE %s AND stock_quantity > 0
            ORDER BY name LIMIT 20
        """, (f"%{search.lower()}%",))
        return cur.fetchall()


def get_categories():
    with get_cursor() as cur:
        cur.execute("SELECT DISTINCT category FROM medicines WHERE category IS NOT NULL ORDER BY category")
        return [r["category"] for r in cur.fetchall()]


def add_medicine(data):
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO medicines (name, manufacturer, category, unit_price,
                stock_quantity, reorder_level, expiry_date, side_effects, substitutes)
            VALUES (%(name)s, %(manufacturer)s, %(category)s, %(unit_price)s,
                %(stock_quantity)s, %(reorder_level)s, %(expiry_date)s,
                %(side_effects)s, %(substitutes)s)
            ON CONFLICT (LOWER(name)) DO UPDATE SET
                manufacturer   = EXCLUDED.manufacturer,
                category       = EXCLUDED.category,
                unit_price     = EXCLUDED.unit_price,
                stock_quantity = EXCLUDED.stock_quantity,
                reorder_level  = EXCLUDED.reorder_level,
                expiry_date    = EXCLUDED.expiry_date,
                side_effects   = EXCLUDED.side_effects,
                substitutes    = EXCLUDED.substitutes
            RETURNING medicine_id
        """, data)
        return cur.fetchone()["medicine_id"]


def update_medicine(medicine_id, data):
    with get_cursor() as cur:
        cur.execute("""
            UPDATE medicines SET
                name           = %(name)s,
                manufacturer   = %(manufacturer)s,
                category       = %(category)s,
                unit_price     = %(unit_price)s,
                stock_quantity = %(stock_quantity)s,
                reorder_level  = %(reorder_level)s,
                expiry_date    = %(expiry_date)s,
                side_effects   = %(side_effects)s,
                substitutes    = %(substitutes)s
            WHERE medicine_id  = %(medicine_id)s
        """, {**data, "medicine_id": medicine_id})


def delete_medicine(medicine_id):
    with get_cursor() as cur:
        cur.execute("DELETE FROM medicines WHERE medicine_id = %s", (medicine_id,))


def get_dashboard_stats():
    with get_cursor() as cur:
        cur.execute("""
            SELECT
                COUNT(*)                                                                         AS total_medicines,
                COALESCE(SUM(CASE WHEN stock_quantity <= reorder_level  THEN 1 ELSE 0 END), 0)   AS low_stock_count,
                COALESCE(SUM(CASE WHEN expiry_date < CURRENT_DATE       THEN 1 ELSE 0 END), 0)   AS expired_count,
                COALESCE(SUM(CASE WHEN expiry_date BETWEEN CURRENT_DATE
                    AND CURRENT_DATE + INTERVAL '{days} days'  THEN 1 ELSE 0 END), 0)            AS expiring_count
            FROM medicines
        """.format(days=EXPIRY_ALERT_DAYS))
        return cur.fetchone()


def get_expiry_alerts():
    with get_cursor() as cur:
        cur.execute("""
            SELECT medicine_id, name, stock_quantity, expiry_date,
                CASE WHEN expiry_date < CURRENT_DATE THEN 'EXPIRED' ELSE 'EXPIRING SOON' END AS status
            FROM medicines
            WHERE expiry_date <= CURRENT_DATE + INTERVAL '{days} days'
            ORDER BY expiry_date
        """.format(days=EXPIRY_ALERT_DAYS))
        return cur.fetchall()


def get_low_stock_alerts():
    with get_cursor() as cur:
        cur.execute("""
            SELECT medicine_id, name, manufacturer, stock_quantity, reorder_level,
                CASE WHEN stock_quantity = 0 THEN 'OUT OF STOCK' ELSE 'LOW STOCK' END AS status
            FROM medicines
            WHERE stock_quantity <= reorder_level
            ORDER BY stock_quantity
        """)
        return cur.fetchall()
