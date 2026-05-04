import cv2
import platform

class CameraManager:

    # ===== 尋找可用的相機系統後端 =====
    # 根據作業系統尋找可用的後端，讓相機使用適合的參數開啟
    # 回傳: 相機系統後端(列表)
    # ================================
    @staticmethod # 裝飾器，不需要其他變數來當物件，可以直接使用類別呼叫
    def get_camera_config():
        print("搜尋可用的相機系統後端 by camera_utils... ")

        # ***** 攝影機參數 *****
        # cv2.VideoCapture(0) => 使用預設後端(有可能使用到不適合的系統)
        # cv2.VideoCapture(0, cv2.【系統參數】) => 可以指定適合的系統
        # Windows => CAP_DSHOW(推薦), CAP_MSMF
        # macOS => CAP_AVFOUNDATION(推薦)
        # Linux => CAP_V4L2(推薦), CAP_GSTREAMER
        # *********************

        # ----- 取得作業系統資訊 -----
        os_type = platform.system() # 會回傳一個字串，代表你目前的作業系統
        backends = [] # 作業系統可用參數(回傳值)

        # ----- 根據作業系統選擇後端參數 -----
        if os_type == "Windows":    # windows系統
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_VFW]
        elif os_type == "Darwin":   # macOS系統
            backends = [cv2.CAP_AVFOUNDATION]
        elif os_type == "Linux":    # linux系統
            backends = [cv2.CAP_V4L2, cv2.CAP_GSTREAMER]
        else:
            backends = [cv2.CAP_ANY]
        
        print(f"選擇{backends}")

        return backends # 回傳「相機系統後端(列表)」
    
    # ===== 開啟攝影機 =====
    # 傳入: 相機索引、系統後端 
    # 回傳: 相機開啟函式
    # ===================== 
    @staticmethod
    def open_camera(index=0, backend=None):
        print("正在開啟相機...")
        # 如果有系統後端則使用，沒有則不使用
        if backend:
            print(f"使用索引{index} 系統參數{backend} by camera_utils")
            return cv2.VideoCapture(index, backend)
        print(f"使用索引{index} by camera_utils")
        return cv2.VideoCapture(index)
    
    # ===== 關閉攝影機&釋放資源 =====
    @staticmethod
    def clean_camera(cap):
        try:
            if cap and cap.isOpened():
                cap.release() # 釋放資源
            cv2.destroyAllWindows() # 關閉cv2所有視窗
            print("相機資源已釋放 by camera_utils")
        except Exception as e:
            print(f"釋放相機資源時發生錯誤 by camera_utils: {e}")

    # ===== 搜尋可用的攝影機 =====
    # 傳入: 相機物件
    # ===========================
    @staticmethod
    def find_camera(backends):
        # ----- 自動搜尋可用的攝影機 -----
        print("搜尋可用的攝影機...")
        
        # ----- 測試攝影機索引 0-5 -----
        for index in range(6):  
            print(f"  測試攝影機索引 {index}...")
            
            # ----- 逐個嘗試系統參數 -----
            for backend in backends: 
                try:
                    print(f"    嘗試後端: {backend}")
                    cap = cv2.VideoCapture(index, backend) # 測試攝影機

                    # ----- 測試是否能讀取影像 -----
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            cap.release() # 釋放攝影機資源(讓其他程式可以使用)
                            print(f"找到可用攝影機: 索引 {index}, 後端 {backend}")
                            return index, backend  # 立即回傳找到的設定(相機索引, 系統參數)

                    cap.release() # 釋放攝影機資源
                # 例外錯誤處理
                except Exception as e:
                    print(f"    後端 {backend} 失敗: {e}")
                    continue
        # 沒有找到任何可用攝影機
        print("沒有找到可用的攝影機")
        return None, None # 回傳空值

    @staticmethod
    def setup_camera(cap):
        pass

# ===== 測試程式 =====
def main():
    backends = CameraManager.get_camera_config() # 取得相機系統後端(列表)
    index, backend = CameraManager.find_camera(backends) # 尋找可用相機設定(相機索引, 系統參數)
    cap = CameraManager.open_camera(index, backend) # 開啟相機(開啟函式)
    if cap.isOpened():
        print("相機已開啟 by camera_utils")
        while True:
            ret, frame = cap.read() # 讀取影像
            # ----- 檢查是否正確讀取，沒有的話則跳出回圈 -----
            if not ret:
                break
            cv2.imshow("TEST CAMERA",frame) # 顯示畫面

            # ----- 按鍵偵測 -----
            key = cv2.waitKey(1) & 0xff
            if key == ord('q'):
                print("攝影機關閉 by camera_utils")
                break
    else:
        print("相機未開啟 by camera_utils")
    CameraManager.clean_camera(cap) # 釋放資源

if __name__ == "__main__":
    main()
    print("程式執行完畢 by camera_utils")