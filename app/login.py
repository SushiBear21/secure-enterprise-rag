import base64
import hashlib
import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

AUTH_BASE = "https://secure-rag-359769212511.auth.us-east-1.amazoncognito.com"
CLIENT_ID = "7clhovnk1ofjeo9855eedofog4"
REDIRECT_URI = "http://localhost:8000/callback"


def login():
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).decode("ascii").rstrip("=")

    outcome = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Do not log callback URLs containing authorization codes.

        def do_GET(self):
            parsed = urllib.parse.urlsplit(self.path)

            if parsed.path != "/callback":
                self.send_error(404)
                return

            parameters = urllib.parse.parse_qs(parsed.query)
            states = parameters.get("state", [])
            codes = parameters.get("code", [])

            valid = (
                len(states) == 1
                and secrets.compare_digest(states[0], state)
                and len(codes) == 1
                and bool(codes[0])
                and "error" not in parameters
            )

            if valid:
                outcome["code"] = codes[0]
                message = b"Login callback received. Return to PowerShell."
            else:
                outcome["error"] = True
                message = b"Login callback rejected. Return to PowerShell."

            self.send_response(200 if valid else 400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(message)

    parameters = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid secure-rag/ask",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "login",
    })

    # Listen only on this computer, not the local network.
    with HTTPServer(("127.0.0.1", 8000), CallbackHandler) as server:
        server.timeout = 1
        print("Opening Cognito login. Complete sign-in in your browser.")
        if not webbrowser.open(f"{AUTH_BASE}/oauth2/authorize?{parameters}"):
            raise RuntimeError("Could not open the browser.")

        deadline = time.monotonic() + 600
        while not outcome and time.monotonic() < deadline:
            server.handle_request()

    if "code" not in outcome:
        raise RuntimeError("Login timed out or the callback was rejected.")

    body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": outcome["code"],
        "redirect_uri": REDIRECT_URI,
        "code_verifier": verifier,
    }).encode("ascii")

    request = urllib.request.Request(
        f"{AUTH_BASE}/oauth2/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        tokens = json.load(response)

    access_token = tokens.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise RuntimeError("No access token was returned.")

    return access_token


if __name__ == "__main__":
    try:
        token = login()
        print("Login and PKCE token exchange succeeded.")
        print("Token kept in memory only; no API request made.")
        del token
    except (OSError, ValueError, RuntimeError, urllib.error.URLError):
        print("Login failed. Check the browser message and local port 8000.")
        raise SystemExit(1)