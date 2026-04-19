# Handling BlockingIOError in AsynapRous Project

## 1. **Cấu trúc hàm trong dự án**
Dựa trên thông tin từ file `README.md` và cấu trúc thư mục, dự án này được xây dựng với kiến trúc module hóa, bao gồm các thành phần chính:

### **1.1. `daemon/asynaprous.py` — AsynapRous Framework**
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

### **1.2. `daemon/proxy.py` — Reverse Proxy**
- Parse `Host` header từ request.
- Tra cứu routing table để xác định backend đích.
- Forward request và trả response về client.
- Hỗ trợ multi-threading cho concurrent connections.

### **1.3. `daemon/backend.py` — Backend Server**
Hỗ trợ 3 chế độ xử lý client:

| Mode         | Mô tả                                      |
|--------------|--------------------------------------------|
| `threading`  | Multi-thread (mặc định) — mỗi client 1 thread |
| `callback`   | Event-driven — sử dụng `selectors`         |
| `coroutine`  | Async/await — sử dụng `asyncio`            |

### **1.4. `daemon/httpadapter.py` — HTTP Adapter**
Quản lý toàn bộ lifecycle của một HTTP request:
- Nhận raw bytes từ socket.
- Parse thành object `Request`.
- Gửi response về client.

---

## 2. **Lỗi `BlockingIOError`**
Lỗi `BlockingIOError` thường xảy ra khi một socket không thể thực hiện ngay lập tức một thao tác I/O (như đọc/ghi) vì socket đang ở chế độ non-blocking. Trong dự án này, lỗi này có thể xảy ra trong các module như `proxy.py`, `backend.py`, hoặc `httpadapter.py` khi xử lý các kết nối socket.

### **2.1. Cách xử lý lỗi `BlockingIOError`**

#### **2.1.1. Sử dụng `try-except` để bắt lỗi**
Đảm bảo rằng các thao tác I/O trên socket được bao bọc bởi khối `try-except` để xử lý lỗi `BlockingIOError`.

Ví dụ:
```python
try:
    data = socket.recv(1024)
except BlockingIOError:
    # Xử lý lỗi, có thể bỏ qua hoặc log lại
    pass
```

#### **2.1.2. Sử dụng `select` hoặc `selectors`**
Thay vì thực hiện các thao tác I/O trực tiếp, sử dụng `select` hoặc `selectors` để kiểm tra xem socket có sẵn sàng để đọc/ghi hay không.

Ví dụ:
```python
import selectors
sel = selectors.DefaultSelector()
sel.register(socket, selectors.EVENT_READ)

events = sel.select(timeout=1)
for key, mask in events:
    if mask & selectors.EVENT_READ:
        data = key.fileobj.recv(1024)
```

#### **2.1.3. Chuyển sang chế độ blocking**
Nếu không cần thiết phải sử dụng non-blocking, có thể chuyển socket về chế độ blocking:
```python
socket.setblocking(True)
```

#### **2.1.4. Sử dụng `asyncio`**
Nếu dự án hỗ trợ coroutine, có thể sử dụng `asyncio` để xử lý I/O bất đồng bộ mà không gặp lỗi `BlockingIOError`.

Ví dụ:
```python
import asyncio

async def handle_client(reader, writer):
    data = await reader.read(100)
    writer.write(data)
    await writer.drain()
    writer.close()

asyncio.run(handle_client())
```

---

## 3. **Kết luận**
- Dự án AsynapRous sử dụng kiến trúc module hóa với các thành phần chính như Reverse Proxy, Backend Server, và RESTful Web Framework.
- Lỗi `BlockingIOError` có thể được xử lý bằng cách sử dụng `try-except`, `selectors`, hoặc chuyển sang chế độ blocking.
- Để tối ưu hóa, có thể sử dụng `asyncio` cho các tác vụ bất đồng bộ.

Nếu cần thêm thông tin hoặc hỗ trợ, hãy liên hệ qua email: **bksysnet@hcmut**.