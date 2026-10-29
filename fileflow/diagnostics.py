"""Bounded structured events with opt-in JSONL output. Never log file paths/contents."""
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
import json
import threading
events = deque(maxlen=1000)
_lock = threading.Lock()
_path = None
def configure(path=None):
    global _path
    with _lock: _path = Path(path) if path else None
def event(name, **fields):
    record = dict(time=datetime.now(timezone.utc).isoformat(timespec='milliseconds'), event=name,
                  thread=threading.current_thread().name, thread_id=threading.get_ident(), **fields)
    with _lock:
        events.append(record)
        if _path:
            try:
                with _path.open('a', encoding='utf-8') as stream: stream.write(json.dumps(record) + '\n')
            except OSError as error:
                events.append(dict(event='diagnostic_write_failed', error=type(error).__name__, errno=error.errno))
    return record
