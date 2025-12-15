// **************
// 後端溝通區
// **************

// ===== 登入api =====
export async function login(formData) {
    // console.log("login api working... By api.js")
    const response = await fetch('/login',
        {
            method: 'POST',
            body: formData
        });
    const result = await response.json(); // 接收後端訊息

    // 如果發生錯誤則回傳錯誤訊息
    if (!response.ok){
        throw new Error(result.message || "登入失敗") // OR語句: 確保有可讀的錯誤訊息
    }

    return result
}

// ===== 註冊api =====
export async function register(formData) {
    const response = await fetch('/register', {
                    method: 'POST',
                    body: formData
                });
    const result = await response.json();

    // 如果發生錯誤則回傳錯誤訊息
    if (!response.ok){
        throw new Error(result.message || "註冊失敗") // 確保有可讀訊息
    }

    return result
}

// =====加入人臉api =====
export async function addFace(formData) {
    const response = await fetch('/add_face', {
        method: 'POST',
        body: formData
    });
    const result = await response.json()

    // 如果發生錯誤則回傳錯誤訊息
    if (!response.ok){
        throw new Error(result.message || "加入人臉失敗")
    }

    return result
}

// ===== 測試人臉api ====
export async function testFace(formData) {
    const response = await fetch('/test_face', {
                method: 'POST',
                body: formData
            });
    const result = await response.json();

    if (!response.ok){
        throw new Error(result.message || "測試人臉失敗")
    }

    return result
}

// ===== 查看人臉資料庫 =====
export async function getFace() {
    // 不需要上傳資料給後端，所以不需要 method 和 body
    const response = await fetch('/get_faces'); 
    const faces = await response.json();
    
    if (!response.ok) {
        throw new Error(faces.message || "查看人臉資料庫失敗")
    }

    return faces
}
