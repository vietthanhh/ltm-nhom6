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

    # ==================== CHỨC NĂNG 2: XỬ LÝ DRAG & DROP ====================
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        selected_items = self.server_table.selectedItems()
        if not selected_items:
            return

        # Lấy danh sách các dòng được chọn (Hỗ trợ kéo 1 hoặc nhiều file cùng lúc)
        selected_rows = sorted(list(set(item.row() for item in selected_items)))
        
        for row in selected_rows:
            filename = self.server_table.item(row, 0).text()
            size = int(self.server_table.item(row, 1).text())

            # 1. Gọi add_download_task() từ Vai trò 3
            task_id, final_filename = self.call_add_download_task(filename, size)

            # 2. Khởi tạo đối tượng Task (dùng struct Task)
            task_obj = Task(
                task_id=task_id,
                filename=filename,
                final_filename=final_filename,
                size=size,
                status="Waiting",
                percent=0,
                speed="0 KB/s"
            )

            # 3. Tạo dòng mới ở Khu vực 2 với trạng thái Waiting
            self.add_task_to_gui(task_obj)

            # 4. Kích hoạt tiến trình tải ngầm
            if self.is_mock_mode:
                self.run_mock_download(task_id)

        event.acceptProposedAction()

    # ==================== HIỂN THỊ DÒNG MỚI NÊN KHU VỰC 2 ====================
    def add_task_to_gui(self, task: Task):
        row = self.download_table.rowCount()
        self.download_table.insertRow(row)

        # Cột 0: Task ID
        self.download_table.setItem(row, 0, QTableWidgetItem(str(task.task_id)))
        
        # Cột 1: Tên file đích (đã xử lý trùng tên)
        self.download_table.setItem(row, 1, QTableWidgetItem(task.final_filename))

        # Cột 2: Progress Bar
        progress_bar = QProgressBar()
        progress_bar.setValue(int(task.percent))
        self.download_table.setCellWidget(row, 2, progress_bar)

        # Cột 3: Tốc độ
        self.download_table.setItem(row, 3, QTableWidgetItem(task.speed))

        # Cột 4: Trạng thái (Mặc định Waiting màu vàng)
        status_item = QTableWidgetItem(task.status)
        status_item.setBackground(Qt.GlobalColor.yellow)
        status_item.setForeground(Qt.GlobalColor.black)
        self.download_table.setItem(row, 4, status_item)

        # Lưu ánh xạ task_id vào dòng
        self.task_row_map[task.task_id] = row

    # ==================== CHỨC NĂNG 3: CẬP NHẬT TRẠNG THÁI & MÀU SẮC (on_progress) ====================
    def on_progress(self, task_id: str, status: str, percent: float, speed: str):
        if task_id not in self.task_row_map:
            return

        row = self.task_row_map[task_id]

        # Cập nhật Progress Bar
        p_bar = self.download_table.cellWidget(row, 2)
        if p_bar:
            p_bar.setValue(int(percent))

        # Cập nhật Tốc độ
        self.download_table.setItem(row, 3, QTableWidgetItem(speed))

        # Cập nhật Nhãn Trạng Thái & Màu sắc phân biệt
        status_item = QTableWidgetItem(status)
        if status == "Waiting":
            status_item.setBackground(Qt.GlobalColor.yellow)
            status_item.setForeground(Qt.GlobalColor.black)
        elif status == "Downloading":
            status_item.setBackground(Qt.GlobalColor.cyan)
            status_item.setForeground(Qt.GlobalColor.black)
        elif status == "Completed":
            status_item.setBackground(Qt.GlobalColor.green)
            status_item.setForeground(Qt.GlobalColor.white)
        elif status == "Failed":
            status_item.setBackground(Qt.GlobalColor.red)
            status_item.setForeground(Qt.GlobalColor.white)

        self.download_table.setItem(row, 4, status_item)

    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(is_mock_mode=True)
    window.show()
    sys.exit(app.exec())