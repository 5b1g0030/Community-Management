// Flask 網頁前端的 JavaScript 主程式檔案

// 瀏覽器要以 module 形式（<script type="module">）載入才能解析 import，
// 否則會在解析階段丟出語法錯誤，整個檔案就不會執行。

import * as DOM from "./dom.js" // 引入網頁元素
import { login, register } from "./api.js"; // 引入後端api溝通函式
import { addFaceModal, testFaceModal, viewFace, visitorBooking, initViewLogDbModal } from "./modals.js";
import { io } from "https://cdn.socket.io/4.6.1/socket.io.esm.min.js";
import { initVisitorBooking } from "./visitor.js";
import { modalsClose } from "./modalController.js";

document.addEventListener('DOMContentLoaded', () => {

    // ===== 登入功能（只在登入頁面執行） =====
    if (DOM.loginForm) {
        console.log("登入");
        DOM.loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (DOM.loginMessage) DOM.loginMessage.textContent = '';

            const formData = new FormData(DOM.loginForm); // 建立表單

            try {
                const result = await login(formData) // 呼叫api函式

                alert(result.message);
                console.log('/login result: ', result);
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
            // 清空所有錯誤訊息
            if (DOM.usernameError) DOM.usernameError.textContent = '';
            if (DOM.passwordError) DOM.passwordError.textContent = '';
            if (DOM.confirmPasswordError) DOM.confirmPasswordError.textContent = '';
            if (DOM.submitMessage) DOM.submitMessage.textContent = '';

            // 驗證欄位
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
    if (DOM.addFaceBtn){
        addFaceModal();
    }

    // ===== 測試辨識彈出視窗 =====
    if (DOM.testFaceBtn){
        testFaceModal();
    }

    // ===== 查看資料庫彈出視窗 =====
    if (DOM.viewFaceDbBtn){
        viewFace();
    }

    // *************************
    // 辨識紀錄篩選-初始化函式
    // *************************
    // ===== 初始化辨識紀錄 DataTable =====
    var recognitionLogsTable = null; // DataTables 實例變數
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
    // 辨識紀錄CSS
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

    // ************************
    // 辨識紀錄篩選-按鈕觸發
    // ************************
    // 點擊「查看辨識紀錄資料庫」按鈕時，顯示對應的彈出視窗，並初始化或更新辨識紀錄的 DataTables 表格
    if (DOM.viewLogDbBtn){
        initViewLogDbModal({
            onOpen: () => {
                initializeRecognitionLogsTable(); // 呼叫「初始化辨識紀錄 DataTable」
            },
            onClose: () => {
                // 清空篩選器
                $('.filter-container input, .filter-container select').val('');
                $('#filter-year, #filter-month, #filter-day').val(''); // 清空日期篩選
                // 如果 DataTable 存在，清空搜尋
                if (recognitionLogsTable) {
                    recognitionLogsTable.search('').columns().search('').draw();
                }
            }
        });
    };

    // **************
    // 訪客預約
    // **************
    // ===== 訪客預約彈出視窗 =====
    // 查該元素是否存在再綁定事件，避免在「網頁執行這個賦值操作時」，沒有該元素的頁面會發生錯誤
    if (DOM.visitorBookingBtn) {
        visitorBooking();
    }
    // ===== 訪客預約驗證表單提交 =====
    initVisitorBooking();

    // 點擊外部關閉 modal
    modalsClose();

});