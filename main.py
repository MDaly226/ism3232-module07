# main.py
# Author: Michael Daly
"""Terminal demo for the Order Invoice Assistant and staff approval workflow."""

from agent import SupportChatbot
from database import (
    all_jobs,
    approve_request,
    create_tables,
    reject_request,
    waiting_requests,
)
from ollama_model import OllamaModel
from settings import DB_FILE, INSTRUCTIONS, MODEL_NAME
from tools import InvoiceTools


def main():
    """Chat about fictional jobs, then review pending financial corrections."""
    create_tables(DB_FILE)
    bot = SupportChatbot(
        "Wonder", INSTRUCTIONS, InvoiceTools(DB_FILE), OllamaModel(MODEL_NAME)
    )

    print("Order Invoice Assistant (simulated MarketSharp records)")
    print("Type a message, or type quit to stop.")
    while True:
        user_message = input("You: ").strip()
        if user_message.lower() == "quit":
            break
        if not user_message:
            continue
        print(f"{bot.name}: {bot.respond(user_message)}")

    print(f"Messages in this conversation: {len(bot.history)}")
    print("Staff review")
    pending = waiting_requests(DB_FILE)
    if not pending:
        print("No requests waiting for review.")

    for request in pending:
        number = request["number"]
        job_id = request["job_id"]
        proposed_cents = int(request["new_value"])
        print(
            f"Request {number}: change job {job_id}'s recorded contract total "
            f"to ${proposed_cents / 100:,.2f}"
        )
        answer = input("Approve? yes or no: ").strip().lower()
        if answer == "yes":
            if approve_request(DB_FILE, number):
                print(f"Request {number} approved.")
            else:
                print(f"Request {number} could not be approved.")
        elif answer == "no":
            if reject_request(DB_FILE, number):
                print(f"Request {number} rejected.")
            else:
                print(f"Request {number} could not be rejected.")
        else:
            print(f"Request {number} is still waiting.")

    print("Final job records:")
    for job in all_jobs(DB_FILE):
        amount = job["recorded_contract_total_cents"] / 100
        print(f"{job['job_id']}: recorded contract total ${amount:,.2f}")


if __name__ == "__main__":
    main()
