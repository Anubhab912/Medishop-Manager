DROP TABLE IF EXISTS bill_items  CASCADE;
DROP TABLE IF EXISTS bills        CASCADE;
DROP TABLE IF EXISTS customers    CASCADE;
DROP TABLE IF EXISTS medicines    CASCADE;

CREATE TABLE medicines (
    medicine_id     SERIAL PRIMARY KEY,
    name            VARCHAR(300) NOT NULL,
    manufacturer    VARCHAR(255) DEFAULT 'Unknown',
    category        VARCHAR(100) DEFAULT 'General',
    unit_price      NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
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
    customer_id  VARCHAR(12)  PRIMARY KEY,
    name         VARCHAR(255) NOT NULL,
    phone        VARCHAR(15)  DEFAULT '',
    email        VARCHAR(255) DEFAULT '',
    address      TEXT         DEFAULT '',
    created_at   TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX idx_customers_name  ON customers(name);
CREATE INDEX idx_customers_phone ON customers(phone);

CREATE TABLE bills (
    bill_id        SERIAL PRIMARY KEY,
    bill_number    VARCHAR(25)    UNIQUE NOT NULL,
    customer_id    VARCHAR(12)    REFERENCES customers(customer_id) ON DELETE SET NULL,
    subtotal       NUMERIC(10, 2) DEFAULT 0.00,
    discount       NUMERIC(10, 2) DEFAULT 0.00,
    tax_percent    NUMERIC(5,  2) DEFAULT 0.00,
    tax_amount     NUMERIC(10, 2) DEFAULT 0.00,
    total_amount   NUMERIC(10, 2) DEFAULT 0.00,
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
    unit_price    NUMERIC(10, 2) NOT NULL,
    subtotal      NUMERIC(10, 2) NOT NULL
);

CREATE INDEX idx_bill_items_bill     ON bill_items(bill_id);
CREATE INDEX idx_bill_items_medicine ON bill_items(medicine_id);

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER medicines_updated_at
    BEFORE UPDATE ON medicines
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
