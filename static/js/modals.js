import * as DOM from "./dom.js" // 引入網頁元素
import { addFace, testFace, getFace } from "./api.js"; // 引入後端api溝通函式

// *************************
// 彈出視窗管理區
// *************************

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
    DOM.modalTestForm.onsubmit = async (e) => {
        e.preventDefault();
        if (!DOM.modalTestImage.files || DOM.modalTestImage.files.length === 0) {
            alert('請選擇圖片');
            return;
        }
        // 建立表單&加入資料
        const formData = new FormData();
        formData.append('image', DOM.modalTestImage.files[0]);
        try {
            const result = await testFace(formData) // 呼叫 api 函式
            DOM.testResult.textContent = result.message;
        } catch (error) {
            DOM.testResult.textContent = '辨識失敗: ' + error;
        }
    };
}

// ===== 查看資料庫彈出視窗 =====
export async function viewFace() {
    DOM.viewFaceDbBtn.onclick = async () => {
        DOM.viewDbModal.style.display = 'block';
        setTimeout(() => centerModal(DOM.viewDbModal), 0); // 視窗置中

        try {
            const faces = await getFace(); // 呼叫 api 程式
            DOM.modalTableBody.innerHTML = '';
            faces.forEach(face => {
                const row = document.createElement('tr');
                row.innerHTML = `<td>${face.id}</td><td>${face.name}</td><td>${face.created_date}</td>`;
                DOM.modalTableBody.appendChild(row);
            });
        } catch (error) {
            DOM.modalTableBody.innerHTML = `<tr><td colspan="3">獲取資料失敗: ${error.message}</td></tr>`;
        }
    };
    DOM.closeViewDbModal.onclick = () => {
        DOM.viewDbModal.style.display = 'none';
        DOM.modalTableBody.innerHTML = '';
    };
    // ===== 關閉資料庫彈出視窗 =====
    closeViewDbModal.onclick = () => {
        viewDbModal.style.display = 'none'; // 隱藏彈出視窗
        modalTableBody.innerHTML = '';      // 清除表格殘留的程式碼
    };
}

// ===== 訪客預約彈出視窗 =====
export async function visitorBooking() {
    // 當按下 id = visitorBookingBtn 的按鈕時，顯示彈出視窗
    // 箭頭函式
    DOM.visitorBookingBtn.onclick = () => {
        // 顯示視窗(CSS)
        DOM.visitorBookingModal.style.display = 'block'; 
        // 延遲執行此函式，瀏覽器渲染好，此函式會使 modal 置中。
        setTimeout(() => centerModal(DOM.visitorBookingModal), 0); 
    };
    // ===== 關閉訪客預約彈出視窗 =====
    // 當按下 id = closeVisitorBookingModal 的按鈕時，關閉彈出視窗
    DOM.closeVisitorBookingModal.onclick = () => {
        DOM.visitorBookingModal.style.display = 'none'; // 隱藏視窗(CSS)
        DOM.visitorBookingForm.reset(); // 清空表單避免資料殘留
        DOM.bookingResult.textContent = ''; // 清空在視窗上顯示的文字
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
[DOM.addFaceModal, DOM.testFaceModal,
 DOM.viewDbModal, DOM.viewLogDbModal,
 DOM.visitorBookingModal].forEach(makeModalDraggable);
