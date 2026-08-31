"""
====== 樹莓派元件控制(電腦端) - Quart (非同步) 版本 =====
"""
import msvcrt
import time
import modules.config as config
from .config import RPI_IP_ADDRESS, RPI_PORT
import asyncio  
# [修改] Quart 為非同步框架，使用 httpx 取代 requests 以避免阻塞事件迴圈
import httpx 

# ===== 樹梅派元件延遲關閉 =====
# [修改] 改為非同步函式 (async def)
async def rpi_time_check():
    # ----- 馬達關閉時間檢查 -----
    if config.door_start_time and time.time() - config.door_start_time >= 3: 
        print("發送關門指令 by resberryPi")
        # [修改] 呼叫非同步函式需加上 await
        await rpi_to_servo('90')  
        config.door_start_time = None
        config.door_last_state = False
        print(f"開門狀態: {config.door_last_state} by resberryPi")
        
    # ----- RBGLED關閉時間檢查 -----
    if config.rgbled_start_time and time.time() - config.rgbled_start_time >= 2: 
        print(f"RGBLED切換為 {config.rgbled_color} by resberryPi")
        # [修改] 呼叫非同步函式需加上 await
        await rpi_to_rgbled('yellow')  
        config.rgbled_start_time = None

# ===== 發送訊息給伺服馬達 =====
# [修改] 改為非同步函式
async def rpi_to_servo(command):
    url = f"http://{RPI_IP_ADDRESS}:{RPI_PORT}/servo/{command}"
    try:
        # [修改] 使用 httpx.AsyncClient 進行非同步 HTTP 請求
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=2.0) 

        if response.status_code == 200:
            print(f"✅ 樹莓派回傳: {response.text}")
        else:
            print(f"❌ 請求失敗: HTTP {response.status_code}")
            print(f"錯誤訊息: {response.text}")

    except httpx.ConnectError:
        print("❌ 連線錯誤: 請檢查樹莓派 IP、埠號是否正確，以及樹莓派程式是否正在執行。")
    except httpx.TimeoutException:
        print("❌ 連線超時: 無法在預定時間內連線到樹莓派。")
    except Exception as e:
        print(f"❌ 發生未知錯誤: {e}")

# ===== 發送訊息給RGBLED =====
# [修改] 改為非同步函式[cite: 1]
async def rpi_to_rgbled(command):
    url = f"http://{RPI_IP_ADDRESS}:{RPI_PORT}/rgb/{command}"
    try:
        # [修改] 非同步 HTTP 請求[cite: 1]
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0) 

        if response.status_code == 200:
            print(f"✅ 樹莓派回傳: {response.text}")
        else:
            print(f"❌ 請求失敗: HTTP {response.status_code}")
            print(f"錯誤訊息: {response.text}")

    except httpx.ConnectError:
        print("❌ 連線錯誤: 請檢查樹莓派 IP、埠號是否正確。")
    except httpx.TimeoutException:
        print("❌ 連線超時: 無法在預定時間內連線到樹莓派。")
    except Exception as e:
        print(f"❌ 發生未知錯誤: {e}")

# ===== 發送訊息給DHT22 =====
# [修改] 改為非同步函式[cite: 1]
async def rpi_to_dht22():
    url = f"http://{RPI_IP_ADDRESS}:{RPI_PORT}/dht22/data"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=2.0)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ DHT22讀取成功 - 溫度: {data['temperature']}°C, 濕度: {data['humidity']}%")
            return {"success": True, "data": data}
        else:
            error_message = response.json().get('message', '未知錯誤')
            return {"success": False, "error": error_message}

    except httpx.ConnectError:
        error_message = "❌ 連線錯誤: 請檢查樹莓派 IP 或伺服器是否啟動"
        print(error_message)
        return {"success": False, "error": error_message}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ===== 發送訊息給MQ135 =====
# [修改] 改為非同步函式[cite: 1]
async def rpi_to_mq135():
    url = f"http://{RPI_IP_ADDRESS}:{RPI_PORT}/mq135/data"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            
        print(f"樹莓派回應: {response}")
        if response.status_code == 200:
            data = response.json()
            print(f"MQ135[{data['timestamp']}] 狀態: {data['message']} ({data['status']})")
            return {"success": True, "data": data}
        else:
            error_message = f"伺服器錯誤: {response.status_code} by mq135"
            print(f"❌ {error_message}")
            return {"success": False, "error": error_message}

    except httpx.ConnectError:
        error_message = "❌ 連線失敗：請檢查樹莓派 IP 或程式是否執行中。"
        print(error_message)
        return {"success": False, "error": error_message}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ===== 發送訊息給蜂鳴器 =====
# [修改] 改為非同步函式[cite: 1]
async def rpi_to_buzzer(command):
    url = f"http://{RPI_IP_ADDRESS}:{RPI_PORT}/bz/{command}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            
        if response.status_code == 200:
            return {"success": True}
        else:
            error_message = f"伺服器錯誤: {response.status_code}"
            print(f"❌ {error_message}")
            return {"success": False, "error": error_message}

    except httpx.ConnectError:
        error_message = "❌ 連線失敗：請檢查樹莓派 IP 或程式是否執行中。"
        return {"success": False, "error": error_message}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ===== 發送訊息給REDLED =====
# [修改] 改為非同步函式[cite: 1]
async def rpi_to_redled(command):
    url = f"http://{RPI_IP_ADDRESS}:{RPI_PORT}/redled/{command}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            
        if response.status_code == 200:
            return {"success": True}
        else:
            error_message = f"伺服器錯誤: {response.status_code}"
            return {"success": False, "error": error_message}

    except httpx.ConnectError:
        error_message = "❌ 連線失敗：請檢查樹莓派 IP 或程式是否執行中。"
        return {"success": False, "error": error_message}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ===== 開關門+RGBLED亮燈 =====
# [修改] 改為非同步函式[cite: 1]
async def open_door_and_rbgled():
        if config.rgbled_color:
            print(f"RGBLED切換為 {config.rgbled_color} by video_streaming")
            config.rgbled_start_time = time.time()
            # [修改] Quart 中不使用 threading.Thread，改用 asyncio.create_task 建立背景任務[cite: 1]
            asyncio.create_task(rpi_to_rgbled(config.rgbled_color))
            
        if config.door_open == True and config.door_last_state == False:
            print("發送開門指令 by video_streaming")
            config.door_start_time = time.time()  
            # [修改] 改用 asyncio.create_task 建立背景任務[cite: 1]
            asyncio.create_task(rpi_to_servo('0'))
            config.door_last_state = config.door_open 
            
        config.door_open = False
        print(f"開門狀態: {config.door_last_state} by video_streaming")

# [修改] Main 測試區也需要改為非同步結構[cite: 1]
async def main():
    print("--- 樹莓派伺服馬達遙控程式(功能測試) ---")
    print(f"目標樹莓派 IP: {RPI_IP_ADDRESS}:{RPI_PORT}")
    
    while True:
        try:
            print("1. servo開門+關門測試")
            print("2. RGBLED各顏色測試")
            print("3. 溫度感測器測試")
            print("4. 煙霧感測器測試")
            # 注意: input() 在非同步中會阻塞，但作為單純本地測試腳本可勉強保留
            user_input = input("請輸入指令: ").strip().lower() 
            if user_input == 'exit':
                print("程式結束。")
                break

            if user_input in ['1', '2', '3', '4']:
                if user_input == '1':
                    await rpi_to_servo('90') # [修改] 加上 await
                    await asyncio.sleep(1)   # [修改] 使用 asyncio.sleep 取代 time.sleep
                    await rpi_to_servo('0')  # [修改] 加上 await
                elif user_input == '2':
                    color = ['off', 'red', 'green', 'yellow', 'off']
                    for i in color:
                        await rpi_to_rgbled(i) # [修改] 加上 await
                        await asyncio.sleep(1) # [修改] 使用 asyncio.sleep
                elif user_input == '3':
                    print("進入溫度感測器測試，按下 x 可停止測試。")
                    stop_test = False 
                    while not stop_test:
                        result = await rpi_to_dht22() # [修改] 加上 await
                        if result['success']:
                            data = result['data']
                            print(f"✅ DHT22讀取成功 - 溫度: {data['temperature']}°C, 濕度: {data['humidity']}%")
                        else:
                            print(f"❌ DHT22讀取失敗: {result['error']}")    
                        print("（2秒後自動繼續，按 x 停止）")
                        for _ in range(20): 
                            if msvcrt.kbhit():
                                key = msvcrt.getwch()
                                if key.lower() == 'x':
                                    stop_test = True
                                    print("已停止溫度感測器測試。")
                                    break
                            await asyncio.sleep(0.1) # [修改] 使用 asyncio.sleep
                elif user_input == '4':
                    print("進入煙霧感測器測試，按下 x 可停止測試。")
                    stop_test = False
                    while not stop_test:
                        result = await rpi_to_mq135() # [修改] 加上 await
                        if result["success"]:
                            data = result["data"]
                            print(f"MQ135[{data['timestamp']}] 狀態: {data['message']} ({data['status']})")
                        else:
                            print(f"❌ MQ135讀取失敗: {result['error']}")
                        
                        print("（2秒後自動繼續，按 x 停止）")
                        for _ in range(20): 
                            if msvcrt.kbhit():
                                key = msvcrt.getwch() 
                                if key.lower() == 'x':
                                    stop_test = True
                                    print("已停止煙霧感測器測試。")
                                    break
                            await asyncio.sleep(0.1) # [修改] 使用 asyncio.sleep
            else:
                print("⚠️ 無效的輸入，請輸入 0, 1, 或 exit。")
                
        except KeyboardInterrupt:
            print("\n程式被手動中斷。")
            break
            
if __name__ == "__main__":
    # [修改] 使用 asyncio.run 來啟動非同步 main()[cite: 1]
    asyncio.run(main())