import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError


def main():
    session = boto3.Session(
        profile_name="portfolio-sandbox",
        region_name="us-east-1",
    )

    try:
        account = session.client("sts").get_caller_identity()["Account"]
        if account != "359769212511":
            raise RuntimeError("AWS account does not match the sandbox.")

        client = session.client("bedrock-runtime")
        response = client.converse(
            modelId="amazon.nova-lite-v1:0",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"text": "Reply with exactly: Model connection works."}
                    ],
                }
            ],
            inferenceConfig={
                "maxTokens": 32,
                "temperature": 0,
            },
        )

        for block in response["output"]["message"]["content"]:
            if "text" in block:
                print(block["text"])

        print("Token usage:", response.get("usage", {}))
        return 0

    except (BotoCoreError, ClientError, RuntimeError) as error:
        print(f"Model test failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())