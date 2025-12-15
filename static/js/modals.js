import * as DOM from "./dom.js" // 引入網頁元素
import { login, register, addFace, testFace, getFace } from "./api.js"; // 引入後端api溝通函式


// ===== 加入人臉按鈕 =====
export async function addFaceModal() {
    // ===== 加入人臉彈出視窗 =====  
    DOM.addFaceBtn.onclick = () => DOM.addFaceModal.style.display = 'block'; // 顯示視窗

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
            result = await addFace(formData) // 呼叫api函式
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