"""
VAI TRÒ 3 — Quản lý hàng đợi (Concurrency)
Phụ trách: Lê Minh Hiền
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Callable, Optional

from Code.common.constants import MAX_CONCURRENT
from Code.common.task import Task


class QueueManager:
    def __init__(
        self,
        download_func: Optional[Callable] = None,
        progress_tracker=None
    ):
        self.tasks = {}
        self.running_tasks = set()
        self.lock = Lock()
        self.executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT)
        self.download_func = download_func
        self.progress_tracker = progress_tracker
        self.is_shutdown = False

    def add_task(self, task: Task) -> bool:
        with self.lock:
            if self.is_shutdown or task.task_id in self.tasks:
                return False

            task.status = "Waiting"
            task.percent = 0
            task.speed = ""
            self.tasks[task.task_id] = task

        self._notify(task, True)
        self._dispatch_tasks()
        return True

    def add_tasks(self, tasks: list[Task]) -> int:
        count = 0
        for task in tasks:
            if self.add_task(task):
                count += 1
        return count

    def get_task(self, task_id: str) -> Optional[Task]:
        with self.lock:
            return self.tasks.get(task_id)

    def get_all_tasks(self) -> list[Task]:
        with self.lock:
            return list(self.tasks.values())

    def get_waiting_tasks(self) -> list[Task]:
        with self.lock:
            return [
                task for task in self.tasks.values()
                if task.status == "Waiting"
            ]

    def get_downloading_tasks(self) -> list[Task]:
        with self.lock:
            return [
                task for task in self.tasks.values()
                if task.status == "Downloading"
            ]

    def get_available_slots(self) -> int:
        with self.lock:
            return max(0, MAX_CONCURRENT - len(self.running_tasks))

    def _dispatch_tasks(self):
        tasks_to_start = []

        with self.lock:
            if self.is_shutdown:
                return

            slots = MAX_CONCURRENT - len(self.running_tasks)

            if slots <= 0:
                return

            waiting_tasks = [
                task for task in self.tasks.values()
                if task.status == "Waiting"
            ]

            for task in waiting_tasks[:slots]:
                task.status = "Downloading"
                task.percent = max(0, min(100, task.percent))
                self.running_tasks.add(task.task_id)
                tasks_to_start.append(task)

        for task in tasks_to_start:
            self._notify(task, True)
            self.executor.submit(self._run_task, task)

    def _run_task(self, task: Task):
        try:
            if self.download_func is None:
                raise RuntimeError(
                    "Chưa cung cấp download_func từ network_client.py"
                )

            def progress_callback(percent: int, speed: str = ""):
                with self.lock:
                    current_task = self.tasks.get(task.task_id)

                    if current_task is None:
                        return

                    current_task.percent = max(
                        0, min(100, int(percent))
                    )

                    if speed:
                        current_task.speed = speed

                self._notify(task)

            self.download_func(task, progress_callback)

            with self.lock:
                current_task = self.tasks.get(task.task_id)

                if current_task:
                    current_task.percent = 100
                    current_task.status = "Completed"
                    current_task.speed = "Done"

        except Exception as e:
            with self.lock:
                current_task = self.tasks.get(task.task_id)

                if current_task:
                    current_task.status = "Failed"
                    current_task.speed = ""

            print(f"[FAILED] {task.filename}: {e}")

        finally:
            with self.lock:
                self.running_tasks.discard(task.task_id)
                finished_task = self.tasks.get(task.task_id)

            if finished_task:
                self._notify(finished_task, True)

            self._dispatch_tasks()

    def _notify(self, task: Task, force: bool = False):
        if self.progress_tracker is None:
            return

        try:
            self.progress_tracker.notify(task, force=force)
        except Exception as e:
            print(f"[ProgressTracker ERROR] {task.task_id}: {e}")

    def remove_task(self, task_id: str) -> bool:
        with self.lock:
            if task_id not in self.tasks:
                return False

            if task_id in self.running_tasks:
                return False

            del self.tasks[task_id]

        if self.progress_tracker:
            try:
                self.progress_tracker.remove_task(task_id)
            except Exception:
                pass

        return True

    def clear_finished(self) -> int:
        removed = []

        with self.lock:
            for task_id, task in list(self.tasks.items()):
                if (
                    task.status in ("Completed", "Failed", "Cancelled")
                    and task_id not in self.running_tasks
                ):
                    removed.append(task_id)

            for task_id in removed:
                del self.tasks[task_id]

        if self.progress_tracker:
            for task_id in removed:
                try:
                    self.progress_tracker.remove_task(task_id)
                except Exception:
                    pass

        return len(removed)

    def shutdown(self):
        with self.lock:
            if self.is_shutdown:
                return

            self.is_shutdown = True

        self.executor.shutdown(wait=True)
