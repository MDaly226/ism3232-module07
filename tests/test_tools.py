"""Tests for model-callable invoice tools and their argument checks."""

import database
from tools import InvoiceTools


def make_tools(tmp_path):
    """Build tools over a fresh database with fictional sample rows."""
    db_file = tmp_path / "test.db"
    database.create_tables(db_file)
    return InvoiceTools(db_file)


def customer(text):
    """Build a history holding one accounting staff message."""
    return [{"role": "user", "content": text}]


def test_job_lookup_finds_id_inside_sentence(tmp_path):
    tools = make_tools(tmp_path)
    reply = tools.run(
        "look_up_job",
        {"job_id": "Can you find job J1001?"},
        customer("Can you find job J1001?"),
    )
    assert "Job J1001 is completed" in reply


def test_balance_lookup_reads_and_checks_totals(tmp_path):
    tools = make_tools(tmp_path)
    reply = tools.run(
        "check_invoice_balance", {"job_id": "J1001"}, customer("Check J1001")
    )
    assert "Totals match" in reply
    assert "$22,000.00" in reply


def test_discrepancy_blocks_final_invoice(tmp_path):
    tools = make_tools(tmp_path)
    reply = tools.run(
        "check_invoice_balance", {"job_id": "J1003"}, customer("Check J1003")
    )
    assert "Discrepancy: $500.00" in reply
    assert "Final invoice generation is blocked" in reply


def test_change_request_waits_and_does_not_apply_immediately(tmp_path):
    tools = make_tools(tmp_path)
    original = database.find_job(tools.db_file, "J1003")[
        "recorded_contract_total_cents"
    ]
    reply = tools.run(
        "request_contract_total_correction",
        {"job_id": "J1003", "new_value": "1750000"},
        customer("Please correct job J1003 to 1750000 cents."),
    )
    assert "Request 1 was sent to staff" in reply
    assert database.find_request(tools.db_file, 1)["status"] == "waiting"
    assert (
        database.find_job(tools.db_file, "J1003")["recorded_contract_total_cents"]
        == original
    )


def test_check_request_reads_waiting_status(tmp_path):
    tools = make_tools(tmp_path)
    database.add_change_request(tools.db_file, "J1003", 1750000)
    reply = tools.run("check_request", {"number": "1"}, customer("Check request 1"))
    assert "waiting for staff" in reply


def test_unknown_tool_refused(tmp_path):
    tools = make_tools(tmp_path)
    assert "There is no tool named" in tools.run(
        "delete_job", {}, customer("Delete J1001")
    )


def test_missing_value_refused(tmp_path):
    tools = make_tools(tmp_path)
    reply = tools.run(
        "request_contract_total_correction", {"job_id": "J1003"}, customer("Fix J1003")
    )
    assert "both needed" in reply


def test_made_up_job_id_refused(tmp_path):
    tools = make_tools(tmp_path)
    reply = tools.run("look_up_job", {"job_id": "J1002"}, customer("Where is J1001?"))
    assert "has not given that job ID" in reply


def test_made_up_amount_refused_without_request(tmp_path):
    tools = make_tools(tmp_path)
    reply = tools.run(
        "request_contract_total_correction",
        {"job_id": "J1003", "new_value": "1750000"},
        customer("Please fix job J1003."),
    )
    assert "has not given that amount" in reply
    assert database.waiting_requests(tools.db_file) == []


def test_bad_amount_refused(tmp_path):
    tools = make_tools(tmp_path)
    reply = tools.run(
        "request_contract_total_correction",
        {"job_id": "J1003", "new_value": "not-a-number"},
        customer("For J1003, use not-a-number cents."),
    )
    assert "nonnegative whole number of cents" in reply
    assert database.waiting_requests(tools.db_file) == []


def test_unknown_request_number_refused(tmp_path):
    tools = make_tools(tmp_path)
    reply = tools.run("check_request", {"number": "1"}, customer("Check request 2"))
    assert "has not given that request number" in reply
