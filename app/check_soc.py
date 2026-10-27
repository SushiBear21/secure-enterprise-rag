from check_ask import call_api
from login import login


def main():
    token = login()

    try:
        call_api(
            "SOC: incident closure",
            {
                "question": (
                    "Who approves incident closure and "
                    "what documentation is required?"
                )
            },
            token,
        )

        call_api(
            "SOC: general employee policy",
            {"question": "Who approves travel with equipment?"},
            token,
        )

        call_api(
            "SOC: restricted acquisition question",
            {
                "question": (
                    "Who approves vendor access and when does it expire?"
                )
            },
            token,
        )
    finally:
        del token


if __name__ == "__main__":
    main()