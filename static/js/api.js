// **************
// 後端溝通區
// **************

// ===== 判斷伺服器回傳是不是 JSON =====
// 是 => 解析並檢查 HTTP 狀態
// 不是 => 直接當錯誤處理
async function parseJsonResponse(response) {
    // 從 HTTP header 取得 Content-Type(後端回傳資料時留下的資料格式說明)
    const contentType = response.headers.get('content-type') || ''; 

    // 檢查是否包含 application/json (標準 JSON API 回應)
    if (contentType.includes('application/json')) {
        const data = await response.json(); // 把 body 轉成 JS 物件
        // 檢查是否有錯誤碼
        if (!response.ok) {
            // 如果後端有錯誤訊息，則直接輸出；沒有的話輸出錯誤碼(確認有data也有massage欄位)
            throw new Error(
                data && data.message
                 ? data.message :
                  `伺服器錯誤 (status ${response.status})`);
        }
        return data;
    // 處理伺服器錯誤時的網頁錯誤訊息，立即傳錯避免後續程式誤用資料(非JSON)
    } else {
        const text = await response.text(); // 轉成文字
        console.error('非 JSON 回應：', response.status, text);
        throw new Error(`伺服器回傳非 JSON 回應 (status ${response.status})`);
    }
}

// ===== 登入api =====
export async function login(formData) {
    const response = await fetch('/login', {
        method: 'POST',
        body: formData
    });
    return await parseJsonResponse(response);
}

// ===== 註冊api =====
export async function register(formData) {
    const response = await fetch('/register', {
        method: 'POST',
        body: formData
    });
    return await parseJsonResponse(response);
}

// =====加入人臉api =====
export async function addFace(formData) {
    const response = await fetch('/add_face', {
        method: 'POST',
        body: formData
    });
    return await parseJsonResponse(response);
}

// ===== 測試人臉api ====
export async function testFace(formData) {
    const response = await fetch('/test_face', {
        method: 'POST',
        body: formData
    });
    return await parseJsonResponse(response);
}

// ===== 查看人臉資料庫 =====
export async function getFace() {
    const response = await fetch('/get_faces');
    return await parseJsonResponse(response);
}

// ===== 訪客驗證碼驗證 =====
export async function verifyBookingCode(formData) {
    // 把表單提交到後端，目的: '/verify_booking_code'，等待回應
    const response = await fetch('/verify_booking_code', {
        method: 'POST', // POST 請求
        body: formData // 要傳送的資料
    });            
    // 後端回應後，把回傳的資料轉 JSON 格式
    return await parseJsonResponse(response)

}
