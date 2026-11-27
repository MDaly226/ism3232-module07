# database.py
import sqlite3
from pathlib import Path

SCHEMA_FILE = Path(__file__).with_name("schema.sql")


def query_all(db_file, sql, values=()):
    """Run a SELECT and return every row as a dictionary."""
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, values).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def query_one(db_file, sql, values=()):
    """Run a SELECT and return the first row, or None."""
    rows = query_all(db_file, sql, values)
    if rows == []:
        return None
    return rows[0]


def change(db_file, sql, values=()):
    """Run an INSERT or UPDATE, save it, and return the last row ID."""
    conn = sqlite3.connect(db_file)
    cursor = conn.execute(sql, values)
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def create_tables(db_file):
    """Load the repeatable schema and sample data from this file's folder."""
    script = SCHEMA_FILE.read_text(encoding="utf-8")
    with sqlite3.connect(db_file) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(script)


# One exact-key lookup per business table.
def find_customer(db_file, customer_id):
    return query_one(
        db_file, "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
    )


def find_job(db_file, job_id):
    return query_one(db_file, "SELECT * FROM jobs WHERE job_id = ?", (job_id,))


def find_item(db_file, item_id):
    return query_one(db_file, "SELECT * FROM order_items WHERE item_id = ?", (item_id,))


def find_change_order(db_file, change_order_id):
    return query_one(
        db_file,
        "SELECT * FROM existing_change_orders WHERE change_order_id = ?",
        (change_order_id,),
    )


def find_payment(db_file, payment_id):
    return query_one(
        db_file, "SELECT * FROM payments WHERE payment_id = ?", (payment_id,)
    )


# Related records used when preparing an invoice.
def items_for_job(db_file, job_id):
    return query_all(
        db_file,
        "SELECT * FROM order_items WHERE job_id = ? ORDER BY item_id",
        (job_id,),
    )


def change_orders_for_job(db_file, job_id):
    return query_all(
        db_file,
        "SELECT * FROM existing_change_orders WHERE job_id = ? ORDER BY change_order_id",
        (job_id,),
    )


def payments_for_job(db_file, job_id):
    return query_all(
        db_file,
        "SELECT * FROM payments WHERE job_id = ? ORDER BY payment_date, payment_id",
        (job_id,),
    )


def add_change_request(db_file, job_id, new_value):
    """File a request; do not modify the job's financial total."""
    if find_job(db_file, job_id) is None:
        raise ValueError("Job not found")
    if isinstance(new_value, bool) or not isinstance(new_value, int) or new_value < 0:
        raise ValueError("New value must be a nonnegative integer number of cents")
    return change(
        db_file,
        "INSERT INTO change_requests (job_id, new_value) VALUES (?, ?)",
        (job_id, str(new_value)),
    )


def find_request(db_file, number):
    return query_one(
        db_file, "SELECT * FROM change_requests WHERE number = ?", (number,)
    )


def waiting_requests(db_file):
    return query_all(
        db_file,
        "SELECT * FROM change_requests WHERE status = ? ORDER BY number",
        ("waiting",),
    )


def approve_request(db_file, number):
    """Apply the proposed total and approve together, or change neither."""
    with sqlite3.connect(db_file) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        request = conn.execute(
            "SELECT * FROM change_requests WHERE number = ? AND status = ?",
            (number, "waiting"),
        ).fetchone()
        if request is None:
            return False
        try:
            new_total = int(request["new_value"])
        except (TypeError, ValueError) as exc:
            raise ValueError("Request has an invalid total") from exc
        if new_total < 0 or str(new_total) != request["new_value"]:
            raise ValueError("Request has an invalid total")
        updated = conn.execute(
            "UPDATE jobs SET recorded_contract_total_cents = ? WHERE job_id = ?",
            (new_total, request["job_id"]),
        )
        if updated.rowcount != 1:
            raise ValueError("Request refers to a missing job")
        conn.execute(
            "UPDATE change_requests SET status = ? WHERE number = ? AND status = ?",
            ("approved", number, "waiting"),
        )
    return True


def reject_request(db_file, number):
    """Reject a waiting request without editing its job."""
    with sqlite3.connect(db_file) as conn:
        cursor = conn.execute(
            "UPDATE change_requests SET status = ? WHERE number = ? AND status = ?",
            ("rejected", number, "waiting"),
        )
        return cursor.rowcount == 1


def all_jobs(db_file):
    """List all jobs for the terminal demonstration."""
    return query_all(db_file, "SELECT * FROM jobs ORDER BY job_id")
