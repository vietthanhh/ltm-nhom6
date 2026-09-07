"""
VAI TRÒ 4 — Progress & Trạng thái
Phụ trách: Phan Thanh Thu Ngân 
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import replace
from threading import Lock

from common.task import Task

MIN_UPDATE_INTERVAL_SEC = 0.15

_TERMINAL_STATUSES = ("Completed", "Failed", "Cancelled")


def format_speed(bytes_per_sec: float) -> str:
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.0f} B/s"
    elif bytes_per_sec < 1024 * 1024:
        return f"{bytes_per_sec / 1024:.1f} KB/s"
    else:
        return f"{bytes_per_sec / 1024 / 1024:.2f} MB/s"


class _TaskState:

    __slots__ = ("last_emit_time", "last_status", "last_bytes", "last_time")

    def __init__(self):
        self.last_emit_time = time.monotonic() - MIN_UPDATE_INTERVAL_SEC
        self.last_status = None
        self.last_bytes = 0.0
        self.last_time = time.monotonic()


class ProgressTracker:
    def __init__(self):
        self._lock = Lock()
        self._state: dict[str, _TaskState] = {}
        self._pending_queue: deque[Task] = deque()

    def notify(self, task: Task, force: bool = False) -> None:
        with self._lock:
            state = self._state.setdefault(task.task_id, _TaskState())

            now = time.monotonic()
            current_bytes = (task.size * task.percent / 100.0) if task.size else 0.0
            elapsed = now - state.last_time
            speed_bytes_per_sec = 0.0
            if elapsed > 0 and task.status == "Downloading":
                speed_bytes_per_sec = max((current_bytes - state.last_bytes) / elapsed, 0.0)
            state.last_bytes = current_bytes
            state.last_time = now

            status_changed = task.status != state.last_status
            is_terminal = task.status in _TERMINAL_STATUSES
            bypass_throttle = force or status_changed or is_terminal

            if not bypass_throttle and (now - state.last_emit_time) < MIN_UPDATE_INTERVAL_SEC:
                return
            state.last_emit_time = now
            state.last_status = task.status

            if task.status == "Downloading":
                speed_str = format_speed(speed_bytes_per_sec)
            elif task.status == "Completed":
                speed_str = "Done"
            else:
                speed_str = ""

            snapshot = replace(task, speed=speed_str)
            self._pending_queue.append(snapshot)

    def poll_updates(self) -> list[Task]:
        with self._lock:
            items = list(self._pending_queue)
            self._pending_queue.clear()
        return items

    def remove_task(self, task_id: str) -> None:
        """Don state khi task bi xoa khoi danh sach (vd: bam nut Clear)."""
        with self._lock:
            self._state.pop(task_id, None)


if __name__ == "__main__":
    import threading

    tracker = ProgressTracker()

    demo_task = Task(
        task_id="t1",
        filename="report.pdf",
        final_filename="report.pdf",
        size=1_000_000,
        status="Waiting",
    )

    def worker_thread_job():
        demo_task.status = "Downloading"
        tracker.notify(demo_task, force=True)
        for pct in range(0, 101, 10):
            demo_task.percent = pct
            if pct >= 100:
                demo_task.status = "Completed"
            tracker.notify(demo_task)
            time.sleep(0.05)

    t = threading.Thread(target=worker_thread_job)
    t.start()

    while t.is_alive():
        for task in tracker.poll_updates():
            print(f"[GUI] {task.task_id}: {task.status} {task.percent}% ({task.speed})")
        time.sleep(0.1)

    t.join()
    for task in tracker.poll_updates():
        print(f"[GUI] {task.task_id}: {task.status} {task.percent}% ({task.speed})")