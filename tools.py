# tools.py — Order Invoice Assistant
"""Validated, model-callable tools for fictional MarketSharp records."""

import database


class InvoiceTools:
    """Database tools; all model requests must pass through run()."""

    def __init__(self, db_file):
        self.db_file = db_file

    def tool_list(self):
        """Return the methods the model may call."""
        return [
            self.look_up_job,
            self.check_invoice_balance,
            self.request_contract_total_correction,
            self.check_request,
        ]

    def _job_in_text(self, text):
        """Find an existing job ID in a sentence, without guessing one."""
        for word in str(text).upper().split():
            job_id = word.strip("?.!,#")
            job = database.find_job(self.db_file, job_id)
            if job is not None:
                return job
        return None

    def look_up_job(self, job_id):
        """Read the status and contract date of one job.

        Args:
            job_id: Job identifier, such as J1001, or a sentence containing it.
        """
        job = self._job_in_text(job_id)
        if job is None:
            return "No job with that ID was found. Job IDs look like J1001."
        return (
            f"Job {job['job_id']} is {job['job_status']} "
            f"(contract date: {job['contract_date']})."
        )

    def check_invoice_balance(self, job_id):
        """Calculate and compare job totals; never edit database records.

        Args:
            job_id: Job identifier, such as J1001, or a sentence containing it.
        """
        job = self._job_in_text(job_id)
        if job is None:
            return "No job with that ID was found. Job IDs look like J1001."
        key = job["job_id"]
        adjustments = sum(
            item["adjustment_cents"]
            for item in database.change_orders_for_job(self.db_file, key)
        )
        calculated = job["original_contract_cents"] + adjustments
        recorded = job["recorded_contract_total_cents"]
        paid = sum(
            payment["amount_cents"]
            for payment in database.payments_for_job(self.db_file, key)
        )
        balance = calculated - paid

        def dollars(cents):
            return f"${cents / 100:,.2f}"

        result = (
            f"Job {key}: calculated contract total {dollars(calculated)}; "
            f"recorded contract total {dollars(recorded)}; "
            f"payments {dollars(paid)}; remaining balance {dollars(balance)}."
        )
        if calculated != recorded:
            difference = abs(calculated - recorded)
            return (
                f"{result} Discrepancy: {dollars(difference)}. "
                "Final invoice generation is blocked; staff must review the records."
            )
        return f"{result} Totals match; no discrepancy detected."

    def request_contract_total_correction(self, job_id, new_value):
        """File a proposed recorded-total correction, without applying it.

        Args:
            job_id: Job identifier, such as J1003, or sentence containing it.
            new_value: Proposed recorded contract total in integer cents.
        """
        job = self._job_in_text(job_id)
        if job is None:
            return "No job with that ID was found. Job IDs look like J1001."
        amount = str(new_value).strip()
        if not amount.isascii() or not amount.isdecimal():
            return "The new contract total must be a nonnegative whole number of cents."
        number = database.add_change_request(self.db_file, job["job_id"], int(amount))
        return (
            f"Request {number} was sent to staff for job {job['job_id']}. "
            "The recorded contract total has not changed yet."
        )

    def check_request(self, number):
        """Read the status of a submitted correction request.

        Args:
            number: Request number, such as 3, or a sentence containing it.
        """
        candidate = None
        for word in str(number).split():
            token = word.strip("?.!,#")
            if token.isascii() and token.isdecimal():
                candidate = token
                break
        if candidate is None:
            return "Request numbers look like 3."
        try:
            request = database.find_request(self.db_file, int(candidate))
        except OverflowError:
            return f"There is no request {candidate}."
        if request is None:
            return f"There is no request {candidate}."
        if request["status"] == "waiting":
            return (
                f"Request {candidate} for job {request['job_id']} is waiting for staff."
            )
        return (
            f"Request {candidate} for job {request['job_id']} was {request['status']}."
        )

    def run(self, name, arguments, history):
        """Validate a requested tool call before executing any tool."""
        if not isinstance(arguments, dict):
            return "Tool arguments must be provided as a dictionary."
        if name in ("look_up_job", "check_invoice_balance"):
            job_id = self.clean(arguments, "job_id")
            if job_id == "":
                return "The job ID is missing. Ask the user for it."
            job = self._job_in_text(job_id)
            if job is None:
                return "No job with that ID was found. Job IDs look like J1001."
            if not self.customer_said(history, job["job_id"]):
                return "The user has not given that job ID. Ask them for it."
            return getattr(self, name)(job["job_id"])
        if name == "request_contract_total_correction":
            job_id = self.clean(arguments, "job_id")
            new_value = self.clean(arguments, "new_value")
            if job_id == "" or new_value == "":
                return "The job ID and proposed total in cents are both needed."
            job = self._job_in_text(job_id)
            if job is None:
                return "No job with that ID was found. Job IDs look like J1001."
            if not self.customer_said(history, job["job_id"]):
                return "The user has not given that job ID. Ask them for it."
            if not self.customer_said(history, new_value):
                return "The user has not given that amount. Ask them for it in cents."
            return self.request_contract_total_correction(job["job_id"], new_value)
        if name == "check_request":
            number = self.clean(arguments, "number")
            if number == "":
                return "The request number is missing. Ask the user for it."
            if not self.customer_said(history, number):
                return "The user has not given that request number. Ask them for it."
            return self.check_request(number)
        return f"There is no tool named {name}."

    def clean(self, arguments, key):
        """Return one argument as text without extra spaces, or "" if it is missing."""
        return str(arguments.get(key, "")).strip()

    def words(self, text):
        """Return text in lower case as whole words, without ?.!,# around each word."""
        cleaned = []
        for word in text.lower().split():
            cleaned.append(word.strip("?.!,#"))
        return " " + " ".join(cleaned) + " "

    def customer_said(self, history, text):
        """Return True if the customer typed text as whole words."""
        wanted = self.words(text)
        for message in history:
            if message["role"] == "user" and wanted in self.words(message["content"]):
                return True
        return False
