# UDM_11 — Download nhiều file
### 1. Danh sách thành viên
- Nguyễn Đỗ Duy Tân
- Tô Lâm Mộc
- Lê Minh Hiền
- Phan Thanh Thu Ngân
- Trần Thị Hồng Ngọc
- Trần Huỳnh Viết Thanh

Phân công
- Giao diện (GUI)	Hiển thị danh sách file trên server, khu vực download với progress bar/trạng thái, xử lý kéo thả
- Xử lý mạng phía Client	Giao tiếp giao thức LIST/GET, đọc dữ liệu theo chunk, xử lý lỗi kết nối
- Quản lý hàng đợi (Concurrency)	Thread pool, xử lý trùng tên có khóa đồng bộ, quản lý trạng thái task
- Progress & Trạng thái	Cập nhật tiến trình/tốc độ lên giao diện qua cơ chế UI thread
- Server	Lắng nghe kết nối, xử lý LIST/GET, phục vụ nhiều client đồng thời, giới hạn connection
- Test & Tích hợp	Chuẩn bị dữ liệu/server giả để test độc lập, thực hiện test case, tích hợp hệ thống
