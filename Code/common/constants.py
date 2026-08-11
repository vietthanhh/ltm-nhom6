"""
Hằng số dùng chung cho toàn bộ app (client + server)
KHÔNG tự đổi giá trị ở đây khi đang code module riêng — mọi thay đổi
phải được nhóm thống nhất trước, vì ảnh hưởng tới tất cả module khác.
"""
SERVER_PORT = 5000
CHUNK_SIZE = 4096
MAX_CONCURRENT = 5
MAX_SERVER_CONNECTIONS = 8
SOCKET_TIMEOUT = 10
