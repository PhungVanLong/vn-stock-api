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
CORS(app)

# =================================================================
# 3. CÁC HÀM HỖ TRỢ (HELPERS)
# =================================================================
def parse_symbols(symbols_str):
    """Tách danh sách mã cổ phiếu từ chuỗi"""
    if not symbols_str:
        return []
    return [s.strip().upper() for s in symbols_str.split(',') if s.strip()]

def fetch_price_for_symbol(symbol):
    """Lấy dữ liệu giá cho 1 mã cổ phiếu"""
    try:
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        quote = Quote(symbol=symbol)
        price_data = quote.history(start=start_date, end=end_date)
        
        if not price_data.empty:
            return symbol, price_data.tail(1).to_dict('records')[0]
        else:
            return symbol, f'Không có dữ liệu giá cho {symbol}'
    except Exception as e:
        return symbol, str(e)

# =================================================================
# 4. CÁC ROUTE (API ENDPOINTS)
# =================================================================

@app.route('/')
def home():
    return jsonify({
        'message': 'VNStock REST API Server - High Performance Edition',
        'version': '2.1',
        'vnstock_version': '3.2.5',
        'endpoints_optimized': {
            '/api/stocks/price?symbols=ACB,FPT,VCB': '⚡ Lấy giá nhiều mã đồng thời',
        },
        'endpoints_single_symbol': {
            '/api/stock/<symbol>': 'Thông tin tổng quan cổ phiếu',
            '/api/stock/<symbol>/price': 'Giá hiện tại (1 mã)',
            '/api/stock/<symbol>/history': 'Lịch sử giá',
            '/api/stock/<symbol>/company': 'Thông tin công ty',
            '/api/stock/<symbol>/intraday': 'Dữ liệu giá trong ngày (intraday)',
        },
        'example_usage': 'http://localhost:5000/api/stocks/price?symbols=ACB,FPT,TCB,HPG,VNM,MWG'
    })

# --- ⚡ ENDPOINT: LẤY GIÁ NHIỀU MÃ ĐỒNG THỜI ---
@app.route('/api/stocks/price')
def get_stocks_price():
    symbols_str = request.args.get('symbols')
    symbols = parse_symbols(symbols_str)

    if not symbols:
        return jsonify({'success': False, 'error': 'Vui lòng cung cấp mã cổ phiếu. Ví dụ: ?symbols=ACB,FPT,VCB'}), 400

    print(f"⚡️ Concurrent Request: Lấy giá cho các mã: {', '.join(symbols)}")

    results, errors = {}, {}

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_results = executor.map(fetch_price_for_symbol, symbols)
        for symbol, data_or_error in future_results:
            if isinstance(data_or_error, dict):
                results[symbol] = data_or_error
            else:
                errors[symbol] = data_or_error

    return jsonify({'success': True, 'data': results, 'errors': errors})

# --- 🧩 ENDPOINT: THÔNG TIN TỔNG QUAN ---
@app.route('/api/stock/<symbol>')
def get_stock_overview(symbol):
    try:
        quote = Quote(symbol=symbol.upper())
        overview = quote.overview()
        if overview.empty:
            return jsonify({'success': False, 'error': f'Không tìm thấy thông tin cho {symbol.upper()}'}), 404
        return jsonify({'success': True, 'symbol': symbol.upper(), 'data': overview.to_dict('records')[0]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# --- 💰 ENDPOINT: GIÁ HIỆN TẠI ---
@app.route('/api/stock/<symbol>/price')
def get_stock_price(symbol):
    try:
        quote = Quote(symbol=symbol.upper())
        price_data = quote.history(
            start=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            end=datetime.now().strftime('%Y-%m-%d')
        )
        if price_data.empty:
            return jsonify({'success': False, 'error': f'Không có dữ liệu giá cho {symbol.upper()}'}), 404
        return jsonify({'success': True, 'symbol': symbol.upper(), 'data': price_data.tail(1).to_dict('records')[0]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# --- ⏳ ENDPOINT: LỊCH SỬ GIÁ ---
@app.route('/api/stock/<symbol>/history')
def get_stock_history(symbol):
    try:
        start = request.args.get('start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
        quote = Quote(symbol=symbol.upper())
        history = quote.history(start=start, end=end)
        if history.empty:
            return jsonify({'success': False, 'error': f'Không có dữ liệu lịch sử cho {symbol.upper()}'}), 404
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'period': {'start': start, 'end': end},
            'count': len(history),
            'data': history.to_dict('records')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# --- 🏢 ENDPOINT: THÔNG TIN CÔNG TY ---
@app.route('/api/stock/<symbol>/company')
def get_company_info(symbol):
    try:
        quote = Quote(symbol=symbol.upper())
        company = quote.company()
        if company.empty:
            return jsonify({'success': False, 'error': f'Không có thông tin công ty cho {symbol.upper()}'}), 404
        return jsonify({'success': True, 'symbol': symbol.upper(), 'data': company.to_dict('records')[0]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# --- 📊 ENDPOINT: DỮ LIỆU INTRADAY ---
@app.route('/api/stock/<symbol>/intraday')
def get_intraday(symbol):
    try:
        quote = Quote(symbol=symbol.upper())
        intraday = quote.intraday()
        if intraday.empty:
            return jsonify({'success': False, 'error': f'Không có dữ liệu intraday cho {symbol.upper()}'}), 404
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'count': len(intraday),
            'data': intraday.to_dict('records')
        })
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
    print("📚 API Docs: http://localhost:5000/")
    print("\n✅ Endpoint tối ưu tốc độ:")
    print("   • http://localhost:5000/api/stocks/price?symbols=ACB,FPT,TCB,HPG,VNM,VIC,VHM,VCB,TCB,BID,MBB,HPG")
    print("\n💡 Thêm:")
    print("   • /api/stock/<symbol>/company")
    print("   • /api/stock/<symbol>/intraday")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
