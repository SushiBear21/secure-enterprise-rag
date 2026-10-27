import json
import urllib.error
import urllib.request

from login import login


API_URL = (
    "https://zol49wfjzh.execute-api.us-east-1.amazonaws.com/whoami"
)


def main():
    token = login()

    request = urllib.request.Request(
        API_URL,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as result:
            print(f"HTTP {result.status}")
            print(json.dumps(json.load(result), indent=2))
    except urllib.error.HTTPError as error:
        print(f"HTTP {error.code}")
        print(error.read().decode("utf-8"))
    finally:
        del token


if __name__ == "__main__":
    main()