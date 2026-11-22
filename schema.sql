-- Order Invoice Assistant: fictional, repeatable SQLite seed data.
-- Monetary values are stored in integer cents.
-- change_requests follows the instructor's required starter schema exactly.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    street_address TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    zip_code TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    contract_date TEXT NOT NULL,
    job_status TEXT NOT NULL CHECK (job_status IN ('scheduled', 'in_progress', 'completed')),
    original_contract_cents INTEGER NOT NULL CHECK (original_contract_cents >= 0),
    recorded_contract_total_cents INTEGER NOT NULL CHECK (recorded_contract_total_cents >= 0),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS order_items (
    item_id INTEGER PRIMARY KEY,
    job_id TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    description TEXT NOT NULL,
    line_total_cents INTEGER NOT NULL CHECK (line_total_cents >= 0),
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

CREATE TABLE IF NOT EXISTS existing_change_orders (
    change_order_id INTEGER PRIMARY KEY,
    job_id TEXT NOT NULL,
    description TEXT NOT NULL,
    adjustment_cents INTEGER NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY,
    job_id TEXT NOT NULL,
    payment_date TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    reference TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

-- Must start empty; the change tool files requests here in Week 14.
CREATE TABLE IF NOT EXISTS change_requests (
    number INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    new_value TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'waiting',
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

INSERT OR IGNORE INTO customers (customer_id, full_name, street_address, city, state, zip_code) VALUES
(1, 'Jordan Rivera', '100 Example Lane', 'Tampa', 'FL', '33601'),
(2, 'Taylor Morgan', '200 Example Lane', 'Brandon', 'FL', '33510'),
(3, 'Avery Chen', '300 Example Lane', 'Riverview', 'FL', '33569'),
(4, 'Casey Bennett', '400 Example Lane', 'Lutz', 'FL', '33549'),
(5, 'Riley Patel', '500 Example Lane', 'Wesley Chapel', 'FL', '33543');

-- J1003 deliberately contains a $500 discrepancy for evaluation.
INSERT OR IGNORE INTO jobs (job_id, customer_id, contract_date, job_status, original_contract_cents, recorded_contract_total_cents) VALUES
('J1001', 1, '2026-10-02', 'completed', 2000000, 2200000),
('J1002', 2, '2026-10-04', 'completed', 1500000, 1500000),
('J1003', 3, '2026-10-06', 'in_progress', 1800000, 1700000),
('J1004', 4, '2026-10-08', 'completed', 1200000, 1300000),
('J1005', 5, '2026-10-10', 'scheduled', 2400000, 2400000);

INSERT OR IGNORE INTO order_items (item_id, job_id, quantity, description, line_total_cents) VALUES
(1, 'J1001', 8, 'Impact-rated vinyl windows', 2000000),
(2, 'J1002', 2, 'Sliding glass doors', 1500000),
(3, 'J1003', 6, 'Aluminum-frame windows', 1800000),
(4, 'J1004', 4, 'Impact-rated casement windows', 1200000),
(5, 'J1005', 10, 'Vinyl replacement windows', 2400000);

-- Signed adjustments; a negative amount represents a credit/reduction.
INSERT OR IGNORE INTO existing_change_orders (change_order_id, job_id, description, adjustment_cents) VALUES
(1, 'J1001', 'Add two matching windows', 200000),
(2, 'J1002', 'No-cost hardware substitution', 0),
(3, 'J1003', 'Credit for frame material substitution', -50000),
(4, 'J1004', 'Upgrade to reinforced glass', 100000),
(5, 'J1005', 'No-cost installation schedule adjustment', 0);

INSERT OR IGNORE INTO payments (payment_id, job_id, payment_date, amount_cents, reference) VALUES
(1, 'J1001', '2026-10-15', 1200000, 'Simulated payment A'),
(2, 'J1001', '2026-10-25', 1000000, 'Simulated payment B'),
(3, 'J1002', '2026-10-26', 1500000, 'Simulated payment C'),
(4, 'J1003', '2026-10-27', 500000, 'Simulated payment D'),
(5, 'J1004', '2026-10-28', 1300000, 'Simulated payment E');
