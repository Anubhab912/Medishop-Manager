import os
import psycopg2
import psycopg2.pool
import psycopg2.extras
from contextlib import contextmanager
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG, DATABASE_URL

_pool = None


def init_pool():
    global _pool
    if _pool is not None:
        return
    try:
        if DATABASE_URL:
            url = DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            _pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=url, sslmode="require")
        else:
            _pool = psycopg2.pool.SimpleConnectionPool(1, 10, **DB_CONFIG)
    except psycopg2.OperationalError as e:
        raise RuntimeError(f"Database connection failed: {e}")


def get_pool():
    global _pool
    if _pool is None:
        init_pool()
    return _pool


@contextmanager
def get_conn():
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


@contextmanager
def get_cursor(cursor_factory=psycopg2.extras.RealDictCursor):
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cur
        finally:
            cur.close()


def test_connection():
    try:
        with get_cursor() as cur:
            cur.execute("SELECT version();")
            result = cur.fetchone()
            return True, str(result["version"])
    except Exception as e:
        return False, str(e)


def setup_database():
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    try:
        with open(schema_path, "r") as f:
            sql = f.read()
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            cur.close()
        return True, "Database setup complete!"
    except Exception as e:
        return False, str(e)
