import * as DOM from "./dom.js";

export function modalsClose(){
    // 點擊外部關閉
    window.onclick = (event) => {
        // 加入人臉
        if (event.target === DOM.addFaceModal) {
            DOM.addFaceModal.style.display = 'none';
            DOM.modalUploadForm.reset();
        }
        // 測試辨識
        if (event.target === DOM.testFaceModal) {
            DOM.testFaceModal.style.display = 'none';
            DOM.modalTestForm.reset();
            DOM.testResult.textContent = '';
        }
        // 顯示已登錄人臉
        if (event.target === DOM.viewDbModal) {
            DOM.viewDbModal.style.display = 'none';
            DOM.modalTableBody.innerHTML = '';
        }
        // 顯示辨識紀錄
        if (event.target === DOM.viewLogDbModal) {
            DOM.viewLogDbModal.style.display = 'none';
            $('.filter-container input, .filter-container select').val('');
            $('#filter-year, #filter-month, #filter-day').val('');
            if (recognitionLogsTable) {
                recognitionLogsTable.search('').columns().search('').draw();
            }
        }
        // 訪客預約
        if (event.target === DOM.visitorBookingModal) {
            DOM.visitorBookingModal.style.display = 'none';
            DOM.visitorBookingForm.reset();
            DOM.bookingResult.textContent = '';
        }
    };
}