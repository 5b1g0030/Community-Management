// Flask 網頁前端的 JavaScript 主程式檔案

document.addEventListener('DOMContentLoaded', () => {
    // 取得元素
    const addFaceBtn = document.getElementById('addFaceBtn');
    const testFaceBtn = document.getElementById('testFaceBtn');
    const viewDbBtn = document.getElementById('viewDbBtn');
    const faceImage = document.getElementById('faceImage');
    const testImage = document.getElementById('testImage');
    const personName = document.getElementById('personName');
    const dbTable = document.getElementById('dbTable');
    const tableBody = document.getElementById('tableBody');
    const recognitionLog = document.getElementById('recognitionLog');

    // 顯示加入人臉欄位
    addFaceBtn.onclick = () => {
        personName.style.display = '';
        faceImage.style.display = '';
        faceImage.click();
    };

    // 上傳人臉圖片
    faceImage.onchange = async () => {
        if (!personName.value) {
            alert('請輸入人名');
            return;
        }
        const formData = new FormData();
        formData.append('image', faceImage.files[0]);
        formData.append('name', personName.value);
        try {
            const response = await fetch('/add_face', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            alert(result.message);
            personName.value = '';
            faceImage.value = '';
            personName.style.display = 'none';
            faceImage.style.display = 'none';
        } catch (error) {
            alert('上傳失敗');
        }
    };

    // 顯示測試辨識欄位
    testFaceBtn.onclick = () => {
        testImage.style.display = '';
        testImage.click();
    };

    // 上傳測試圖片
    testImage.onchange = async () => {
        const formData = new FormData();
        formData.append('image', testImage.files[0]);
        try {
            const response = await fetch('/test_face', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            alert(result.message);
            testImage.value = '';
            testImage.style.display = 'none';
        } catch (error) {
            alert('測試失敗');
        }
    };

    // 查看資料庫
    viewDbBtn.onclick = async () => {
        try {
            const response = await fetch('/get_faces');
            const faces = await response.json();
            tableBody.innerHTML = '';
            faces.forEach(face => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${face.id}</td>
                    <td>${face.name}</td>
                    <td>${face.created_date}</td>
                `;
                tableBody.appendChild(row);
            });
            dbTable.style.display = 'block';
        } catch (error) {
            alert('獲取資料失敗');
        }
    };

    // WebSocket 連線（辨識紀錄）
    let wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    let ws = new WebSocket(wsProtocol + '//' + location.host + '/ws');
    ws.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'recognition') {
                addLogEntry(data.message);
            }
        } catch (e) {}
    };
    function addLogEntry(message) {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        entry.textContent = `${new Date().toLocaleTimeString()} - ${message}`;
        recognitionLog.insertBefore(entry, recognitionLog.firstChild);
    }
});