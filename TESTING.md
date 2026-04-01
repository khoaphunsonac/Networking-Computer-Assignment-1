# Assignment 1 - Test Guide

## 1. Start Services (3 terminals)

Terminal 1:
```powershell
cd Ass1
python start_backend.py --server-ip 127.0.0.1 --server-port 9000
```

Terminal 2:
```powershell
cd Ass1
python start_sampleapp.py --server-ip 127.0.0.1 --server-port 2026
```

Terminal 3:
```powershell
cd Ass1
python start_proxy.py --server-ip 127.0.0.1 --server-port 8080
```

Expected:
- Each service prints a listening log and does not exit unexpectedly.

## 2. Test Backend Directly (port 9000)

```powershell
curl.exe http://127.0.0.1:9000/
curl.exe http://127.0.0.1:9000/login.html
```

Expected:
- Both requests return `HTTP 200`.
- `/` returns HTML content from `www/index.html`.
- `/login.html` returns HTML content from `www/login.html`.

## 3. Test Sample REST App Directly (port 2026)

```powershell
curl.exe -X POST "http://127.0.0.1:2026/login"
curl.exe -X POST "http://127.0.0.1:2026/echo" -H "Content-Type: application/json" --data '{"msg":"hello"}'
curl.exe -X PUT "http://127.0.0.1:2026/hello"
```

Expected:
- `POST /login` -> `200`, body contains `"Welcome to the RESTful TCP WebApp"`.
- `POST /echo` -> `200`, body contains `{"received":{"msg":"hello"}}` (format spacing may differ).
- `PUT /hello` -> `200`, body contains user info with `"name":"Alice"`.

## 4. Test Through Proxy (port 8080)

```powershell
curl.exe -H "Host: 127.0.0.1:8080" "http://127.0.0.1:8080/"
curl.exe -X POST -H "Host: sampleapp.local" "http://127.0.0.1:8080/login"
```

Expected:
- `GET /` via proxy -> `200`, returns backend homepage content.
- `POST /login` via proxy with `Host: sampleapp.local` -> `200`, returns sample app JSON welcome message.

## 5. One-Command Smoke Test

From repo root:
```powershell
python scripts/smoke_test.py
```

Expected:
- Output shows each check with `status=200 ok=True`.
- Final line is `Smoke test PASSED`.
- No service remains in `LISTENING` state after script exits.

## 6. Optional Port Check (PowerShell)

```powershell
netstat -ano | findstr ":9000 :2026 :8080"
```

Expected:
- After manual testing (while services are running): ports may show `LISTENING`.
- After stopping services or after smoke test: only `TIME_WAIT` is acceptable, no `LISTENING`.
