from Code.client.network_client import NetworkClient
from Code.common.task import Task


def progress(percent, speed):
    print(f"Progress: {percent}% | Speed: {speed}")


client = NetworkClient("192.168.1.7")

task = Task(
    task_id="test-001",
    filename="report.txt",
    final_filename="downloaded_report.txt",
    size=8,
    status="Waiting",
)

try:
    result = client.download_file(
        task,
        progress,
    )

    print(f"Download thành công: {result}")

except Exception as e:
    print(f"Download thất bại: {e}")