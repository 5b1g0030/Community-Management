import * as DOM from "./dom.js" // 引入網頁元素
import { addFace, testFace, getFace } from "./api.js"; // 引入後端api溝通函式

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
export async function viewFace() {
    DOM.viewFaceDbBtn.onclick = async () => {
        DOM.viewDbModal.style.display = 'block';
        setTimeout(() => centerModal(DOM.viewDbModal), 0); // 視窗置中

        try {
            const result = await getFace(); // 呼叫 api 程式
            DOM.modalTableBody.innerHTML = '';
            // 檢查回應是否成功且有 faces 陣列
            if (result.success && result.faces && Array.isArray(result.faces)) {
                result.faces.forEach(face => {
                    const row = document.createElement('tr');
                    row.innerHTML = `<td>${face.id}</td><td>${face.name}</td><td>${face.created_date || '無'}</td>`;
                    DOM.modalTableBody.appendChild(row);
                });
            } else {
                DOM.modalTableBody.innerHTML = `<tr><td colspan="3">無人臉資料</td></tr>`;
            }
        } catch (error) {
            DOM.modalTableBody.innerHTML = `<tr><td colspan="3">獲取資料失敗: ${error.message}</td></tr>`;
        }
    };
    // ===== 關閉資料庫彈出視窗 =====
    DOM.closeViewDbModal.onclick = () => {
        viewDbModal.style.display = 'none'; // 隱藏彈出視窗
        modalTableBody.innerHTML = '';      // 清除表格殘留的程式碼
    };
}

// ===== 訪客預約彈出視窗 =====
export function visitorBooking() {
    // 檢查必要元素是否存在
    if (!DOM.visitorBookingModal || !DOM.visitorBookingBtn || 
        !DOM.visitorBookingCloseBtn || !DOM.visitorBookingForm) {
        console.error('訪客預約相關元素未找到');
        return;
    }

    // 開啟彈窗
    DOM.visitorBookingBtn.onclick = function() {
        DOM.visitorBookingModal.style.display = 'block';
        setTimeout(() => centerModal(DOM.visitorBookingModal), 0);
    }

    // 關閉彈窗
    DOM.visitorBookingCloseBtn.onclick = function() {
        DOM.visitorBookingModal.style.display = 'none';
        DOM.visitorBookingForm.reset();
        DOM.frontFacePreview.innerHTML = '';
        DOM.leftFacePreview.innerHTML = '';
        DOM.rightFacePreview.innerHTML = '';
    }

    // 照片預覽功能
    function setupImagePreview(input, previewContainer) {
        if (!input || !previewContainer) return;
        
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
            const response = await fetch('/generate_booking_code', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

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
    DOM.visitorBookingModal  // 新增訪客預約 modal
].forEach(makeModalDraggable);
