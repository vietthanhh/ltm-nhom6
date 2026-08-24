import socket
import threading
import os

# TODO: nối liên kết file lại (common/constants.py của nhóm)
PORT = 5000
SERVER = socket.gethostbyname(socket.gethostname())
CHUNK_SIZE = 4096

ADDR = (SERVER, PORT)
FORMAT = 'utf-8'

MAX_CONNECTIONS = 8
SOCKET_TIMEOUT = 10
current_connections = 0
conn_lock = threading.Lock()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

def recv_line(conn):
    """
    Hàm đọc dữ liệu từ stream của TCP. 
    Lấy từng byte đến khi gặp '\n' để có được 1 lệnh hoàn chỉnh.
    """
    buffer=""
    while True:
        char = conn.recv(1).decode(FORMAT)
        # Tranh lặp vô hạn: recv() trả về chuỗi rỗng -> thoát
        if not char:
            break
        buffer += char
        # '\n' là dấu hiệu kết thúc 1 message
        if char =='\n':
            return buffer.strip()
    return buffer


def handle_client(conn, addr):
    """
    Hàm xử lý 1 connection với client.
    Quy tắc: Xử lý xong 1 lệnh là đóng kết nối ngay lập tức.
    """
    print(f"[NEW CONNECTIONS] {addr} connected.")

    global current_connections

    conn.settimeout(SOCKET_TIMEOUT)
    # TODO: Bọc try...finally, dùng Lock 
    try:
        msg = recv_line(conn)
        if msg:
            print (f"[{addr}] {msg}")
            #Xử lý lệnh LIST (Client xin danh sách file hiện có)
            if msg =="LIST":
                file_list = os.listdir("shared_files")
                # Duyệt từng file, lấy dung lượng và đóng gói
                for file_name in file_list:
                    file_path = os.path.join("shared_files", file_name)
                    file_size = os.stat(file_path).st_size

                    # Format: FILE|tên_file|kích_thước
                    file_stat = f"FILE|{file_name}|{file_size}\n"
                    conn.send(file_stat.encode(FORMAT))
                #Thông báo để client dừng đọc
                conn.send("END\n".encode(FORMAT))

            #Xử lý lệnh GET
            elif msg.startswith("GET|"):
                file_name = msg.split("|")[1]
                file_path = os.path.join("shared_files", file_name)

                # Không cho client dùng ".." để thoát khỏi thư mục shared_files
                if ".." in file_name or not os.path.exists(file_path):
                    error_msg = "ERROR|File not found\n"
                    conn.send(error_msg.encode(FORMAT))
                else:
                    # Gửi file size trước khi truyền dữ liệu
                    file_size = os.stat(file_path).st_size
                    header_msg = f"OK|{file_size}\n"
                    conn.send(header_msg.encode(FORMAT))
                    # Truyền dữ liệu
                    with open (file_path, 'rb') as rf:
                        rf_chunk = rf.read(CHUNK_SIZE)
                        while len(rf_chunk) >0:
                            conn.send(rf_chunk)
                            rf_chunk = rf.read(CHUNK_SIZE)
    except socket.timeout:
        print(f"[TIMEOUT] {addr} quá thời gian chờ 10s. Đang ngắt kết nối...")
    except Exception as e:
        print(f"[ERROR] Có sự cố với {addr}. Chi tiết: {e}")

    finally:
        with conn_lock:
            current_connections -=1
        # Đóng kết nối ngay lập tức sau khi gửi xong response
        conn.close()
        print(f"[DISCONNECTED] {addr} closed.")


def start():
    """
    Hàm khởi động server, luôn lắng nghe và cấp thread mới cho mỗi client.
    """
    server.listen()
    print (f"[LISTENING] Server is listening on {SERVER}")

    global current_connections

    while True:
        conn, addr =server.accept()
        # Dùng Lock check giới hạn, >= 8 thì báo ERROR|Server busy rồi ngắt
        with conn_lock:
            if current_connections >= MAX_CONNECTIONS:
                conn.send("ERROR|Server busy\n".encode(FORMAT))
                conn.close()
                continue

            current_connections += 1
        
        thread = threading.Thread(target = handle_client, args = (conn, addr))
        thread.start()
        
        print( f"[ACTIVE CONNECTIONS] {current_connections}")



print("[STARTING] server is listening...")
start()



