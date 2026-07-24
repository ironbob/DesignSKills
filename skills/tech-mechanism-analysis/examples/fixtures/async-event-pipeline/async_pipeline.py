from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json


@dataclass(frozen=True)
class Event:
    sequence: int
    payload: str


async def produce(payloads: list[str], queue: asyncio.Queue[Event | None]) -> None:
    for sequence, payload in enumerate(payloads):
        await queue.put(Event(sequence=sequence, payload=payload))
    await queue.put(None)


async def transform(
    source: asyncio.Queue[Event | None],
    target: asyncio.Queue[Event | None],
) -> None:
    while True:
        event = await source.get()
        if event is None:
            await target.put(None)
            return
        await asyncio.sleep(0)
        await target.put(Event(event.sequence, event.payload.upper()))


async def collect(queue: asyncio.Queue[Event | None]) -> list[str]:
    results: list[Event] = []
    while True:
        event = await queue.get()
        if event is None:
            return [item.payload for item in sorted(results, key=lambda item: item.sequence)]
        results.append(event)


async def run_pipeline(payloads: list[str]) -> list[str]:
    incoming: asyncio.Queue[Event | None] = asyncio.Queue()
    outgoing: asyncio.Queue[Event | None] = asyncio.Queue()
    producer = asyncio.create_task(produce(payloads, incoming))
    worker = asyncio.create_task(transform(incoming, outgoing))
    sink = asyncio.create_task(collect(outgoing))
    await asyncio.gather(producer, worker)
    return await sink


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run_pipeline(["alpha", "beta"]))))
