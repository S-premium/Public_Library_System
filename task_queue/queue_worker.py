"""
task_queue/queue_worker.py
--------------------------
Lightweight in-process background task queue.
Uses Python's built-in threading + queue — NO Redis, NO Celery, no extra deps.

Usage:
    from task_queue import enqueue

    # Fire-and-forget: enqueue any callable with args/kwargs
    enqueue(send_otp_email, to_email, otp)
    enqueue(notify_admins_new_registration, firstname, lastname, email)

The HTTP response returns immediately; the task runs in a background thread.

Worker pool: 4 threads (configurable via QUEUE_WORKERS env var).
Queue capacity: 500 tasks (configurable via QUEUE_MAX_SIZE env var).
On overflow: task is executed synchronously so nothing is ever dropped.
"""

import os
import queue
import threading
import traceback
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────
_WORKER_COUNT = int(os.getenv("QUEUE_WORKERS", 4))
_MAX_QUEUE_SIZE = int(os.getenv("QUEUE_MAX_SIZE", 500))

# ── The shared queue ───────────────────────────────────────────────────────────
task_queue: queue.Queue = queue.Queue(maxsize=_MAX_QUEUE_SIZE)

# ── Stats (thread-safe counters) ───────────────────────────────────────────────
_stats_lock = threading.Lock()
_stats = {
    "enqueued": 0,
    "completed": 0,
    "failed": 0,
    "sync_fallbacks": 0,  # tasks run synchronously because queue was full
}


def get_stats() -> dict:
    """Return a snapshot of queue stats (safe to call from any thread)."""
    with _stats_lock:
        return dict(_stats)


# ── Worker loop ────────────────────────────────────────────────────────────────

def _worker():
    """Runs forever in a daemon thread, pulling tasks off the queue."""
    while True:
        task = task_queue.get()
        if task is None:          # poison pill — stop this worker
            task_queue.task_done()
            break

        fn, args, kwargs, label = task
        try:
            fn(*args, **kwargs)
            with _stats_lock:
                _stats["completed"] += 1
            logger.debug("[TaskQueue] ✓ %s", label)
        except Exception:
            with _stats_lock:
                _stats["failed"] += 1
            logger.error(
                "[TaskQueue] ✗ %s failed:\n%s", label, traceback.format_exc()
            )
        finally:
            task_queue.task_done()


# ── Start worker pool ──────────────────────────────────────────────────────────

def _start_workers(n: int = _WORKER_COUNT):
    for i in range(n):
        t = threading.Thread(target=_worker, name=f"TaskQueue-{i+1}", daemon=True)
        t.start()
    logger.info("[TaskQueue] Started %d worker thread(s).", n)


# Start workers immediately when this module is imported.
# daemon=True ensures they don't block process shutdown.
_start_workers()


# ── Public API ─────────────────────────────────────────────────────────────────

def enqueue(fn, *args, **kwargs):
    """
    Schedule `fn(*args, **kwargs)` to run in a background worker thread.

    If the queue is full, the task is executed synchronously in the calling
    thread (so nothing is ever silently dropped) and a warning is logged.

    Parameters
    ----------
    fn       : callable — the function to run
    *args    : positional arguments forwarded to fn
    **kwargs : keyword arguments forwarded to fn
    """
    label = getattr(fn, "__name__", repr(fn))
    item = (fn, args, kwargs, label)

    with _stats_lock:
        _stats["enqueued"] += 1

    try:
        task_queue.put_nowait(item)
        logger.debug("[TaskQueue] Queued: %s", label)
    except queue.Full:
        # Queue is at capacity — run synchronously so the task isn't lost.
        with _stats_lock:
            _stats["sync_fallbacks"] += 1
        logger.warning(
            "[TaskQueue] Queue full! Running %s synchronously.", label
        )
        try:
            fn(*args, **kwargs)
            with _stats_lock:
                _stats["completed"] += 1
        except Exception:
            with _stats_lock:
                _stats["failed"] += 1
            logger.error(
                "[TaskQueue] Sync fallback for %s failed:\n%s",
                label, traceback.format_exc()
            )