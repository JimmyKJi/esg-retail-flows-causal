"""Shared HTTP layer for all SEC EDGAR pulls.

SEC requires every automated client to (a) send a descriptive User-Agent of
the form ``Name email`` and (b) stay under ~10 requests/second. This module
centralises both, plus retry/backoff, and — importantly — turns SEC's two
block responses into one clear, actionable exception:

  * HTTP 403 (Akamai WAF), and
  * HTTP 200 whose body is the "Your Request Originates from an Undeclared
    Automated Tool" interstitial,

are both raised as :class:`EdgarBlocked` with guidance. SEC's bot-manager blocks
datacenter / VPN / proxy IPs wholesale, so the most common cause of a block on an
otherwise-correct setup is an **active VPN**. (Confirmed in development: this
environment egresses through a Datacamp/Dublin datacenter IP, flagged proxy +
hosting, which SEC 403s across every host, User-Agent and TLS fingerprint.)
:func:`_egress_diagnosis` checks the live egress IP and, when it looks like a
datacenter network, says so — so the failure explains itself instead of looking
like a code bug.

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

# SEC mandates a "Name email" UA with a *real, contactable* address. SEC's filter
# rejects non-deliverable domains — notably `noreply.github.com`-style addresses
# return the "Undeclared Automated Tool" 403 (learned the hard way). Set your own
# contact in a gitignored .env (SEC_EDGAR_UA=...); this default is deliberately
# unusable so a missing .env fails closed rather than sending a fake contact.
_DEFAULT_UA = "UNSET - declare SEC_EDGAR_UA in .env as: Your Name your-real-contact-email"
USER_AGENT = os.environ.get("SEC_EDGAR_UA", _DEFAULT_UA)

_MIN_INTERVAL = 0.15  # seconds between requests => ~6.7/s, under SEC's 10/s cap
_last_request_ts = 0.0

_BLOCK_MARKER = "Undeclared Automated Tool"


class EdgarBlocked(RuntimeError):
    """Raised when SEC refuses the request (403 or the interstitial page)."""


_egress_hint: str | None = None  # computed once per process, best-effort


def _egress_diagnosis() -> str:
    """Best-effort one-liner naming the egress IP and flagging VPN/datacenter.

    SEC blocks datacenter / VPN / proxy IPs wholesale, so an active VPN is the
    single most common cause of a block on a correct setup. Looks the current
    egress IP up once and caches it. Never raises — a diagnosis must not mask
    the original error — and returns "" if the lookup is unavailable.
    """
    global _egress_hint
    if _egress_hint is not None:
        return _egress_hint
    try:
        import json
        import urllib.request

        url = "http://ip-api.com/json/?fields=query,country,isp,proxy,hosting"
        with urllib.request.urlopen(url, timeout=3) as r:
            d = json.loads(r.read())
        ip, isp, ctry = d.get("query", "?"), d.get("isp", "?"), d.get("country", "?")
        if d.get("proxy") or d.get("hosting"):
            _egress_hint = (
                f"\n>> Your egress IP {ip} ({isp}, {ctry}) is flagged as a "
                "datacenter / VPN / proxy network, which SEC blocks wholesale. "
                "This is almost certainly the cause: turn off any VPN and retry, "
                "confirming the IP changes to your residential ISP."
            )
        else:
            _egress_hint = (
                f"\n>> Egress IP {ip} ({isp}, {ctry}) does not look like a "
                "datacenter, so a VPN is probably not the cause — suspect the "
                "User-Agent or a transient SEC rate penalty (wait, then retry)."
            )
    except Exception:
        _egress_hint = ""
    return _egress_hint


def _guidance(detail: str) -> str:
    return (
        f"SEC EDGAR refused this request ({detail}).\n"
        "This is NOT a code bug — SEC's bot-manager refused the connection. To "
        "pull SEC data, run the ingestion from an unblocked network (a normal "
        "residential connection, no datacenter VPN), e.g. a plain terminal on "
        "your Mac, and confirm https://www.sec.gov/ loads in your browser first. "
        "The User-Agent in use is:\n"
        f"    {USER_AGENT}\n"
        "Override it with SEC_EDGAR_UA in a .env file at the repo root. Note SEC "
        "rejects non-deliverable contacts: a 'Name email' UA with a real address "
        "(e.g. you@gmail.com) works; noreply/github.com-style addresses 403."
        f"{_egress_diagnosis()}"
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
