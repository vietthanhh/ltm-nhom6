"""
VAI TRÒ 3 — Quản lý hàng đợi (Concurrency)
Phụ trách: Lê Minh Hiền
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import time

from common.constants import MAX_CONCURRENT
from common.task import Task


class ProgressTracker:
    def __init__(self):
        self.tasks = {}

        self.executor = ThreadPoolExecutor(
            max_workers=MAX_CONCURRENT
        )

        self.lock = Lock()

    def add_task(self, task: Task):
        with self.lock:
            task.status = "Waiting"
            task.percent = 0
            self.tasks[task.task_id] = task

    def get_task(self, task_id: str):
        with self.lock:
            return self.tasks.get(task_id)

    def get_all_tasks(self):
        with self.lock:
            return list(self.tasks.values())

    def update_status(self, task_id: str, status: str):
        with self.lock:
            task = self.tasks.get(task_id)

            if task is None:
                return False

            task.status = status
            return True

    def update_progress(self, task_id: str, percent: int):
        with self.lock:
            task = self.tasks.get(task_id)

            if task is None:
                return False

            percent = max(0, min(100, percent))
            task.percent = percent

            if percent >= 100:
                task.status = "Completed"

            return True

    def get_waiting_tasks(self):
        with self.lock:
            return [
                task
                for task in self.tasks.values()
                if task.status == "Waiting"
            ]

    def get_downloading_tasks(self):
        with self.lock:
            return [
                task
                for task in self.tasks.values()
                if task.status == "Downloading"
            ]

    def remove_task(self, task_id: str):
        with self.lock:
            if task_id not in self.tasks:
                return False

            del self.tasks[task_id]
            return True

    def run_test_task(self, task_id: str, seconds: int = 3):
        with self.lock:
            task = self.tasks.get(task_id)

            if task is None:
                return

            task.status = "Downloading"

        print(f"[START] {task_id}")

        time.sleep(seconds)

        self.update_progress(task_id, 100)

        print(f"[DONE] {task_id}")

    def start_test_tasks(self):
        waiting_tasks = self.get_waiting_tasks()

        for task in waiting_tasks:
            self.executor.submit(
                self.run_test_task,
                task.task_id
            )

    def shutdown(self):
        self.executor.shutdown(wait=True)
