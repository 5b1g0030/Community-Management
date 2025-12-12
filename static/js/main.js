// Flask 網頁前端的 JavaScript 主程式檔案

// 瀏覽器要以 module 形式（<script type="module">）載入才能解析 import，
// 否則會在解析階段丟出語法錯誤，整個檔案就不會執行。

import * as DOM from "./dom.js" // 引入網頁元素
import { login, register } from "./api.js"; // 引入後端api溝通函式

document.addEventListener('DOMContentLoaded', () => {

    // ===== 登入功能（只在登入頁面執行） =====
    if (DOM.loginForm) {
        
        DOM.loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (DOM.loginMessage) DOM.loginMessage.textContent = '';

            const formData = new FormData(DOM.loginForm); // 建立表單

            try {
                const result = await login(formData) // 呼叫api函式

                alert(result.message);
                console.log('/login result: ', result)
                if(result.redirect) {
                    window.location.href = result.redirect;
                }
                DOM.loginForm.reset();

            } catch (error) {
                alert('登入失敗: ' + error.message);
                DOM.loginForm.reset();
            }
        });
    }

    // ===== 註冊功能（只在註冊頁面執行） =====
    if (DOM.registerForm && DOM.username && DOM.password && DOM.confirmPassword) {
        // 即時密碼確認檢查
        DOM.confirmPassword.addEventListener('input', () => {
            if (DOM.password.value !== DOM.confirmPassword.value) {
                if (DOM.confirmPasswordError) {
                    DOM.confirmPasswordError.textContent = '密碼不一致';
                    DOM.confirmPassword.style.borderColor = 'red';
                }
            } else {
                if (DOM.confirmPasswordError) {
                    DOM.confirmPasswordError.textContent = '';
                    DOM.confirmPassword.style.borderColor = '#ccc';
                }
            }
        });

        // 表單提交處理
        DOM.registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            if (DOM.usernameError) DOM.usernameError.textContent = '';
            if (DOM.passwordError) DOM.passwordError.textContent = '';
            if (DOM.confirmPasswordError) DOM.confirmPasswordError.textContent = '';
            if (DOM.submitMessage) DOM.submitMessage.textContent = '';

            if (DOM.username.value.trim().length < 3) {
                alert('使用者名稱至少需要3個字元');
                DOM.username.focus();
                return;
            }
            if (DOM.password.value.length < 6) {
                alert('密碼至少需要6個字元');
                DOM.password.focus();
                return;
            }
            if (DOM.password.value !== DOM.confirmPassword.value) {
                alert('密碼不一致');
                DOM.confirmPassword.focus();
                return;
            }

            try {
                const formData = new FormData();
                formData.append('username', DOM.username.value);
                formData.append('password', DOM.password.value);
                formData.append('confirm_password', DOM.confirmPassword.value);
                formData.append('role', document.querySelector('input[name="role"]:checked').value);
                
                const result = await register(formData)
                
                if (result.redirect){
                    window.location.href = result.redirect
                }
            } catch (error) {
                alert('註冊失敗：' + error.message);
                DOM.registerForm.reset();
            }
        });
    }

    // ===== 加入人臉彈出視窗 =====  
    DOM.addFaceBtn.onclick = () => DOM.addFaceModal.style.display = 'block'; // 顯示視窗

    // ===== 關閉加入人臉彈出視窗 =====
    DOM.closeAddFaceModal.onclick = () => {
        DOM.addFaceModal.style.display = 'none';
        DOM.modalUploadForm.reset();
    };

    DOM.modalUploadForm.onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData();
        formData.append('image', DOM.modalFaceImage.files[0]);
        formData.append('name', DOM.modalPersonName.value);
        
        try {
            const response = await fetch('/add_face', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            alert(result.message);
            DOM.addFaceModal.style.display = 'none';
            DOM.modalUploadForm.reset();
        } catch (error) {
            alert('上傳失敗：' + error.message);
        }
    };

    // ===== 測試辨識彈出視窗 =====
    DOM.testFaceBtn.onclick = () => DOM.testFaceModal.style.display = 'block';

    // ===== 關閉測試辨識彈出視窗 =====
    DOM.closeTestFaceModal.onclick = () => {
        DOM.testFaceModal.style.display = 'none';
        DOM.modalTestForm.reset();
        DOM.testResult.textContent = '';
    };
    DOM.modalTestForm.onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData();
        formData.append('image', DOM.modalTestImage.files[0]);
        try {
            const response = await fetch('/test_face', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            DOM.testResult.textContent = result.message;
        } catch (error) {
            DOM.testResult.textContent = '辨識失敗';
        }
    };

    // ===== 查看資料庫彈出視窗 =====
    DOM.viewFaceDbBtn.onclick = async () => {
        DOM.viewDbModal.style.display = 'block';
        setTimeout(()=>centerModal(DOM.viewDbModal), 0);
        try {
            const response = await fetch('/get_faces');
            const faces = await response.json();
            DOM.modalTableBody.innerHTML = '';
            faces.forEach(face => {
                const row = document.createElement('tr');
                row.innerHTML = `<td>${face.id}</td><td>${face.name}</td><td>${face.created_date}</td>`;
                DOM.modalTableBody.appendChild(row);
            });
        } catch (error) {
            DOM.modalTableBody.innerHTML = `<tr><td colspan="3">獲取資料失敗: ${error.message}</td></tr>`;
        }
    };
    DOM.closeViewDbModal.onclick = () => {
        DOM.viewDbModal.style.display = 'none';
        DOM.modalTableBody.innerHTML = '';
    };
    // ===== 關閉資料庫彈出視窗 =====
    closeViewDbModal.onclick = () => {
        viewDbModal.style.display = 'none'; // 隱藏彈出視窗
        modalTableBody.innerHTML = '';      // 清除表格殘留的程式碼
    };
    // ===== 查看辨識紀錄資料庫彈出視窗 =====
    var recognitionLogsTable = null; // DataTables 實例變數

    // *************************
    // 辨識紀錄篩選-初始化函式
    // *************************
    // ===== 初始化辨識紀錄 DataTable =====
    function initializeRecognitionLogsTable() {
        // 檢查 DataTables 是否已初始化，避免重複綁定
        if ($.fn.DataTable.isDataTable('#recognition_logs_table')) {
            console.log("辨識紀錄 DataTables 已經初始化，調整欄位寬度。");
            recognitionLogsTable.columns.adjust().draw(); // 自動調整 DataTables 的欄位寬度，確保表格內容能正確顯示
            return;
        }
        
        console.log("辨識紀錄 DataTables 正在初始化...");

        // ===== 初始化 DataTables =====
        recognitionLogsTable = $('#recognition_logs_table').DataTable({
            // 資料來源設定
            ajax: {
                url: '/api/recognition_logs', // 後端獲取資料的 API 路徑(路由名稱)，會向此路徑自動發送請求
                dataSrc: 'data'  // 後端回應的 JSON 資料中，哪個欄位包含表格的資料
            },
            // ---定義表格的每一欄如何對應後端回應的資料--
            // 跟網頁設定的篩選編號有關
            // ----------------------------------------
            columns: [
                { data: 0 }, // ID
                { data: 1 }, // 發生時間
                { data: 2 }, // 事件類型
                { data: 3 }, // 事件訊息
                { data: 4 }, // 人臉ID
                { data: 5 }  // 信心度
            ],
            // ---預設排序：按發生時間降序（最新的在前）---
            // 'asc'：升序（由小到大）。
            // 'desc'：降序（由大到小）。
            // -----------------------------------------
            order: [[ 1, 'desc' ]], // [指定要排序的欄位索引（從 0 開始）, 排序方向]
            // 載入中文語言包
            language: {
                url: '//cdn.datatables.net/plug-ins/2.0.8/i18n/zh-Hant.json'
            },
            // 每頁顯示數量選項
            lengthMenu: [10, 25, 50, 100],
            // 啟用搜尋
            searching: true,
            // 啟用分頁
            paging: true
        });

        // ===== 綁定日期篩選事件 (只綁定一次) =====
        // 選取有 filter-container input, filter-container select class的元素
        // keyup=> 文字框輸入, change=> 下拉選單的值改變
        // .on()=> 綁定事件, .off()=> 解除綁定事件
        // ===================================
        $('.filter-container input[data-column], .filter-container select[data-column]').off('keyup change').on('keyup change', function() {
            // 取得欄位索引(有 data-column 變數的元素)
            var column_index = $(this).attr('data-column'); // this=> 觸發事件的元素
            // 取得篩選器的值
            var value = this.value;

            // 如果是 <select> 標籤，執行下列程式(處理下拉選單與文字輸入)
            if (this.tagName === 'SELECT') {
                // 對於下拉選單，使用正規表達式精確匹配
                recognitionLogsTable.column(column_index).search(value ? '^' + value + '$' : '', true, false).draw();
            } else {
                // 對於文字輸入框，執行標準模糊搜索
                recognitionLogsTable.column(column_index).search(value).draw();
            }
        });

        // ===== 日期篩選功能 =====
        // 使用 jQuery 選擇器來確保正確綁定事件，先解除再綁定
        // 避免多次執行（例如，當彈窗多次打開時），導致同一事件被多次綁定，從而造成重複執行
        $('#filter-year, #filter-month, #filter-day').off('input change keyup').on('input change keyup', function() {
            console.log('日期輸入事件觸發:', $(this).attr('id'), '值:', this.value);
            applyDateFilter(); // 呼叫「日期篩選函數」
        });

        // 清除日期篩選按鈕
        $('#clear-date-filter').off('click').on('click', function() {
            console.log('清除日期篩選按鈕被點擊');
            $('#filter-year, #filter-month, #filter-day').val('');
            applyDateFilter();
        });

        // ===== 日期篩選函數 =====
        function applyDateFilter() {
            console.log('applyDateFilter 函數被呼叫');

            // --- 正規表達式 ---
            // 2023-\d{2}-\d{2} = 限2023-都可以-都可以
            // \d{4}-\d{2}-\d{2} = 都可以-都可以-都可以 
            // -----------------

            // --- 取得年、月、日欄位的值(輸入框) ---
            var year = $('#filter-year').val();
            var month = $('#filter-month').val();
            var day = $('#filter-day').val();
            
            console.log('日期值:', { year: year, month: month, day: day });
            
            // 建立日期篩選的正規表達式
            var datePattern = '';
            
            // --- 當年、月、日其中之一有數值時，執行下列程式 ---
            if (year || month || day) {
                // 格式: YYYY-MM-DD HH:MM:SS
                datePattern = '^';
                
                // 年份部分
                if (year) {
                    datePattern += year;
                } else {
                    // \\d{4} => 匹配一個由 4 個數字組成的字串，例如 2023、1234 等
                    // 確保正規表達式仍然有效，而不會因為部分為空而導致正規表達式無法匹配
                    datePattern += '\\d{4}'; // 任意4位數字
                }
                
                datePattern += '-';
                
                // 月份部分 - 使用更可靠的補零方法
                if (month) {
                    var monthStr = month.toString().length === 1 ? '0' + month : month.toString();
                    datePattern += monthStr;
                } else {
                    datePattern += '\\d{2}'; // 任意2位數字
                }
                
                datePattern += '-';
                
                // 日期部分 - 使用更可靠的補零方法
                if (day) {
                    var dayStr = day.toString().length === 1 ? '0' + day : day.toString();
                    datePattern += dayStr;
                } else {
                    datePattern += '\\d{2}'; // 任意2位數字
                }
                
                datePattern += '.*$'; // 後面的時間部分任意匹配，加上結尾錨點
                
                console.log('日期篩選正規表達式:', datePattern); // 除錯用
                
                // 對發生時間欄位(索引1)進行篩選
                // 正規表達式, 啟用正規表達式匹配, 
                recognitionLogsTable.column(1).search(datePattern, true, false).draw();
            } else {
                console.log('清空日期篩選');
                // 如果所有日期欄位都是空的，清空篩選
                recognitionLogsTable.column(1).search('').draw();
            }
        }

        console.log("辨識紀錄 DataTables 初始化與事件綁定完成。");
    }
    // ************************
    // 辨識紀錄篩選-按鈕觸發
    // ************************
    // 點擊「查看辨識紀錄資料庫」按鈕時，顯示對應的彈出視窗，並初始化或更新辨識紀錄的 DataTables 表格
    DOM.viewLogDbBtn.onclick = async () => {
        DOM.viewLogDbModal.style.display = 'block';
        setTimeout(()=>centerModal(DOM.viewLogDbModal), 0);
        
        // 在彈窗顯示後，呼叫初始化函數
        initializeRecognitionLogsTable(); // 呼叫「初始化辨識紀錄 DataTable」
    };
    DOM.closeViewLogDbModal.onclick = () => {
        DOM.viewLogDbModal.style.display = 'none';
        // 清空篩選器
        $('.filter-container input, .filter-container select').val('');
        $('#filter-year, #filter-month, #filter-day').val(''); // 清空日期篩選
        // 如果 DataTable 存在，清空搜尋
        if (recognitionLogsTable) {
            recognitionLogsTable.search('').columns().search('').draw();
        }
    };

    // **************
    // 訪客預約
    // **************
    

    // ===== 訪客預約彈出視窗 =====
    // 查該元素是否存在再綁定事件，避免在「網頁執行這個賦值操作時」，沒有該元素的頁面會發生錯誤
    if (DOM.visitorBookingBtn) {
        // 當按下 id = visitorBookingBtn 的按鈕時，顯示彈出視窗
        // 箭頭函式
        DOM.visitorBookingBtn.onclick = () => {
            // 顯示視窗(CSS)
            DOM.visitorBookingModal.style.display = 'block'; 
            // 延遲執行此函式，瀏覽器渲染好，此函式會使 modal 置中。
            setTimeout(() => centerModal(DOM.visitorBookingModal), 0); 
        };
    }
    // ===== 關閉訪客預約彈出視窗 =====
    // 查該元素是否存在再綁定事件
    if (DOM.closeVisitorBookingModal) {
        // 當按下 id = closeVisitorBookingModal 的按鈕時，關閉彈出視窗
        DOM.closeVisitorBookingModal.onclick = () => {
            DOM.visitorBookingModal.style.display = 'none'; // 隱藏視窗(CSS)
            DOM.visitorBookingForm.reset(); // 清空表單避免資料殘留
            DOM.bookingResult.textContent = ''; // 清空在視窗上顯示的文字
        };
    }
    // ===== 訪客預約驗證表單提交 =====
    if (DOM.visitorBookingForm) {
        // 當 id = visitorBookingForm 的表單被提交，執行下面程式
        // async => 宣告「非同步函式」的語法，不會使網頁停住 
        DOM.visitorBookingForm.onsubmit = async (e) => {
            e.preventDefault(); // 阻止預設提交，避免頁面被重新整理中斷後續操作
            const formData = new FormData(); // 建立表單
            // 將使用者輸入的「6位數字」加入表單，欄位 'booking_code'
            formData.append('booking_code', DOM.bookingCodeInput.value);
            
            try {
                // 把表單提交到後端，目的: '/verify_booking_code'，等待回應
                const response = await fetch('/verify_booking_code', {
                    method: 'POST', // POST 請求
                    body: formData // 要傳送的資料
                });
                
                // 後端回應後，把回傳的資料轉 JSON 格式
                const result = await response.json();
                
                // 檢查回傳的狀態碼，判斷是否有成功執行(True, False)
                // response.ok => HTTP狀態碼介於200~299，在網頁可視為成功
                if (response.ok) {
                    DOM.bookingResult.textContent = result.message; // 顯示訊息
                    DOM.bookingResult.style.color = 'green'; // 設定顏色綠色(成功)
                    DOM.visitorBookingForm.reset(); // 清空表單
                    
                    // 如果驗證成功且需要開始倒數，準備拍照
                    if (result.start_countdown) {
                        // 呼叫函式，輸入: 使用者名稱, 驗證碼
                        startVisitorPhotoCountdown(result.username, result.booking_code);
                    }
                } else {
                    DOM.bookingResult.textContent = result.message;
                    DOM.bookingResult.style.color = 'red';
                }
            } catch (error) {
                DOM.bookingResult.textContent = '驗證失敗：' + error.message;
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

    // 點擊外部關閉
    window.onclick = (event) => {
        if (event.target === DOM.addFaceModal) {
            DOM.addFaceModal.style.display = 'none';
            DOM.modalUploadForm.reset();
        }
        if (event.target === DOM.testFaceModal) {
            DOM.testFaceModal.style.display = 'none';
            DOM.modalTestForm.reset();
            DOM.testResult.textContent = '';
        }
        if (event.target === DOM.viewDbModal) {
            DOM.viewDbModal.style.display = 'none';
            DOM.modalTableBody.innerHTML = '';
        }
        if (event.target === DOM.viewLogDbModal) {
            DOM.viewLogDbModal.style.display = 'none';
            $('.filter-container input, .filter-container select').val('');
            $('#filter-year, #filter-month, #filter-day').val('');
            if (recognitionLogsTable) {
                recognitionLogsTable.search('').columns().search('').draw();
            }
        }
        if (event.target === DOM.visitorBookingModal) {
            DOM.visitorBookingModal.style.display = 'none';
            DOM.visitorBookingForm.reset();
            DOM.bookingResult.textContent = '';
        }
    };

    // 辨識紀錄
    const socket = io();
    socket.on('recognition', function(data) {
        if (data.type === 'recognition') {
            addLogEntry(data.message);
        }
    });
    function addLogEntry(message) {
        const entry = document.createElement('div');
        entry.className = 'log-entry';

        if (message.includes('住戶來到大門')){
            entry.classList.add('know-face')
        }
        else if(message.includes('未偵測到人臉')){
            entry.classList.add('no-face')
        }
        else if(message.includes('偵測到未知人物')){
            entry.classList.add('unknow-face')
        }

        entry.textContent = `${new Date().toLocaleTimeString()} - ${message}`;
        DOM.recognitionLog.insertBefore(entry, DOM.recognitionLog.firstChild);
    }

    // Modal 拖曳與置中
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
            content.style.zIndex = 3000;
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
    [DOM.addFaceModal, DOM.testFaceModal, DOM.viewDbModal, DOM.viewLogDbModal, DOM.visitorBookingModal].forEach(makeModalDraggable);

    // 彈窗打開時自動置中
    DOM.addFaceBtn.onclick = () => {
        DOM.addFaceModal.style.display = 'block';
        setTimeout(()=>centerModal(DOM.addFaceModal), 0);
    };
    DOM.testFaceBtn.onclick = () => {
        DOM.testFaceModal.style.display = 'block';
        setTimeout(()=>centerModal(DOM.testFaceModal), 0);
    };
    DOM.viewFaceDbBtn.onclick = async () => {
        DOM.viewDbModal.style.display = 'block';
        setTimeout(()=>centerModal(DOM.viewDbModal), 0);
        try {
            const response = await fetch('/get_faces');
            const faces = await response.json();
            DOM.modalTableBody.innerHTML = '';
            faces.forEach(face => {
                const row = document.createElement('tr');
                row.innerHTML = `<td>${face.id}</td><td>${face.name}</td><td>${face.created_date}</td>`;
                DOM.modalTableBody.appendChild(row);
            });
        } catch (error) {
            DOM.modalTableBody.innerHTML = '<tr><td colspan="3">獲取資料失敗</td></tr>';
        }
    };
});