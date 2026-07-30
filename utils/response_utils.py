from flask import jsonify

""" ===== 這裡放app.py的共用回傳函式"""

# **kwargs = 可以自由傳入資料項目

# ===== 回傳函式-成功 =====
def success_response(message="", status=200, **kwargs):
    response = {
        "success": True,
        "message": message
    }
    response.update(kwargs) # 把額外傳進來的 kwargs 合併進回應裡
    return jsonify(response), status

# ===== 回傳函式-失敗 =====
def error_response(message="", status=400, **kwargs):
    response = {
        "success": False,
        "message": message
    }
    response.update(kwargs) # 把額外傳進來的 kwargs 合併進回應裡
    return jsonify(response), status