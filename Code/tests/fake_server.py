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
            if (
                os.path.basename(filename) != filename
                or not os.path.isfile(filepath)
            ):
                client_socket.sendall(b"ERROR|File not found\n")
                return
            file_size = os.path.getsize(filepath)
            header = f"OK|{file_size}\n"
            client_socket.sendall(header.encode())
            
            with open(filepath, "rb") as file: # Mở file ở chế độ đọc nhị phân
                while True:
                    chunk = file.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    client_socket.sendall(chunk)
            print(f"Sent file: {filename}")
        else:
            client_socket.sendall(b"ERROR|Unknown command\n")

    # Xử lí lỗi
    except socket.timeout:
        print(f"Socket timeout: {client_address}")
    except ConnectionResetError:
        print(f"Client disconnected: {client_address}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()
        print(f"Connection closed: {client_address}")

def start_server(): # Khởi động server
    os.makedirs(MOCK_FILES_DIR,exist_ok=True)
    server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    server.bind((HOST, PORT))
    server.listen(MAX_SERVER_CONNECTIONS)
    print(f"Mock Server listening on {HOST}:{PORT}")
    print(f"MAX_SERVER_CONNECTIONS = "f"{MAX_SERVER_CONNECTIONS}")
    print(f"SOCKET_TIMEOUT = "f"{SOCKET_TIMEOUT}s")
    
    while True:
        client_socket, client_address = (server.accept())
        # Tạo một Thread riêng để xử lý Client
        thread = threading.Thread(
            target=handle_client,
            args=(
                client_socket,
                client_address
            )
        )
        thread.start()

if __name__ == "__main__":
    start_server()
