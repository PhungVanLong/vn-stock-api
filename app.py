# =================================================================
# 1. IMPORT CÁC THƯ VIỆN CẦN THIẾT
# =================================================================
from flask import Flask, jsonify, request
from flask_cors import CORS
from vnstock.explorer.vci.quote import Quote
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import time
from functools import lru_cache
import threading

# =================================================================
# 2. KHỞI TẠO ỨNG DỤNG FLASK
# =================================================================
app = Flask(__name__)
CORS(app)

# =================================================================
# 3. RATE LIMITING CONFIGURATION
# =================================================================
REQUEST_DELAY = 0.5  # Delay 500ms giữa mỗi request
rate_limit_lock = threading.Lock()
last_request_time = {}

def rate_limited_request(symbol):
    """Đảm bảo không gọi API quá nhanh"""
    with rate_limit_lock:
        current_time = time.time()
        if symbol in last_request_time:
            time_since_last = current_time - last_request_time[symbol]
            if time_since_last < REQUEST_DELAY:
                time.sleep(REQUEST_DELAY - time_since_last)
        last_request_time[symbol] = time.time()

# =================================================================
# 4. CÁC HÀM HỖ TRỢ (HELPERS)
# =================================================================
def parse_symbols(symbols_str):
    """Tách danh sách mã cổ phiếu từ chuỗi"""
    if not symbols_str:
        return []
    return [s.strip().upper() for s in symbols_str.split(',') if s.strip()]

def fetch_price_for_symbol(symbol, max_retries=2):
    """Lấy dữ liệu giá cho 1 mã cổ phiếu với retry logic"""
    for attempt in range(max_retries):
        try:
            # Rate limiting
            rate_limited_request(symbol)
            
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            quote = Quote(symbol=symbol)
            price_data = quote.history(start=start_date, end=end_date)
            
            if not price_data.empty:
                return symbol, price_data.tail(1).to_dict('records')[0]
            else:
                return symbol, {'error': f'Không có dữ liệu giá cho {symbol}'}
                
        except SystemExit as e:
            # Bắt lỗi rate limit từ vnstock
            error_msg = str(e)
            if 'Rate limit exceeded' in error_msg:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    print(f"⚠️ Rate limit hit for {symbol}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                return symbol, {'error': 'Rate limit exceeded. Vui lòng thử lại sau.'}
            return symbol, {'error': f'SystemExit: {error_msg}'}
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return symbol, {'error': str(e)}
    
    return symbol, {'error': 'Max retries exceeded'}

# =================================================================
# 5. CÁC ROUTE (API ENDPOINTS)
# =================================================================

@app.route('/')
def home():
    return jsonify({
        'message': 'VNStock REST API Server - Production Ready',
        'version': '2.2',
        'vnstock_version': '3.2.5',
        'status': 'Rate limit protected ✅',
        'endpoints_optimized': {
            '/api/stocks/price?symbols=ACB,FPT,VCB': '⚡ Lấy giá nhiều mã (tối đa 5-10 mã/request)',
        },
        'endpoints_single_symbol': {
            '/api/stock/<symbol>': 'Thông tin tổng quan cổ phiếu',
            '/api/stock/<symbol>/price': 'Giá hiện tại (1 mã)',
            '/api/stock/<symbol>/history': 'Lịch sử giá',
            '/api/stock/<symbol>/company': 'Thông tin công ty',
            '/api/stock/<symbol>/intraday': 'Dữ liệu giá trong ngày (intraday)',
        },
        'rate_limit_info': {
            'delay_between_requests': f'{REQUEST_DELAY}s',
            'max_concurrent_symbols': '5 (recommended)',
            'retry_attempts': '2'
        },
        'example_usage': 'http://localhost:5000/api/stocks/price?symbols=ACB,FPT,TCB,HPG,VNM'
    })

# --- ⚡ ENDPOINT: LẤY GIÁ NHIỀU MÃ ĐỒNG THỜI ---
@app.route('/api/stocks/price')
def get_stocks_price():
    symbols_str = request.args.get('symbols')
    symbols = parse_symbols(symbols_str)

    if not symbols:
        return jsonify({
            'success': False, 
            'error': 'Vui lòng cung cấp mã cổ phiếu. Ví dụ: ?symbols=ACB,FPT,VCB'
        }), 400

    # Giới hạn số lượng symbols để tránh rate limit
    if len(symbols) > 10:
        return jsonify({
            'success': False,
            'error': f'Vượt quá giới hạn. Vui lòng gửi tối đa 10 mã/request (đang gửi {len(symbols)} mã)'
        }), 400

    print(f"⚡️ Processing request for: {', '.join(symbols)}")

    results, errors = {}, {}

    # Giảm số worker threads xuống 3 để tránh rate limit
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_results = executor.map(fetch_price_for_symbol, symbols)
        
        try:
            for symbol, data_or_error in future_results:
                if isinstance(data_or_error, dict):
                    if 'error' in data_or_error:
                        errors[symbol] = data_or_error['error']
                    else:
                        results[symbol] = data_or_error
                else:
                    errors[symbol] = str(data_or_error)
        except Exception as e:
            print(f"❌ Error in thread execution: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Có lỗi xảy ra khi xử lý request',
                'details': str(e)
            }), 500

    return jsonify({
        'success': True, 
        'data': results, 
        'errors': errors,
        'total_requested': len(symbols),
        'successful': len(results),
        'failed': len(errors)
    })

# --- 🧩 ENDPOINT: THÔNG TIN TỔNG QUAN ---
@app.route('/api/stock/<symbol>')
def get_stock_overview(symbol):
    try:
        rate_limited_request(symbol)
        quote = Quote(symbol=symbol.upper())
        overview = quote.overview()
        if overview.empty:
            return jsonify({
                'success': False, 
                'error': f'Không tìm thấy thông tin cho {symbol.upper()}'
            }), 404
        return jsonify({
            'success': True, 
            'symbol': symbol.upper(), 
            'data': overview.to_dict('records')[0]
        })
    except SystemExit as e:
        return jsonify({
            'success': False, 
            'error': 'Rate limit exceeded. Vui lòng thử lại sau.'
        }), 429
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# --- 💰 ENDPOINT: GIÁ HIỆN TẠI ---
@app.route('/api/stock/<symbol>/price')
def get_stock_price(symbol):
    try:
        rate_limited_request(symbol)
        quote = Quote(symbol=symbol.upper())
        price_data = quote.history(
            start=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            end=datetime.now().strftime('%Y-%m-%d')
        )
        if price_data.empty:
            return jsonify({
                'success': False, 
                'error': f'Không có dữ liệu giá cho {symbol.upper()}'
            }), 404
        return jsonify({
            'success': True, 
            'symbol': symbol.upper(), 
            'data': price_data.tail(1).to_dict('records')[0]
        })
    except SystemExit as e:
        return jsonify({
            'success': False, 
            'error': 'Rate limit exceeded. Vui lòng thử lại sau.'
        }), 429
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# --- ⏳ ENDPOINT: LỊCH SỬ GIÁ ---
@app.route('/api/stock/<symbol>/history')
def get_stock_history(symbol):
    try:
        rate_limited_request(symbol)
        start = request.args.get('start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
        quote = Quote(symbol=symbol.upper())
        history = quote.history(start=start, end=end)
        if history.empty:
            return jsonify({
                'success': False, 
                'error': f'Không có dữ liệu lịch sử cho {symbol.upper()}'
            }), 404
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'period': {'start': start, 'end': end},
            'count': len(history),
            'data': history.to_dict('records')
        })
    except SystemExit as e:
        return jsonify({
            'success': False, 
            'error': 'Rate limit exceeded. Vui lòng thử lại sau.'
        }), 429
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# --- 🏢 ENDPOINT: THÔNG TIN CÔNG TY ---
@app.route('/api/stock/<symbol>/company')
def get_company_info(symbol):
    try:
        rate_limited_request(symbol)
        quote = Quote(symbol=symbol.upper())
        company = quote.company()
        if company.empty:
            return jsonify({
                'success': False, 
                'error': f'Không có thông tin công ty cho {symbol.upper()}'
            }), 404
        return jsonify({
            'success': True, 
            'symbol': symbol.upper(), 
            'data': company.to_dict('records')[0]
        })
    except SystemExit as e:
        return jsonify({
            'success': False, 
            'error': 'Rate limit exceeded. Vui lòng thử lại sau.'
        }), 429
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# --- 📊 ENDPOINT: DỮ LIỆU INTRADAY ---
@app.route('/api/stock/<symbol>/intraday')
def get_intraday(symbol):
    try:
        rate_limited_request(symbol)
        quote = Quote(symbol=symbol.upper())
        intraday = quote.intraday()
        if intraday.empty:
            return jsonify({
                'success': False, 
                'error': f'Không có dữ liệu intraday cho {symbol.upper()}'
            }), 404
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'count': len(intraday),
            'data': intraday.to_dict('records')
        })
    except SystemExit as e:
        return jsonify({
            'success': False, 
            'error': 'Rate limit exceeded. Vui lòng thử lại sau.'
        }), 429
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# =================================================================
# 6. KHỞI CHẠY SERVER
# =================================================================
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 VNStock REST API Server - Production Ready")
    print("=" * 60)
    print("📍 URL: http://localhost:5000")
    print("📚 API Docs: http://localhost:5000/")
    print(f"\n⚡ Rate Limit Protection: {REQUEST_DELAY}s delay between requests")
    print("✅ Endpoint tối ưu:")
    print("   • http://localhost:5000/api/stocks/price?symbols=ACB,FPT,TCB,HPG,VNM")
    print("\n⚠️  Lưu ý: Giới hạn tối đa 10 mã/request để tránh rate limit")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)