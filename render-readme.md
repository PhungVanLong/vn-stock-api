# 🚀 VNStock REST API

API server để lấy dữ liệu chứng khoán Việt Nam từ thư viện vnstock, trả về JSON qua HTTP.

## 📚 Endpoints

- `GET /` - Trang chủ, danh sách tất cả endpoints
- `GET /api/test` - Test endpoint để kiểm tra API hoạt động
- `GET /api/stock/{symbol}` - Thông tin tổng quan cổ phiếu
- `GET /api/stock/{symbol}/price` - Giá hiện tại
- `GET /api/stock/{symbol}/history` - Lịch sử giá
- `GET /api/stock/{symbol}/company` - Thông tin công ty
- `GET /api/stock/{symbol}/intraday` - Dữ liệu trong ngày

## 🔧 Chạy local

```bash
# Cài đặt dependencies
pip install -r requirements.txt

# Chạy server
python app.py

# Hoặc dùng gunicorn (production)
gunicorn app:app
```

Truy cập: http://localhost:5000

## 🌐 Deploy lên Render.com

### Bước 1: Tạo GitHub Repository

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/vnstock-api.git
git push -u origin main
```

### Bước 2: Deploy trên Render

1. Truy cập https://render.com
2. Sign up/Login bằng GitHub
3. Click **New** → **Web Service**
4. Click **Connect GitHub** và chọn repository
5. Cấu hình:
   - **Name**: `vnstock-api` (hoặc tên bạn muốn)
   - **Environment**: `Python 3`
   - **Region**: `Singapore` (gần Việt Nam nhất)
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: `Free`
6. Click **Create Web Service**
7. Đợi 2-3 phút để deploy

### Bước 3: Test API

Sau khi deploy xong, bạn sẽ có URL dạng:
```
https://vnstock-api-xxxx.onrender.com
```

Test các endpoints:
```
https://vnstock-api-xxxx.onrender.com/
https://vnstock-api-xxxx.onrender.com/api/test
https://vnstock-api-xxxx.onrender.com/api/stock/ACB
https://vnstock-api-xxxx.onrender.com/api/stock/ACB/history?start=2024-01-01&end=2025-01-01
```

## ⚠️ Lưu ý về Free Tier

- Server sẽ "ngủ" sau 15 phút không có request
- Khi có request mới, server sẽ khởi động lại (mất ~30 giây)
- Để giữ server "thức" 24/7, dùng UptimeRobot ping mỗi 10 phút

## 🔄 Giữ server luôn chạy (Optional)

### Cách 1: Dùng UptimeRobot (Miễn phí)

1. Đăng ký tại https://uptimerobot.com
2. Tạo monitor mới:
   - **Monitor Type**: HTTP(s)
   - **URL**: `https://your-app.onrender.com/api/test`
   - **Monitoring Interval**: 5 minutes
3. Save → Done!

### Cách 2: Dùng Cron-Job.org (Miễn phí)

1. Đăng ký tại https://cron-job.org
2. Tạo cron job mới ping endpoint `/api/test` mỗi 10 phút

## 📊 Ví dụ sử dụng

### cURL
```bash
curl https://vnstock-api-xxxx.onrender.com/api/stock/ACB
```

### Python
```python
import requests

response = requests.get('https://vnstock-api-xxxx.onrender.com/api/stock/ACB/history', 
                       params={'start': '2024-01-01', 'end': '2025-01-01'})
data = response.json()
print(data)
```

### Java
```java
import java.net.http.*;
import java.net.URI;

HttpClient client = HttpClient.newHttpClient();
HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("https://vnstock-api-xxxx.onrender.com/api/stock/ACB"))
    .GET()
    .build();

HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
System.out.println(response.body());
```

### JavaScript
```javascript
fetch('https://vnstock-api-xxxx.onrender.com/api/stock/ACB/history?start=2024-01-01&end=2025-01-01')
  .then(response => response.json())
  .then(data => console.log(data));
```

## 🛠️ Tech Stack

- **Backend**: Flask (Python)
- **Data Source**: vnstock 3.2.5
- **Server**: Gunicorn
- **Hosting**: Render.com

## 📝 License

MIT

## 👤 Author

Your Name

## 🤝 Contributing

Pull requests are welcome!