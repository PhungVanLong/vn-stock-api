from flask import Flask, jsonify, request
from flask_cors import CORS
from vnstock.explorer.vci.quote import Quote
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)  # Cho phép truy cập từ mọi nguồn

# Route chính - Trang chủ
@app.route('/')
def home():
    return jsonify({
        'message': 'VNStock REST API Server',
        'version': '1.0',
        'vnstock_version': '3.2.5',
        'endpoints': {
            '/': 'Trang chủ - Danh sách endpoints',
            '/api/stock/<symbol>': 'Thông tin tổng quan cổ phiếu',
            '/api/stock/<symbol>/price': 'Giá hiện tại',
            '/api/stock/<symbol>/history': 'Lịch sử giá (params: start, end)',
            '/api/stock/<symbol>/company': 'Thông tin công ty',
            '/api/stock/<symbol>/intraday': 'Dữ liệu trong ngày',
        },
        'examples': {
            'overview': 'http://localhost:5000/api/stock/ACB',
            'price': 'http://localhost:5000/api/stock/ACB/price',
            'history': 'http://localhost:5000/api/stock/ACB/history?start=2024-01-01&end=2025-01-01',
            'company': 'http://localhost:5000/api/stock/ACB/company',
            'intraday': 'http://localhost:5000/api/stock/ACB/intraday',
        }
    })

# Lấy thông tin tổng quan cổ phiếu
@app.route('/api/stock/<symbol>')
def get_stock_overview(symbol):
    try:
        print(f"📊 Request: Tổng quan {symbol.upper()}")
        
        quote = Quote(symbol=symbol.upper())
        overview = quote.overview()
        
        if overview.empty:
            return jsonify({
                'success': False,
                'error': f'Không tìm thấy thông tin cho mã {symbol.upper()}'
            }), 404
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'data': overview.to_dict('records')[0]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

# Lấy giá hiện tại
@app.route('/api/stock/<symbol>/price')
def get_stock_price(symbol):
    try:
        print(f"💰 Request: Giá {symbol.upper()}")
        
        quote = Quote(symbol=symbol.upper())
        
        # Lấy giá 2 ngày gần nhất
        price_data = quote.history(
            start=(datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
            end=datetime.now().strftime('%Y-%m-%d')
        )
        
        if price_data.empty:
            return jsonify({
                'success': False,
                'error': f'Không có dữ liệu giá cho {symbol.upper()}'
            }), 404
        
        # Lấy ngày gần nhất
        latest = price_data.tail(1).to_dict('records')[0]
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'data': latest
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

# Lấy lịch sử giá
@app.route('/api/stock/<symbol>/history')
def get_stock_history(symbol):
    try:
        # Lấy tham số từ query string
        start = request.args.get('start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
        
        print(f"📈 Request: Lịch sử {symbol.upper()} từ {start} đến {end}")
        
        # Khởi tạo Quote object
        quote = Quote(symbol=symbol.upper())
        
        # Lấy dữ liệu lịch sử
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
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

# Thông tin công ty
@app.route('/api/stock/<symbol>/company')
def get_company_info(symbol):
    try:
        print(f"🏢 Request: Thông tin công ty {symbol.upper()}")
        
        quote = Quote(symbol=symbol.upper())
        
        # Lấy thông tin tổng quan công ty
        overview = quote.overview()
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'data': overview.to_dict('records')[0] if not overview.empty else {}
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

# Dữ liệu trong ngày (intraday)
@app.route('/api/stock/<symbol>/intraday')
def get_intraday(symbol):
    try:
        print(f"⏱️  Request: Dữ liệu trong ngày {symbol.upper()}")
        
        quote = Quote(symbol=symbol.upper())
        
        # Lấy dữ liệu intraday
        intraday = quote.intraday()
        
        if intraday.empty:
            return jsonify({
                'success': False,
                'error': f'Không có dữ liệu trong ngày cho {symbol.upper()}'
            }), 404
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'count': len(intraday),
            'data': intraday.to_dict('records')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

# Test endpoint
@app.route('/api/test')
def test():
    """Endpoint test để kiểm tra server hoạt động"""
    try:
        # Test với ACB như ví dụ
        quote = Quote(symbol='ACB')
        df = quote.history(start='2024-01-01', end='2025-01-01')
        
        return jsonify({
            'success': True,
            'message': 'API hoạt động tốt!',
            'sample_data': {
                'symbol': 'ACB',
                'rows': len(df),
                'first_5_rows': df.head().to_dict('records')
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 VNStock REST API Server")
    print("=" * 60)
    print("📍 URL: http://localhost:5000")
    print("📚 Tài liệu API: http://localhost:5000/")
    print("\n✅ Endpoints có thể test:")
    print("   • http://localhost:5000/api/test")
    print("   • http://localhost:5000/api/stock/ACB")
    print("   • http://localhost:5000/api/stock/ACB/price")
    print("   • http://localhost:5000/api/stock/ACB/history")
    print("   • http://localhost:5000/api/stock/ACB/history?start=2024-01-01&end=2025-01-01")
    print("   • http://localhost:5000/api/stock/ACB/company")
    print("   • http://localhost:5000/api/stock/ACB/intraday")
    print("\n💡 Mở trình duyệt và truy cập các URL trên để xem JSON")
    print("=" * 60)
    print()
    app.run(host='0.0.0.0', port=5000, debug=True)