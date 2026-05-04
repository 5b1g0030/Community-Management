// Flask 網頁前端的 JavaScript 主程式檔案

// 瀏覽器要以 module 形式（<script type="module">）載入才能解析 import，
// 否則會在解析階段丟出語法錯誤，整個檔案就不會執行。

import * as DOM from "./dom.js" // 引入網頁元素
import { login, register, getFireStatus, FireStatusDanger } from "./api.js"; // 引入後端api溝通函式
import { addFaceModal, testFaceModal, viewFace, visitorBooking, initViewLogDbModal, pickUp, packageRegistration } from "./modals.js";
import { initializeRecognitionLogsTable, initRecognitionSocket, clearLogFilters } from "./recognitionLogs.js";
import { io } from "https://cdn.socket.io/4.6.1/socket.io.esm.min.js";
import { modalsClose } from "./modalController.js";

document.addEventListener('DOMContentLoaded', () => {

    // ===== 相機控制功能 =====
    if (DOM.toggleCameraBtn && DOM.cameraStatus) {
        let cameraActive = false;

        // 初始化相機狀態
        fetch('/camera_status')
            .then(res => res.json())
            .then(data => {
                cameraActive = data.active;
                updateCameraUI(cameraActive);
            })
            .catch(err => console.error('取得相機狀態失敗:', err));

        // 相機開關按鈕點擊事件
        DOM.toggleCameraBtn.addEventListener('click', async () => {
            try {
                const endpoint = cameraActive ? '/stop_camera' : '/start_camera';
                const response = await fetch(endpoint, { method: 'POST' });
                const result = await response.json();

                if (result.success) {
                    cameraActive = !cameraActive;
                    updateCameraUI(cameraActive);
                    alert(result.message);
                } else {
                    alert('操作失敗: ' + result.message);
                }
            } catch (error) {
                alert('操作失敗: ' + error.message);
            }
        });

        // 更新相機 UI 狀態
        function updateCameraUI(isActive) {
            if (isActive) {
                DOM.toggleCameraBtn.textContent = '關閉相機';
                DOM.toggleCameraBtn.classList.remove('btn-primary');
                DOM.toggleCameraBtn.classList.add('btn-danger');
                DOM.cameraStatus.textContent = '相機狀態: 開啟';
                DOM.cameraStatus.style.color = '#4CAF50';
            } else {
                DOM.toggleCameraBtn.textContent = '開啟相機';
                DOM.toggleCameraBtn.classList.remove('btn-danger');
                DOM.toggleCameraBtn.classList.add('btn-primary');
                DOM.cameraStatus.textContent = '相機狀態: 關閉';
                DOM.cameraStatus.style.color = '#f44336';
            }
        }
    }

    // ===== 登入功能（只在登入頁面執行） =====
    if (DOM.loginForm) {
        console.log("登入");
        DOM.loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (DOM.loginMessage) DOM.loginMessage.textContent = '';

            const formData = new FormData(DOM.loginForm); // 建立表單

            try {
                const result = await login(formData) // 呼叫api函式

                alert(result.message);
                console.log('/login result: ', result);
                if(result.redirect) {
                    window.location.href = result.redirect;
                }
                DOM.loginForm.reset();

            } catch (error) {
                alert('登入失敗: ' + error.message);
                DOM.loginForm.reset();
            }
        });
    }

    // ===== 註冊功能（只在註冊頁面執行） =====
    if (DOM.registerForm && DOM.username && DOM.password && DOM.confirmPassword) {
        console.log("密碼確認檢查")
        // 即時密碼確認檢查
        DOM.confirmPassword.addEventListener('input', () => {
            if (DOM.password.value !== DOM.confirmPassword.value) {
                if (DOM.confirmPasswordError) {
                    DOM.confirmPasswordError.textContent = '密碼不一致';
                    DOM.confirmPassword.style.borderColor = 'red';
                }
            } else {
                if (DOM.confirmPasswordError) {
                    DOM.confirmPasswordError.textContent = '';
                    DOM.confirmPassword.style.borderColor = '#ccc';
                }
            }
        });

        console.log("表單提交處理")
        // 表單提交處理
        DOM.registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            // 清空所有錯誤訊息
            if (DOM.usernameError) DOM.usernameError.textContent = '';
            if (DOM.passwordError) DOM.passwordError.textContent = '';
            if (DOM.confirmPasswordError) DOM.confirmPasswordError.textContent = '';
            if (DOM.submitMessage) DOM.submitMessage.textContent = '';

            // 驗證欄位
            if (DOM.username.value.trim().length < 3) {
                alert('使用者名稱至少需要3個字元');
                DOM.username.focus();
                return;
            }
            if (DOM.password.value.length < 6) {
                alert('密碼至少需要6個字元');
                DOM.password.focus();
                return;
            }
            if (DOM.password.value !== DOM.confirmPassword.value) {
                alert('密碼不一致');
                DOM.confirmPassword.focus();
                return;
            }

            try {
                const formData = new FormData();
                formData.append('username', DOM.username.value);
                formData.append('password', DOM.password.value);
                formData.append('confirm_password', DOM.confirmPassword.value);
                formData.append('role', document.querySelector('input[name="role"]:checked').value);
                
                const result = await register(formData)
                
                if (result.redirect){
                    window.location.href = result.redirect
                }
            } catch (error) {
                alert('註冊失敗：' + error.message);
                DOM.registerForm.reset();
            }
        });
    }

    // ===== 加入人臉彈出視窗 =====
    if (DOM.addFaceBtn){
        addFaceModal();
    }

    // ===== 測試辨識彈出視窗 =====
    if (DOM.testFaceBtn){
        testFaceModal();
    }

    // ===== 查看資料庫彈出視窗 =====
    if (DOM.viewFaceDbBtn){
        viewFace();
    }

    // ===== 取貨功能彈出視窗 =====
    if (DOM.pickUpBtn && DOM.pickUpModal) {
        pickUp()
    }

    // ===== 包裹登記彈出視窗 =====
    if (DOM.packageRegisterBtn) {
        packageRegistration()
    }

    // ===== 火災監測狀態更新 (每 3 秒更新) =====
    if (DOM.zoneATemp || DOM.zoneBStatus) {
        // ----- 警告樣式更新 -----
        function updateZoneWarning(zoneCard, isWarning) {
            if (isWarning) {
                zoneCard.classList.add('warning'); // 添加警告樣式
                console.log("添加警告樣式")
            } else {
                zoneCard.classList.remove('warning'); // 移除警告樣式
            }
        }
        // ----- 感測器資料寫入 -----
        // 先執行一次，避免剛載入時等待
        const updateFireStatus = async () => {
            try {
                const data = await getFireStatus(); // 呼叫api
                const dht22_temperature = data.dht22.temperature;
                const mq135_status = data.mq135.status;
                const mq135_message = data.mq135.message;
                // success: 表示 API 呼叫是否成功。
                // zone_a_temp: 區域 A 的溫度資訊(josn項目)。
                // zone_b_status: 區域 B 的狀態資訊。
                if (data.success) {
                    // 寫入資到網頁 data.mq135.status data.mq135.message
                    if (DOM.zoneATemp) DOM.zoneATemp.textContent = dht22_temperature;
                    if (DOM.zoneBStatus) DOM.zoneBStatus.textContent = mq135_message;
                }

                // 火災警報觸發邏輯
                // data.mq135.message = 有無煙霧
                // data.dht22.temperature = 溫度
                // await FireStatusDanger() = 觸發警報(交給後端處理)
                const isZoneAWarning = Number(dht22_temperature) > 26;
                const isZoneBWarning = mq135_status === "Danger";
                console.log("isZoneBWarning=",isZoneBWarning, mq135_status)
                console.log("isZoneAWarning=",isZoneAWarning)
                
                // 更新顯示樣式
                updateZoneWarning(DOM.Acard, isZoneAWarning);
                updateZoneWarning(DOM.Bcard, isZoneBWarning);

                if (isZoneAWarning || isZoneBWarning){
                    await FireStatusDanger() // 觸發警報(交給後端處理)
                }

            } catch (error) {
                console.error('取得火災監測狀態失敗:', error);
            }
        };
        
        // 網頁剛載入時，先手動執行一次，讓畫面立刻有數字
        updateFireStatus();

        // 設定定時器：每隔 3000 毫秒（3秒），就自動再執行一次 updateFireStatus 函式
        setInterval(updateFireStatus, 3000);
    }

    // *************************
    // 辨識紀錄篩選-初始化函式
    // *************************
    // ===== 初始化辨識紀錄 DataTable =====
    // var recognitionLogsTable = null; // DataTables 實例變數
    // 辨識紀錄即時推送
    const socket = io();
    initRecognitionSocket(socket); // 辨識紀錄及時顯示與更新
    
    // ===== 監聽取貨成功事件 =====
    socket.on('pickup_success', function(data) {
        console.log('[取貨] 收到取貨成功訊息:', data);
        
        // 顯示取貨訊息
        if (DOM.pickupStatusMessage) {
            DOM.pickupStatusMessage.textContent = data.message;
            DOM.pickupStatusMessage.style.display = 'block';
        }
        
        // 3 秒後自動關閉 Modal
        setTimeout(() => {
            if (DOM.pickUpModal && DOM.pickUpModal.style.display === 'block') {
                DOM.closePickUpModal.click();
            }
        }, 3000);
    });

    // 辨識紀錄彈窗
    if (DOM.viewLogDbBtn) {
        initViewLogDbModal({
            onOpen: () => initializeRecognitionLogsTable(),
            onClose: () => clearLogFilters()
        });
    }

    // **************
    // 訪客預約
    // **************
    // ===== 訪客預約彈出視窗 =====
    if (DOM.visitorBookingBtn) {
        visitorBooking();
    }
    
    // 點擊外部關閉 modal
    modalsClose();

});