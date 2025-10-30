// Flask 網頁前端的 JavaScript 主程式檔案

document.addEventListener('DOMContentLoaded', () => {
    // *****************************
    // 元素定義區
    // *****************************

    // ===== 功能按鈕、辨識紀錄元素 =====
    const addFaceBtn = document.getElementById('addFaceBtn');           // 「加入人臉」功能按鈕
    const testFaceBtn = document.getElementById('testFaceBtn');         // 「測試辨識」功能按鈕
    const viewFaceDbBtn = document.getElementById('viewFaceDbBtn');     // 「查看資料庫」功能按鈕
    const viewLogDbBtn = document.getElementById('viewLogDbBtn');       // 「查看辨識紀錄資料庫」功能按鈕
    const visitorBookingBtn = document.getElementById('visitorBookingBtn'); // 「訪客預約」功能按鈕
    const recognitionLog = document.getElementById('recognitionLog');       // 辨識紀錄清單

    // ===== 加入人臉彈出視窗 =====
    const addFaceModal = document.getElementById('addFaceModal');           // 「加入人臉」浮空視窗
    const closeAddFaceModal = document.getElementById('closeAddFaceModal'); // 「加入人臉」關閉視窗鍵
    const modalUploadForm = document.getElementById('modalUploadForm');     // 上傳的表單元素
    const modalFaceImage = document.getElementById('modalFaceImage');       // 表單中圖片欄位
    const modalPersonName = document.getElementById('modalPersonName');     // 表單中人名

    // ===== 測試辨識彈出視窗 =====
    const testFaceModal = document.getElementById('testFaceModal');           // 彈出視窗容器
    const closeTestFaceModal = document.getElementById('closeTestFaceModal'); // 關閉視窗按鈕
    const modalTestForm = document.getElementById('modalTestForm');           // 處理表單提交
    const modalTestImage = document.getElementById('modalTestImage');         // 顯示內容(在 testResult)
    const testResult = document.getElementById('testResult');                 // 清空顯示內容

    // ===== 查看系統中已註冊的所有人臉資料 =====
    const viewDbModal = document.getElementById('viewDbModal');             // 彈出視窗容器
    const closeViewDbModal = document.getElementById('closeViewDbModal');   // 關閉按鈕
    const modalTableBody = document.getElementById('modalTableBody');       // 資料庫查詢表格

    const viewLogDbModal = document.getElementById('viewLogDbModal');
    const closeViewLogDbModal = document.getElementById('closeViewLogDbModal');
    const modalLogTableBody = document.getElementById('modalLogTableBody'); // 辨識紀錄查詢表格

    const registerForm = document.getElementById('registerForm');
    const username = document.getElementById('username');
    const password = document.getElementById('password');
    const confirmPassword = document.getElementById('confirm_password');
    const usernameError = document.getElementById('usernameError');
    const passwordError = document.getElementById('passwordError');
    const confirmPasswordError = document.getElementById('confirmPasswordError');
    const submitMessage = document.getElementById('submitMessage');

    const loginForm = document.getElementById('loginForm');
    const loginMessage = document.getElementById('loginMessage');

    // ===== 登入功能（只在登入頁面執行） =====
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (loginMessage) loginMessage.textContent = '';

            const formData = new FormData(loginForm);

            try {
                const response = await fetch('/login', { method: 'POST', body: formData});
                const result = await response.json();

                if (response.ok) {
                    alert(result.message);
                    if(result.redirect) {
                        setTimeout(() => {
                            window.location.href = result.redirect;
                        }, 100);
                    }
                } else {
                    alert(result.message);
                    loginForm.reset();
                }
            } catch (error) {
                alert('登入失敗: ' + error.message);
                loginForm.reset();
            }
        });
    }

    // ===== 註冊功能（只在註冊頁面執行） =====
    if (registerForm && username && password && confirmPassword) {
        // 即時密碼確認檢查
        confirmPassword.addEventListener('input', () => {
            if (password.value !== confirmPassword.value) {
                if (confirmPasswordError) {
                    confirmPasswordError.textContent = '密碼不一致';
                    confirmPassword.style.borderColor = 'red';
                }
            } else {
                if (confirmPasswordError) {
                    confirmPasswordError.textContent = '';
                    confirmPassword.style.borderColor = '#ccc';
                }
            }
        });

        // 表單提交處理
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            // 清空之前的錯誤訊息
            if (usernameError) usernameError.textContent = '';
            if (passwordError) passwordError.textContent = '';
            if (confirmPasswordError) confirmPasswordError.textContent = '';
            if (submitMessage) submitMessage.textContent = '';

            // 前端驗證
            if (username.value.trim().length < 3) {
                alert('使用者名稱至少需要3個字元');
                username.focus();
                return;
            }

            if (password.value.length < 6) {
                alert('密碼至少需要6個字元');
                password.focus();
                return;
            }

            if (password.value !== confirmPassword.value) {
                alert('密碼不一致');
                confirmPassword.focus();
                return;
            }

            // 發送註冊請求
            try {
                const formData = new FormData();
                formData.append('username', username.value);
                formData.append('password', password.value);
                formData.append('confirm_password', confirmPassword.value);
                // 加上身分欄位（從 radio 讀取選中的值）
                formData.append('role', document.querySelector('input[name="role"]:checked').value);
                const response = await fetch('/register', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                if (response.ok) {
                    alert(result.message);
                    registerForm.reset();
                    window.location.href = '/login';
                } else {
                    alert(result.message);
                    registerForm.reset();
                }
            } catch (error) {
                alert('註冊失敗：' + error.message);
                registerForm.reset();
            }
        });
    }

    // ===== 加入人臉彈出視窗 =====  
    // 按下按鈕後，顯示視窗(display 設為 block)
    addFaceBtn.onclick = () => addFaceModal.style.display = 'block'; // 顯示視窗

    // ===== 關閉加入人臉彈出視窗 =====
    // 點擊關閉按鈕，隱藏視窗(display 設為 none)
    closeAddFaceModal.onclick = () => {
        addFaceModal.style.display = 'none'; // 隱藏視窗
        modalUploadForm.reset(); // 清空在視窗中輸入的資料，避免殘留
    };

    // 點擊送出按鈕，送出照片和人名到後端 
    modalUploadForm.onsubmit = async (e) => {
        e.preventDefault();                 // 阻止預設提交(避免網頁自動更新，導致 javaScript 函式無法執行或執行不完整)
        const formData = new FormData();    // 用來裝表單的資料
        formData.append('image', modalFaceImage.files[0]);  // 圖片儲存欄位名稱(image)
        formData.append('name', modalPersonName.value);     // 人名儲存欄位名稱(name)
        
        // ----- 例外處理語法 -----
        // 當 try 裡面執行的程式碼發生錯誤，將會跳到 catch 執行處理錯誤
        // error變數 => 儲存錯誤訊息
        // -----------------------
        try {
            // ----- 把資料送到後端的'/add_face' -----
            const response = await fetch('/add_face', {
                method: 'POST', // 指定用POST方法
                body: formData  // 人臉和姓名資料
            });
            const result = await response.json();   // 把後段傳回的資料轉換為json格式，取得處理結果(是否成功、辨識結果、資料庫內容、錯誤原因)
            alert(result.message);                  // 顯示處理結果或錯誤原因
            addFaceModal.style.display = 'none';    // 隱藏浮動視窗
            modalUploadForm.reset();                // 輸入欄位清空，避免資料殘留
        } catch (error) {
            alert('上傳失敗：' + error.message); // 展示錯誤訊息
        }
    };

    // ===== 測試辨識彈出視窗 =====
    testFaceBtn.onclick = () => testFaceModal.style.display = 'block';

    // ===== 關閉測試辨識彈出視窗 =====
    closeTestFaceModal.onclick = () => {
        testFaceModal.style.display = 'none';
        modalTestForm.reset();
        testResult.textContent = '';
    };
    modalTestForm.onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData();
        formData.append('image', modalTestImage.files[0]);
        try {
            const response = await fetch('/test_face', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            testResult.textContent = result.message;
        } catch (error) {
            testResult.textContent = '辨識失敗';
        }
    };

    // ===== 查看資料庫彈出視窗 =====
    // 「()=>」 => 箭頭函式，一般 function 的簡寫版
    viewFaceDbBtn.onclick = async () => {
        viewDbModal.style.display = 'block';         // 顯示彈出視窗
        setTimeout(()=>centerModal(viewDbModal), 0); // 延遲一點點時間在讓函式執行(讓瀏覽器有時間渲染)
        // AJAX 取得資料
        // try...catch => JavaScript 錯誤處理語法，try 發生錯誤時執行 catch 區塊
        try {
            // await => 等待後端回應，沒有 await 不會拿到空資料，而是拿到「承諾會給你資料的憑證」，但還沒拿到真正的資料
            const response = await fetch('/get_faces'); // 從後端的'get_faces'取得資料
            const faces = await response.json();        // 把 json 格式的資料解析成 JavaScript 可以直接使用的字串
            modalTableBody.innerHTML = '';              // 清除表格殘留的程式碼
            // 對 faces 陣列中的每一個元素執行這個函式
            // face 代表目前處理的這筆資料 
            faces.forEach(face => {
                const row = document.createElement('tr'); // 建立表格列元素 <tr></tr>
                row.innerHTML = `<td>${face.id}</td><td>${face.name}</td><td>${face.created_date}</td>`; // 把資料製作成列表，加入 <tr></tr> 中
                modalTableBody.appendChild(row); // 把這個列表加入資料庫表格中
            });
        // 錯誤處理(error => JavaScript 自動提供的錯誤物件)
        } catch (error) {
            //  HTML + JavaScript 樣板字串:
            // `字串內容 ${變數} 更多內容`
            modalTableBody.innerHTML = `<tr><td colspan="3">獲取資料失敗: ${error.message}</td></tr>`;
        }
    };
    // ===== 關閉資料庫彈出視窗 =====
    closeViewDbModal.onclick = () => {
        viewDbModal.style.display = 'none'; // 隱藏彈出視窗
        modalTableBody.innerHTML = '';      // 清除表格殘留的程式碼
    };

    // ===== 查看辨識紀錄資料庫彈出視窗 =====
    viewLogDbBtn.onclick = async () => {
        viewLogDbModal.style.display = 'block';
        setTimeout(()=>centerModal(viewLogDbModal), 0);
        
        try {
            const response = await fetch('/get_recognition_logs');
            const logs = await response.json();
            modalLogTableBody.innerHTML = '';
            
            logs.forEach(log => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${log.id}</td>
                    <td>${log.name || '未知'}</td>
                    <td>${log.recognition_date}</td>
                    <td>${log.confidence ? log.confidence.toFixed(1) : 'N/A'}</td>
                `;
                modalLogTableBody.appendChild(row);
            });
        } catch (error) {
            modalLogTableBody.innerHTML = `<tr><td colspan="4">獲取資料失敗: ${error.message}</td></tr>`;
        }
    };

    // ===== 關閉辨識紀錄資料庫彈出視窗 =====
    closeViewLogDbModal.onclick = () => {
        viewLogDbModal.style.display = 'none';
        modalLogTableBody.innerHTML = '';
    };

    // ===== 訪客預約彈出視窗元素 =====
    const visitorBookingModal = document.getElementById('visitorBookingModal');
    const closeVisitorBookingModal = document.getElementById('closeVisitorBookingModal');
    const visitorBookingForm = document.getElementById('visitorBookingForm');
    const bookingCodeInput = document.getElementById('bookingCodeInput');
    const bookingResult = document.getElementById('bookingResult');

    // ===== 訪客預約彈出視窗 =====
    if (visitorBookingBtn) {
        visitorBookingBtn.onclick = () => {
            visitorBookingModal.style.display = 'block';
            setTimeout(() => centerModal(visitorBookingModal), 0);
        };
    }

    // ===== 關閉訪客預約彈出視窗 =====
    if (closeVisitorBookingModal) {
        closeVisitorBookingModal.onclick = () => {
            visitorBookingModal.style.display = 'none';
            visitorBookingForm.reset();
            bookingResult.textContent = '';
        };
    }

    // ===== 訪客預約驗證表單提交 =====
    if (visitorBookingForm) {
        visitorBookingForm.onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData();
            formData.append('booking_code', bookingCodeInput.value);
            
            try {
                const response = await fetch('/verify_booking_code', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    bookingResult.textContent = result.message;
                    bookingResult.style.color = 'green';
                    visitorBookingForm.reset();
                    
                    // 如果驗證成功且需要開始倒數
                    if (result.start_countdown) {
                        startVisitorPhotoCountdown(result.username, result.booking_code);
                    }
                } else {
                    bookingResult.textContent = result.message;
                    bookingResult.style.color = 'red';
                }
            } catch (error) {
                bookingResult.textContent = '驗證失敗：' + error.message;
                bookingResult.style.color = 'red';
            }
        };
    }

    // ===== 訪客拍照倒數功能 =====
    function startVisitorPhotoCountdown(username, bookingCode) {
        let countdown = 3;
        const originalContent = bookingResult.innerHTML;
        
        const countdownInterval = setInterval(() => {
            bookingResult.innerHTML = `
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

    // ===== 擷取訪客照片 =====
    async function captureVisitorPhoto(username, bookingCode) {
        try {
            bookingResult.innerHTML = `
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
                bookingResult.innerHTML = `
                    <div style="text-align: center;">
                        <h4>✅ 拍照成功！</h4>
                        <p>${result.message}</p>
                        <p>檔案名稱：${result.filename}</p>
                        ${result.db_message ? `<p>資料庫：${result.db_message}</p>` : ''}
                    </div>
                `;
                bookingResult.style.color = 'green';
                
                // 3秒後關閉彈出視窗
                setTimeout(() => {
                    visitorBookingModal.style.display = 'none';
                    bookingResult.textContent = '';
                    visitorBookingForm.reset();
                }, 3000);
                
            } else {
                bookingResult.innerHTML = `
                    <div style="text-align: center;">
                        <h4>❌ 拍照失敗</h4>
                        <p>${result.message}</p>
                        ${result.db_error ? `<p style="color: orange;">資料庫錯誤：${result.db_error}</p>` : ''}
                    </div>
                `;
                bookingResult.style.color = 'red';
            }
        } catch (error) {
            bookingResult.innerHTML = `
                <div style="text-align: center;">
                    <h4>❌ 拍照失敗</h4>
                    <p>錯誤：${error.message}</p>
                </div>
            `;
            bookingResult.style.color = 'red';
        }
    }

    // ===== 點擊外部關閉 =====
    // 監聽整個網頁的點擊事件
    window.onclick = (event) => {
        // 加入人臉視窗
        if (event.target === addFaceModal) {     // 只有在點擊是窗外的空白部分才會執行
            addFaceModal.style.display = 'none'; // 隱藏視窗
            modalUploadForm.reset();             // 清空表單輸入內容
        }
        // 測試辨識視窗
        if (event.target === testFaceModal) {
            testFaceModal.style.display = 'none';
            modalTestForm.reset();
            testResult.textContent = '';         // 清空輸入框文字
        }
        // 查看資料庫視窗
        if (event.target === viewDbModal) {
            viewDbModal.style.display = 'none';
            modalTableBody.innerHTML = '';      // 清空表格顯示區
        }
        // 查看辨識紀錄視窗
        if (event.target === viewLogDbModal) {
            viewLogDbModal.style.display = 'none';
            modalLogTableBody.innerHTML = '';
        }
        // 訪客預約視窗
        if (event.target === visitorBookingModal) {
            visitorBookingModal.style.display = 'none';
            visitorBookingForm.reset();
            bookingResult.textContent = '';
        }
    };

    // ===== 辨識紀錄 =====
    const socket = io(); // 建立 WebSocket 連線
    // 及時辨識紀錄推送(socket.IO 事件監聽)
    // ( '事件名稱', 當收到事件執行的函數(後端傳來的資料物件) )
    socket.on('recognition', function(data) {
        // 確認接收到了資料類型是 recognition
        if (data.type === 'recognition') {
            addLogEntry(data.message); // 呼叫「新增即時辨識紀錄函式」
        }
    });
    // ----- 新增即時辨識紀錄 -----
    // insertBefore(新元素, 參考元素) => 在參考元素前面插入新元素
    function addLogEntry(message) {
        const entry = document.createElement('div'); // 建立 div 標籤
        entry.className = 'log-entry'; // CSS 設定(字體、顏色...)

        // 根據訊息變換顏色
        // entry.classList.add() => 動態添加樣式(類似添加字串來改變class類別的方式)
        // message.includes('字串') => message 是否包含此字串? 回傳 true, false 
        if (message.includes('住戶來到大門')){ // 已知人物 - 綠色(.log-entry.know-face)
            entry.classList.add('know-face')
        }
        else if(message.includes('未偵測到人臉')){ // 未偵測人臉 - 灰色(.log-entry.no-face)
            entry.classList.add('no-face')
        }
        else if(message.includes('偵測到未知人物')){ // 未知人物 - 紅色(.log-entry.unknow-face)
            entry.classList.add('unknow-face')
        }

        // 包裝訊息
        entry.textContent = `${new Date().toLocaleTimeString()} - ${message}`; // 發生時間-訊息
        recognitionLog.insertBefore(entry, recognitionLog.firstChild); // 將新紀錄插入最上方
    }

    // ===== 人工審核區塊 =====
    // 未知人臉處理
    socket.on('unknown_face', function(data) {
        showReviewPanel(data.image_url);
    });
    function showReviewPanel(imageUrl) {
        const panel = document.getElementById('reviewPanel');
        if (!panel) return;
        panel.innerHTML = `
            <div style="border:2px solid #222; border-radius:8px; background:#fff; padding:16px; margin-bottom:10px; max-width:400px;">
                <h2 style="margin-top:0;">認識的人？</h2>
                <img id="reviewImage" src="${imageUrl}" style="width:100%;max-width:350px; border:1px solid #222;"><br><br>
                <input type="text" id="reviewPersonName" placeholder="請輸入人名" style="width:90%;"><br><br>
                <button id="reviewYesBtn">是</button>
                <button id="reviewNoBtn">否</button>
                <button id="reviewRetakeBtn">再拍一張</button>
            </div>
        `;
        document.getElementById('reviewYesBtn').onclick = async () => {
            const name = document.getElementById('reviewPersonName').value;
            if (!name) {
                alert('請輸入人名');
                return;
            }
            const formData = new FormData();
            const imgBlob = await fetch(document.getElementById('reviewImage').src).then(r => r.blob());
            formData.append('image', imgBlob);
            formData.append('name', name);
            await fetch('/add_face', { method: 'POST', body: formData });
            panel.innerHTML = '';
        };
        document.getElementById('reviewNoBtn').onclick = () => {
            panel.innerHTML = '';
        };
        document.getElementById('reviewRetakeBtn').onclick = async () => {
            try {
                const response = await fetch('/latest_unknown_face');
                const data = await response.json();
                if (data.image_url) {
                    document.getElementById('reviewImage').src = data.image_url;
                } else {
                    alert('目前沒有新的未知人物影像');
                }
            } catch (error) {
                alert('取得最新影像失敗');
            }
        };
    }

    // ===== Modal 浮空視窗拖曳與置中功能 =====
    function centerModal(modal) {
        const content = modal.querySelector('.modal-content');
        content.style.left = 'calc(50vw - ' + (content.offsetWidth/2) + 'px)';
        content.style.top = 'calc(50vh - ' + (content.offsetHeight/2) + 'px)';
        content.style.zIndex = 2000;
    }
    function makeModalDraggable(modal) {
        const header = modal.querySelector('h2');
        let isDragging = false, offsetX = 0, offsetY = 0;
        header.style.cursor = 'move';
        header.onmousedown = function(e) {
            isDragging = true;
            const content = modal.querySelector('.modal-content');
            content.style.zIndex = 3000; // 拖曳時提升 z-index
            const rect = content.getBoundingClientRect();
            offsetX = e.clientX - rect.left;
            offsetY = e.clientY - rect.top;
            document.onmousemove = function(e2) {
                if (isDragging) {
                    content.style.position = 'fixed';
                    content.style.left = (e2.clientX - offsetX) + 'px';
                    content.style.top = (e2.clientY - offsetY) + 'px';
                }
            };
            document.onmouseup = function() {
                isDragging = false;
                content.style.zIndex = 2000;
                document.onmousemove = null;
                document.onmouseup = null;
            };
        };
    }
    [addFaceModal, testFaceModal, viewDbModal, viewLogDbModal, visitorBookingModal].forEach(makeModalDraggable);

    // ====== 彈窗打開時自動置中 ======
    addFaceBtn.onclick = () => {
        addFaceModal.style.display = 'block';
        setTimeout(()=>centerModal(addFaceModal), 0);
    };
    testFaceBtn.onclick = () => {
        testFaceModal.style.display = 'block';
        setTimeout(()=>centerModal(testFaceModal), 0);
    };
    viewFaceDbBtn.onclick = async () => {
        viewDbModal.style.display = 'block';
        setTimeout(()=>centerModal(viewDbModal), 0);
        // AJAX 取得資料
        try {
            const response = await fetch('/get_faces');
            const faces = await response.json();
            modalTableBody.innerHTML = '';
            faces.forEach(face => {
                const row = document.createElement('tr');
                row.innerHTML = `<td>${face.id}</td><td>${face.name}</td><td>${face.created_date}</td>`;
                modalTableBody.appendChild(row);
            });
        } catch (error) {
            modalTableBody.innerHTML = '<tr><td colspan="3">獲取資料失敗</td></tr>';
        }
    };
});