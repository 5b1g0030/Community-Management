import * as DOM from "./dom.js";
import { verifyBookingCode } from "./api.js";

export function initVisitorBooking() {
    // 當 id = visitorBookingForm 的表單被提交，執行下面程式
    // async => 宣告「非同步函式」的語法，不會使網頁停住 
    DOM.visitorBookingForm.onsubmit = async (e) => {
        e.preventDefault(); // 阻止預設提交，避免頁面被重新整理中斷後續操作
        const formData = new FormData(); // 建立表單
        // 將使用者輸入的「6位數字」加入表單，欄位 'booking_code'
        formData.append('booking_code', DOM.bookingCodeInput.value);

        try {
            // // 把表單提交到後端，目的: '/verify_booking_code'，等待回應
            // const response = await fetch('/verify_booking_code', {
            //     method: 'POST', // POST 請求
            //     body: formData // 要傳送的資料
            // });

            // // 後端回應後，把回傳的資料轉 JSON 格式
            // const result = await response.json();
            const result = await verifyBookingCode(formData); // 使用api函式取得後端資料

            if (result && result.message) {
                DOM.bookingResult.textContent = result.message;
            }
            if (result && result.start_countdown) {
                DOM.bookingResult.style.color = 'green';
                DOM.visitorBookingForm.reset();
                startVisitorPhotoCountdown(result.username, result.booking_code);
            } else {
                DOM.bookingResult.style.color = result && result.start_countdown ? 'green' : 'red';
            }
        } catch (error) {
            DOM.bookingResult.textContent = '驗證失敗：' + (error.message || error);
            DOM.bookingResult.style.color = 'red';
        }
    };
}


// ===== 訪客拍照倒數功能函式 =====
// 輸入: 使用者名稱, 驗證碼
// 輸出: HTML
// ==============================
function startVisitorPhotoCountdown(username, bookingCode) {
    let countdown = 3;
    const countdownInterval = setInterval(() => {
        DOM.bookingResult.innerHTML = `
                <div style="text-align: center;">
                    <h4>準備為 ${username} 的訪客拍照</h4>
                    <div style="font-size: 48px; color: #007bff; font-weight: bold;">${countdown}</div>
                    <p>請保持鏡頭前方有訪客身影</p>
                </div>
            `;

        countdown--;

        if (countdown < 0) {
            clearInterval(countdownInterval);
            captureVisitorPhoto(username, bookingCode);
        }
    }, 1000);
}

// ===== 擷取訪客照片函式 =====
// 輸入: 使用者名稱、驗證碼
// 輸出: HTML
// ========================== 
// async => 宣告「非同步函式」的語法，不會使網頁停住 
async function captureVisitorPhoto(username, bookingCode) {
    try {
        DOM.bookingResult.innerHTML = `
                <div style="text-align: center;">
                    <h4>正在拍照...</h4>
                    <p>📸</p>
                </div>
            `;

        const formData = new FormData();
        formData.append('username', username);
        if (bookingCode) {
            formData.append('booking_code', bookingCode);
        }

        const response = await fetch('/capture_visitor_photo', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            DOM.bookingResult.innerHTML = `
                    <div style="text-align: center;">
                        <h4>✅ 拍照成功！</h4>
                        <p>${result.message}</p>
                        <p>檔案名稱：${result.filename}</p>
                        ${result.db_message ? `<p>資料庫：${result.db_message}</p>` : ''}
                    </div>
                `;
            DOM.bookingResult.style.color = 'green';

            setTimeout(() => {
                DOM.visitorBookingModal.style.display = 'none';
                DOM.bookingResult.textContent = '';
                DOM.visitorBookingForm.reset();
            }, 3000);

        } else {
            DOM.bookingResult.innerHTML = `
                    <div style="text-align: center;">
                        <h4>❌ 拍照失敗</h4>
                        <p>${result.message}</p>
                        ${result.db_error ? `<p style="color: orange;">資料庫錯誤：${result.db_error}</p>` : ''}
                    </div>
                `;
            DOM.bookingResult.style.color = 'red';
        }
    } catch (error) {
        DOM.bookingResult.innerHTML = `
                <div style="text-align: center;">
                    <h4>❌ 拍照失敗</h4>
                    <p>錯誤：${error.message}</p>
                </div>
            `;
        DOM.bookingResult.style.color = 'red';
    }
}

