"""Tonight's target: prove Hindsight Cloud can store and recall a test memory."""

from hindsight_client import Hindsight

from config import load_keys

BANK_ID = "feedback-analyser-test"


def main():
    keys = load_keys()
    client = Hindsight(
        base_url="https://api.hindsight.vectorize.io",
        api_key=keys["HINDSIGHT_API_KEY"],
    )

    client.create_bank(bank_id=BANK_ID, name="Feedback Analyser Test")

    client.retain(
        bank_id=BANK_ID,
        content=(
            "Week 1 theme: login issues. Score: 7/10 severity. "
            "12 reviews mentioned login failures, sentiment mostly negative."
        ),
    )

    result = client.recall(bank_id=BANK_ID, query="What did week 1 say about login issues?")

    print("Recall results:")
    for memory in result.results:
        print("-", memory.text)


if __name__ == "__main__":
    main()
