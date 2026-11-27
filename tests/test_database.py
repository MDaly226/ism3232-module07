"""Tests for the Order Invoice Assistant database layer."""

import database


def make_db(tmp_path):
    """Create an isolated SQLite database for each test."""
    db_file = tmp_path / "test.db"
    database.create_tables(db_file)
    return db_file


def test_create_tables_twice_adds_no_duplicate_rows(tmp_path):
    db_file = make_db(tmp_path)
    before = {
        table: database.query_one(db_file, f"SELECT COUNT(*) AS count FROM {table}")[
            "count"
        ]
        for table in (
            "customers",
            "jobs",
            "order_items",
            "existing_change_orders",
            "payments",
            "change_requests",
        )
    }
    database.create_tables(db_file)
    after = {
        table: database.query_one(db_file, f"SELECT COUNT(*) AS count FROM {table}")[
            "count"
        ]
        for table in before
    }
    assert after == before
    assert before == {
        "customers": 5,
        "jobs": 5,
        "order_items": 5,
        "existing_change_orders": 5,
        "payments": 5,
        "change_requests": 0,
    }


def test_find_job_needs_the_exact_id(tmp_path):
    db_file = make_db(tmp_path)
    job = database.find_job(db_file, "J1001")
    assert job is not None
    assert job["job_id"] == "J1001"
    assert database.find_job(db_file, "J100") is None
    assert database.find_job(db_file, "J1001extra") is None


def test_sql_in_a_job_id_is_just_text(tmp_path):
    db_file = make_db(tmp_path)
    assert database.find_job(db_file, "J1001' OR '1'='1") is None
    assert len(database.all_jobs(db_file)) == 5


def test_change_requests_get_numbers_and_wait(tmp_path):
    db_file = make_db(tmp_path)
    original = database.find_job(db_file, "J1003")["recorded_contract_total_cents"]
    number = database.add_change_request(db_file, "J1003", 1750000)
    assert number == 1
    request = database.find_request(db_file, number)
    assert request["job_id"] == "J1003"
    assert request["new_value"] == "1750000"
    assert request["status"] == "waiting"
    assert (
        database.find_job(db_file, "J1003")["recorded_contract_total_cents"] == original
    )
    assert [row["number"] for row in database.waiting_requests(db_file)] == [1]


def test_approve_changes_the_total_once(tmp_path):
    db_file = make_db(tmp_path)
    number = database.add_change_request(db_file, "J1003", 1750000)
    assert database.approve_request(db_file, number) is True
    assert (
        database.find_job(db_file, "J1003")["recorded_contract_total_cents"] == 1750000
    )
    assert database.find_request(db_file, number)["status"] == "approved"
    assert database.approve_request(db_file, number) is False
    assert (
        database.find_job(db_file, "J1003")["recorded_contract_total_cents"] == 1750000
    )
    assert database.waiting_requests(db_file) == []


def test_reject_changes_nothing_and_cannot_be_approved_later(tmp_path):
    db_file = make_db(tmp_path)
    original = database.find_job(db_file, "J1003")["recorded_contract_total_cents"]
    number = database.add_change_request(db_file, "J1003", 1750000)
    assert database.reject_request(db_file, number) is True
    assert database.find_request(db_file, number)["status"] == "rejected"
    assert (
        database.find_job(db_file, "J1003")["recorded_contract_total_cents"] == original
    )
    assert database.approve_request(db_file, number) is False
    assert database.reject_request(db_file, number) is False
    assert (
        database.find_job(db_file, "J1003")["recorded_contract_total_cents"] == original
    )
    assert database.waiting_requests(db_file) == []


def test_related_records_belong_to_the_requested_job(tmp_path):
    db_file = make_db(tmp_path)
    items = database.items_for_job(db_file, "J1001")
    changes = database.change_orders_for_job(db_file, "J1001")
    payments = database.payments_for_job(db_file, "J1001")
    assert len(items) == 1
    assert len(changes) == 1
    assert len(payments) == 2
    assert all(record["job_id"] == "J1001" for record in items + changes + payments)


def test_missing_job_cannot_receive_a_change_request(tmp_path):
    import pytest

    db_file = make_db(tmp_path)
    with pytest.raises(ValueError, match="Job not found"):
        database.add_change_request(db_file, "MISSING", 100000)
    assert database.waiting_requests(db_file) == []
