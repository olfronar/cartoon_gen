from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import logging
import re
import secrets
import subprocess
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Event, Thread

from shared.config import Settings

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
_TUNNEL_URL_RE = re.compile(r"(https://[a-z0-9-]+\.trycloudflare\.com)")


def authorize(settings: Settings) -> dict:
    """Run the OAuth flow via cloudflared tunnel + local HTTP server."""
    if not settings.tiktok_client_key or not settings.tiktok_client_secret:
        raise RuntimeError("TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET must be set in .env")

    port = settings.tiktok_redirect_port

    # Start cloudflared tunnel
    print(f"Starting cloudflared tunnel on port {port}...")
    tunnel_proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    tunnel_url = _wait_for_tunnel_url(tunnel_proc)
    if not tunnel_url:
        tunnel_proc.terminate()
        raise RuntimeError("Failed to start cloudflared tunnel — is cloudflared installed?")

    # Drain remaining cloudflared output in background so pipe doesn't block
    Thread(target=_drain_pipe, args=(tunnel_proc.stdout,), daemon=True).start()

    redirect_uri = f"{tunnel_url}/callback"
    print(f"\nTunnel ready! Your redirect URI is:\n\n  {redirect_uri}\n")
    print("Register this URI in your TikTok Developer portal (app Settings > Redirect URI).")
    print("Press Enter when done...")
    with contextlib.suppress(EOFError):
        input()

    state = secrets.token_urlsafe(32)

    # PKCE
    code_verifier = secrets.token_urlsafe(64)
    challenge_digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_digest).rstrip(b"=").decode("ascii")

    params = urllib.parse.urlencode(
        {
            "client_key": settings.tiktok_client_key,
            "response_type": "code",
            "scope": "video.publish,video.upload",
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    auth_url = f"{_AUTH_URL}?{params}"

    # Start local HTTP server to receive callback via the tunnel
    result: dict = {}
    done = Event()
    handler_class = _make_handler_class(state, result, done)
    server = HTTPServer(("localhost", port), handler_class)

    # Run server in background thread
    server_thread = Thread(target=_serve_until_done, args=(server, done), daemon=True)
    server_thread.start()

    print("\nOpening browser for TikTok authorization...")
    print(f"If the browser doesn't open, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    # Wait for callback
    done.wait(timeout=300)
    server.shutdown()
    tunnel_proc.terminate()

    if not done.is_set():
        raise RuntimeError("Authorization timed out (5 minutes)")

    if "error" in result:
        raise RuntimeError(f"Authorization failed: {result['error']}")

    code = result["code"]
    token_data = _exchange_code(settings, code, redirect_uri, code_verifier)
    _save_tokens(settings, token_data)

    print(f"\nAuthorization successful! Tokens saved to {settings.tiktok_tokens_path}")
    return token_data


def refresh_tokens(settings: Settings) -> dict:
    """Refresh the access token using the stored refresh token."""
    tokens = _read_tokens(settings)
    if not tokens.get("refresh_token"):
        raise RuntimeError(
            f"No refresh token found in {settings.tiktok_tokens_path}. Run 'auth' first."
        )

    data = urllib.parse.urlencode(
        {
            "client_key": settings.tiktok_client_key,
            "client_secret": settings.tiktok_client_secret,
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        _TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        token_data = json.loads(resp.read().decode("utf-8"))

    if "error" in token_data and token_data["error"] != "ok":
        raise RuntimeError(
            f"Token refresh failed: {token_data.get('error_description', token_data['error'])}"
        )

    _save_tokens(settings, token_data)
    logger.info("Tokens refreshed successfully")
    print(f"Tokens refreshed! Saved to {settings.tiktok_tokens_path}")
    return token_data


def load_tokens(settings: Settings) -> dict:
    """Load tokens from file, auto-refreshing if expired."""
    tokens = _read_tokens(settings)

    if not tokens.get("access_token"):
        raise RuntimeError(f"No tokens found in {settings.tiktok_tokens_path}. Run 'auth' first.")

    if tokens.get("expires_at", 0) < time.time():
        logger.info("Access token expired, refreshing...")
        refresh_tokens(settings)
        tokens = _read_tokens(settings)

    return tokens


def _wait_for_tunnel_url(proc: subprocess.Popen, timeout: int = 30) -> str | None:
    """Read cloudflared output until the tunnel URL appears."""
    assert proc.stdout is not None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                return None
            continue
        match = _TUNNEL_URL_RE.search(line)
        if match:
            return match.group(1)
    return None


def _drain_pipe(pipe) -> None:
    """Read and discard output from a pipe to prevent buffer blocking."""
    try:
        for _ in pipe:
            pass
    except (OSError, ValueError):
        pass


def _serve_until_done(server: HTTPServer, done: Event) -> None:
    """Serve HTTP requests until the done event is set."""
    while not done.is_set():
        server.handle_request()


def _exchange_code(settings: Settings, code: str, redirect_uri: str, code_verifier: str) -> dict:
    """Exchange authorization code for tokens."""
    data = urllib.parse.urlencode(
        {
            "client_key": settings.tiktok_client_key,
            "client_secret": settings.tiktok_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        _TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        token_data = json.loads(resp.read().decode("utf-8"))

    if "error" in token_data and token_data["error"] != "ok":
        raise RuntimeError(
            f"Token exchange failed: {token_data.get('error_description', token_data['error'])}"
        )

    return token_data


def _save_tokens(settings: Settings, token_data: dict) -> None:
    """Save tokens to JSON file."""
    tokens = {
        "access_token": token_data["access_token"],
        "refresh_token": token_data["refresh_token"],
        "open_id": token_data.get("open_id", ""),
        "expires_at": time.time() + token_data.get("expires_in", 86400),
    }
    path = Path(settings.tiktok_tokens_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tokens, indent=2), encoding="utf-8")


def _read_tokens(settings: Settings) -> dict:
    """Read tokens from JSON file. Returns empty dict if file doesn't exist."""
    path = Path(settings.tiktok_tokens_path)
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _make_handler_class(state: str, result: dict, done: Event) -> type[BaseHTTPRequestHandler]:
    """Create a handler class with shared state via closure."""

    class Handler(BaseHTTPRequestHandler):
        expected_state = state
        callback_result = result
        callback_done = done

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)

            if parsed.path != "/callback":
                self.send_response(404)
                self.end_headers()
                return

            # Check for error
            if "error" in params:
                self.callback_result["error"] = params["error"][0]
                self._respond(
                    400,
                    f"<h1>Authorization Failed</h1>"
                    f"<p>{params.get('error_description', ['Unknown error'])[0]}</p>",
                )
                self.callback_done.set()
                return

            # Validate state
            received_state = params.get("state", [None])[0]
            if received_state != self.expected_state:
                self.callback_result["error"] = "state_mismatch"
                self._respond(
                    400,
                    "<h1>Authorization Failed</h1><p>State mismatch (CSRF check failed).</p>",
                )
                self.callback_done.set()
                return

            # Success
            self.callback_result["code"] = params["code"][0]
            self._respond(
                200,
                "<h1>Authorization Successful!</h1>"
                "<p>You can close this tab and return to the terminal.</p>",
            )
            self.callback_done.set()

        def _respond(self, code: int, body: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        def log_message(self, format: str, *args) -> None:  # noqa: A002
            """Suppress default HTTP server logging."""

    return Handler
