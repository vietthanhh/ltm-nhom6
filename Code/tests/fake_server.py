import socket
import os
import threading

HOST = "127.0.0.1"
PORT = 5000
MOCK_FILES_DIR = "mock_files"
CHUNK_SIZE = 4096
MAX_SERVER_CONNECTIONS = 8
SOCKET_TIMEOUT = 10

def get_file_list(): # Lấy danh sách file
    files = []
    for filename in os.listdir(MOCK_FILES_DIR): # Duyệt tất cả file
        filepath = os.path.join(MOCK_FILES_DIR, filename)
        if os.path.isfile(filepath):
            size = os.path.getsize(filepath)
            files.append((filename, size))
    return files

def handle_client(client_socket, client_address):
    print(f"Client connected: {client_address}")
    # Timeout 10 giây cho connection
    client_socket.settimeout(SOCKET_TIMEOUT)
    try:
        # Mỗi connection chỉ xử lý 1 request
        data = client_socket.recv(1024)
        if not data:
            return
        request = data.decode().strip() # Chuyển dữ liệu nhận được từ byte sang chuỗi
        print(f"Request: {request}")

        # LIST
        if request == "LIST":
            files = get_file_list()
            response = ""
            for filename, size in files:
                response += f"FILE|{filename}|{size}\n"
            response += "END\n"
            client_socket.sendall(response.encode())

        # GET
        elif request.startswith("GET|"):
            # Lấy tên file từ request
            # Ví dụ: GET|test.txt
            # filename = test.txt
            filename = request[4:]
            filepath = os.path.join(MOCK_FILES_DIR, filename)
            # Kiểm tra filename có hợp lệ không
            if 
            (
                os.path.basename(filename) != filename
                or not os.path.isfile(filepath)
            ):
                client_socket.sendall
                (
                    b"ERROR|File not found\n"
                )
                return
            file_size = os.path.getsize(filepath)
