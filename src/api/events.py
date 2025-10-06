# src/api/events.py
import asyncio
import json
from collections import defaultdict
from typing import Dict, Set

# src/api/events.py
class EventHub:
    def __init__(self):
        self._subs: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
        self._last: Dict[str, dict] = {}  # <- remember last event

    def subscribe(self, key: str) -> asyncio.Queue:
        q = asyncio.Queue(maxsize=100)
        self._subs[key].add(q)
        return q

    def unsubscribe(self, key: str, q: asyncio.Queue) -> None:
        subs = self._subs.get(key)
        if subs and q in subs:
            subs.remove(q)
            if not subs:
                self._subs.pop(key, None)
                self._last.pop(key, None)

    async def publish(self, key: str, event: dict) -> None:
        self._last[key] = event            # <- store last
        for q in list(self._subs.get(key, ())):
            try: q.put_nowait(event)
            except asyncio.QueueFull: pass

    def last(self, key: str) -> dict | None:
        return self._last.get(key)


hub = EventHub()

def sse_format(data: dict) -> str:
    # keep it simple: only data lines
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
