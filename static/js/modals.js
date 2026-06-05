import * as DOM from "./dom.js" // 引入網頁元素
import { addFace, testFace, getFace, generateBookingCode, getLockerStatus, registerPackage, clearLocker, deleteFaces } from "./api.js"; // 引入後端api溝通函式

// ===== 加入人臉按鈕 =====
export async function addFaceModal() {
    // ===== 加入人臉彈出視窗 =====  
    DOM.addFaceBtn.onclick = () => DOM.addFaceModal.style.display = 'block'; // 顯示視窗
    setTimeout(() => centerModal(DOM.addFaceModal), 0); // 視窗置中

    // ===== 關閉加入人臉彈出視窗 =====
    DOM.closeAddFaceModal.onclick = () => {
        DOM.addFaceModal.style.display = 'none';
        DOM.modalUploadForm.reset();
    };

    // ===== 加入人臉 =====
    DOM.modalUploadForm.onsubmit = async (e) => {
        e.preventDefault();
        // 建立表單&加入資料
        const formData = new FormData();
        formData.append('image', DOM.modalFaceImage.files[0]);
        formData.append('name', DOM.modalPersonName.value);

        try {
            const result = await addFace(formData) // 呼叫api函式
            alert(result.message);
            DOM.addFaceModal.style.display = 'none';
            DOM.modalUploadForm.reset();
        } catch (error) {
            alert('上傳失敗：' + error.message);
        }
    };
}

// ===== 測試辨識按鈕 =====
export async function testFaceModal() {
    // ===== 測試辨識彈出視窗 =====
    DOM.testFaceBtn.onclick = () => DOM.testFaceModal.style.display = 'block';
    setTimeout(() => centerModal(DOM.testFaceModal), 0); // 視窗置中

    // ===== 關閉測試辨識彈出視窗 =====
    DOM.closeTestFaceModal.onclick = () => {
        DOM.testFaceModal.style.display = 'none';
        DOM.modalTestForm.reset();
        DOM.testResult.textContent = '';
    };
    // ===== 辨識過程 =====
    DOM.modalTestForm.onsubmit = async (e) => {
        e.preventDefault();
        if (!DOM.modalTestImage.files || DOM.modalTestImage.files.length === 0) {
            alert('請選擇圖片');
            return;
        }
        
        // 取得送出按鈕
        const submitBtn = DOM.modalTestForm.querySelector('button[type="submit"]');
        
        // 禁用送出按鈕，防止重複提交
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.style.opacity = '0.5';
            submitBtn.style.cursor = 'not-allowed';
        }
        
        // 顯示進度條容器
        let progressContainer = document.getElementById('test-progress-container');
        if (!progressContainer) {
            // 如果不存在，創建進度條元素
            progressContainer = document.createElement('div');
            progressContainer.id = 'test-progress-container';
            progressContainer.style.cssText = 'margin: 10px 0; width: 100%;';
            progressContainer.innerHTML = `
                <div style="background: #f0f0f0; border-radius: 5px; overflow: hidden; height: 25px; position: relative;">
                    <div id="test-progress-bar" style="background: linear-gradient(90deg, #4CAF50, #45a049); height: 100%; width: 0%; transition: width 0.3s; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; font-weight: bold;"></div>
                </div>
                <div id="test-progress-text" style="text-align: center; margin-top: 5px; font-size: 14px; color: #666;"></div>
            `;
            // 插入到結果顯示區域之前
            DOM.testResult.parentNode.insertBefore(progressContainer, DOM.testResult);
        }
        
        const progressBar = document.getElementById('test-progress-bar');
        const progressText = document.getElementById('test-progress-text');
        
        // 重置進度條
        progressBar.style.width = '0%';
        progressBar.textContent = '0%';
        progressText.textContent = '準備中...';
        progressContainer.style.display = 'block';
        
        // 清空結果
        DOM.testResult.textContent = '';
        
        // 模擬進度更新
        let progress = 0;
        const stages = [
            { progress: 10, text: '上傳圖片中...' },
            { progress: 30, text: '處理圖片中...' },
            { progress: 50, text: '偵測人臉中...' },
            { progress: 70, text: '提取特徵中...' },
            { progress: 90, text: '比對資料庫中...' }
        ];
        
        let stageIndex = 0;
        const progressInterval = setInterval(() => {
            if (stageIndex < stages.length) {
                const stage = stages[stageIndex];
                progress = stage.progress;
                progressBar.style.width = progress + '%';
                progressBar.textContent = progress + '%';
                progressText.textContent = stage.text;
                stageIndex++;
            }
        }, 800); // 每 0.8 秒更新一次進度
        
        // 建立表單&加入資料
        const formData = new FormData();
        formData.append('image', DOM.modalTestImage.files[0]);
        
        try {
            const result = await testFace(formData); // 呼叫 api 函式
            
            // 清除進度更新定時器
            clearInterval(progressInterval);
            
            // 完成進度條
            progressBar.style.width = '100%';
            progressBar.textContent = '100%';
            progressText.textContent = '辨識完成！';
            
            // 顯示結果
            if (result.success && result.results) {
                DOM.testResult.textContent = result.message + '\n\n' + 
                    result.results.map((r, i) => 
                        `結果: ${r.name} (信心度: ${r.confidence})`
                    ).join('\n');
            } else {
                DOM.testResult.textContent = result.message;
            }
            
            // 1秒後隱藏進度條
            setTimeout(() => {
                progressContainer.style.display = 'none';
            }, 1500);
            
        } catch (error) {
            // 清除進度更新定時器
            clearInterval(progressInterval);
            
            // 顯示錯誤
            progressBar.style.background = '#f44336';
            progressBar.style.width = '100%';
            progressBar.textContent = '錯誤';
            progressText.textContent = '辨識失敗';
            DOM.testResult.textContent = '辨識失敗: ' + error;
            
            // 2秒後隱藏進度條
            setTimeout(() => {
                progressContainer.style.display = 'none';
            }, 2000);
        } finally {
            // 恢復送出按鈕
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.style.opacity = '1';
                submitBtn.style.cursor = 'pointer';
            }
        }
    };
}

// ===== 查看資料庫彈出視窗 =====
let isDeleteMode = false; // 紀錄目前是否處於刪除模式
export async function viewFace() {
    // 獨立成一個函式，方便刪除後重新載入表格
    const loadFaceTable = async () => {
        try {
            const result = await getFace(); // 呼叫 api 程式
            DOM.modalTableBody.innerHTML = '';
            
            // 檢查回應是否成功且有 faces 陣列
            if (result.success && result.faces && Array.isArray(result.faces)) {
                result.faces.forEach(face => {
                    const row = document.createElement('tr');
                    // 根據 isDeleteMode 判斷是否顯示 checkbox
                    const checkboxDisplay = isDeleteMode ? 'table-cell' : 'none';
                    
                    row.innerHTML = `
                        <td class="delete-checkbox-col" style="display: ${checkboxDisplay}; text-align: center;">
                            <input type="checkbox" class="face-delete-cb" value="${face.id}" style="transform: scale(1.5);">
                        </td>
                        <td>${face.id}</td>
                        <td>${face.name}</td>
                        <td>${face.created_date || '無'}</td>`;
                    DOM.modalTableBody.appendChild(row);
                });
            } else {
                DOM.modalTableBody.innerHTML = `<tr><td colspan="4">無人臉資料</td></tr>`;
            }
        } catch (error) {
            DOM.modalTableBody.innerHTML = `<tr><td colspan="4">獲取資料失敗: ${error.message}</td></tr>`;
        }
    };

    // 更新刪除模式下的 UI (包含按鈕與欄位顯示/隱藏)
    const updateDeleteModeUI = () => {
        const cols = document.querySelectorAll('.delete-checkbox-col');
        if (isDeleteMode) {
            DOM.toggleDeleteModeBtn.textContent = '刪除確認';
            DOM.toggleDeleteModeBtn.style.backgroundColor = '#f44336'; // 變成紅色警告
            cols.forEach(col => col.style.display = 'table-cell');
        } else {
            DOM.toggleDeleteModeBtn.textContent = '刪除指定人臉';
            DOM.toggleDeleteModeBtn.style.backgroundColor = ''; // 恢復原按鈕顏色
            cols.forEach(col => col.style.display = 'none');
        }
    };

    // 點擊「查看已登錄人臉」按鈕
    DOM.viewFaceDbBtn.onclick = async () => {
        console.log("查詢資料中")
        DOM.viewDbModal.style.display = 'block';
        setTimeout(() => centerModal(DOM.viewDbModal), 0); // 視窗置中
        
        isDeleteMode = false; // 每次開啟預設為非刪除模式
        updateDeleteModeUI();
        await loadFaceTable();
    };

    // 點擊「刪除指定人臉/刪除確認」按鈕
    if (DOM.toggleDeleteModeBtn) {
        DOM.toggleDeleteModeBtn.onclick = async () => {
            if (!isDeleteMode) {
                // 進入刪除模式
                isDeleteMode = true;
                updateDeleteModeUI();
            } else {
                // 執行刪除動作
                const checkedBoxes = document.querySelectorAll('.face-delete-cb:checked');
                const selectedIds = Array.from(checkedBoxes).map(cb => parseInt(cb.value));

                if (selectedIds.length === 0) {
                    alert('請先勾選要刪除的人臉');
                    return;
                }

                // 彈出確認對話框
                if (confirm(`確定要刪除這 ${selectedIds.length} 筆人臉資料嗎？(該動作無法復原)`)) {
                    try {
                        const res = await deleteFaces(selectedIds);
                        if (res.success) {
                            alert('刪除成功！');
                            isDeleteMode = false; // 刪除完畢退出刪除模式
                            updateDeleteModeUI();
                            await loadFaceTable(); // 重新整理表格
                        } else {
                            alert('刪除失敗：' + res.message);
                        }
                    } catch (e) {
                        alert('發生錯誤：' + e.message);
                    }
                }
            }
        };
    }

    // ===== 關閉資料庫彈出視窗 =====
    DOM.closeViewDbModal.onclick = () => {
        DOM.viewDbModal.style.display = 'none'; // 隱藏彈出視窗
        DOM.modalTableBody.innerHTML = '';      // 清除表格殘留的程式碼
        isDeleteMode = false;                   // 重置刪除模式狀態
        updateDeleteModeUI();
    };
}

// ===== 訪客預約彈出視窗 =====
export async function visitorBooking() {
    // --- 檢查必要元素是否存在 ---
    if (!DOM.visitorBookingModal || !DOM.visitorBookingBtn || 
        !DOM.visitorBookingCloseBtn || !DOM.visitorBookingForm) {
        console.error('訪客預約相關元素未找到');
        return;
    }

    // --- 開啟彈窗 ---
    DOM.visitorBookingBtn.onclick = function() {
        DOM.visitorBookingModal.style.display = 'block';
        setTimeout(() => centerModal(DOM.visitorBookingModal), 0);
        // 照片預覽功能
        function setupImagePreview(input, previewContainer) {
            // 如果 input(照片) 或預覽容器不存在，就直接結束，不做任何事
            if (!input || !previewContainer) return;
            
            // 產生預覽標籤
            input.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        previewContainer.innerHTML = `<img src="${e.target.result}" alt="預覽" style="max-width: 100%; max-height: 150px;">`;
                    }
                    reader.readAsDataURL(file);
                }
            });
        }

        // 設定三個照片上傳的預覽
        setupImagePreview(DOM.frontFaceInput, DOM.frontFacePreview);
        setupImagePreview(DOM.leftFaceInput, DOM.leftFacePreview);
        setupImagePreview(DOM.rightFaceInput, DOM.rightFacePreview);

        // 表單提交處理
        DOM.visitorBookingForm.onsubmit = async function(e) {
            e.preventDefault();
            // 取得使用者名稱+訪客照片
            const username = DOM.bookingUsernameInput.value.trim();
            const frontFace = DOM.frontFaceInput.files[0];
            const leftFace = DOM.leftFaceInput.files[0];
            const rightFace = DOM.rightFaceInput.files[0];

            // 驗證
            if (!username) {
                alert('請輸入住戶名稱');
                return;
            }
            if (!frontFace || !leftFace || !rightFace) {
                alert('請上傳三張照片（正面、左微側、右微側）');
                return;
            }

            // 建立 FormData
            const formData = new FormData();
            formData.append('username', username);
            formData.append('front_face', frontFace);
            formData.append('left_face', leftFace);
            formData.append('right_face', rightFace);

            try {
                const result = await generateBookingCode(formData)

                if (result.success) {
                    alert(result.message);
                    DOM.visitorBookingModal.style.display = 'none';
                    DOM.visitorBookingForm.reset();
                    DOM.frontFacePreview.innerHTML = '';
                    DOM.leftFacePreview.innerHTML = '';
                    DOM.rightFacePreview.innerHTML = '';
                } else {
                    alert('預約失敗：' + result.message);
                }
            } catch (error) {
                alert('預約失敗：' + error.message);
            }
        }
    }

    // ---- 關閉彈窗 ---
    DOM.visitorBookingCloseBtn.onclick = function() {
        DOM.visitorBookingModal.style.display = 'none';
        DOM.visitorBookingForm.reset();
        DOM.frontFacePreview.innerHTML = '';
        DOM.leftFacePreview.innerHTML = '';
        DOM.rightFacePreview.innerHTML = '';
    }
}

// ===== 包裹登記彈出視窗 =====
export async function packageRegistration() {
    // 開啟 Modal
    DOM.packageRegisterBtn.onclick = async () => {
        DOM.packageRegisterModal.style.display = 'block';
        setTimeout(() => centerModal(DOM.packageRegisterModal), 0);
        
        // 載入櫃位狀態
        await loadLockerStatus();
    };
    
    // 關閉 Modal
    DOM.closePackageRegisterModal.onclick = () => {
        DOM.packageRegisterModal.style.display = 'none';
        DOM.packageRegisterForm.reset();
    };
    
    // 表單提交
    DOM.packageRegisterForm.onsubmit = async (e) => {
        e.preventDefault();
        
        const recipientName = DOM.recipientNameInput.value.trim();
        
        if (!recipientName) {
            alert('請輸入取件人姓名');
            return;
        }
        
        try {
            const result = await registerPackage(recipientName);
            
            if (result.success) {
                alert(result.message);
                DOM.packageRegisterForm.reset();
                // 重新載入櫃位狀態
                await loadLockerStatus();
            } else {
                alert('登記失敗：' + result.message);
            }
        } catch (error) {
            alert('登記失敗：' + error.message);
        }
    };
    
    // 清除櫃位按鈕事件（事件委派）
    DOM.lockerStatusDisplay.addEventListener('click', async (e) => {
        if (e.target.classList.contains('clear-locker-btn')) {
            const lockerNumber = parseInt(e.target.dataset.locker);
            
            if (confirm(`確定要清除 ${lockerNumber} 號櫃的登記資料嗎？`)) {
                try {
                    const result = await clearLocker(lockerNumber);
                    
                    if (result.success) {
                        alert(result.message);
                        await loadLockerStatus();
                    } else {
                        alert('清除失敗：' + result.message);
                    }
                } catch (error) {
                    alert('清除失敗：' + error.message);
                }
            }
        }
    });
}

// ===== 載入櫃位狀態 =====
async function loadLockerStatus() {
    try {
        const result = await getLockerStatus();
        
        if (result.success && result.lockers) {
            result.lockers.forEach(locker => {
                const lockerCard = document.getElementById(`locker${locker.locker_number}Status`);
                const statusText = lockerCard.querySelector('.locker-status');
                const recipientText = lockerCard.querySelector('.locker-recipient');
                const clearBtn = lockerCard.querySelector('.clear-locker-btn');
                
                // 移除舊的 class
                lockerCard.classList.remove('available', 'occupied');
                
                // 根據占用狀態賦予 CSS
                if (locker.is_occupied) {
                    // 已佔用CSS
                    lockerCard.classList.add('occupied');
                    statusText.textContent = '已佔用';
                    statusText.style.color = '#f44336';
                    recipientText.textContent = `取件人：${locker.recipient_name}`;
                    clearBtn.style.display = 'inline-block';
                } else {
                    // 空閒CSS
                    lockerCard.classList.add('available');
                    statusText.textContent = '空閒';
                    statusText.style.color = '#4CAF50';
                    recipientText.textContent = '';
                    clearBtn.style.display = 'none';
                }
            });
        }
    } catch (error) {
        console.error('載入櫃位狀態失敗：', error);
        alert('無法載入櫃位狀態');
    }
}

// ===== 取貨功能彈出視窗 =====
export async function pickUp() {
    // 按鈕事件
    DOM.pickUpBtn.addEventListener('click', async () => {
        try {
            // 1. 關閉主串流（停止相機）
            const stopResponse = await fetch('/stop_camera', { method: 'POST' });
            const stopResult = await stopResponse.json();

            if (!stopResult.success) {
                alert('無法關閉主串流：' + stopResult.message);
                return;
            }

            // 2. 開啟取貨 Modal
            DOM.pickUpModal.style.display = 'block';
            
            // 隱藏狀態訊息
            DOM.pickupStatusMessage.style.display = 'none';
            DOM.pickupStatusMessage.textContent = '';

            // 3. 設定取貨串流來源
            DOM.pickupVideoStream.src = '/pick_up_feed?' + new Date().getTime();

            console.log('[取貨] 取貨視窗已開啟');
        } catch (error) {
            alert('開啟取貨視窗失敗：' + error.message);
        }
    });

    // 關閉取貨 Modal
    const closePickUpWindow = async () => {
        try {
            // 1. 停止取貨串流
            DOM.pickupVideoStream.src = '';

            // 2. 關閉 Modal
            DOM.pickUpModal.style.display = 'none';
            
            // 隱藏狀態訊息
            DOM.pickupStatusMessage.style.display = 'none';
            DOM.pickupStatusMessage.textContent = '';

            // 3. 重新開啟主串流
            const startResponse = await fetch('/start_camera', { method: 'POST' });
            const startResult = await startResponse.json();

            if (startResult.success) {
                console.log('[取貨] 主串流已重新開啟');
                // 移除 updateCameraUI 呼叫
            } else {
                console.warn('[取貨] 重新開啟主串流失敗：', startResult.message);
            }

            console.log('[取貨] 取貨視窗已關閉');
        } catch (error) {
            console.error('關閉取貨視窗失敗：', error);
        }
    };

    // 點擊關閉按鈕
    if (DOM.closePickUpModal) {
        DOM.closePickUpModal.addEventListener('click', closePickUpWindow);
    }

    // 點擊 Modal 外部關閉
    DOM.pickUpModal.addEventListener('click', (e) => {
        if (e.target === DOM.pickUpModal) {
            closePickUpWindow();
        }
    });
}

// ===== 辨識紀錄 =====
export function initViewLogDbModal({
    onOpen,
    onClose
}) {
    if (!DOM.viewLogDbBtn) return;

    DOM.viewLogDbBtn.onclick = () => {
        DOM.viewLogDbModal.style.display = 'block';
        setTimeout(() => centerModal(DOM.viewLogDbModal), 0);
        if (onOpen) onOpen();
    };

    DOM.closeViewLogDbModal.onclick = () => {
        DOM.viewLogDbModal.style.display = 'none';
        if (onClose) onClose();
    };
}

// ===== Modal 拖曳與置中 =====
function centerModal(modal) {
    const content = modal.querySelector('.modal-content');
    content.style.left = 'calc(50vw - ' + (content.offsetWidth / 2) + 'px)';
    content.style.top = 'calc(50vh - ' + (content.offsetHeight / 2) + 'px)';
    content.style.zIndex = 2000;
}

// ===== 讓指定的 modal 可透過標題欄（<h2>）拖曳移動 =====
function makeModalDraggable(modal) {
    // 檢查有沒有彈窗
    if (!modal){
        console.log("沒有彈窗")
        return;
    };

    const header = modal.querySelector('h2'); // 取得 modal 的第一個 <h2>
    const content = modal.querySelector('.modal-content');
    if (!header || !content){
        console.log("沒有捕捉到<h2> 或 .modal-content 未連接成功")
        return; // 加入 return 避免後續錯誤
    };

    // 初始化拖曳狀態與滑鼠相對位移變數：isDragging 表示是否正在拖曳
    let isDragging = false, offsetX = 0, offsetY = 0;
    header.style.cursor = 'move'; // 將滑鼠游標改為可拖曳的樣式(提示作用)

    // ----- 開始拖移時的動作 -----
    header.onmousedown = function (e) {
        isDragging = true; // 進入拖曳狀態
        content.style.zIndex = 3000; // z軸提高(避免被遮擋)
        const rect = content.getBoundingClientRect(); // 
        offsetX = e.clientX - rect.left;
        offsetY = e.clientY - rect.top;
        document.onmousemove = function (e2) {
            if (isDragging) {
                content.style.position = 'fixed';
                content.style.left = (e2.clientX - offsetX) + 'px';
                content.style.top = (e2.clientY - offsetY) + 'px';
            }
        };
        document.onmouseup = function () {
            isDragging = false;
            content.style.zIndex = 2000;
            document.onmousemove = null;
            document.onmouseup = null;
        };
    };
}
// 需要拖移的視窗
[
    DOM.addFaceModal, 
    DOM.testFaceModal,
    DOM.viewDbModal, 
    DOM.viewLogDbModal,
    DOM.visitorBookingModal, 
    DOM.packageRegisterModal  // 新增
].forEach(makeModalDraggable);
