"""Single-use WebSocket tickets.

Browsers can't set an Authorization header on a WebSocket, and a long-lived
token in a URL ends up in logs. So an authenticated REST call issues a random
ticket that is valid for 30 seconds and can be used once.
"""

import time
from threading import Lock

from app.core.security import digest, new_opaque_token

TICKET_TTL_SECONDS = 30


class TicketStore:
    def __init__(self) -> None:
        self._tickets: dict[str, tuple[int, float]] = {}
        self._lock = Lock()

    def issue(self, user_id: int) -> str:
        ticket = new_opaque_token()
        now = time.monotonic()
        with self._lock:
            self._tickets = {k: v for k, v in self._tickets.items() if v[1] > now}
            self._tickets[digest(ticket)] = (user_id, now + TICKET_TTL_SECONDS)
        return ticket

    def redeem(self, ticket: str) -> int | None:
        with self._lock:
            entry = self._tickets.pop(digest(ticket), None)
        if entry is None or entry[1] < time.monotonic():
            return None
        return entry[0]


tickets = TicketStore()
