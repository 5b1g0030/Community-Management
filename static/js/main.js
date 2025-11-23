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
    const testFaceModal = document.getElementById('testFaceModal');           // 測試辨識-彈出視窗容器
    const closeTestFaceModal = document.getElementById('closeTestFaceModal'); // 測試辨識-關閉視窗按鈕
    const modalTestForm = document.getElementById('modalTestForm');           // 測試辨識-處理表單提交
    const modalTestImage = document.getElementById('modalTestImage');         // 測試辨識-顯示內容(在 testResult)
    const testResult = document.getElementById('testResult');                 // 測試辨識-清空顯示內容

    // ===== 查看系統中已註冊的所有人臉資料 =====
    const viewDbModal = document.getElementById('viewDbModal');             // 人臉資料庫彈出視窗容器
    const closeViewDbModal = document.getElementById('closeViewDbModal');   // 關閉按鈕(人臉資料庫)
    const modalTableBody = document.getElementById('modalTableBody');       // 資料庫查詢表格

    // ====== 查看辨識紀錄的所有資料 =====
    const viewLogDbModal = document.getElementById('viewLogDbModal');       // 辨識紀錄 Modal(彈出視窗)
    const closeViewLogDbModal = document.getElementById('closeViewLogDbModal'); // 關閉按鈕(辨識紀錄)
    // const modalLogTableBody = document.getElementById('modalLogTableBody'); // 辨識紀錄查詢表格

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
                            window.location.href = result.redirect; // 導向網頁
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

        // ===== 綁定篩選事件 (只綁定一次) =====
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
    viewLogDbBtn.onclick = async () => {
        viewLogDbModal.style.display = 'block'; // 顯示彈窗
        setTimeout(()=>centerModal(viewLogDbModal), 0); // 視窗置中
        
        // 在彈窗顯示後，呼叫初始化函數
        initializeRecognitionLogsTable(); // 呼叫「初始化辨識紀錄 DataTable」
    };
    // ===== 關閉辨識紀錄資料庫彈出視窗 =====
    closeViewLogDbModal.onclick = () => {
        viewLogDbModal.style.display = 'none';
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
    // ===== 訪客預約彈出視窗元素 =====
    const visitorBookingModal = document.getElementById('visitorBookingModal'); // 訪客預約的 modal 容器
    const closeVisitorBookingModal = document.getElementById('closeVisitorBookingModal'); // 關閉按鈕
    const visitorBookingForm = document.getElementById('visitorBookingForm'); // 驗證碼輸入表單
    const bookingCodeInput = document.getElementById('bookingCodeInput');     // 使用者輸入的驗證碼欄位
    const bookingResult = document.getElementById('bookingResult');           // 顯示驗證和拍照結果的區塊

    // ===== 訪客預約彈出視窗 =====
    // 查該元素是否存在再綁定事件，避免在「網頁執行這個賦值操作時」，沒有該元素的頁面會發生錯誤
    if (visitorBookingBtn) {
        // 當按下 id = visitorBookingBtn 的按鈕時，顯示彈出視窗
        // 箭頭函式
        visitorBookingBtn.onclick = () => {
            // 顯示視窗(CSS)
            visitorBookingModal.style.display = 'block'; 
            // 延遲執行此函式，瀏覽器渲染好，此函式會使 modal 置中。
            setTimeout(() => centerModal(visitorBookingModal), 0); 
        };
    }
    // ===== 關閉訪客預約彈出視窗 =====
    // 查該元素是否存在再綁定事件
    if (closeVisitorBookingModal) {
        // 當按下 id = closeVisitorBookingModal 的按鈕時，關閉彈出視窗
        closeVisitorBookingModal.onclick = () => {
            visitorBookingModal.style.display = 'none'; // 隱藏視窗(CSS)
            visitorBookingForm.reset(); // 清空表單避免資料殘留
            bookingResult.textContent = ''; // 清空在視窗上顯示的文字
        };
    }
    // ===== 訪客預約驗證表單提交 =====
    if (visitorBookingForm) {
        // 當 id = visitorBookingForm 的表單被提交，執行下面程式
        // async => 宣告「非同步函式」的語法，不會使網頁停住 
        visitorBookingForm.onsubmit = async (e) => {
            e.preventDefault(); // 阻止預設提交，避免頁面被重新整理中斷後續操作
            const formData = new FormData(); // 建立表單
            // 將使用者輸入的「6位數字」加入表單，欄位 'booking_code'
            formData.append('booking_code', bookingCodeInput.value);
            
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
                    bookingResult.textContent = result.message; // 顯示訊息
                    bookingResult.style.color = 'green'; // 設定顏色綠色(成功)
                    visitorBookingForm.reset(); // 清空表單
                    
                    // 如果驗證成功且需要開始倒數，準備拍照
                    if (result.start_countdown) {
                        // 呼叫函式，輸入: 使用者名稱, 驗證碼
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
    // ===== 訪客拍照倒數功能函式 =====
    // 輸入: 使用者名稱, 驗證碼
    // 輸出: HTML
    // ==============================
    function startVisitorPhotoCountdown(username, bookingCode) {
        let countdown = 3; // 秒數
        //const originalContent = bookingResult.innerHTML; // 如果需要還原畫面可用
        
        // 每秒執行的程式碼
        // setInterval({...}, 1000) => 會每隔 1000 毫秒（1 秒）重複執行傳入的函式
        const countdownInterval = setInterval(() => {
            // 顯示在網頁上的內容
            bookingResult.innerHTML = `
                <div style="text-align: center;">
                    <h4>準備為 ${username} 的訪客拍照</h4>
                    <div style="font-size: 48px; color: #007bff; font-weight: bold;">${countdown}</div>
                    <p>請保持鏡頭前方有訪客身影</p>
                </div>
            `;
            
            countdown--; // 減一秒
            
            // 如果 3 秒數完
            if (countdown < 0) {
                // 恢復計時器，防止倒數結束後定時器繼續每秒執行，造成重複拍照
                clearInterval(countdownInterval); 
                // 呼叫函式，執行拍照
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
            // 顯示拍照提示
            bookingResult.innerHTML = `
                <div style="text-align: center;">
                    <h4>正在拍照...</h4>
                    <p>📸</p>
                </div>
            `;
            
            // 建立表單
            const formData = new FormData(); 

            // 在表單裡加入:
            // 使用者名稱，欄位'username'
            // 驗證碼，欄位'booking_code'
            formData.append('username', username);
            // 如果有驗證碼
            if (bookingCode) {
                formData.append('booking_code', bookingCode);
            }
            
            // 把表單提交到後端，目的'/capture_visitor_photo'，等待回應
            const response = await fetch('/capture_visitor_photo', {
                method: 'POST',
                body: formData  // 要傳送的資料
            });
            
            // 把回傳的資料轉 JSON
            const result = await response.json();
            
            // 如果網頁狀態碼正常(200~299)，執行以下程式
            if (response.ok) {
                // 顯示成功訊息
                bookingResult.innerHTML = `
                    <div style="text-align: center;">
                        <h4>✅ 拍照成功！</h4>
                        <p>${result.message}</p>
                        <p>檔案名稱：${result.filename}</p>
                        ${result.db_message ? `<p>資料庫：${result.db_message}</p>` : ''}
                    </div>
                `;
                // 訊息顏色
                bookingResult.style.color = 'green';
                
                // 3秒後關閉彈出視窗
                // setTimeout() => 在 n 秒後執行裡面的程式
                setTimeout(() => {
                    visitorBookingModal.style.display = 'none';
                    bookingResult.textContent = '';
                    visitorBookingForm.reset();
                }, 3000);
                
            } else {
                // 錯誤訊息
                bookingResult.innerHTML = `
                    <div style="text-align: center;">
                        <h4>❌ 拍照失敗</h4>
                        <p>${result.message}</p>
                        ${result.db_error ? `<p style="color: orange;">資料庫錯誤：${result.db_error}</p>` : ''}
                    </div>
                `;
                // 訊息顏色
                bookingResult.style.color = 'red';
            }
        } catch (error) {
            // 例外錯誤訊息
            bookingResult.innerHTML = `
                <div style="text-align: center;">
                    <h4>❌ 拍照失敗</h4>
                    <p>錯誤：${error.message}</p>
                </div>
            `;
            // 訊息顏色
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
            // 清空篩選器
            $('.filter-container input, .filter-container select').val('');
            $('#filter-year, #filter-month, #filter-day').val(''); // 清空日期篩選
            // 如果 DataTable 存在，清空搜尋
            if (recognitionLogsTable) {
                recognitionLogsTable.search('').columns().search('').draw();
            }
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

        // ---根據訊息變換顏色---
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

    // // ===== 人工審核區塊 =====
    // // 未知人臉處理
    // socket.on('unknown_face', function(data) {
    //     showReviewPanel(data.image_url);
    // });
    // function showReviewPanel(imageUrl) {
    //     const panel = document.getElementById('reviewPanel');
    //     if (!panel) return;
    //     panel.innerHTML = `
    //         <div style="border:2px solid #222; border-radius:8px; background:#fff; padding:16px; margin-bottom:10px; max-width:400px;">
    //             <h2 style="margin-top:0;">認識的人？</h2>
    //             <img id="reviewImage" src="${imageUrl}" style="width:100%;max-width:350px; border:1px solid #222;"><br><br>
    //             <input type="text" id="reviewPersonName" placeholder="請輸入人名" style="width:90%;"><br><br>
    //             <button id="reviewYesBtn">是</button>
    //             <button id="reviewNoBtn">否</button>
    //             <button id="reviewRetakeBtn">再拍一張</button>
    //         </div>
    //     `;
    //     document.getElementById('reviewYesBtn').onclick = async () => {
    //         const name = document.getElementById('reviewPersonName').value;
    //         if (!name) {
    //             alert('請輸入人名');
    //             return;
    //         }
    //         const formData = new FormData();
    //         const imgBlob = await fetch(document.getElementById('reviewImage').src).then(r => r.blob());
    //         formData.append('image', imgBlob);
    //         formData.append('name', name);
    //         await fetch('/add_face', { method: 'POST', body: formData });
    //         panel.innerHTML = '';
    //     };
    //     document.getElementById('reviewNoBtn').onclick = () => {
    //         panel.innerHTML = '';
    //     };
    //     document.getElementById('reviewRetakeBtn').onclick = async () => {
    //         try {
    //             const response = await fetch('/latest_unknown_face');
    //             const data = await response.json();
    //             if (data.image_url) {
    //                 document.getElementById('reviewImage').src = data.image_url;
    //             } else {
    //                 alert('目前沒有新的未知人物影像');
    //             }
    //         } catch (error) {
    //             alert('取得最新影像失敗');
    //         }
    //     };
    // }

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