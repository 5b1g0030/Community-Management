// 辨識紀錄管理模組
import * as DOM from "./dom.js";

/*
這個篩選功能通過以下步驟實現：

1. 事件綁定：
使用 jQuery 綁定 keyup 和 change 事件到篩選器（文字框和下拉選單）。
當使用者輸入或選擇篩選條件時，觸發篩選邏輯。

2. 取得篩選條件：
從篩選器元素（如 #filter-year）獲取值。
根據輸入值動態生成正則表達式（如 YYYY-MM-DD 格式）。

3. 應用篩選：
使用 DataTables 的 column().search() 方法，將正則表達式應用到指定欄位（如日期欄位）。
設定 true 啟用正則匹配，並刷新表格顯示結果。

4. 清空篩選：
提供按鈕清空所有篩選條件，並重置表格顯示。
這樣，篩選功能能即時更新表格內容，根據使用者的條件動態篩選資料。
*/ 

var recognitionLogsTable = null;

// ===== 初始化辨識紀錄 DataTable =====
export function initializeRecognitionLogsTable() {
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
        // 跟網頁設定的篩選編號有關；data: 0 表示第一欄對應後端 data 中的第 0 個元素(log['id'])
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
        order: [[1, 'desc']], // [指定要排序的欄位索引（從 0 開始）, 排序方向]
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
    $('.filter-container input[data-column], .filter-container select[data-column]').off('keyup change').on('keyup change', function () {
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
    $('#filter-year, #filter-month, #filter-day').off('input change keyup').on('input change keyup', function () {
        console.log('日期輸入事件觸發:', $(this).attr('id'), '值:', this.value);
        applyDateFilter(); // 呼叫「日期篩選函數」
    });
    // 清除日期篩選按鈕
    $('#clear-date-filter').off('click').on('click', function () {
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

// ===== 添加辨識紀錄到即時顯示區(CSS) =====
export function addLogEntry(message) {
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    // 根據訊息內容添加不同的 CSS 樣式
    if (message.includes('住戶來到大門')) {
        entry.classList.add('know-face')
    }
    else if (message.includes('未偵測到人臉')) {
        entry.classList.add('no-face')
    }
    else if (message.includes('偵測到未知人物')) {
        entry.classList.add('unknow-face')
    }
    // 將即時辨識紀錄新增到前端的顯示區域，並確保最新的紀錄顯示在最前面
    entry.textContent = `${new Date().toLocaleTimeString()} - ${message}`;
    DOM.recognitionLog.insertBefore(entry, DOM.recognitionLog.firstChild);
}

// ===== 初始化 Socket.IO 連接 =====
export function initRecognitionSocket(socket) {
    // 監聽 recognition 事件，當後端推送辨識訊息時，調用 addLogEntry 將訊息顯示到前端
    socket.on('recognition', function(data) {
        if (data.type === 'recognition') {
            addLogEntry(data.message);
        }
    });
}

// ===== 清空篩選器 =====
export function clearLogFilters() {
    // 清空文字輸入框和下拉選單的值
    $('.filter-container input, .filter-container select').val('');
    $('#filter-year, #filter-month, #filter-day').val('');
    // 如果 DataTable 存在，清空搜尋條件並刷新表格
    if (recognitionLogsTable) {
        recognitionLogsTable.search('').columns().search('').draw();
    }
}