"""
VAI TRÒ 3 - Quản lý hàng đợi (Concurrency)
Phụ trách: Lê Minh Hiền
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import time

from common.constants import MAX_CONCURRENT
from common.task import Task


class ProgressTracker:
    def __init__(self):
        # Lưu tất cả các task theo task_id
        self.tasks = {}

        # Thread Pool giới hạn số task chạy đồng thời
        self.executor = ThreadPoolExecutor(
            max_workers=MAX_CONCURRENT
        )

        # Khóa dữ liệu khi nhiều thread cùng truy cập
        self.lock = Lock()

    def add_task(self, task: Task):
        """
        Thêm task mới vào hàng đợi.
        Task mới sẽ có trạng thái Waiting.
        """

        with self.lock:
            task.status = "Waiting"
            task.percent = 0
            self.tasks[task.task_id] = task

    def get_task(self, task_id: str):
        """
        Lấy một task theo task_id.
        """

        with self.lock:
            return self.tasks.get(task_id)

    def get_all_tasks(self):
        """
        Lấy danh sách tất cả task.
        """

        with self.lock:
            return list(self.tasks.values())

    def update_status(self, task_id: str, status: str):
        """
        Cập nhật trạng thái của task.
        """

        with self.lock:
            task = self.tasks.get(task_id)

            if task is None:
                return False

            task.status = status
            return True

    def update_progress(self, task_id: str, percent: int):
        """
        Cập nhật phần trăm download của task.
        """

        with self.lock:
            task = self.tasks.get(task_id)

            if task is None:
                return False

            # Không cho percent nhỏ hơn 0 hoặc lớn hơn 100
            percent = max(0, min(100, percent))

            task.percent = percent

            # Download đạt 100% thì hoàn thành
            if percent >= 100:
                task.status = "Completed"

            return True

    def get_waiting_tasks(self):
        """
        Lấy tất cả task đang chờ.
        """

        with self.lock:
            return [
                task
                for task in self.tasks.values()
                if task.status == "Waiting"
            ]

    def get_downloading_tasks(self):
        """
        Lấy tất cả task đang download.
        """

        with self.lock:
            return [
                task
                for task in self.tasks.values()
                if task.status == "Downloading"
            ]

    def remove_task(self, task_id: str):
        """
        Xóa task khỏi danh sách.
        """

        with self.lock:
            if task_id not in self.tasks:
                return False

            del self.tasks[task_id]
            return True

    def run_test_task(self, task_id: str, seconds: int = 3):
        """
        Hàm giả lập download để kiểm tra Concurrency.

        Hàm này chỉ dùng trong giai đoạn test.
        Sau này network_client.py sẽ thực hiện download thật.
        """

        with self.lock:
            task = self.tasks.get(task_id)

            if task is None:
                return

            task.status = "Downloading"

        print(f"[START] {task_id}")

        # Giả lập thời gian download
        time.sleep(seconds)

        # Download hoàn thành
        self.update_progress(task_id, 100)

        print(f"[DONE] {task_id}")

    def start_test_tasks(self):
        """
        Chạy tất cả task đang Waiting.
        Dùng để kiểm tra ThreadPool.
        """

        waiting_tasks = self.get_waiting_tasks()

        for task in waiting_tasks:
            self.executor.submit(
                self.run_test_task,
                task.task_id
            )

    def shutdown(self):
        """
        Đóng ThreadPool khi chương trình kết thúc.
        """

        self.executor.shutdown(wait=True)