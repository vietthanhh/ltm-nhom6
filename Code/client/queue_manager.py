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
        self.tasks: dict[str, Task] = {}
        self.running_tasks: set[str] = set()
        self.lock = Lock()

        self.executor = ThreadPoolExecutor(
            max_workers=MAX_CONCURRENT
        )

        self.download_func = download_func
        self.progress_tracker = progress_tracker
        self.is_shutdown = False

    def add_task(self, task: Task) -> bool:
        with self.lock:
            if self.is_shutdown:
                return False

            if task.task_id in self.tasks:
                return False

            task.status = "Waiting"
            task.percent = 0
            task.speed = ""

            self.tasks[task.task_id] = task

        self._notify(task, force=True)
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
                task
                for task in self.tasks.values()
                if task.status == "Waiting"
            ]

    def get_downloading_tasks(self) -> list[Task]:
        with self.lock:
            return [
                task
                for task in self.tasks.values()
                if task.status == "Downloading"
            ]

    def get_available_slots(self) -> int:
        with self.lock:
            return max(
                0,
                MAX_CONCURRENT - len(self.running_tasks)
            )

    def _dispatch_tasks(self):
        tasks_to_start = []

        with self.lock:
            if self.is_shutdown:
                return

            available_slots = (
                MAX_CONCURRENT
                - len(self.running_tasks)
            )

            if available_slots <= 0:
                return

            waiting_tasks = [
                task
                for task in self.tasks.values()
                if task.status == "Waiting"
            ]

            for task in waiting_tasks[:available_slots]:
                task.status = "Downloading"
                task.percent = max(
                    0,
                    min(100, task.percent)
                )

                self.running_tasks.add(
                    task.task_id
                )

                tasks_to_start.append(task)

        for task in tasks_to_start:
            self._notify(task, force=True)

            self.executor.submit(
                self._run_task,
                task
            )

    def _run_task(self, task: Task):
        try:
            if self.download_func is None:
                raise RuntimeError(
                    "Chưa cung cấp download_func từ network_client.py"
                )

            def progress_callback(
                percent: int,
                speed: str = ""
            ):
                with self.lock:
                    current_task = self.tasks.get(
                        task.task_id
                    )

                    if current_task is None:
                        return

                    current_task.percent = max(
                        0,
                        min(100, int(percent))
                    )

                    if speed:
                        current_task.speed = speed

                self._notify(task)

            self.download_func(
                task,
                progress_callback
            )

            with self.lock:
                current_task = self.tasks.get(
                    task.task_id
                )

                if current_task is not None:
                    current_task.percent = 100
                    current_task.status = "Completed"
                    current_task.speed = "Done"

        except Exception as e:
            with self.lock:
                current_task = self.tasks.get(
                    task.task_id
                )

                if current_task is not None:
                    current_task.status = "Failed"
                    current_task.speed = ""

                    print(
                        f"[FAILED] "
                        f"{current_task.filename}: {e}"
                    )

        finally:
            with self.lock:
                self.running_tasks.discard(
                    task.task_id
                )

                finished_task = self.tasks.get(
                    task.task_id
                )

            if finished_task is not None:
                self._notify(
                    finished_task,
                    force=True
                )

            self._dispatch_tasks()

    def _notify(
        self,
        task: Task,
        force: bool = False
    ):
        if self.progress_tracker is None:
            return

        try:
            self.progress_tracker.notify(
                task,
                force=force
            )
        except Exception as e:
            print(
                f"[ProgressTracker ERROR] "
                f"{task.task_id}: {e}"
            )

    def remove_task(
        self,
        task_id: str
    ) -> bool:
        with self.lock:
            if task_id not in self.tasks:
                return False

            if task_id in self.running_tasks:
                return False

            del self.tasks[task_id]

        if self.progress_tracker is not None:
            try:
                self.progress_tracker.remove_task(
                    task_id
                )
            except Exception:
                pass

        return True

    def clear_finished(self) -> int:
        removed_ids = []

        with self.lock:
            for task_id, task in list(
                self.tasks.items()
            ):
                if (
                    task.status
                    in (
                        "Completed",
                        "Failed",
                        "Cancelled"
                    )
                    and task_id
                    not in self.running_tasks
                ):
                    removed_ids.append(
                        task_id
                    )

            for task_id in removed_ids:
                del self.tasks[task_id]

        if self.progress_tracker is not None:
            for task_id in removed_ids:
                try:
                    self.progress_tracker.remove_task(
                        task_id
                    )
                except Exception:
                    pass

        return len(removed_ids)

    def shutdown(self):
        with self.lock:
            if self.is_shutdown:
                return

            self.is_shutdown = True

        self.executor.shutdown(
            wait=True
        )


if __name__ == "__main__":
    import time

    def fake_download(
        task: Task,
        progress_callback
    ):
        print(
            f"[START] {task.filename}"
        )

        for percent in range(0, 101, 10):
            time.sleep(0.2)

            progress_callback(
                percent,
                f"{percent * 10} KB/s"
            )

        print(
            f"[DONE] {task.filename}"
        )

    manager = QueueManager(
        download_func=fake_download
    )

    test_tasks = []

    for i in range(1, 9):
        task = Task(
            task_id=f"task-{i}",
            filename=f"file_{i}.txt",
            final_filename=f"file_{i}.txt",
            size=100000,
            status="Waiting"
        )

        test_tasks.append(task)

    manager.add_tasks(test_tasks)

    while True:
        time.sleep(0.5)

        all_tasks = manager.get_all_tasks()

        waiting = len(
            manager.get_waiting_tasks()
        )

        downloading = len(
            manager.get_downloading_tasks()
        )

        completed = sum(
            1
            for task in all_tasks
            if task.status == "Completed"
        )

        failed = sum(
            1
            for task in all_tasks
            if task.status == "Failed"
        )

        print(
            f"[QUEUE] "
            f"Waiting={waiting} | "
            f"Downloading={downloading} | "
            f"Completed={completed} | "
            f"Failed={failed}"
        )

        if completed + failed == len(all_tasks):
            break

    print("\nKET QUA:")

    for task in manager.get_all_tasks():
        print(
            f"{task.task_id:<10} | "
            f"{task.filename:<15} | "
            f"{task.status:<12} | "
            f"{task.percent}%"
        )

    manager.shutdown()

    print("\n[TEST] Hoan thanh.")
