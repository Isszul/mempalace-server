import asyncio

_update_event: asyncio.Event = asyncio.Event()


def signal_update() -> None:
    """Signal all SSE clients that palace data has changed."""
    _update_event.set()


def get_event() -> asyncio.Event:
    return _update_event
