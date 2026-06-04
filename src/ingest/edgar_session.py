"""Shared HTTP layer for all SEC EDGAR pulls.

SEC requires every automated client to (a) send a descriptive User-Agent of
the form ``Name email`` and (b) stay under ~10 requests/second. This module
centralises both, plus retry/backoff, and — importantly — turns SEC's two
block responses into one clear, actionable exception:

  * HTTP 403 (Akamai WAF), and
  * HTTP 200 whose body is the "Your Request Originates from an Undeclared
    Automated Tool" interstitial,

are both raised as :class:`EdgarBlocked` with guidance. We hit exactly this
block from the build environment (egress IP 149.34.242.15 is 403-ed by SEC
across every host and client), so downstream modules must surface it legibly
rather than producing empty data.

Set the User-Agent once via a gitignored ``.env`` at the repo root:

    SEC_EDGAR_UA=Your Name your.email@example.com
"""

from __future__ import annotations

import os
import time

import requests

try:  # optional: load .env if python-dotenv is present
    from dotenv import load_dotenv

    from src.utils.paths import REPO_ROOT

    load_dotenv(REPO_ROOT / ".env")
except Exception:
    pass

# SEC mandates a "Name email" UA. Override in .env; this default is a fallback.
_DEFAULT_UA = "Jimmy Ji ESG Flows Research JimmyKJi@users.noreply.github.com"
USER_AGENT = os.environ.get("SEC_EDGAR_UA", _DEFAULT_UA)

_MIN_INTERVAL = 0.15  # seconds between requests => ~6.7/s, under SEC's 10/s cap
_last_request_ts = 0.0

_BLOCK_MARKER = "Undeclared Automated Tool"


class EdgarBlocked(RuntimeError):
    """Raised when SEC refuses the request (403 or the interstitial page)."""


def _guidance(detail: str) -> str:
    return (
        f"SEC EDGAR refused this request ({detail}).\n"
        "This environment's egress IP is blocked by SEC's bot-manager — it is "
        "NOT a code bug. To pull SEC data, run the ingestion from an unblocked "
        "network (a normal residential connection, no datacenter VPN), e.g. a "
        "plain terminal on your Mac, and confirm https://www.sec.gov/ loads in "
        "your browser first. The User-Agent in use is:\n"
        f"    {USER_AGENT}\n"
        "Override it with SEC_EDGAR_UA in a .env file at the repo root."
    )


def edgar_get(url: str, *, params: dict | None = None, timeout: int = 60,
              max_retries: int = 4) -> requests.Response:
    """GET a SEC URL with compliant headers, rate limiting and block detection.

    Returns the Response on success; raises :class:`EdgarBlocked` if SEC
    refuses, or the underlying requests exception on network failure.
    """
    global _last_request_ts
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Accept": "application/json, text/html, application/xml;q=0.9, */*;q=0.8",
    }
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        wait = _MIN_INTERVAL - (time.monotonic() - _last_request_ts)
        if wait > 0:
            time.sleep(wait)
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        except requests.RequestException as exc:  # transient network error
            last_exc = exc
            time.sleep(1.5 * (attempt + 1))
            continue
        finally:
            _last_request_ts = time.monotonic()

        if resp.status_code == 403:
            raise EdgarBlocked(_guidance("HTTP 403"))
        if resp.status_code in (429, 503):  # rate-limited / unavailable: back off
            time.sleep(2.0 * (attempt + 1))
            last_exc = EdgarBlocked(_guidance(f"HTTP {resp.status_code}"))
            continue
        if _BLOCK_MARKER in resp.text[:2000]:
            raise EdgarBlocked(_guidance("undeclared-automated-tool interstitial"))
        resp.raise_for_status()
        return resp

    if isinstance(last_exc, EdgarBlocked):
        raise last_exc
    raise EdgarBlocked(_guidance(f"exhausted {max_retries} retries: {last_exc}"))
