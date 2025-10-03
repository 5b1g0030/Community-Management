// Flask 網頁前端的 JavaScript 主程式檔案

document.addEventListener('DOMContentLoaded', () => {
    // ===== 取得元素 =====
    const addFaceBtn = document.getElementById('addFaceBtn');           // 「加入人臉」功能按鈕
    const testFaceBtn = document.getElementById('testFaceBtn');         // 「測試辨識」功能按鈕
    const viewDbBtn = document.getElementById('viewDbBtn');             // 「查看資料庫」功能按鈕
    const recognitionLog = document.getElementById('recognitionLog');   // 辨識紀錄清單

    // Modal 相關元素
    const addFaceModal = document.getElementById('addFaceModal');           // 「加入人臉」浮空視窗
    const closeAddFaceModal = document.getElementById('closeAddFaceModal'); // 「加入人臉」關閉視窗鍵
    const modalUploadForm = document.getElementById('modalUploadForm');     // 上傳的表單元素
    const modalFaceImage = document.getElementById('modalFaceImage');       // 表單中圖片欄位
    const modalPersonName = document.getElementById('modalPersonName');     // 表單中人名

    const testFaceModal = document.getElementById('testFaceModal');
    const closeTestFaceModal = document.getElementById('closeTestFaceModal');
    const modalTestForm = document.getElementById('modalTestForm');
    const modalTestImage = document.getElementById('modalTestImage');
    const testResult = document.getElementById('testResult');

    const viewDbModal = document.getElementById('viewDbModal');
    const closeViewDbModal = document.getElementById('closeViewDbModal');
    const modalTableBody = document.getElementById('modalTableBody');       // 資料庫查詢表格

    const registerForm = document.getElementById('registerForm');
    const username = document.getElementById('username');
    const password = document.getElementById('password');
    const confirmPassword = document.getElementById('confirm_password');
    const usernameError = document.getElementById('usernameError');
    const passwordError = document.getElementById('passwordError');
    const confirmPasswordError = document.getElementById('confirmPasswordError');
    const submitMessage = document.getElementById('submitMessage');


    // ===== 註冊資料獲取 =====
    // 即時密碼確認檢查
    confirmPassword.addEventListener('input', () => {
        if (password.value !== confirmPassword.value) {
            confirmPasswordError.textContent = '密碼不一致';
            confirmPassword.style.borderColor = 'red';
        } else {
            confirmPasswordError.textContent = '';
            confirmPassword.style.borderColor = '#ccc';
        }
    });

    // 表單提交處理
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // 清空之前的錯誤訊息
        usernameError.textContent = '';
        passwordError.textContent = '';
        confirmPasswordError.textContent = '';
        submitMessage.textContent = '';

        // 前端驗證
        let hasError = false;

        if (username.value.trim().length < 3) {
            usernameError.textContent = '使用者名稱至少需要3個字元';
            hasError = true;
        }

        if (password.value.length < 6) {
            passwordError.textContent = '密碼至少需要6個字元';
            hasError = true;
        }

        if (password.value !== confirmPassword.value) {
            confirmPasswordError.textContent = '密碼不一致';
            hasError = true;
        }

        if (hasError) return;

        // 發送註冊請求
        try {
            const formData = new FormData();
            formData.append('username', username.value);
            formData.append('password', password.value);
            formData.append('confirm_password', confirmPassword.value);

            const response = await fetch('/register', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                submitMessage.textContent = result.message;
                submitMessage.className = 'success';
                registerForm.reset();
                // 3秒後跳轉到登入頁面
                setTimeout(() => {
                    window.location.href = '/login';
                }, 3000);
            } else {
                submitMessage.textContent = result.message;
                submitMessage.className = 'error';
            }
        } catch (error) {
            submitMessage.textContent = '註冊失敗：' + error.message;
            submitMessage.className = 'error';
        }
    });

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
    viewDbBtn.onclick = async () => {
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
    };

    // ===== SocketIO 連線（辨識紀錄） =====
    const socket = io();
    socket.on('recognition', function(data) {
        if (data.type === 'recognition') {
            addLogEntry(data.message);
        }
    });
    function addLogEntry(message) {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        entry.textContent = `${new Date().toLocaleTimeString()} - ${message}`;
        recognitionLog.insertBefore(entry, recognitionLog.firstChild);
    }

    // ===== 人工審核區塊 =====
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
    [addFaceModal, testFaceModal, viewDbModal].forEach(makeModalDraggable);

    // ====== 彈窗打開時自動置中 ======
    addFaceBtn.onclick = () => {
        addFaceModal.style.display = 'block';
        setTimeout(()=>centerModal(addFaceModal), 0);
    };
    testFaceBtn.onclick = () => {
        testFaceModal.style.display = 'block';
        setTimeout(()=>centerModal(testFaceModal), 0);
    };
    viewDbBtn.onclick = async () => {
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