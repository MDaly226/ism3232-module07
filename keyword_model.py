# keyword_model.py
"""Keyword fallback for accounting-staff invoice questions (no Ollama needed)."""

import re


class KeywordModel:
    """Choose an approved invoice tool using simple keyword rules."""

    def decide(self, instructions, history, tools):
        """Return a tool request or a text reply based on the last message."""
        last = history[-1]
        if last["role"] == "tool":
            return {"text": last["content"]}

        message = last["content"]
        text = message.lower()

        # Choose the specific request tool before general job lookups.
        if "request" in text and any(
            word in text
            for word in ("status", "check", "waiting", "approved", "rejected")
        ):
            return {"tool": "check_request", "arguments": {"number": message}}

        if any(
            word in text
            for word in ("correct", "correction", "update", "fix", "change")
        ) and any(word in text for word in ("total", "amount", "cents", "contract")):
            # Require a number explicitly written as cents. Do not fabricate an amount.
            match = re.search(r"\b(\d+)\s*cents?\b", text)
            value = match.group(1) if match else ""
            return {
                "tool": "request_contract_total_correction",
                "arguments": {"job_id": message, "new_value": value},
            }

        if any(
            word in text
            for word in ("invoice", "balance", "payment", "total", "discrepancy")
        ):
            return {"tool": "check_invoice_balance", "arguments": {"job_id": message}}

        if any(word in text for word in ("job", "contract", "status")):
            return {"tool": "look_up_job", "arguments": {"job_id": message}}

        if "hello" in text or "hi" == text.strip():
            return {"text": "Hello! I can look up jobs and check invoice balances."}

        return {
            "text": "I can look up a job, check an invoice balance, or file a total correction request."
        }
