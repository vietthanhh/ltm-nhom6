"""
VAI TRÒ 1 — Giao diện (GUI)
Phụ trách: Tô Lâm Mộc 
"""
import sys
import os
import time
import uuid

# Thêm đường dẫn thư mục gốc dự án để import module common
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QLabel,
    QMessageBox, QAbstractItemView
)

# Import struct Task chuẩn từ common/task.py
from Code.common.task import Task

class ProgressSignal(QWidget):
    # Signal cập nhật tiến trình an toàn giữa các Thread: (task_id, status, percent, speed)
    progress_updated = pyqtSignal(str, str, float, str)

class MainWindow(QMainWindow):
    def __init__(self, is_mock_mode=True):
        super().__init__()
        self.is_mock_mode = is_mock_mode
        self.setWindowTitle("UDM_11 - Multi File Downloader (Role 1 - GUI)")
        self.resize(1100, 600)

        # Quản lý ánh xạ task_id -> dòng trên Bảng Download (Khu vực 2)
        self.task_row_map = {} 

        # Signal cập nhật UI Thread
        self.signals = ProgressSignal()
        self.signals.progress_updated.connect(self.on_progress)

        self.init_ui()

        # Gọi danh sách file từ Server khi mở ứng dụng
        self.load_server_files()

    def init_ui(self):
        main_layout = QHBoxLayout()

       