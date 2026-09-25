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

from PyQt6.QtCore import Qt, pyqtSignal, QThread , QTimer
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QLabel,
    QMessageBox, QAbstractItemView
)

# Import struct Task chuẩn từ common/task.py , import thêm từ network,queue,progress
from Code.common.task import Task
from Code.client.network_client import NetworkClient
from Code.client.queue_manager import QueueManager
from Code.client.ProgressTracker import ProgressTracker

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
        # Giúp GUI đưa file vào hệ thống dowload 
        self.network_client = NetworkClient(server_host="127.0.0.1",server_port=5000)
        self.progress_tracker = ProgressTracker()
        self.queue_manager = QueueManager(
            download_func=self.network_client.download_file,
            progress_tracker=self.progress_tracker
        )

        # Signal cập nhật UI Thread
        self.signals = ProgressSignal()
        self.signals.progress_updated.connect(self.on_progress)
        self.timer = QTimer() #Cập nhập tiến trình 
        self.timer.timeout.connect(self.poll_progress)
        self.timer.start(100)
        self.init_ui()

        # Gọi danh sách file từ Server khi mở ứng dụng
        self.load_server_files()
    def on_progress(self, task_id, status, percent, speed): # Cập nhập progress
        row = self.task_row_map.get(task_id)
    
        if row is None:
            return
    
        # Cập nhật trạng thái
        self.download_table.setItem(row, 4, QTableWidgetItem(status))
    
        # Cập nhật tốc độ
        self.download_table.setItem(row, 3, QTableWidgetItem(speed))
    
        # Cập nhật progress bar
        progress_bar = self.download_table.cellWidget(row, 2)
    
        if progress_bar:
            progress_bar.setValue(int(percent))
    
    def poll_progress(self):
        updates = self.progress_tracker.poll_updates()
    
        for task in updates:
            self.on_progress(
                task.task_id,
                task.status,
                task.percent,
                task.speed
            )
            
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
        self.server_table.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)  # Chỉ được kéo

        server_box.addWidget(server_label)
        server_box.addWidget(self.server_table)

        # ==================== KHU VỰC 2: KHU VỰC DOWNLOAD ====================
        download_box = QVBoxLayout()
        download_label = QLabel("<b>Khu vực 2: Tiến Trình Download (Kéo file vào đây)</b>")
        
        self.download_table = QTableWidget(0, 5)
        self.download_table.setHorizontalHeaderLabels(["Task ID", "Tên File Đích", "Tiến Trình (%)", "Tốc Độ", "Trạng Thái"])
        self.download_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.download_table.setAcceptDrops(True)  # Bật tính năng THẢ (Drop)
        self.download_table.setDropIndicatorShown(True)
        self.download_table.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)  # Chỉ được thả 
        
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
                from Code.client.network_client import NetworkClient
                client = NetworkClient(server_host="127.0.0.1",server_port=5000)

                file_list = client.get_file_list()
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

    def dragEnterEvent(self, event): # Cho phép kéo từ bảng server 
        if event.source() == self.server_table:
            event.acceptProposedAction()
        else:
            event.ignore()
    
    
    def dragMoveEvent(self, event): # Lấy tất cả file được chọn 
        if event.source() == self.server_table:
            event.acceptProposedAction()
        else:
            event.ignore()
    
    
    def get_unique_filename(self, filename): # Tìm tên file chưa bị trùng
        base, ext = os.path.splitext(filename)
    
        candidate = filename
        counter = 1
    
        while os.path.exists(candidate) or any(
            task.final_filename == candidate
            for task in self.queue_manager.tasks.values()
        ):
            candidate = f"{base}({counter}){ext}"
            counter += 1
    
        return candidate
    
    def dropEvent(self, event):
        if event.source() != self.server_table:
            event.ignore()
            return
    
        selected_rows = self.server_table.selectionModel().selectedRows()
    
        for index in selected_rows:
            filename = self.server_table.item(index.row(), 0).text()
            size = int(self.server_table.item(index.row(), 1).text())
    
            task_id = str(uuid.uuid4())
    
            final_filename = self.get_unique_filename(filename)
            task = Task(
                task_id=task_id,
                filename=filename,
                final_filename=final_filename,
                size=size,
                status="Waiting",
                percent=0,
                speed=""
            )
    
            # Thêm row vô bảng dowload 
            row = self.download_table.rowCount()
            self.download_table.insertRow(row)
    
            # Cột 0: Task ID
            self.download_table.setItem(row, 0, QTableWidgetItem(task_id[:8]))
    
            # Cột 1: Tên file đích
            self.download_table.setItem(row, 1, QTableWidgetItem(filename))
    
            # Cột 2: Progress bar
            progress_bar = QProgressBar()
            progress_bar.setValue(0)
            self.download_table.setCellWidget(row, 2, progress_bar)
    
            # Cột 3: Tốc độ
            self.download_table.setItem(row, 3, QTableWidgetItem(""))
    
            # Cột 4: Trạng thái
            self.download_table.setItem(row, 4, QTableWidgetItem("Waiting"))
    
            # Lưu task_id -> row
            self.task_row_map[task_id] = row
    
            added = self.queue_manager.add_task(task)
            if added:
                print(f"[GUI] Added task: {filename}")
            else:
                print(f"[GUI] Couldn't add task: {filename}")
    
        event.acceptProposedAction()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(is_mock_mode=False)
    window.show()
    sys.exit(app.exec())
