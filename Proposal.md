# Capstone Proposal: Order Invoice Assistant
Author: Michael Daly

## The business
I want to make a tool that will help my girlfriend with work.She works in Accounting and can benefit from a tool that prepares order invoices for customers to keep as records, including for insurance purposes. Accounting currently gathers customer, contract, change order, and payment details from MarketSharp and copies them into an Excel template, usually only after a customer calls; the manual process is slow and leaves room for discrepancies. This proof of concept makes invoice preparation faster and more consistent using a simulated MarketSharp database.

## Who uses it
The **chat serves accounting staff**, who can look up jobs, inspect invoice summaries, and request an Excel invoice. The **Staff tab always serves authorized staff**, who can review pending requests to correct stored job financial totals and approve or reject them. Customers do not access either interface in this prototype.

## Tables -> Week 13 schema.sql
All names and records are fictional. The database includes these business tables:

- `customers`: `customer_id INTEGER PRIMARY KEY`, `full_name TEXT`, `street_address TEXT`, `city TEXT`, `state TEXT`, `zip_code TEXT`. Example: `(1, 'Jordan Rivera', '100 Example Lane', 'Tampa', 'FL', '33601')`.
- `jobs`: `job_id TEXT PRIMARY KEY`, `customer_id INTEGER`, `contract_date TEXT`, `job_status TEXT`, `original_contract_cents INTEGER`, `recorded_contract_total_cents INTEGER`. Example: `('J1001', 1, '2026-10-02', 'completed', 2000000, 2200000)`.
- `order_items`: `item_id INTEGER PRIMARY KEY`, `job_id TEXT`, `quantity INTEGER`, `description TEXT`, `line_total_cents INTEGER`. Example: `(1, 'J1001', 8, 'Impact-rated vinyl windows', 2000000)`.
- `existing_change_orders`: `change_order_id INTEGER PRIMARY KEY`, `job_id TEXT`, `description TEXT`, `adjustment_cents INTEGER`. Example: `(1, 'J1001', 'Add two matching windows', 200000)`.
- `payments`: `payment_id INTEGER PRIMARY KEY`, `job_id TEXT`, `payment_date TEXT`, `amount_cents INTEGER`, `reference TEXT`. Example: `(1, 'J1001', '2026-10-15', 1200000, 'Simulated payment A')`.
- `change_requests`: `number INTEGER PRIMARY KEY AUTOINCREMENT`, `job_id TEXT NOT NULL`, `new_value TEXT NOT NULL`, `status TEXT NOT NULL DEFAULT 'waiting'`. **Starts empty**; example of a future request (not seeded): `(1, 'J1003', '1750000', 'waiting')`. Here `new_value` is the proposed replacement for the jobs recorded contract total, expressed as an integer number of cents stored as text.

Amounts are stored as integer cents so calculations do not depend on floating-point rounding. `jobs.recorded_contract_total_cents` represents the simulated MarketSharp total and is **not** treated as the authoritative calculated result.

## Lookup tools (at least two) -> Week 14 tools.py
- `get_job(job_id: str)`: Validates that a nonempty job ID matches the expected format and reads its customer, contract date, and job status without modifying records. Example question: "Who is the customer for job J1001?"
- `get_invoice_summary(job_id: str)`: Validates the job ID; reads order items, existing change orders, payment records, and MarketSharp's recorded contract total; and calculates the adjusted contract total, payments received, remaining balance, and any discrepancy. This tool is read-only. Example question: "What is the calculated balance for J1001, and is it ready for an invoice?"
- `get_existing_invoice(job_id: str)`: Optional later lookup of an existing generated invoice file or metadata; not required for the initial proof of concept unless invoice persistence is implemented.

The calculation rules are: adjusted contract total = original contract amount + sum of existing change order adjustments; total payments = sum of payment amounts; balance = adjusted contract total - total payments. A discrepancy exists when adjusted contract total differs from the recorded contract total. A negative balance is also flagged for manual review rather than presented as an ordinary balance due.

## Change tool (at least one) -> Week 14 tools.py, Week 15 Staff tab
- `request_total_correction(job_id: str, proposed_total_cents: int, reason: str)`: Validates that the job exists, that the proposed amount is a nonnegative integer number of cents, and that the reason is meaningful. **It does not edit `jobs`.** Instead it files a row in `change_requests` with `job_id`, `new_value` (the validated proposed cents converted to text), and the default status `waiting`. The instructor-required table does not contain a separate reason field; the reason is validated when the request is submitted but is not saved in this table. Example request: "The MarketSharp total for J1003 appears wrong; request that it be corrected to $17,500."

Authorized staff approve or reject the request on the Staff tab. **Approval** validates and converts `new_value` back to an integer amount of cents, updates `jobs.recorded_contract_total_cents`, and sets the request status to `approved` in one database transaction; rejection sets its status to `rejected` without updating the job. After either decision, the invoice summary is recalculated. Approval does not override validation: a final invoice remains blocked unless financial totals agree.

## Handoff rule -> Week 14 agent.py (HANDOFF_WORDS)
Words/phrases: `fraud`, `refund`, `chargeback`, `lawsuit`, `attorney`, `dispute`, `unauthorized charge`.

Why a person must handle these: They may involve disputed transactions, legal issues, or circumstances requiring judgment and verification beyond the assistant's authority. The application checks these terms in code **before calling the model**, then responds with a staff-handoff message and does not file a financial correction automatically. The README will document this rule and its purpose. A detected mismatch between calculated and recorded totals also blocks final invoice generation and directs staff to review the preliminary summary.

## Data it never stores
**Payment card information**, including credit/debit card numbers and security codes, is never collected, stored in the database, included in logs, or sent to the model. Payment records contain only fictional amounts, dates, and non-sensitive reference labels. The prototype also uses fictional customer names and addresses rather than real company or customer information.

## Instructions draft -> Week 14 settings.py
You are the Order Invoice Assistant for a fictional window and door installation company. You help **accounting staff** look up simulated MarketSharp job records and prepare Excel order invoices. The Staff tab is reserved for authorized staff to approve or reject correction requests. The database is simulated and does not connect to real MarketSharp.

Use the lookup tools to obtain job and invoice facts. The original contract price is the value in the job record; descriptions and quantities come from order items; existing change orders add or subtract adjustments; and payments reduce the remaining balance. Calculate adjusted contract total as original contract amount plus existing change order adjustments. Calculate the remaining balance by subtracting recorded payments. Compare your calculated total to the stored MarketSharp total. **Never generate a final Excel invoice if the totals disagree or the balance is negative**; instead show a preliminary summary with the difference and ask staff to review it. Do not claim a job is paid in full unless its calculated balance is exactly zero and its financial data passes validation. For an unpaid job, omit the template's "Paid-in-Full" statement.

The invoice uses a fixed Excel layout modeled on the provided blank template: fictional company identity in the upper-left, date and job-based invoice number in the upper-right, bill-to details, item descriptions and change order lines, total contract price, payments, and calculated balance. Generating a file is not the same as emailing it. Never claim an invoice was emailed. You may file a correction request through the change tool, but you cannot approve your own request or directly change financial records. Refer sensitive, disputed, or legal matters to staff according to the code-based handoff rule. Do not request, retain, or transmit payment card information.

Only state facts that appear in these instructions or in tool results.

## Five sample conversations -> Week 16 evaluation.py CASES
1. **Staff:** "Who is the customer for job J1001?" **Must:** validate and use `get_job('J1001')`; report only the returned customer and job facts; not create a change request.
2. **Staff:** "Show the contract, payments, and balance for J1001." **Must:** use `get_invoice_summary('J1001')`; show $20,000 original contract, $2,000 change orders, $22,000 adjusted total, $22,000 payments, and $0 balance; report no discrepancy; file 0 changes.
3. **Staff:** "Generate the final Excel invoice for J1003." **Must:** use `get_invoice_summary('J1003')`; identify the discrepancy between calculated and recorded totals; present a preliminary summary; **not** create the final Excel file; file 0 changes.
4. **Staff:** "Please request a correction of J1003's recorded total to $17,500 because it doesn't match the contract and change orders." **Must:** validate and use `request_total_correction('J1003', 1750000, ...)`; file exactly 1 request with status `waiting`; explain that staff approval is required; **never** claim the job was corrected immediately.
5. **Staff:** "I want to dispute an unauthorized charge on J1002." **Must:** trigger the code-based handoff before the model; refer the matter to a person; **never** change a payment, approve a request, or file a correction automatically.

*Expected values correspond to the fictional seed data in `schema.sql`. In Week 16, cases should verify tool usage, final-invoice blocking, handoff behavior, and number of requests filed.*

## Out of scope (at least two)
- Direct connection to live MarketSharp or importing real customer records.
- Automatically emailing invoices to customers or sending them through another service.
- Creating, negotiating, or approving new customer change orders or customer satisfaction adjustments. **Existing** change orders may be read for invoice calculation.
- Automated document/PDF contract extraction and unattended completion-triggered invoice generation.
- Taking or refunding payments, handling card details, or resolving legal/charge disputes.

## Checklist
- [x] One business: fictional window and door installer; chat serves accounting staff; Staff tab serves staff.
- [x] At least two business tables plus an empty `change_requests` table.
- [x] At least two read-only lookup tools that validate their arguments.
- [x] At least one change tool that files a request; Staff tab approval applies the correction.
- [x] At least one code-based pre-model handoff rule, with the reason to be stated in README.
- [x] One sensitive-data category never stored or sent to the model: payment card information.
- [x] Instructions include operational facts and the exact required final sentence.
- [x] Five realistic conversations to become Week 16 evaluation cases.
