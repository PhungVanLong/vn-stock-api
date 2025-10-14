# =================================================================
# 1. IMPORT CÁC THƯ VIỆN CẦN THIẾT
# =================================================================
from flask import Flask, jsonify, request
from flask_cors import CORS
from vnstock.explorer.vci.quote import Quote
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# =================================================================
# 2. KHỞI TẠO ỨNG DỤNG FLASK
# =================================================================
app = Flask(__name__)
CORS(app)  # Cho phép truy cập từ mọi nguồn (Cross-Origin Resource Sharing)

# =================================================================
# 3. CÁC HÀM HỖ TRỢ (HELPERS)
# =================================================================
def parse_symbols(symbols_str):
    """
    Tách chuỗi các mã cổ phiếu (phân cách bởi dấu phẩy) thành một danh sách.
    Ví dụ: "ACB, FPT, VCB " -> ['ACB', 'FPT', 'VCB']
    """
    if not symbols_str:
        return []
    return [s.strip().upper() for s in symbols_str.split(',') if s.strip()]

def fetch_price_for_symbol(symbol):
    """
    Lấy dữ liệu giá cho MỘT mã cổ phiếu. 
    Hàm này được thiết kế để chạy trong một luồng (thread) riêng biệt.
    """
    try:
        # Lấy dữ liệu trong 7 ngày gần nhất để đảm bảo có giá trị
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        quote = Quote(symbol=symbol)
        price_data = quote.history(start=start_date, end=end_date)
        
        if not price_data.empty:
            # Trả về tuple (mã, dữ liệu) nếu thành công
            return symbol, price_data.tail(1).to_dict('records')[0]
        else:
            # Trả về tuple (mã, thông báo lỗi) nếu không có dữ liệu
            return symbol, f'Không có dữ liệu giá cho {symbol}'
    except Exception as e:
        # Trả về tuple (mã, thông báo lỗi) nếu có exception
        return symbol, str(e)

# =================================================================
# 4. ĐỊNH NGHĨA CÁC ROUTE (API ENDPOINTS)
# =================================================================

# --- Route chính - Trang chủ ---
@app.route('/')
def home():
    """Hiển thị thông tin chung và danh sách các API endpoints."""
    return jsonify({
        'message': 'VNStock REST API Server - High Performance Edition',
        'version': '2.0',
        'vnstock_version': '3.2.5',
        'endpoints_optimized': {
            '/api/stocks/price?symbols=ACB,FPT,VCB': '⚡ (TỐI ƯU) Lấy giá nhiều mã đồng thời',
        },
        'endpoints_single_symbol': {
            '/api/stock/<symbol>': 'Thông tin tổng quan cổ phiếu',
            '/api/stock/<symbol>/price': 'Giá hiện tại (1 mã)',
            '/api/stock/<symbol>/history': 'Lịch sử giá',
            '/api/stock/<symbol>/company': 'Thông tin công ty',
            '/api/stock/<symbol>/intraday': 'Dữ liệu trong ngày',
        },
        'example_usage': 'http://localhost:5000/api/stocks/price?symbols=ACB,FPT,TCB,HPG,VNM,MWG'
    })

# --- ✨ ENDPOINT TỐI ƯU: LẤY GIÁ NHIỀU MÃ ĐỒNG THỜI ---
@app.route('/api/stocks/price')
def get_stocks_price():
    """
    Xử lý yêu cầu lấy giá cho nhiều mã cổ phiếu một cách đồng thời.
    Sử dụng ThreadPoolExecutor để tăng tốc độ phản hồi.
    """
    symbols_str = request.args.get('symbols')
    symbols = parse_symbols(symbols_str)

    if not symbols:
        return jsonify({
            'success': False,
            'error': 'Vui lòng cung cấp mã cổ phiếu. Ví dụ: ?symbols=ACB,FPT,VCB'
        }), 400

    print(f"⚡️ Concurrent Request: Lấy giá cho các mã: {', '.join(symbols)}")

    results = {}
    errors = {}

    # Sử dụng ThreadPoolExecutor để chạy các tác vụ lấy dữ liệu song song
    # max_workers=10 nghĩa là chạy tối đa 10 luồng cùng lúc
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Gửi tất cả các yêu cầu lấy dữ liệu cùng lúc
        future_results = executor.map(fetch_price_for_symbol, symbols)

        # Thu thập kết quả khi chúng hoàn thành
        for symbol, data_or_error in future_results:
            if isinstance(data_or_error, dict):  # Nếu kết quả là dữ liệu (dict) -> thành công
                results[symbol] = data_or_error
            else:  # Nếu kết quả là chuỗi (string) -> là thông báo lỗi
                errors[symbol] = data_or_error

    return jsonify({
        'success': True,
        'data': results,
        'errors': errors
    })

# --- CÁC ENDPOINT CŨ (XỬ LÝ 1 MÃ) - GIỮ ĐỂ TƯƠNG THÍCH ---

@app.route('/api/stock/<symbol>')
def get_stock_overview(symbol):
    try:
        quote = Quote(symbol=symbol.upper())
        overview = quote.overview()
        if overview.empty:
            return jsonify({'success': False, 'error': f'Không tìm thấy thông tin cho mã {symbol.upper()}'}), 404
        return jsonify({'success': True, 'symbol': symbol.upper(), 'data': overview.to_dict('records')[0]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/stock/<symbol>/price')
def get_stock_price(symbol):
    try:
        quote = Quote(symbol=symbol.upper())
        price_data = quote.history(start=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'), end=datetime.now().strftime('%Y-%m-%d'))
        if price_data.empty:
            return jsonify({'success': False, 'error': f'Không có dữ liệu giá cho {symbol.upper()}'}), 404
        return jsonify({'success': True, 'symbol': symbol.upper(), 'data': price_data.tail(1).to_dict('records')[0]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/stock/<symbol>/history')
def get_stock_history(symbol):
    try:
        start = request.args.get('start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
        quote = Quote(symbol=symbol.upper())
        history = quote.history(start=start, end=end)
        if history.empty:
            return jsonify({'success': False, 'error': f'Không có dữ liệu lịch sử cho {symbol.upper()}'}), 404
        return jsonify({'success': True, 'symbol': symbol.upper(), 'period': {'start': start, 'end': end}, 'count': len(history), 'data': history.to_dict('records')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# =================================================================
# 5. KHỞI CHẠY SERVER
# =================================================================
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 VNStock REST API Server - High Performance Edition")
    print("=" * 60)
    print("📍 URL: http://localhost:5000")
    print("📚 Tài liệu API: http://localhost:5000/")
    print("\n✅ Endpoint tối ưu tốc độ (khuyên dùng):")
    print("   • http://localhost:5000/api/stocks/price?symbols=ACB,FPT,TCB,HPG,VNM,VIC,VHM,VCB,TCB,BID,MBB,HPG")
    print("\n💡 Mở trình duyệt và truy cập URL trên để xem kết quả JSON.")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)