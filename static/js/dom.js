// ******************
// DOM 元素管理區
// ******************

// ===== 功能按鈕、辨識紀錄元素 =====
export const addFaceBtn = document.getElementById('addFaceBtn');           // 「加入人臉」功能按鈕
export const testFaceBtn = document.getElementById('testFaceBtn');         // 「測試辨識」功能按鈕
export const viewFaceDbBtn = document.getElementById('viewFaceDbBtn');     // 「查看資料庫」功能按鈕
export const viewLogDbBtn = document.getElementById('viewLogDbBtn');       // 「查看辨識紀錄資料庫」功能按鈕
export const visitorBookingBtn = document.getElementById('visitorBookingBtn'); // 「訪客預約」功能按鈕
export const recognitionLog = document.getElementById('recognitionLog');       // 辨識紀錄清單

// ===== 加入人臉彈出視窗 =====
export const addFaceModal = document.getElementById('addFaceModal');           // 「加入人臉」浮空視窗
export const closeAddFaceModal = document.getElementById('closeAddFaceModal'); // 「加入人臉」關閉視窗鍵
export const modalUploadForm = document.getElementById('modalUploadForm');     // 上傳的表單元素
export const modalFaceImage = document.getElementById('modalFaceImage');       // 表單中圖片欄位
export const modalPersonName = document.getElementById('modalPersonName');     // 表單中人名

// ===== 測試辨識彈出視窗 =====
export const testFaceModal = document.getElementById('testFaceModal');           // 測試辨識-彈出視窗容器
export const closeTestFaceModal = document.getElementById('closeTestFaceModal'); // 測試辨識-關閉視窗按鈕
export const modalTestForm = document.getElementById('modalTestForm');           // 測試辨識-處理表單提交
export const modalTestImage = document.getElementById('modalTestImage');         // 測試辨識-顯示內容(在 testResult)
export const testResult = document.getElementById('testResult');                 // 測試辨識-清空顯示內容

// ===== 查看系統中已註冊的所有人臉資料 =====
export const viewDbModal = document.getElementById('viewDbModal');             // 人臉資料庫彈出視窗容器
export const closeViewDbModal = document.getElementById('closeViewDbModal');   // 關閉按鈕(人臉資料庫)
export const modalTableBody = document.getElementById('modalTableBody');       // 資料庫查詢表格

// ====== 查看辨識紀錄的所有資料 =====
export const viewLogDbModal = document.getElementById('viewLogDbModal');       // 辨識紀錄 Modal(彈出視窗)
export const closeViewLogDbModal = document.getElementById('closeViewLogDbModal'); // 關閉按鈕(辨識紀錄)
// export const modalLogTableBody = document.getElementById('modalLogTableBody'); // 辨識紀錄查詢表格

export const registerForm = document.getElementById('registerForm');
export const username = document.getElementById('username');
export const password = document.getElementById('password');
export const confirmPassword = document.getElementById('confirm_password');
export const usernameError = document.getElementById('usernameError');
export const passwordError = document.getElementById('passwordError');
export const confirmPasswordError = document.getElementById('confirmPasswordError');
export const submitMessage = document.getElementById('submitMessage');

export const loginForm = document.getElementById('loginForm');
export const loginMessage = document.getElementById('loginMessage');

// ===== 訪客預約彈出視窗元素 =====
export const visitorBookingModal = document.getElementById('visitorBookingModal'); // 訪客預約的 modal 容器
export const closeVisitorBookingModal = document.getElementById('closeVisitorBookingModal'); // 關閉按鈕
export const visitorBookingForm = document.getElementById('visitorBookingForm'); // 驗證碼輸入表單
export const bookingCodeInput = document.getElementById('bookingCodeInput');     // 使用者輸入的驗證碼欄位
export const bookingResult = document.getElementById('bookingResult');           // 顯示驗證和拍照結果的區塊


// ===== 匯出元素 =====

// 元素列表
const DOM = {
    addFaceBtn,
    testFaceBtn,
    viewFaceDbBtn,
    viewLogDbBtn,
    visitorBookingBtn,
    recognitionLog,

    addFaceModal,
    closeAddFaceModal,
    modalUploadForm,
    modalFaceImage,
    modalPersonName,

    testFaceModal,
    closeTestFaceModal,
    modalTestForm,
    modalTestImage,
    testResult,

    viewDbModal,
    closeViewDbModal,
    modalTableBody,

    viewLogDbModal,
    closeViewLogDbModal,

    registerForm,
    username,
    password,
    confirmPassword,
    usernameError,
    passwordError,
    confirmPasswordError,
    submitMessage,

    loginForm,
    loginMessage,

    visitorBookingModal,
    closeVisitorBookingModal,
    visitorBookingForm,
    bookingCodeInput,
    bookingResult
}; 

export default DOM