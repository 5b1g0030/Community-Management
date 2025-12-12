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