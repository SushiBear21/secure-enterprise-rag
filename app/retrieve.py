import argparse
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError

PROFILE = "portfolio-sandbox"
REGION = "us-east-1"
ACCOUNT_ID = "359769212511"
KNOWLEDGE_BASE_ID = "CIDAASDHVV"


def retrieve(question, audience):
    session = boto3.Session(
        profile_name=PROFILE,
        region_name=REGION,
    )

    identity = session.client("sts").get_caller_identity()
    if identity["Account"] != ACCOUNT_ID:
        raise RuntimeError("AWS account does not match the sandbox.")

    client = session.client("bedrock-agent-runtime")
    response = client.retrieve(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        retrievalQuery={"text": question},
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": 3,
                "filter": {
                    "equals": {
                        "key": "audience",
                        "value": audience,
                    }
                },
            }
        },
    )

    results = response.get("retrievalResults", [])

    # Check returned metadata before passing evidence onward.
    for result in results:
        if result.get("metadata", {}).get("audience") != audience:
            raise RuntimeError("Unexpected audience in retrieved evidence.")

    return results


def main():
    parser = argparse.ArgumentParser(description="Retrieve synthetic RAG evidence.")
    parser.add_argument("question")
    parser.add_argument(
        "--audience",
        required=True,
        choices=["all_employees", "soc_analysts", "acquisition_team"],
        help="Development test selector; not authenticated authorization.",
    )
    args = parser.parse_args()

    if not args.question.strip():
        parser.error("Question must not be empty.")

    try:
        results = retrieve(args.question, args.audience)
    except (BotoCoreError, ClientError, RuntimeError) as error:
        print(f"Retrieval failed: {error}", file=sys.stderr)
        return 1

    if not results:
        print("No matching evidence returned.")
        return 0

    for number, result in enumerate(results, start=1):
        metadata = result.get("metadata", {})
        source = result.get("location", {}).get("s3Location", {}).get("uri", "")
        text = result.get("content", {}).get("text", "")

        print(f"\n[{number}] Document: {metadata.get('document_id', 'unknown')}")
        print(f"Audience: {metadata.get('audience', 'unknown')}")
        print(f"Source: {source}")
        print("Text:")
        print("\n".join(text.splitlines()))

    return 0


if __name__ == "__main__":
    sys.exit(main())