"""Offline triage of request observations from two own accounts.

Only local analysis of already collected HAR-like observations. No network,
no real credentials, no real responses, no verdict. Every result is a
hypothesis requiring manual verification on own synthetic data and own
accounts, compliant with the program scope.

Inspired by `nasktriage` from branch Gemma-konkurs/arena/c4eeb067-gemma-konkurs
and aligned with `nask/lab/auth_matrix.py`: shared access to a shared resource
is not IDOR by itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Sequence

TOKEN_PARAM_NAMES = {
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "apikey",
    "key",
    "secret",
    "session",
    "sessionid",
    "session_id",
    "authorization",
    "jwt",
    "id_token",
}

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
HEX_LONG_RE = re.compile(r"^[0-9a-fA-F]{16,}$")
BASE64_LONG_RE = re.compile(r"^[A-Za-z0-9+/=]{24,}$")
NUMERIC_ID_RE = re.compile(r"^\d{4,}$")


def normalize_template(path: str) -> str:
    """Replace likely identifier segments with {id} for grouping endpoints.

    Not a security decision. Public numeric identifiers may also be normalized;
    the analyst must verify the business meaning before any report.
    """
    parts = path.strip("/").split("/")
    out = []
    for part in parts:
        if UUID_RE.match(part) or HEX_LONG_RE.match(part) or BASE64_LONG_RE.match(part) or NUMERIC_ID_RE.match(part):
            out.append("{id}")
        else:
            out.append(part)
    return "/" + "/".join(out)


def has_token_param(url: str, extra: Sequence[str] = ()) -> bool:
    names = TOKEN_PARAM_NAMES | set(extra)
    query = url.split("?", 1)[-1] if "?" in url else ""
    for pair in query.split("&"):
        if "=" in pair:
            name = pair.split("=", 1)[0].lower()
            if name in names:
                return True
        elif pair.lower() in names:
            return True
    return False


@dataclass
class Observation:
    method: str
    url: str
    template: str
    status: int
    account: str | None = None  # None = anonymous/no session cookie
    json_keys: tuple[str, ...] = field(default_factory=tuple)
    cache_control: str | None = None
    has_cookie: bool = False
    body_size: int | None = None

    def __post_init__(self) -> None:
        if type(self.status) is not int or not 100 <= self.status <= 599:
            raise ValueError("status must be int 100-599")
        self.method = self.method.upper()


@dataclass
class Finding:
    kind: str
    template: str
    method: str
    accounts: tuple[str, ...]
    statuses: tuple[int, ...]
    detail: str
    evidence_sample: tuple[str, ...] = field(default_factory=tuple)
    severity_hypothesis: str = "hipoteza_do_weryfikacji"


def analyze(
    observations: Iterable[Observation],
    *,
    scope_hosts: Sequence[str] | None = None,
    token_param_names: Sequence[str] = (),
) -> list[Finding]:
    if scope_hosts is not None:
        allowed = {h.lower() for h in scope_hosts}
        observations = [o for o in observations if _host(o.url).lower() in allowed]

    obs = list(observations)
    findings: list[Finding] = []

    # 1. Permission asymmetry: same template, one account 2xx, another 401/403.
    by_template: dict[tuple[str, str], dict[str, list[int]]] = {}
    for o in obs:
        if o.account is None:
            continue
        by_template.setdefault((o.template, o.method), {}).setdefault(o.account, []).append(o.status)

    for (template, method), per_account in by_template.items():
        statuses_2xx = {a for a, sts in per_account.items() if any(200 <= s < 300 for s in sts)}
        statuses_denied = {a for a, sts in per_account.items() if any(s in (401, 403) for s in sts)}
        if statuses_2xx and statuses_denied and (statuses_2xx & statuses_denied):
            accounts = tuple(sorted(statuses_2xx | statuses_denied))
            statuses = tuple(sorted({s for a in accounts for s in per_account[a]}))
            findings.append(
                Finding(
                    kind="permission_asymmetry",
                    template=template,
                    method=method,
                    accounts=accounts,
                    statuses=statuses,
                    detail=(
                        "ten sam endpoint: jedno konto dostaje 2xx, drugie 401/403 — "
                        "sprawdź, czy to celowe różnicowanie uprawnień, a nie błąd"
                    ),
                    evidence_sample=tuple(f"{a}: {sorted(set(per_account[a]))}" for a in accounts),
                )
            )

    # 2. IDOR candidate: identifier endpoint returns 2xx for multiple IDs with
    # identical JSON key shape. Same account first; cross-account same ID is
    # already covered by permission asymmetry when statuses differ.
    by_template_id: dict[tuple[str, str], dict[str, dict[str, tuple[str, ...]]]] = {}
    for o in obs:
        if "{id}" not in o.template or o.account is None:
            continue
        # Use the original identifier segment if present; otherwise fall back to
        # the last path segment for grouping, without trusting it.
        ident = o.url.rstrip("/").split("/")[-1] if "/" in o.url else o.url
        by_template_id.setdefault((o.template, o.method), {}).setdefault(o.account, {})[ident] = o.json_keys

    for (template, method), per_account in by_template_id.items():
        for account, by_id in per_account.items():
            if len(by_id) < 2:
                continue
            shapes = {keys for keys in by_id.values()}
            if all(200 <= s < 300 for s in _statuses_for(obs, template, method, account)) and len(shapes) == 1:
                ids = tuple(sorted(by_id))[:5]
                findings.append(
                    Finding(
                        kind="idor_candidate",
                        template=template,
                        method=method,
                        accounts=(account,),
                        statuses=(200,),
                        detail=(
                            f"{len(by_id)} różnych identyfikatorów zwraca 2xx z identycznym kształtem JSON — "
                            "sprawdź dostęp do cudzych zasobów na własnych danych testowych"
                        ),
                        evidence_sample=ids,
                    )
                )

    # 3. Token/key/session in URL.
    for o in obs:
        if has_token_param(o.url, token_param_names):
            findings.append(
                Finding(
                    kind="token_in_url",
                    template=o.template,
                    method=o.method,
                    accounts=(o.account or "anonymous",),
                    statuses=(o.status,),
                    detail="parametr nazywa się jak token/klucz/sesja — może wyciekać w logach i Referer",
                    evidence_sample=(o.url,),
                )
            )

    # 4. Unauthenticated access to endpoint also seen by an account.
    anonymous_by_template: dict[tuple[str, str], list[int]] = {}
    for o in obs:
        if o.account is None:
            anonymous_by_template.setdefault((o.template, o.method), []).append(o.status)

    for (template, method), anon_statuses in anonymous_by_template.items():
        if any(200 <= s < 300 for s in anon_statuses):
            authenticated = {
                (o.template, o.method)
                for o in obs
                if o.account is not None and o.template == template and o.method == method
            }
            if (template, method) in authenticated:
                findings.append(
                    Finding(
                        kind="unauth_access",
                        template=template,
                        method=method,
                        accounts=("anonymous",),
                        statuses=tuple(sorted(set(anon_statuses))),
                        detail="żądanie bez ciasteczka dostało 2xx na endpoincie widzianym też przez konto",
                        evidence_sample=tuple(f"anonimowo: {s}" for s in sorted(set(anon_statuses))),
                    )
                )

    # 5. Publicly cacheable sensitive response.
    for o in obs:
        if 200 <= o.status < 300 and o.cache_control and "public" in o.cache_control.lower():
            findings.append(
                Finding(
                    kind="sensitive_cached",
                    template=o.template,
                    method=o.method,
                    accounts=(o.account or "anonymous",),
                    statuses=(o.status,),
                    detail="JSON lub Set-Cookie oznaczony jako publicznie cache'owalny",
                    evidence_sample=(o.cache_control or "",),
                )
            )

    return findings


def _statuses_for(obs: Sequence[Observation], template: str, method: str, account: str) -> list[int]:
    return [o.status for o in obs if o.template == template and o.method == method and o.account == account]


def _host(url: str) -> str:
    return url.split("://", 1)[-1].split("/", 1)[0].split("?", 1)[0]
