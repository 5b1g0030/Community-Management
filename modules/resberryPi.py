"""
====== 樹莓派元件控制(電腦端) =====
"""

import msvcrt
import requests
import time
from .config import RPI_IP_ADDRESS, RPI_PORT

# ===== 發送訊息給伺服馬達 =====
# 【辨識到已知人物時開門，3秒後自動關上】
def rpi_to_servo(command):
    # 根據指令 1 或 0 構造 URL
    url = f"http://{RPI_IP_ADDRESS}:{RPI_PORT}/servo/{command}"
    
    try:
        # 發送 GET 請求
        response = requests.get(url, timeout=5) # 設定 5 秒超時
        
        # 檢查 HTTP 狀態碼
        if response.status_code == 200:
            print(f"✅ 樹莓派回傳: {response.text}")
        else:
            print(f"❌ 請求失敗: HTTP {response.status_code}")
            print(f"錯誤訊息: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ 連線錯誤: 請檢查樹莓派 IP、埠號是否正確，以及樹莓派程式是否正在執行。")
    except requests.exceptions.Timeout:
        print("❌ 連線超時: 無法在預定時間內連線到樹莓派。")
    except Exception as e:
        print(f"❌ 發生未知錯誤: {e}")

# ===== 發送訊息給RGBLED =====
# 【辨識人臉時呼叫，已知人物亮綠燈，未知人亮紅燈，2秒後變回常態的黃燈】
def rpi_to_rgbled(command):
    # 根據指令 1 或 0 構造 URL
    url = f"http://{RPI_IP_ADDRESS}:{RPI_PORT}/rgb/{command}"
    
    try:
        # 發送 GET 請求
        response = requests.get(url, timeout=5) # 設定 5 秒超時
        
        # 檢查 HTTP 狀態碼
        if response.status_code == 200:
            print(f"✅ 樹莓派回傳: {response.text}")
        else:
            print(f"❌ 請求失敗: HTTP {response.status_code}")
            print(f"錯誤訊息: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ 連線錯誤: 請檢查樹莓派 IP、埠號是否正確，以及樹莓派程式是否正在執行。")
    except requests.exceptions.Timeout:
        print("❌ 連線超時: 無法在預定時間內連線到樹莓派。")
    except Exception as e:
        print(f"❌ 發生未知錯誤: {e}")

# ===== RGBLED正式引用版 =====
# 傳入狀態(known=已知；unknown=未知；None=常態)
def open_rgbLed(state=None):
    if state == 'Known':
        rpi_to_rgbled('green')
        start_time = time.time()  # 記錄切換的開始時間
    elif state == 'Unknown':
        rpi_to_rgbled('red')
        start_time = time.time()  # 記錄切換的開始時間

    return start_time

# ===== 發送訊息給DHT22 =====
# 【每兩秒呼叫一次，更新資料】
def rpi_to_dht22():
    url = f"http://{RPI_IP_ADDRESS}:{RPI_PORT}/dht22/data"
    
    try:
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            #print(f"✅ DHT22讀取成功 - 溫度: {data['temperature']}°C, 濕度: {data['humidity']}%")
            return {"success": True, "data": data}
        else:
            error_message = response.json().get('message', '未知錯誤')
            return {"success": False, "error": error_message}

    except requests.exceptions.ConnectionError:
        error_message = "❌ 連線錯誤: 請檢查樹莓派 IP 或伺服器是否啟動"
        #print(error_message)
        return {"success": False, "error": error_message}
    except Exception as e:
        error_message = f"❌ 發生錯誤: {e}"
        #print(error_message)
        return {"success": False, "error": str(e)}

# ===== 發送訊息給MQ135 =====
# 【每兩秒呼叫一次，更新資料】
def rpi_to_mq135():
    url = f"http://{RPI_IP_ADDRESS}:{RPI_PORT}/mq135/data"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            #print(f"MQ135[{data['timestamp']}] 狀態: {data['message']} ({data['status']})")
            return {"success": True, "data": data}
        else:
            error_message = f"伺服器錯誤: {response.status_code}"
            print(f"❌ {error_message}")
            return {"success": False, "error": error_message}

    except requests.exceptions.ConnectionError:
        error_message = "❌ 連線失敗：請檢查樹莓派 IP 或程式是否執行中。"
        print(error_message)
        return {"success": False, "error": error_message}
    except Exception as e:
        error_message = f"❌ 發生錯誤: {e}"
        print(error_message)
        return {"success": False, "error": str(e)}

def main():
    print("--- 樹莓派伺服馬達遙控程式(功能測試) ---")
    print(f"目標樹莓派 IP: {RPI_IP_ADDRESS}:{RPI_PORT}")
    
    while True:
        try:
            # 控制測試區
            print("1. servo開門+關門測試")
            print("2. RGBLED各顏色測試")
            print("3. 溫度感測器測試")
            print("4. 煙霧感測器測試")
            user_input = input("請輸入指令: ").strip().lower()
            if user_input == 'exit':
                print("程式結束。")
                break

            if user_input in ['1', '2', '3', '4']:
                if user_input == '1':
                    rpi_to_servo('open') # 伺服馬達開門
                    time.sleep(1) # 停頓一秒
                    rpi_to_servo('close') # 伺服馬達關門
                elif user_input == '2':
                    color = ['off', 'red', 'green', 'yellow', 'off'] # 控制列表
                    for i in color:
                        rpi_to_rgbled(i) # 切換LED顏色
                        time.sleep(1) # 停頓一秒
                elif user_input == '3':
                    print("進入溫度感測器測試，按下 x 可停止測試。")
                    stop_test = False  # 新增一個標誌變數
                    while not stop_test:
                        result = rpi_to_dht22() # 獲取資料
                        if result['success']:
                            data = result['data']
                            print(f"✅ DHT22讀取成功 - 溫度: {data['temperature']}°C, 濕度: {data['humidity']}%")
                        else:
                            print(f"❌ DHT22讀取失敗: {result['error']}")    
                        print("（2秒後自動繼續，按 x 停止）")
                        for _ in range(20):  # 2秒，每0.1秒檢查一次
                            # 檢查是否有任何鍵被按下
                            if msvcrt.kbhit():
                                key = msvcrt.getwch() # 讀取這個按鍵的字元
                                if key.lower() == 'x':
                                    stop_test = True
                                    print("已停止溫度感測器測試。")
                                    break
                            time.sleep(0.1)
                elif user_input == '4':
                    print("進入煙霧感測器測試，按下 x 可停止測試。")
                    stop_test = False
                    while not stop_test:
                        result = rpi_to_mq135() # 獲取資料
                        if result["success"]:
                            data = result["data"]
                            print(f"MQ135[{data['timestamp']}] 狀態: {data['message']} ({data['status']})")
                        else:
                            print(f"❌ MQ135讀取失敗: {result['error']}")
                        
                        print("（2秒後自動繼續，按 x 停止）")
                        for _ in range(20):  # 2秒，每0.1秒檢查一次
                            # 檢查是否有任何鍵被按下
                            if msvcrt.kbhit():
                                key = msvcrt.getwch() # 讀取這個按鍵的字元
                                if key.lower() == 'x':
                                    stop_test = True
                                    print("已停止煙霧感測器測試。")
                                    break
                            time.sleep(0.1)
            else:
                print("⚠️ 無效的輸入，請輸入 0, 1, 或 exit。")
                
        except KeyboardInterrupt:
            print("\n程式被手動中斷。")
            break
            
if __name__ == "__main__":
    main()