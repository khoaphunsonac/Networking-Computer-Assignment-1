# Hybrid Chat Application Implementation

## 1. **Mô tả**
Ứng dụng chat hybrid là một ứng dụng mạng kết hợp cả hai mô hình **Client-Server** và **Peer-to-Peer (P2P)**. Ứng dụng này hỗ trợ quản lý kênh, đồng bộ hóa giữa các peer phân tán và cung cấp giao diện web RESTful thông qua framework **AsynapRous**.

---

## 2. **Yêu cầu chức năng chính**

### **2.1. Giai đoạn khởi tạo (Client-Server Paradigm)**
- **Đăng ký Peer**: Khi một peer mới tham gia, nó phải gửi IP và port của mình đến server trung tâm.
- **Cập nhật Tracker**: Server trung tâm duy trì danh sách các peer đang hoạt động.
- **Khám phá Peer**: Các peer có thể yêu cầu danh sách các peer đang hoạt động từ server.
- **Thiết lập kết nối**: Các peer sử dụng danh sách tracker để thiết lập kết nối P2P trực tiếp.

### **2.2. Giai đoạn chat giữa các Peer (Peer-to-Peer Paradigm)**
- **Kết nối Broadcast**: Một peer phải có khả năng broadcast tin nhắn đến tất cả các peer đã kết nối.
- **Giao tiếp trực tiếp giữa các peer**: Các peer trao đổi tin nhắn mà không cần thông qua server trung tâm trong các phiên trực tiếp.

### **2.3. Quản lý kênh**
- **Danh sách kênh**: Người dùng có thể xem danh sách các kênh đã tham gia.
- **Hiển thị tin nhắn**: Mỗi kênh có một cửa sổ tin nhắn cuộn.
- **Gửi tin nhắn**: Giao diện hỗ trợ nhập và gửi tin nhắn.
- **Không chỉnh sửa/xóa**: Tin nhắn không thể chỉnh sửa hoặc xóa sau khi gửi.
- **Hệ thống thông báo**: Người dùng được thông báo khi có tin nhắn mới.
- **Kiểm soát truy cập (Tùy chọn)**: Các kênh có thể định nghĩa chính sách truy cập tùy chỉnh.

---

## 3. **Yêu cầu kỹ thuật**

- **Giao tiếp không blocking** giữa các daemon:
  - Sử dụng callback hoặc coroutine để các daemon trong mỗi peer giao tiếp với nhau.
  - **JavaScript** chỉ được phép sử dụng ở phía client để cập nhật giao diện hoặc tương tác GUI không đồng bộ.
  - Backend phải được triển khai bằng thư viện chuẩn của Python, không được sử dụng JavaScript hoặc các web framework có sẵn.

- **Lập trình Client-Server**:
  - Thiết kế giao thức trong giao tiếp tin nhắn và quy trình xử lý.

- **API mẫu**:
  - `http://IP:port/login/` — API đăng nhập.
  - `http://IP:port/submit-info/` — API gửi thông tin.
  - `http://IP:port/add-list/` — API thêm danh sách.
  - `http://IP:port/get-list/` — API lấy danh sách.
  - `http://IP:port/connect-peer/` — API kết nối peer.
  - `http://IP:port/broadcast-peer/` — API broadcast tin nhắn.
  - `http://IP:port/send-peer/` — API gửi tin nhắn trực tiếp giữa các peer.

- **Xử lý đồng thời (Concurrency)**:
  - Hỗ trợ giao tiếp đồng thời giữa các peer và server.

- **Xử lý lỗi (Error Handling)**:
  - Đảm bảo ứng dụng có thể xử lý các lỗi như mất kết nối, peer không phản hồi, hoặc lỗi giao tiếp mạng.

---

## 4. **Các bước triển khai**

### **4.1. Giai đoạn khởi tạo**
1. **Đăng ký Peer**:
   - Tạo API `/submit-info` để nhận thông tin IP và port từ peer mới.
   - Lưu thông tin vào danh sách tracker trên server.

2. **Cập nhật Tracker**:
   - Server duy trì danh sách các peer đang hoạt động.
   - Xóa các peer không còn hoạt động (timeout).

3. **Khám phá Peer**:
   - Tạo API `/get-list` để trả về danh sách các peer đang hoạt động.

4. **Thiết lập kết nối**:
   - Peer sử dụng danh sách tracker để thiết lập kết nối P2P trực tiếp với các peer khác.

### **4.2. Giai đoạn chat giữa các Peer**
1. **Kết nối Broadcast**:
   - Tạo API `/broadcast-peer` để gửi tin nhắn đến tất cả các peer đã kết nối.

2. **Giao tiếp trực tiếp giữa các peer**:
   - Tạo API `/send-peer` để gửi tin nhắn trực tiếp giữa các peer.

### **4.3. Quản lý kênh**
1. **Danh sách kênh**:
   - Tạo API `/channel-list` để trả về danh sách các kênh mà người dùng đã tham gia.

2. **Hiển thị tin nhắn**:
   - Tạo giao diện web hiển thị tin nhắn trong mỗi kênh.

3. **Gửi tin nhắn**:
   - Tạo giao diện hỗ trợ nhập và gửi tin nhắn.

4. **Hệ thống thông báo**:
   - Sử dụng cơ chế polling hoặc WebSocket để thông báo tin nhắn mới.

---

## 5. **Kết hợp với AsynapRous**
- Sử dụng các route RESTful để triển khai các API cần thiết.
- Tận dụng các phương pháp giao tiếp không đồng bộ (multi-thread, callback, coroutine) của framework để xử lý giao tiếp giữa các peer.

---

## 6. **Kiểm tra và hoàn thiện**
- Kiểm tra các API bằng công cụ như Postman hoặc curl.
- Kiểm tra giao diện web trên trình duyệt (tab Network trong Developer Tools).
- Đảm bảo các yêu cầu chức năng và kỹ thuật được đáp ứng đầy đủ.

---

Nếu cần hỗ trợ thêm trong việc triển khai hoặc kiểm tra, hãy cho tôi biết!