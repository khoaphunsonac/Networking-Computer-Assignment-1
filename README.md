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
    │   └── sampleapp.py          # Sample RESTful app (login, echo, hello)
    │
    ├── config/                   # Cấu hình
    │   └── proxy.conf            # Virtual host config cho Proxy
    │
    ├── www/                      # Static HTML pages
    │   ├── index.html            # Trang chủ
    │   ├── login.html            # Trang đăng nhập
    │   └── form.html             # Form mẫu
    │
    ├── static/                   # Static assets
    │   ├── css/
    │   ├── js/
    │   └── images/
    │
    ├── cert/                     # SSL certificates (trống — dự phòng cho HTTPS)
    └── db/                       # Database storage (trống — dự phòng)
```

---

## 🏗️ Kiến trúc hệ thống

```
┌─────────┐       ┌──────────────────┐       ┌──────────────────┐
│  Client  │──────▶│   Reverse Proxy  │──────▶│  Backend Server  │
│ (Browser)│◀──────│   (port 8080)    │◀──────│   (port 9000)    │
└─────────┘       └──────────────────┘       └──────────────────┘
                         │                          │
                         │  hostname routing        │  HttpAdapter
                         │  (proxy.conf)            │  Request/Response
                         │                          │
                         │                    ┌─────┴─────┐
                         │                    │ AsynapRous │
                         │                    │  (RESTful  │
                         │                    │   Router)  │
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

## 🧪 Test nhanh

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

## 📄 License

MIT License — Chỉ dùng cho mục đích học tập trong môn CO3093/CO3094 tại HCMUT.

---

> **Lưu ý:** Đây là dự án bài tập lớn (Assignment 1). Nhiều phần được đánh dấu `TODO` cần sinh viên tự hoàn thiện theo yêu cầu đề bài trong file `assignment1-asynaprous.pdf`.
