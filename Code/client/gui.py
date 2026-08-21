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

        # ==================== KHU VỰC 1: DANH SÁCH FILE TRÊN SERVER ====================
        server_box = QVBoxLayout()
        server_label = QLabel("<b>Khu vực 1: Danh sách file trên Server</b>")
        
        self.server_table = QTableWidget(0, 2)
        self.server_table.setHorizontalHeaderLabels(["Tên File", "Kích Thước (Bytes)"])
        self.server_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.server_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.server_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)  # Cho phép chọn 1 hoặc nhiều file
        self.server_table.setDragEnabled(True)  # Bật tính năng KÉO (Drag)

        server_box.addWidget(server_label)
        server_box.addWidget(self.server_table)

        # ==================== KHU VỰC 2: KHU VỰC DOWNLOAD ====================
        download_box = QVBoxLayout()
        download_label = QLabel("<b>Khu vực 2: Tiến Trình Download (Kéo file vào đây)</b>")
        
        self.download_table = QTableWidget(0, 5)
        self.download_table.setHorizontalHeaderLabels(["Task ID", "Tên File Đích", "Tiến Trình (%)", "Tốc Độ", "Trạng Thái"])
        self.download_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.download_table.setAcceptDrops(True)  # Bật tính năng THẢ (Drop)
        
        # Override sự kiện Drag & Drop
        self.download_table.dragEnterEvent = self.dragEnterEvent
        self.download_table.dragMoveEvent = self.dragMoveEvent
        self.download_table.dropEvent = self.dropEvent

        download_box.addWidget(download_label)
        download_box.addWidget(self.download_table)

        # Bố cục 2 khu vực (Tỷ lệ 40% - 60%)
        main_layout.addLayout(server_box, 40)
        main_layout.addLayout(download_box, 60)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    # ==================== CHỨC NĂNG 1: GỌI get_file_list() ====================
    def load_server_files(self):
        try:
            if self.is_mock_mode:
                # Dữ liệu giả lập khi chạy kiểm thử độc lập
                file_list = [
                    {"filename": "doc 1.docx", "size": 204800},
                    {"filename": "report.txt", "size": 1048576},
                    {"filename": "data.zip", "size": 5242880},
                    {"filename": "image.png", "size": 3145728},
                ]
            else:
                # Ghép nối với Vai trò 2 khi tích hợp thật
                from Code.client.network_client import get_file_list
                file_list = get_file_list()

            self.server_table.setRowCount(0)
            for row, f in enumerate(file_list):
                self.server_table.insertRow(row)
                self.server_table.setItem(row, 0, QTableWidgetItem(f["filename"]))
                self.server_table.setItem(row, 1, QTableWidgetItem(str(f["size"])))

        except Exception as e:
            # Hiển thị popup thông báo lỗi rõ ràng nếu kết nối Server thất bại
            QMessageBox.critical(
                self, 
                "Lỗi Kết Nối Server", 
                f"Không thể lấy danh sách file từ Server!\nChi tiết: {str(e)}"
            )

   

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(is_mock_mode=True)
    window.show()
    sys.exit(app.exec())