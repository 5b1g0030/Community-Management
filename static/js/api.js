// **************
// 後端溝通區
// **************

async function parseJsonResponse(response) {
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data && data.message ? data.message : `伺服器錯誤 (status ${response.status})`);
        }
        return data;
    } else {
        const text = await response.text();
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
