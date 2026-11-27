"""Agent integration tests, without importing or requiring Ollama."""

import database
from agent import SupportChatbot
from fallback_model import FallbackModel
from keyword_model import KeywordModel
from tools import InvoiceTools


class DecisionModel:
    """Return predetermined decisions, in order, without any AI service."""

    def __init__(self, decisions):
        self.decisions = iter(decisions)

    def decide(self, instructions, history, tools):
        return next(self.decisions, None)


class SilentModel:
    """Simulate an unavailable primary model."""

    def decide(self, instructions, history, tools):
        return None


def make_bot(tmp_path, model):
    """Build an assistant over isolated fictional sample records."""
    db_file = tmp_path / "test.db"
    database.create_tables(db_file)
    return SupportChatbot(
        "Invoice Assistant", "Be concise and accurate.", InvoiceTools(db_file), model
    )


def ask_for_tool(name, arguments):
    """Make a tool request in the model's expected shape."""
    return {"tool": name, "arguments": arguments}


def test_model_chosen_job_lookup_answers_from_database(tmp_path):
    model = DecisionModel(
        [
            ask_for_tool("look_up_job", {"job_id": "J1001"}),
            {"text": "Job J1001 is completed."},
        ]
    )
    bot = make_bot(tmp_path, model)
    bot.respond("What is the status of job J1001?")
    assert any(
        item["role"] == "tool" and "Job J1001 is completed" in item["content"]
        for item in bot.history
    )


def test_made_up_correction_never_reaches_database(tmp_path):
    model = DecisionModel(
        [
            ask_for_tool(
                "request_contract_total_correction",
                {"job_id": "J1003", "new_value": "1750000"},
            ),
            {"text": "Please provide the amount in cents."},
        ]
    )
    bot = make_bot(tmp_path, model)
    bot.respond("Please correct the total for job J1003.")
    assert database.waiting_requests(bot.tools.db_file) == []


def test_keyword_fallback_reads_invoice_balance(tmp_path):
    model = FallbackModel(SilentModel(), KeywordModel())
    bot = make_bot(tmp_path, model)
    reply = bot.respond("Check the invoice balance for J1001")
    assert "22,000.00" in reply or any(
        "22,000.00" in item["content"] for item in bot.history if item["role"] == "tool"
    )


def test_keyword_model_cannot_file_unspoken_amount(tmp_path):
    bot = make_bot(tmp_path, KeywordModel())
    bot.respond("Please correct the contract total for J1003")
    assert database.waiting_requests(bot.tools.db_file) == []
