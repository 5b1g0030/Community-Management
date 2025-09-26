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
    const modalTableBody = document.getElementById('modalTableBody');

    // ===== 加入人臉 Modal 控制 =====  
    // 按下按鈕後，顯示視窗(display 設為 block)
    addFaceBtn.onclick = () => addFaceModal.style.display = 'block'; // 顯示視窗

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

    // ===== 測試辨識 Modal 控制 =====
    testFaceBtn.onclick = () => testFaceModal.style.display = 'block';
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

    // ===== 查看資料庫 Modal 控制 =====
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
    closeViewDbModal.onclick = () => {
        viewDbModal.style.display = 'none';
        modalTableBody.innerHTML = '';
    };

    // ===== 點擊 modal 外部關閉 =====
    window.onclick = (event) => {
        if (event.target === addFaceModal) {
            addFaceModal.style.display = 'none';
            modalUploadForm.reset();
        }
        if (event.target === testFaceModal) {
            testFaceModal.style.display = 'none';
            modalTestForm.reset();
            testResult.textContent = '';
        }
        if (event.target === viewDbModal) {
            viewDbModal.style.display = 'none';
            modalTableBody.innerHTML = '';
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