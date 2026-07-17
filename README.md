# 🤖 Telegram Remote Dev Agent 🚀

Bảng điều khiển và Trợ lý AI lập trình (Coding Agent) từ xa, cho phép bạn quản lý dự án, biên dịch code, vận hành Docker, và lập trình trực tiếp bằng AI thông qua Telegram Bot. Hoàn toàn bảo mật, gọn nhẹ và tương tác thời gian thực 24/7.

---

## 🌟 Tính Năng VIP & Agentic Nổi Bật

*   **🧠 Trợ lý Lập trình Chủ động (`/troly`)**: Tự động phân tích trạng thái dự án hiện tại (Git branch, Docker, Resource tải phần cứng) khi bạn bắt đầu ngày mới và đề xuất 3 hành động lập trình tiếp theo.
*   **🗂 Bảng điều khiển Đa dự án (`/projects` hoặc `/p`)**: Quản lý song song nhiều dự án trong thư mục gốc. Bot tự động nạp cấu hình `.env` riêng biệt, phát hiện file `docker-compose.yml` và áp dụng môi trường làm việc động cho từng dự án con.
*   **🎛 Bàn phím điều khiển nhanh (`/menu`)**: Sử dụng bàn phím nút bấm Inline Keyboard của Telegram giúp kích hoạt nhanh các tác vụ hệ thống, Docker, Git mà không cần gõ lệnh.
*   **💬 Context Flags thông minh (`/ask`)**: Hỗ trợ đính kèm nhanh tài nguyên hệ thống vào context của **Gemini 3.5 Flash** (VD: `/ask -f main.py -d "Phân tích lỗi log này và sửa file"` tự động nhúng nội dung file code và `git diff` thực tế vào prompt).
*   **🔨 Biên dịch & Chẩn đoán lỗi Tự động (`/buildcheck`)**: Tự biên dịch code. Nếu gặp lỗi biên dịch, bot tự trích xuất log lỗi và chuyển tiếp cho Gemini 3.5 Flash phân tích nguyên nhân cùng giải pháp sửa đổi ngay lập tức.
*   **📖 File Viewer Phân trang Tương tác**: Đọc code trực tiếp bằng lệnh `/cat <file>`. File tự động đánh số dòng, chia trang (50 dòng/trang) và chèn nút bấm lật trang `[◀ Trang trước]` / `[Trang sau ▶]` mượt mà.
*   **🔔 Cảnh báo Đẩy (Push Notification) 24/7**: Chạy nền tự động giám sát CPU, RAM, Disk. Nếu phần cứng vượt ngưỡng quá tải (> 90%), bot sẽ chủ động nhắn tin cảnh báo cho bạn lập tức (cooldown 30 phút chống spam).

---

## 📋 Yêu cầu hệ thống

*   **Hệ điều hành**: Windows 10 / 11
*   **Python**: Phiên bản 3.10 trở lên
*   **Mạng**: Có kết nối internet
*   **Tài khoản**: Telegram cá nhân

---

## 🛠️ Cài đặt & Khởi động nhanh

### 1. Tạo Telegram Bot
1. Tìm kiếm `@BotFather` trên Telegram.
2. Gửi lệnh `/newbot` và đặt tên cho Bot.
3. BotFather sẽ cấp cho bạn một **Token** dạng: `1234567890:ABCdef...`
4. Copy token này điền vào file `.env`.

### 2. Lấy Chat ID của bạn (Bảo mật tuyệt đối)
1. Tìm kiếm `@userinfobot` trên Telegram và nhấn `/start`.
2. Bot sẽ trả về ID cá nhân của bạn (VD: `7314276066`).
3. Chỉ tài khoản Telegram có ID này mới có quyền ra lệnh cho máy tính của bạn. Điền ID này vào mục `ALLOWED_CHAT_ID` trong `.env`.

### 3. Cài đặt codebase trên máy tính
Mở Command Prompt hoặc PowerShell tại thư mục dự án và chạy:

```bash
# Tạo môi trường ảo python (khuyến nghị)
python -m venv venv
venv\Scripts\activate

# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

### 4. Thiết lập file cấu hình `.env`
Tạo file `.env` ở thư mục gốc của bot và cấu hình như sau:

```env
# ------ Telegram Bot Settings ------
BOT_TOKEN=8306953450:AAGC4LwWuJ3ABE0a...  # Token bot của bạn
ALLOWED_CHAT_ID=7314276066                 # Chat ID Telegram cá nhân của bạn

# ------ Project Settings ------
# Thư mục gốc chứa toàn bộ các dự án con của bạn
PROJECT_PATH=D:\ADMIN

# ------ AI Command Settings ------
# Sử dụng Gemini 3.5 Flash làm model lập trình mặc định
AI_COMMAND=gemini.cmd --model gemini-3.5-flash --skip-trust
GEMINI_API_KEY=AQ.Ab8RN6JRJD...           # API Key lấy từ Google AI Studio

# ------ Memory / Context Tuning ------
MEMORY_CONTEXT_N=5                         # Số lần hội thoại trước gửi kèm làm context
MEMORY_MAX_ENTRIES=100                     # Giới hạn số hội thoại lưu trữ trong file
CONTEXT_TREE_DEPTH=2                       # Độ sâu hiển thị cấu trúc cây thư mục trong GEMINI.md
```

---

## 🚀 Cách Vận Hành

### Chạy trực tiếp
```bash
venv\Scripts\activate
python main.py
```

### Thiết lập tự khởi động cùng Windows (Không cần Login)
Tôi đã chuẩn bị sẵn Script PowerShell để đăng ký bot chạy ngầm thông qua Windows Task Scheduler:

1. Click phải vào nút Start (hoặc bấm `Win + X`) → Chọn **Terminal (Admin)** hoặc **PowerShell (Admin)**.
2. Chạy lệnh đăng ký:
   ```powershell
   powershell -ExecutionPolicy Bypass -File register_startup_task.ps1
   ```
3. Từ bây giờ, bot sẽ tự động chạy ngầm mỗi khi máy tính bật lên mà không cần bạn phải đăng nhập tài khoản Windows.

---

## 🎮 Danh Sách Lệnh Điều Khiển

| Nhóm | Lệnh | Mô tả |
| :--- | :--- | :--- |
| **🎛 Dashboard** | `/menu` | Mở bảng điều khiển nhanh bằng nút bấm Inline |
| | `/troly` | Trợ lý chủ động phân tích dự án & đưa gợi ý hành động |
| **🗂 Projects** | `/projects` (hoặc `/p`) | Hiển thị danh sách dự án con và click để chuyển đổi dự án |
| **🖥 System** | `/status` | Xem hiệu năng CPU, RAM, Disk, Uptime, Path dự án |
| | `/ip` | Kiểm tra IP Local và IP Public của máy |
| | `/ping` | Kiểm tra phản hồi kết nối |
| **🤖 AI Agent** | `/ask <prompt>` | Gửi prompt lập trình. Hỗ trợ flag: `-f <file>` (đính kèm file), `-d` (đính kèm git diff), `-l` (đính kèm logs) |
| | `/context` | Xem file context dự án `GEMINI.md` |
| | `/context update` | Quét lại dự án và tự cập nhật `GEMINI.md` |
| | `/memory` | Xem lịch sử hội thoại gần nhất |
| | `/memory clear` | Xóa lịch sử hội thoại để dọn dẹp token |
| **📁 Explorer** | `/ls [thư_mục]` | Liệt kê danh sách file & thư mục con |
| | `/cat <đường_dẫn_file>` | Đọc file phân trang tương tác kèm số dòng |
| | `/run <lệnh>` | Chạy lệnh Terminal tùy ý trong thư mục dự án |
| **🔨 Build** | `/build` | Chạy lệnh build đã cấu hình trong `.env` |
| | `/buildcheck` | Build thử dự án & tự động phân tích sửa lỗi qua AI |
| **🐳 Docker** | `/docker ps` | Xem danh sách container đang chạy |
| | `/docker up` | Khởi động Docker Compose ngầm |
| | `/docker down` | Dừng toàn bộ Docker Compose |
| | `/docker logs` | Xem log container |
| **📋 Logs** | `/log [N]` | Xem N dòng log hệ thống gần nhất |

---

## 📂 Cấu trúc thư mục Agent

```
TelegramRemoteDev/
├── config/
│   ├── active_project.json  ← Lưu trạng thái project đang active (local)
│   └── config.py            ← Dynamic project-aware configuration
├── modules/
│   ├── assistant.py         ← Trợ lý chủ động /troly
│   ├── buildcheck.py        ← Biên dịch & tự sửa lỗi biên dịch
│   ├── projects.py          ← Multi-project manager
│   ├── explorer.py          ← Paged cat & ls file manager
│   ├── system.py            ← /status /ip /ping
│   ├── git.py               ← /git operations
│   ├── build.py             ← /build operations
│   ├── docker.py            ← /docker compose manager
│   ├── logs.py              ← /log viewer
│   ├── monitor.py           ← Resource monitor background task
│   └── ai.py                ← AI context provider & CLI wrapper
├── handlers/
│   └── commands.py          ← Command router & Button Callback dispatcher
├── utils/
│   ├── auth.py              ← ALLOWED_CHAT_ID guard decorator
│   ├── executor.py          ← Async subprocess execution
│   └── i18n.py              ← Hỗ trợ đa ngôn ngữ Vi/En
├── logs/
│   ├── agent.log            ← Logs vận hành của hệ thống
│   └── history.json         ← Lịch sử hội thoại AI lưu động
├── main.py                  ← Khởi chạy bot & polling event routing
├── register_startup_task.ps1← Powershell script đăng ký Windows Task Scheduler
├── start_bot.bat            ← Khởi động nhanh bot qua batch file
├── requirements.txt         ← Danh sách python dependencies
└── README.md                ← Tài liệu hướng dẫn sử dụng
```

---

## 🔒 Cơ chế bảo mật an toàn

*   **Access Control**: Chỉ có tin nhắn gửi từ tài khoản Telegram khớp với ID `ALLOWED_CHAT_ID` trong `.env` mới được xử lý. Tất cả các tài khoản khác nhắn tin cho bot đều nhận phản hồi `"Unauthorized."` và bị block.
*   **Chống scan cổng**: Bot hoạt động dựa trên cơ chế Long Polling (kết nối kéo dữ liệu từ Telegram Server), hoàn toàn không mở cổng inbound trên máy tính của bạn. Do đó, hacker không thể quét IP hay tấn công port máy tính qua internet.
*   **Bảo vệ đường dẫn**: Các module `ls` và `cat` đều được nhúng cơ chế ngăn chặn Path Traversal, chặn đứng việc đọc các file hệ thống nhạy cảm nằm ngoài phạm vi thư mục Base Path.

---

*Phát triển bởi Antigravity AI (Gemini 3.5 Flash) — Google DeepMind*
