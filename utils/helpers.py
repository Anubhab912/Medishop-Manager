import random
import string
from datetime import datetime, date


def generate_customer_id():
    chars  = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=6))
    return f"CUST-{suffix}"


def generate_bill_number():
    today  = datetime.now().strftime("%Y%m%d")
    suffix = "".join(random.choices(string.digits, k=4))
    return f"BILL-{today}-{suffix}"


def format_currency(amount, symbol="₹"):
    try:
        return f"{symbol}{float(amount):,.2f}"
    except (TypeError, ValueError):
        return f"{symbol}0.00"


def format_date(d):
    if d is None:
        return "N/A"
    if isinstance(d, str):
        return d
    try:
        return d.strftime("%d-%m-%Y")
    except Exception:
        return str(d)


def format_datetime(dt, fmt="%d-%m-%Y %H:%M"):
    if dt is None:
        return "N/A"
    try:
        return dt.strftime(fmt)
    except Exception:
        return str(dt)


def parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(value), fmt).date()
        except ValueError:
            continue
    return None
