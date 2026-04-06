// ******************
// DOM 元素管理區
// ******************

// ===== 功能按鈕、辨識紀錄元素 =====
export const addFaceBtn = document.getElementById('addFaceBtn');           // 「加入人臉」功能按鈕
export const testFaceBtn = document.getElementById('testFaceBtn');         // 「測試辨識」功能按鈕
export const viewFaceDbBtn = document.getElementById('viewFaceDbBtn');     // 「查看資料庫」功能按鈕
export const viewLogDbBtn = document.getElementById('viewLogDbBtn');       // 「查看辨識紀錄資料庫」功能按鈕
export const packageRegisterBtn = document.getElementById('packageRegisterBtn'); // 新增
export const recognitionLog = document.getElementById('recognitionMessages');  // 辨識紀錄清單（修改為正確的 ID）

// ===== 相機控制元素 =====
export const toggleCameraBtn = document.getElementById('toggleCamera');    // 相機開關按鈕
export const cameraStatus = document.getElementById('cameraStatus');       // 相機狀態顯示

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

// ===== 訪客預約 Modal =====
export const visitorBookingBtn = document.getElementById('visitor-booking-btn'); // 「訪客預約」功能按鈕
export const visitorBookingModal = document.getElementById('visitor-booking-modal'); // 訪客預約彈出視窗
export const visitorBookingCloseBtn = document.querySelector('#visitor-booking-modal .close'); // 關閉按鈕
export const visitorBookingForm = document.getElementById('visitor-booking-form'); // 表單
export const bookingUsernameInput = document.getElementById('booking-username'); // 住戶名稱輸入框
    
// 照片上傳相關元素
export const frontFaceInput = document.getElementById('front-face-input');
export const leftFaceInput = document.getElementById('left-face-input');
export const rightFaceInput = document.getElementById('right-face-input');
export const frontFacePreview = document.getElementById('front-face-preview');
export const leftFacePreview = document.getElementById('left-face-preview');
export const rightFacePreview = document.getElementById('right-face-preview');

// 使用者註冊
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

// ===== 包裹登記 Modal =====
export const packageRegisterModal = document.getElementById('packageRegisterModal');
export const closePackageRegisterModal = document.getElementById('closePackageRegisterModal');
export const packageRegisterForm = document.getElementById('packageRegisterForm');
export const recipientNameInput = document.getElementById('recipientName');
export const lockerStatusDisplay = document.getElementById('lockerStatusDisplay');

// ===== 取貨相關元素 =====
export const pickUpBtn = document.getElementById('pickUpBtn');
export const pickUpModal = document.getElementById('pickUpModal');
export const closePickUpModal = document.getElementById('closePickUpModal');
export const pickupVideoStream = document.getElementById('pickup-video-stream');
export const pickupStatusMessage = document.getElementById('pickupStatusMessage'); // 新增

// ===== 火災監測元素 =====
export const zoneATemp = document.getElementById('zoneATemp');             // 火災監測 A區 數值
export const zoneBStatus = document.getElementById('zoneBStatus');         // 火災監測 B區 數值


// ================
// 匯出元素 
// ================
// 元素列表
const DOM = {
    zoneATemp,
    zoneBStatus,
    addFaceBtn,
    testFaceBtn,
    viewFaceDbBtn,
    viewLogDbBtn,
    packageRegisterBtn,
    packageRegisterModal,
    closePackageRegisterModal,
    packageRegisterForm,
    recipientNameInput,
    lockerStatusDisplay,
    recognitionLog,

    toggleCameraBtn,
    cameraStatus,

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

    visitorBookingBtn,
    visitorBookingModal,
    visitorBookingCloseBtn,
    visitorBookingForm,
    bookingUsernameInput,
    frontFaceInput,
    leftFaceInput,
    rightFaceInput,
    frontFacePreview,
    leftFacePreview,
    rightFacePreview,

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

    pickUpBtn,
    pickUpModal,
    closePickUpModal,
    pickupVideoStream,
    pickupStatusMessage,
}; 

export default DOM