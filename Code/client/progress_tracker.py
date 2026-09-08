"""
VAI TRÒ 3 — Quản lý hàng đợi (Concurrency)
Phụ trách: Lê Minh Hiền
"""
from collections import deque
from dataclasses import replace
from threading import Lock
import time

from Code.common.task import Task


MIN_UPDATE_INTERVAL_SEC = 0.15
TERMINAL_STATUSES = ("Completed", "Failed", "Cancelled")


def format_speed(bytes_per_sec: float) -> str:
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.0f} B/s"

    if bytes_per_sec < 1024 * 1024:
        return f"{bytes_per_sec / 1024:.1f} KB/s"

    return f"{bytes_per_sec / (1024 * 1024):.2f} MB/s"


class TaskState:
    def __init__(self):
        self.last_emit_time = time.monotonic() - MIN_UPDATE_INTERVAL_SEC
        self.last_status = None
        self.last_bytes = 0.0
        self.last_time = time.monotonic()


class ProgressTracker:
    def __init__(self):
        self.lock = Lock()
        self.states = {}
        self.pending_updates = deque()

    def notify(self, task: Task, force: bool = False):
        with self.lock:
            state = self.states.setdefault(
                task.task_id,
                TaskState()
            )

            now = time.monotonic()

            current_bytes = (
                task.size * task.percent / 100.0
                if task.size
                else 0.0
            )

            elapsed = now - state.last_time
            speed = 0.0

            if elapsed > 0 and task.status == "Downloading":
                speed = max(
                    (current_bytes - state.last_bytes) / elapsed,
                    0.0
                )

            state.last_bytes = current_bytes
            state.last_time = now

            status_changed = task.status != state.last_status
            terminal = task.status in TERMINAL_STATUSES

            if (
                not force
                and not status_changed
                and not terminal
                and now - state.last_emit_time < MIN_UPDATE_INTERVAL_SEC
            ):
                return

            state.last_emit_time = now
            state.last_status = task.status

            if task.status == "Downloading":
                speed_text = format_speed(speed)
            elif task.status == "Completed":
                speed_text = "Done"
            else:
                speed_text = ""

            snapshot = replace(
                task,
                speed=speed_text
            )

            self.pending_updates.append(snapshot)

    def poll_updates(self) -> list[Task]:
        with self.lock:
            updates = list(self.pending_updates)
            self.pending_updates.clear()

        return updates

    def get_updates(self) -> list[Task]:
        return self.poll_updates()

    def remove_task(self, task_id: str):
        with self.lock:
            self.states.pop(task_id, None)

    def clear(self):
        with self.lock:
            self.states.clear()
            self.pending_updates.clear()
