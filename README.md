# AsynapRous — Asynchronous Reverse Proxy & RESTful Web Framework

> **Môn học:** CO3093/CO3094 — Mạng máy tính  
> **Trường:** Đại học Bách khoa TP.HCM (HCMUT) — ĐHQG-HCM  
> **Học kỳ:** HK252 — Năm 3  
> **Tác giả framework gốc:** pdnguyen (bksysnet@hcmut)

---

## 📖 Mô tả tổng quan

**AsynapRous** là một framework web nhẹ được xây dựng hoàn toàn bằng Python, sử dụng **raw socket** và **threading** (không dùng các web framework có sẵn như Flask hay Django). Dự án mô phỏng kiến trúc của một hệ thống web hoàn chỉnh gồm:

- 🔀 **Reverse Proxy Server** — chuyển tiếp HTTP request đến backend dựa trên hostname
- 🖥️ **Backend HTTP Server** — xử lý request, phân giải route, trả về response
- 🌐 **RESTful Web Application** — ứng dụng mẫu với decorator-based routing (tương tự Flask)

---

## 📁 Cấu trúc thư mục

```
BTL/
├── assignment1-asynaprous.pdf   # Đề bài Assignment 1
├── spec.md                      # Specification
├── README.md                    # File này
├── TESTING.md                   # Kịch bản test chi tiết
├── scripts/
│   └── smoke_test.py            # Smoke test tự động
└── Ass1/                        # Source code chính
    ├── __init__.py               # Package init — export các module chính
    ├── start_proxy.py            # Entry point: khởi chạy Proxy Server
    ├── start_backend.py          # Entry point: khởi chạy Backend Server
    ├── start_sampleapp.py        # Entry point: khởi chạy Sample RESTful App
    ├── tree.py                   # Utility hiển thị cấu trúc thư mục
    │
    ├── daemon/                   # Core modules
    │   ├── __init__.py
    │   ├── asynaprous.py         # AsynapRous — Web framework (routing decorator)
    │   ├── proxy.py              # Reverse Proxy Server (socket + threading)
    │   ├── backend.py            # Backend Server (multi-thread / callback / coroutine)
    │   ├── httpadapter.py        # HTTP Adapter — xử lý request/response lifecycle
    │   ├── request.py            # Request object — parse HTTP request
    │   ├── response.py           # Response object — build HTTP response
    │   ├── dictionary.py         # CaseInsensitiveDict — dict header không phân biệt hoa/thường
    │   └── utils.py              # Utility functions (URL parsing, auth extraction)
    │
    ├── apps/                     # Ứng dụng mẫu
    │   ├── __init__.py
    │   ├── sampleapp.py          # Sample RESTful app + Hybrid Chat APIs
    │   └── hybrid_chat.py        # Non-blocking P2P daemon (selectors)
    │
    ├── config/                   # Cấu hình
    │   └── proxy.conf            # Virtual host config cho Proxy
    │
    ├── www/                      # Static HTML pages
    │   ├── index.html            # Trang chủ
    │   ├── login.html            # Trang đăng nhập
    │   ├── form.html             # Form mẫu
    │   └── chat.html             # Chat UI cho Hybrid Chat
    │
    ├── static/                   # Static assets
    │   ├── css/
    │   │   ├── styles.css
    │   │   └── chatapp.css       # Style cho chat UI
    │   ├── js/
    │   │   └── chatapp.js        # Client-side logic gọi chat APIs
    │   └── images/
    │
    ├── cert/                     # SSL certificates (trống — dự phòng cho HTTPS)
    └── db/                       # Database storage (trống — dự phòng)
```

---

## 🏗️ Kiến trúc hệ thống

```
┌──────────┐        ┌───────────────────┐       ┌──────────────────┐
│  Client  │───────▶│   Reverse Proxy  │──────▶│  Backend Server  │
│ (Browser)│◀───────│   (port 8080)    │◀──────│   (port 9000)    │
└──────────┘        └───────────────────┘       └──────────────────┘
                         │                          │
                         │  hostname routing        │  HttpAdapter
                         │  (proxy.conf)            │  Request/Response
                         │                          │
                         │                    ┌─────┴─────┐
                         │                    │ AsynapRous│
                         │                    │  (RESTful │
                         │                    │   Router) │
                         │                    └───────────┘
                         │
                   ┌─────┴──────┐
                   │ SampleApp  │
                   │ (port 2026)│
                   └────────────┘
```

### Luồng xử lý request

1. **Client** gửi HTTP request đến **Proxy Server** (port `8080`)
2. **Proxy** đọc header `Host`, tra cứu `proxy.conf` để xác định backend đích
3. **Proxy** forward request đến **Backend Server** tương ứng
4. **Backend** nhận request, sử dụng `HttpAdapter` để parse và route
5. Nếu có RESTful route (qua `AsynapRous`), gọi handler function tương ứng
6. Nếu là static file, `Response` đọc file từ `www/` hoặc `static/`
7. Response được trả ngược lại qua Proxy về Client

---

## 🚀 Hướng dẫn chạy

### Yêu cầu

- **Python 3.x** (khuyến nghị Python 3.8+)
- Không cần cài thêm thư viện bên ngoài (chỉ dùng standard library)

### 1. Khởi chạy Backend Server

```bash
cd Ass1
python start_backend.py --server-ip 0.0.0.0 --server-port 9000
```

| Tham số | Mặc định | Mô tả |
|---------|----------|-------|
| `--server-ip` | `0.0.0.0` | Địa chỉ IP bind |
| `--server-port` | `9000` | Cổng lắng nghe |

### 2. Khởi chạy Reverse Proxy

```bash
cd Ass1
python start_proxy.py --server-ip 0.0.0.0 --server-port 8080
```

| Tham số | Mặc định | Mô tả |
|---------|----------|-------|
| `--server-ip` | `0.0.0.0` | Địa chỉ IP bind |
| `--server-port` | `8080` | Cổng proxy lắng nghe |

Proxy đọc cấu hình routing từ file `config/proxy.conf`.

### 3. Khởi chạy Sample RESTful App

```bash
cd Ass1
python start_sampleapp.py --server-ip 0.0.0.0 --server-port 2026
```

| Tham số | Mặc định | Mô tả |
|---------|----------|-------|
| `--server-ip` | `0.0.0.0` | Địa chỉ IP bind |
| `--server-port` | `2026` | Cổng app lắng nghe |

---

## 🔧 Cấu hình Proxy

File `config/proxy.conf` định nghĩa virtual host routing:

```nginx
host "192.168.56.114:8080" {
    proxy_pass http://192.168.56.114:9000;
}

host "app1.local" {
    proxy_pass http://192.168.56.114:9001;
}

host "app2.local" {
    proxy_pass http://192.168.56.114:9002;
    proxy_pass http://192.168.56.114:9002;
    dist_policy round-robin
}
```

- Mỗi block `host` map một hostname đến một hoặc nhiều backend
- `dist_policy` xác định chính sách phân phối khi có nhiều `proxy_pass` (mặc định: `round-robin`)

---

## 📦 Các module chính

### `daemon/asynaprous.py` — AsynapRous Framework

Micro web framework với decorator-based routing, hỗ trợ cả sync và async handler:

```python
from daemon import AsynapRous

app = AsynapRous()

@app.route('/login', methods=['POST'])
def login(headers, body):
    return json.dumps({"message": "Welcome"}).encode("utf-8")

@app.route('/hello', methods=['PUT'])
async def hello(headers, body):
    return json.dumps({"name": "Alice"}).encode("utf-8")

app.prepare_address("0.0.0.0", 2026)
app.run()
```

### `daemon/proxy.py` — Reverse Proxy

- Parse `Host` header từ request
- Tra cứu routing table để xác định backend đích
- Forward request và trả response về client
- Hỗ trợ multi-threading cho concurrent connections

### `daemon/backend.py` — Backend Server

Hỗ trợ 3 chế độ xử lý client:

| Mode | Mô tả |
|------|--------|
| `threading` | Multi-thread (mặc định) — mỗi client 1 thread |
| `callback` | Event-driven — sử dụng `selectors` |
| `coroutine` | Async/await — sử dụng `asyncio` |

### `daemon/httpadapter.py` — HTTP Adapter

Quản lý toàn bộ lifecycle của một HTTP request:
- Nhận raw bytes từ socket
- Parse thành `Request` object
- Dispatch đến route handler (nếu có)
- Build `Response` và gửi về client

### `daemon/request.py` — Request Object

Parse HTTP request: method, path, version, headers, body, cookies.

### `daemon/response.py` — Response Object

Build HTTP response: status code, headers, content (MIME detection, file serving).

---

## 📝 Các TODO (phần sinh viên cần hoàn thành)

| Module | Vị trí | Yêu cầu |
|--------|--------|----------|
| `proxy.py` | `run_proxy()` | Implement multi-thread cho client connections |
| `backend.py` | `run_backend()` | Implement non-blocking communication (thread / callback / coroutine) |
| `httpadapter.py` | `handle_client()` | Xử lý App hook cho RESTful routing |
| `request.py` | `prepare()` | Implement cookie parsing từ header |
| `response.py` | `build_response_header()` | Build formatted HTTP response header |
| `response.py` | `build_content()` | Fetch object file từ storage |
| `response.py` | `build_response()` | Hỗ trợ thêm MIME types (image, video, v.v.) |
| `httpadapter.py` | `build_proxy_headers()` | Implement authentication |

---

## ✅ Trạng thái Hybrid Chat Application

Phần 2.3 (Hybrid Chat Application) đã được tích hợp trong sample app với các thành phần chính:

- Client-server phase:
    - Đăng ký peer: `POST /submit-info`
    - Đồng bộ list peer: `POST /add-list`
    - Lấy list peer: `GET|POST /get-list`
- Peer-to-peer phase (non-blocking bằng selectors):
    - Kết nối peer: `POST /connect-peer`
    - Broadcast: `POST /broadcast-peer`
    - Direct message: `POST /send-peer`
- Channel management:
    - Join channel: `POST /join-channel`
    - List channels: `GET|POST /channel-list`
    - Lấy message theo channel: `POST /channel-messages`
- Authentication + cookie:
    - `POST /login` trả `Set-Cookie: session_id=...; HttpOnly`

### Danh sách API Hybrid Chat (đã tích hợp)

| API | Method | Mục đích |
|-----|--------|----------|
| `/login` | `POST` | Xác thực user, trả session cookie |
| `/submit-info` | `POST` | Đăng ký peer vào tracker |
| `/add-list` | `POST` | Đồng bộ danh sách peer |
| `/get-list` | `GET/POST` | Lấy danh sách peer đang hoạt động |
| `/connect-peer` | `POST` | Thiết lập kết nối P2P non-blocking |
| `/broadcast-peer` | `POST` | Broadcast tin nhắn đến toàn bộ peer đã kết nối |
| `/send-peer` | `POST` | Gửi direct message đến một peer |
| `/join-channel` | `POST` | Join channel |
| `/channel-list` | `GET/POST` | Liệt kê channel + unread count |
| `/channel-messages` | `POST` | Lấy message của channel |

### File chính đã triển khai

- `Ass1/apps/sampleapp.py`: route RESTful cho hybrid chat
- `Ass1/apps/hybrid_chat.py`: daemon P2P non-blocking (listener + read/write event loop)
- `Ass1/daemon/httpadapter.py`: hỗ trợ handler kiểu `(headers, body)` và `(request, response)`
- `Ass1/daemon/response.py`: merge custom headers (đặc biệt `Set-Cookie`) vào HTTP response

---

## 🧪 Tự Test End-to-End (khuyến nghị cho demo)

### 1) Chạy 2 peer app

Terminal 1:

```bash
cd Ass1
python start_sampleapp.py --server-ip 127.0.0.1 --server-port 2026
```

Terminal 2:

```bash
cd Ass1
python start_sampleapp.py --server-ip 127.0.0.1 --server-port 2027
```

Lưu ý: mỗi app tự mở P2P listener tại `server-port + 1000`.
- Peer A: HTTP `2026`, P2P `3026`
- Peer B: HTTP `2027`, P2P `3027`

### 2) Test cookie ở API login

```bash
curl -i -X POST http://127.0.0.1:2026/login -H "Content-Type: application/json" -d "{\"username\":\"alice\"}"
```

Kỳ vọng: trong response header có `Set-Cookie: session_id=token-alice; Path=/; HttpOnly`.

### 3) Đăng ký peer vào tracker

```bash
curl -X POST http://127.0.0.1:2026/submit-info -H "Content-Type: application/json" -d "{\"peer_id\":\"peer-2026\",\"ip\":\"127.0.0.1\",\"port\":3026}"
curl -X POST http://127.0.0.1:2026/submit-info -H "Content-Type: application/json" -d "{\"peer_id\":\"peer-2027\",\"ip\":\"127.0.0.1\",\"port\":3027}"
curl http://127.0.0.1:2026/get-list
```

Kỳ vọng: `get-list` trả về cả `peer-2026` và `peer-2027`.

### 4) Thiết lập kết nối P2P và broadcast

```bash
curl -X POST http://127.0.0.1:2026/connect-peer -H "Content-Type: application/json" -d "{\"peer_id\":\"peer-2027\",\"ip\":\"127.0.0.1\",\"port\":3027}"
curl -X POST http://127.0.0.1:2027/join-channel -H "Content-Type: application/json" -d "{\"channel\":\"general\"}"
curl -X POST http://127.0.0.1:2026/broadcast-peer -H "Content-Type: application/json" -d "{\"from\":\"alice\",\"channel\":\"general\",\"message\":\"hello from peer A\"}"
curl -X POST http://127.0.0.1:2027/channel-messages -H "Content-Type: application/json" -d "{\"channel\":\"general\",\"limit\":10}"
```

Kỳ vọng: peer B thấy message incoming từ `alice`.

### 5) Test direct peer message

```bash
curl -X POST http://127.0.0.1:2026/send-peer -H "Content-Type: application/json" -d "{\"peer_id\":\"peer-2027\",\"from\":\"alice\",\"channel\":\"general\",\"message\":\"private hello\"}"
curl -X POST http://127.0.0.1:2027/channel-messages -H "Content-Type: application/json" -d "{\"channel\":\"general\",\"limit\":10}"
```

Kỳ vọng: message mới xuất hiện thêm trong danh sách channel.

### 6) Kiểm tra trên Chrome (Network tab)

- Mở F12 -> Network
- Gọi `POST /login`
- Chọn request và kiểm tra phần Response Headers có `Set-Cookie`
- Kiểm tra request kế tiếp có thể gửi `Cookie: session_id=...`

### 7) Dùng giao diện web thay cho curl

Giao diện đã thêm tại URL `http://127.0.0.1:2026/chat.html` (hoặc peer khác như `2027`).

Các bước dùng UI:

1. Mở 2 tab trình duyệt:
    - Tab A: `http://127.0.0.1:2026/chat.html`
    - Tab B: `http://127.0.0.1:2027/chat.html`
2. Login ở mỗi tab:
    - Nhập username
    - Self IP: `127.0.0.1`
    - Self P2P Port: `3026` cho peer 2026, `3027` cho peer 2027
3. Ở tab A, nhập peer cần kết nối trong khung Connect:
    - peer id: `peer-2027`
    - ip: `127.0.0.1`
    - port: `3027`
4. Dùng input cuối trang để gửi tin:
    - Chọn `Broadcast` để gửi tất cả peer đã connect
    - Chọn `Direct` để gửi riêng 1 peer
5. Tin nhắn sẽ tự refresh định kỳ và hiển thị trong khung chat.

---

## 🧪 Test nhanh framework cũ (tuỳ chọn)

Sau khi khởi chạy Backend Server (port `9000`):

```bash
# GET trang chủ
curl http://localhost:9000/

# GET trang login
curl http://localhost:9000/login.html
```

Sau khi khởi chạy Sample App (port `2026`):

```bash
# POST login
curl -X POST http://localhost:2026/login

# POST echo
curl -X POST http://localhost:2026/echo -H "Content-Type: application/json" -d '{"msg":"hello"}'

# PUT hello
curl -X PUT http://localhost:2026/hello
```

---

## 🧭 Quy trình Demo Đề Tài (gợi ý chấm điểm)

1. **Authentication (2 điểm)**
    - Gọi `POST /login` từ curl hoặc UI `chat.html`.
    - Mở Network tab để chứng minh `Set-Cookie` được trả về.
2. **ChatApp Client-Server (1 điểm)**
    - Gọi `submit-info`, `get-list` để chứng minh tracker hoạt động.
3. **ChatApp Peer-to-Peer (2 điểm)**
    - Gọi `connect-peer`, `broadcast-peer`, `send-peer` giữa 2 peer.
4. **Non-blocking mechanism (2 điểm)**
    - Trình bày file `apps/hybrid_chat.py` dùng `selectors`, socket non-blocking.
    - Nêu rõ xử lý `BlockingIOError` trong vòng lặp đọc/ghi.

---

## 📏 Coding Style & Docstring

Dự án tuân theo yêu cầu học phần:

- **PEP 8**: style code Python (đặt tên, khoảng trắng, line length, import order).
- **PEP 257**: docstring cho module, class, function.
- Backend và framework dùng **Python standard library**.
- JavaScript chỉ dùng ở client-side (UI) để tương tác bất đồng bộ.

Khuyến nghị trước khi nộp:

```bash
python -m py_compile Ass1/apps/sampleapp.py Ass1/apps/hybrid_chat.py Ass1/daemon/httpadapter.py Ass1/daemon/response.py
python scripts/smoke_test.py
```

---

## 📦 Submission Checklist

1. Đảm bảo source code chạy được theo hướng dẫn ở phần test.
2. Đặt file báo cáo vào thư mục source code gốc (`BTL/`).
3. Nén toàn bộ thư mục source thành file:
    - `assignment_STUDENTID.zip`
4. Submit file zip lên LMS.

Khuyến nghị nội dung report:

- Kiến trúc hệ thống và sơ đồ luồng.
- Thiết kế protocol cho Hybrid Chat.
- Cơ chế non-blocking đã chọn (callback/selectors hoặc coroutine).
- Cách xử lý lỗi và kiểm thử.
- Ảnh chụp màn hình các ca demo chính.

---

## 🧮 Grading (theo đề bài)

- **Demonstration: 7 điểm**
  - Authentication: 2 điểm
  - ChatApp Client-server paradigm: 1 điểm
  - ChatApp Peer-to-peer paradigm: 2 điểm
  - Non-blocking communication mechanism: 2 điểm
- **Report: 3 điểm**

---

## ⚖️ Code of Ethics & License Scope

- Source code framework thuộc bản quyền của giảng viên/phụ trách môn học.
- Sinh viên được cấp quyền cá nhân để sử dụng/chỉnh sửa mã nguồn cho mục đích học tập trong CO3093/CO3094 tại HCMUT.
- Không sử dụng mã nguồn cho mục đích thương mại hoặc phát hành ngoài phạm vi học phần nếu chưa có sự cho phép của tác giả.

---

## 📄 License

MIT License — Chỉ dùng cho mục đích học tập trong môn CO3093/CO3094 tại HCMUT.

---

> **Lưu ý:** Đây là dự án bài tập lớn (Assignment 1). Nhiều phần được đánh dấu `TODO` cần sinh viên tự hoàn thiện theo yêu cầu đề bài trong file `assignment1-asynaprous.pdf`.
