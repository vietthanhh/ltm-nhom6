from dataclasses import dataclass

@dataclass
class task:
    task_id: str
    filename: str          # tên gốc ở server
    final_filename: str    # tên sau khi xử lý trùng, VD: report(1).pdf
    size: int
    status: str             # Waiting | Downloading | Completed | Failed
    percent: int = 0
    speed: str = ""
