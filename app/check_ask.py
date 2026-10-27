import json
import urllib.error
import urllib.request

from login import login


API_URL = "https://zol49wfjzh.execute-api.us-east-1.amazonaws.com/ask"


def call_api(label, payload, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    print(f"\n--- {label} ---")

    try:
        with urllib.request.urlopen(request, timeout=40) as result:
            print(f"HTTP {result.status}")
            print(json.dumps(json.load(result), indent=2))
    except urllib.error.HTTPError as error:
        print(f"HTTP {error.code}")
        print(error.read().decode("utf-8"))
    except urllib.error.URLError:
        print("Connection failed.")


def main():
    call_api(
        "No login",
        {"question": "Who approves travel with equipment?"},
    )

    print("\nSign in as employee-demo.")
    token = login()

    try:
        call_api(
            "Employee: permitted question",
            {"question": "Who approves travel with equipment?"},
            token,
        )

        call_api(
            "Employee: restricted SOC question",
            {
                "question": (
                    "Who approves incident closure and "
                    "what documentation is required?"
                )
            },
            token,
        )

        call_api(
            "Employee: attempted audience override",
            {
                "question": "Who approves incident closure?",
                "audience": "soc_analysts",
            },
            token,
        )
    finally:
        del token


if __name__ == "__main__":
    main()