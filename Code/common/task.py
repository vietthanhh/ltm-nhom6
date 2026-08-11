"""
Struct Task dùng chung — đại diện 1 dòng download trên UI.
Quy tắc : chỉ queue_manager.py và network_client.py
được phép thay đổi status/percent/speed. gui.py CHỈ ĐỌC để hiển thị,
không tự set trạng thái.
"""
from dataclasses import dataclass

@dataclass
class Task:
    task_id: str
    filename: str          # tên gốc ở server
    final_filename: str    # tên sau khi xử lý trùng, VD: report(1).pdf
    size: int
    status: str             # Waiting | Downloading | Completed | Failed
    percent: int = 0
    speed: str = ""
