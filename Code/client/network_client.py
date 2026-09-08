"""
VAI TRÒ 2 — Xử lý mạng phía Client

Phụ trách: Nguyễn Đỗ Duy Tân

Chức năng:
- Kết nối TCP tới server
- Gửi LIST và nhận danh sách file
- Gửi GET và tải file
- Đọc message theo dòng
- Nhận dữ liệu file theo CHUNK_SIZE
- Cập nhật tiến trình và tốc độ
- Xử lý timeout, lỗi socket
- Xử lý File not found / Server busy
- Ghi file tạm .part
- Xóa file .part nếu download thất bại
"""

import os
import socket
import time
from typing import Callable, Optional

from Code.common.constants import (
    SERVER_PORT,
    CHUNK_SIZE,
    SOCKET_TIMEOUT,
)
from Code.common.task import Task


class NetworkError(Exception):
    """Lỗi mạng phía client."""


class ServerBusyError(NetworkError):
    """Server đang quá tải."""


class RemoteFileNotFoundError(NetworkError):
    """File không tồn tại trên server."""


class ProtocolError(NetworkError):
    """Response từ server không đúng protocol."""


class NetworkClient:
    """
    Xử lý giao tiếp TCP giữa client và server.

    Mỗi request sử dụng một TCP connection riêng.
    """

    def __init__(
        self,
        server_host: str,
        server_port: int = SERVER_PORT,
        timeout: int = SOCKET_TIMEOUT,
    ):
        self.server_host = server_host
        self.server_port = server_port
        self.timeout = timeout

    # ==========================================================
    # CONNECTION
    # ==========================================================

    def _connect(self) -> socket.socket:
        """
        Tạo TCP connection tới server.
        """

        try:
            sock = socket.create_connection(
                (self.server_host, self.server_port),
                timeout=self.timeout,
            )

            sock.settimeout(self.timeout)

            return sock

        except socket.timeout as exc:
            raise NetworkError(
                "Kết nối tới server bị timeout."
            ) from exc

        except socket.error as exc:
            raise NetworkError(
                f"Không thể kết nối tới server: {exc}"
            ) from exc

    # ==========================================================
    # SEND LINE
    # ==========================================================

    @staticmethod
    def _send_line(
        sock: socket.socket,
        message: str,
    ) -> None:
        """
        Gửi message dạng text kết thúc bằng '\\n'.
        """

        data = (message + "\n").encode("utf-8")

        try:
            sock.sendall(data)

        except socket.timeout as exc:
            raise NetworkError(
                "Timeout khi gửi request tới server."
            ) from exc

        except socket.error as exc:
            raise NetworkError(
                f"Lỗi gửi request tới server: {exc}"
            ) from exc

    # ==========================================================
    # RECEIVE LINE
    # ==========================================================

    @staticmethod
    def _recv_line(
        sock: socket.socket,
    ) -> str:
        """
        Đọc dữ liệu TCP cho tới khi gặp '\\n'.

        TCP là stream nên không giả định mỗi recv()
        tương ứng với một message hoàn chỉnh.
        """

        buffer = bytearray()

        while True:

            try:
                data = sock.recv(1)

            except socket.timeout as exc:
                raise NetworkError(
                    "Server không phản hồi trong thời gian cho phép."
                ) from exc

            except socket.error as exc:
                raise NetworkError(
                    f"Lỗi nhận dữ liệu từ server: {exc}"
                ) from exc

            if not data:
                raise NetworkError(
                    "Server đóng kết nối trước khi gửi đầy đủ response."
                )

            if data == b"\n":
                break

            buffer.extend(data)

            # Không cho header tăng vô hạn.
            if len(buffer) > 64 * 1024:
                raise ProtocolError(
                    "Response line quá dài."
                )

        try:
            return buffer.decode("utf-8").rstrip("\r")

        except UnicodeDecodeError as exc:
            raise ProtocolError(
                "Response từ server không phải UTF-8 hợp lệ."
            ) from exc

    # ==========================================================
    # FILENAME VALIDATION
    # ==========================================================

    @staticmethod
    def _validate_filename(
        filename: str,
    ) -> None:
        """
        Chỉ cho phép filename dạng basename.

        Không cho phép:
        - ..
        - ../file
        - folder/file
        - folder\\file
        """

        if not filename:
            raise ValueError(
                "Tên file không được rỗng."
            )

        if filename in (".", ".."):
            raise ValueError(
                "Tên file không hợp lệ."
            )

        if "/" in filename or "\\" in filename:
            raise ValueError(
                "Filename không được chứa dấu phân cách thư mục."
            )

        if ".." in filename:
            raise ValueError(
                "Filename không được chứa '..'."
            )

        if os.path.basename(filename) != filename:
            raise ValueError(
                "Filename phải là basename."
            )

    # ==========================================================
    # LIST
    # ==========================================================

    def get_file_list(self) -> list[dict]:
        """
        Lấy danh sách file từ server.

        Request:

            LIST\\n

        Response:

            FILE|filename|size\\n
            FILE|filename|size\\n
            END\\n

        Returns:

            [
                {
                    "filename": "report.pdf",
                    "size": 204800
                }
            ]
        """

        sock: Optional[socket.socket] = None

        try:
            sock = self._connect()

            self._send_line(
                sock,
                "LIST",
            )

            files = []

            while True:

                line = self._recv_line(sock)

                if line == "END":
                    break

                if not line.startswith("FILE|"):
                    raise ProtocolError(
                        f"Response LIST không hợp lệ: {line}"
                    )

                parts = line.split("|")

                if len(parts) != 3:
                    raise ProtocolError(
                        f"Định dạng FILE không hợp lệ: {line}"
                    )

                _, filename, size_text = parts

                self._validate_filename(filename)

                try:
                    size = int(size_text)

                except ValueError as exc:
                    raise ProtocolError(
                        f"Kích thước file không hợp lệ: {size_text}"
                    ) from exc

                if size < 0:
                    raise ProtocolError(
                        "Kích thước file không thể âm."
                    )

                files.append(
                    {
                        "filename": filename,
                        "size": size,
                    }
                )

            return files

        finally:

            if sock is not None:
                try:
                    sock.close()
                except socket.error:
                    pass

    # ==========================================================
    # DOWNLOAD
    # ==========================================================

    def download_file(
        self,
        task: Task,
        progress_callback: Optional[
            Callable[[int, str], None]
        ] = None,
    ) -> str:
        """
        Tải file theo Task.

        Đây là hàm được QueueManager gọi:

            download_func(task, progress_callback)

        Callback có dạng:

            progress_callback(percent, speed)

        Returns:
            Đường dẫn file hoàn chỉnh.
        """

        filename = task.filename
        destination_path = task.final_filename

        self._validate_filename(filename)

        # ------------------------------------------------------
        # Destination
        # ------------------------------------------------------

        # QueueManager/GUI có thể truyền final_filename là
        # tên file hoặc đường dẫn tương đối.
        #
        # Đảm bảo thư mục download tồn tại.
        destination_path = os.path.abspath(
            destination_path
        )

        destination_dir = os.path.dirname(
            destination_path
        )

        os.makedirs(
            destination_dir,
            exist_ok=True,
        )

        temp_path = destination_path + ".part"

        sock: Optional[socket.socket] = None

        bytes_received = 0
        total_size = 0

        start_time = time.monotonic()

        try:

            # --------------------------------------------------
            # CONNECT
            # --------------------------------------------------

            sock = self._connect()

            # --------------------------------------------------
            # GET
            # --------------------------------------------------

            self._send_line(
                sock,
                f"GET|{filename}",
            )

            # --------------------------------------------------
            # RESPONSE HEADER
            # --------------------------------------------------

            header = self._recv_line(sock)

            # --------------------------------------------------
            # ERROR
            # --------------------------------------------------

            if header.startswith("ERROR|"):

                error_message = header[6:]

                if error_message == "File not found":
                    raise RemoteFileNotFoundError(
                        f"File không tồn tại trên server: {filename}"
                    )

                if error_message == "Server busy":
                    raise ServerBusyError(
                        "Server đang quá tải."
                    )

                raise NetworkError(
                    f"Server trả về lỗi: {error_message}"
                )

            # --------------------------------------------------
            # OK
            # --------------------------------------------------

            if not header.startswith("OK|"):
                raise ProtocolError(
                    f"Response GET không hợp lệ: {header}"
                )

            parts = header.split("|")

            if len(parts) != 2:
                raise ProtocolError(
                    f"Header OK không hợp lệ: {header}"
                )

            try:
                total_size = int(parts[1])

            except ValueError as exc:
                raise ProtocolError(
                    f"Kích thước file không hợp lệ: {parts[1]}"
                ) from exc

            if total_size < 0:
                raise ProtocolError(
                    "Kích thước file không thể âm."
                )

            # --------------------------------------------------
            # CHECK SIZE WITH TASK
            # --------------------------------------------------

            if task.size != total_size:
                raise ProtocolError(
                    "Kích thước file không khớp với danh sách server."
                )

            # --------------------------------------------------
            # RECEIVE FILE
            # --------------------------------------------------

            with open(
                temp_path,
                "wb",
            ) as file:

                while bytes_received < total_size:

                    remaining = (
                        total_size - bytes_received
                    )

                    recv_size = min(
                        CHUNK_SIZE,
                        remaining,
                    )

                    try:
                        chunk = sock.recv(
                            recv_size
                        )

                    except socket.timeout as exc:
                        raise NetworkError(
                            "Server timeout trong quá trình tải."
                        ) from exc

                    except socket.error as exc:
                        raise NetworkError(
                            f"Lỗi nhận dữ liệu file: {exc}"
                        ) from exc

                    # Server đóng kết nối khi chưa đủ dữ liệu.
                    if not chunk:
                        raise NetworkError(
                            "Mất kết nối giữa chừng khi đang tải."
                        )

                    try:
                        file.write(chunk)

                    except (OSError, IOError) as exc:
                        raise OSError(
                            f"Lỗi ghi file: {exc}"
                        ) from exc

                    bytes_received += len(chunk)

                    # ------------------------------------------------
                    # PROGRESS
                    # ------------------------------------------------

                    if total_size > 0:
                        percent = int(
                            bytes_received * 100
                            / total_size
                        )
                    else:
                        percent = 100

                    elapsed = (
                        time.monotonic()
                        - start_time
                    )

                    if elapsed > 0:
                        speed_bytes = (
                            bytes_received
                            / elapsed
                        )
                    else:
                        speed_bytes = 0.0

                    speed = self._format_speed(
                        speed_bytes
                    )

                    # ------------------------------------------------
                    # CALLBACK
                    # ------------------------------------------------

                    if progress_callback is not None:

                        try:
                            progress_callback(
                                percent,
                                speed,
                            )
                        except Exception:
                            # Lỗi callback không làm crash
                            # quá trình download.
                            pass

            # --------------------------------------------------
            # VERIFY SIZE
            # --------------------------------------------------

            if bytes_received != total_size:
                raise NetworkError(
                    "Số byte nhận được không khớp kích thước file."
                )

            # --------------------------------------------------
            # RENAME .part -> FINAL
            # --------------------------------------------------

            try:
                os.replace(
                    temp_path,
                    destination_path,
                )

            except (OSError, IOError) as exc:
                raise OSError(
                    f"Không thể hoàn tất file tải xuống: {exc}"
                ) from exc

            # --------------------------------------------------
            # FINAL CALLBACK
            # --------------------------------------------------

            if progress_callback is not None:

                try:
                    progress_callback(
                        100,
                        "Done",
                    )
                except Exception:
                    pass

            return destination_path

        except (NetworkError, OSError, IOError):
            # Lỗi đã biết: dọn file tạm rồi ném lại
            # để QueueManager chuyển Task -> Failed.

            self._remove_temp_file(
                temp_path
            )

            raise

        except Exception:
            # Lỗi ngoài dự kiến cũng phải dọn file .part.
            self._remove_temp_file(
                temp_path
            )

            raise

        finally:

            # Mỗi request chỉ dùng 1 connection.
            if sock is not None:

                try:
                    sock.close()

                except socket.error:
                    pass

    # ==========================================================
    # HELPERS
    # ==========================================================

    @staticmethod
    def _remove_temp_file(
        temp_path: str,
    ) -> None:
        """
        Xóa file .part nếu tồn tại.
        """

        try:

            if os.path.exists(temp_path):
                os.remove(temp_path)

        except (OSError, IOError):
            # Không để lỗi cleanup làm crash chương trình.
            pass

    @staticmethod
    def _format_speed(
        speed_bytes: float,
    ) -> str:
        """
        Đổi tốc độ từ bytes/s sang chuỗi dễ hiển thị.
        """

        if speed_bytes < 1024:
            return f"{speed_bytes:.1f} B/s"

        if speed_bytes < 1024 * 1024:
            return f"{speed_bytes / 1024:.1f} KB/s"

        return f"{speed_bytes / (1024 * 1024):.1f} MB/s"


# ==============================================================
# TEST ĐƠN GIẢN
# ==============================================================

if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:
        print(
            "Cách dùng:"
        )
        print(
            "python -m Code.client.network_client <server_ip>"
        )
        sys.exit(1)

    server_ip = sys.argv[1]

    client = NetworkClient(
        server_host=server_ip
    )

    try:

        files = client.get_file_list()

        print("Danh sách file trên server:")

        for item in files:
            print(
                f"- {item['filename']} "
                f"({item['size']} bytes)"
            )

    except NetworkError as exc:

        print(
            f"Lỗi: {exc}"
        )