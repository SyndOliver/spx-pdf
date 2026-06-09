# spx-pdf

Dự án xử lý nhãn vận chuyển Shopee SPX và tích hợp Telegram Bot (in đậm SL ≥ 2, Combo, thêm lưu ý quay video).

## Hướng dẫn Deploy trên Server Linux

Có 2 cách chính để deploy dự án lên máy chủ Linux (Ubuntu/Debian):

---

### Cách 1: Sử dụng Docker & Docker Compose (Khuyên dùng)

Cách này đơn giản và ổn định nhất vì Docker đã đóng gói sẵn các font tiếng Việt cần thiết và môi trường Python chuẩn.

#### 1. Yêu cầu hệ thống
Đã cài đặt **Docker** và **Docker Compose**. Nếu chưa cài đặt, chạy lệnh sau:
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
```

#### 2. Deploy
1. Clone dự án về server:
   ```bash
   git clone https://github.com/SyndOliver/spx-pdf.git
   cd spx-pdf
   ```
2. Tạo và sửa cấu hình token trong file `.env`:
   ```bash
   cp .env.example .env  # hoặc tự tạo file .env mới
   nano .env
   ```
   Thêm nội dung:
   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   ```
3. Khởi chạy bot bằng Docker Compose:
   ```bash
   docker compose up --build -d
   ```
4. Kiểm tra log của bot:
   ```bash
   docker logs -f pdf-bot
   ```

---

### Cách 2: Chạy trực tiếp bằng Python & Systemd

#### 1. Cài đặt font hệ thống (Bắt buộc)
Để file PDF tiếng Việt hiển thị chính xác không lỗi font, bạn cần cài đặt các font tiếng Việt cho Linux:
```bash
sudo apt-get update
sudo apt-get install -y fonts-liberation fonts-dejavu-core
```

#### 2. Cài đặt Python và thư viện
1. Cài đặt Python 3.8+ và pip:
   ```bash
   sudo apt-get install -y python3 python3-pip python3-venv
   ```
2. Tạo virtual environment và cài đặt thư viện:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

#### 3. Cấu hình chạy ngầm với Systemd
Tạo một service file để quản lý bot tự động khởi động cùng hệ thống:

1. Tạo file service:
   ```bash
   sudo nano /etc/systemd/system/spx-bot.service
   ```
2. Dán nội dung cấu hình sau (nhớ thay đổi đường dẫn `/path/to/spx-pdf` cho phù hợp):
   ```ini
   [Unit]
   Description=SPX PDF Telegram Bot Service
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/path/to/spx-pdf
   Environment="TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here"
   ExecStart=/path/to/spx-pdf/venv/bin/python bot.py
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```
3. Khởi động service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable spx-bot
   sudo systemctl start spx-bot
   ```
4. Xem log hoạt động:
   ```bash
   sudo journalctl -u spx-bot -f
   ```