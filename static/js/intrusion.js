/** One editable, normalized polygon over the existing manager MJPEG image. */
/* 區域偵測 JavaScript */

export function initIntrusionUI(socket) {
    const img = document.getElementById('video-stream');
    const canvas = document.getElementById('intrusion-canvas');
    const status = document.getElementById('intrusion-state');
    const error = document.getElementById('intrusion-error');
    const eventList = document.getElementById('intrusion-events');
    if (!img || !canvas || !status) return;

    const btn = {
        edit: document.getElementById('intrusion-edit'),
        undo: document.getElementById('intrusion-undo'),
        save: document.getElementById('intrusion-save'),
        toggle: document.getElementById('intrusion-toggle'),
        clear: document.getElementById('intrusion-clear'),
        permission: document.getElementById('intrusion-permission')
    };
    const ctx = canvas.getContext('2d');
    let points = [];
    let savedPoints = [];
    let editing = false;
    let enabled = false;

    function setError(message = '') { error.textContent = message; }
    async function api(url, options = {}) {
        const response = await fetch(url, { cache: 'no-store', ...options });
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(data.message || `HTTP ${response.status}`);
        return data;
    }
    const jsonRequest = (method, data) => ({
        method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data)
    });
    function syncCanvas() {
        const rect = img.getBoundingClientRect();
        const width = Math.round(rect.width);
        const height = Math.round(rect.height);
        if (width <= 0 || height <= 0) return;
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
        const scale = window.devicePixelRatio || 1;
        canvas.width = Math.round(width * scale);
        canvas.height = Math.round(height * scale);
        ctx.setTransform(scale, 0, 0, scale, 0, 0);
        draw();
    }
    function draw() {
        const width = parseFloat(canvas.style.width) || img.clientWidth;
        const height = parseFloat(canvas.style.height) || img.clientHeight;
        if (!width || !height) return;
        ctx.clearRect(0, 0, width, height);
        if (!points.length) return;
        ctx.beginPath();
        ctx.moveTo(points[0][0] * width, points[0][1] * height);
        for (const [x, y] of points.slice(1)) ctx.lineTo(x * width, y * height);
        if (points.length >= 3 && !editing) ctx.closePath();
        ctx.strokeStyle = enabled && !editing ? '#ff3b30' : '#ffba08';
        ctx.lineWidth = 3;
        ctx.stroke();
        if (points.length >= 3 && !editing) {
            ctx.fillStyle = 'rgba(255,59,48,0.18)';
            ctx.fill();
        }
        for (const [x, y] of points) {
            ctx.beginPath();
            ctx.arc(x * width, y * height, 4, 0, Math.PI * 2);
            ctx.fillStyle = '#ffffff';
            ctx.fill();
            ctx.stroke();
        }
    }
    function refreshButtons() {
        canvas.style.pointerEvents = editing ? 'auto' : 'none';
        canvas.style.cursor = editing ? 'crosshair' : 'default';
        btn.edit.textContent = editing ? '取消畫定' : '✏️ 畫定區域';
        btn.save.disabled = !editing || points.length < 3;
        btn.undo.disabled = !editing || points.length === 0;
        btn.toggle.disabled = editing || savedPoints.length < 3;
        btn.toggle.textContent = enabled ? '暫停偵測' : '啟用偵測';
        status.textContent = editing
            ? `編輯中：${points.length} 個頂點（至少 3 個）`
            : (savedPoints.length < 3 ? '尚未設定禁止進入區域'
                : enabled ? '🔴 區域入侵偵測已啟用（相機開啟時才會分析影像）'
                          : '⏸ 已儲存區域，但目前停用偵測');
        draw();
    }
    function applyZone(data) {
        savedPoints = Array.isArray(data.points) ? data.points.map(p => [...p]) : [];
        enabled = Boolean(data.enabled);
        if (!editing) points = savedPoints.map(p => [...p]);
        refreshButtons();
    }
    canvas.addEventListener('click', e => {
        if (!editing || points.length >= 20) return;
        const rect = canvas.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return;
        const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
        points.push([x, y]);
        refreshButtons();
    });
    btn.edit.addEventListener('click', () => {
        editing = !editing;
        points = editing ? [] : savedPoints.map(p => [...p]);
        setError();
        refreshButtons();
    });
    btn.undo.addEventListener('click', () => {
        if (editing) points.pop();
        refreshButtons();
    });
    btn.save.addEventListener('click', async () => {
        try {
            setError();
            const data = await api('/api/intrusion/zone', jsonRequest('PUT', { points, enabled: true }));
            editing = false;
            applyZone(data);
        } catch (e) { setError(`儲存失敗：${e.message}`); }
    });
    btn.toggle.addEventListener('click', async () => {
        try {
            setError();
            const data = await api('/api/intrusion/zone', jsonRequest('PUT', { enabled: !enabled }));
            applyZone(data);
        } catch (e) { setError(`切換失敗：${e.message}`); }
    });
    btn.clear.addEventListener('click', async () => {
        if (!confirm('確定清除目前禁止進入區域並停止偵測？')) return;
        try {
            setError();
            const data = await api('/api/intrusion/zone', { method: 'DELETE' });
            editing = false;
            applyZone(data);
        } catch (e) { setError(`清除失敗：${e.message}`); }
    });
    btn.permission.addEventListener('click', async () => {
        if (!('Notification' in window)) {
            return setError('瀏覽器不支援桌面通知，仍可使用頁面內通知');
        }
        try {
            const permission = await Notification.requestPermission();
            setError(permission === 'granted' ? '桌面通知已允許；請保持管理頁面開啟。'
                                                  : '尚未允許桌面通知；頁面警報仍可運作。');
        } catch (e) { setError(`通知權限錯誤：${e.message}`); }
    });
    function addEvent(ev) {
        const li = document.createElement('li');
        const time = String(ev.timestamp || '');
        li.textContent = `${time}｜${String(ev.message || '有人進入禁止區域')}`;
        eventList.prepend(li);
        while (eventList.children.length > 20) eventList.lastChild.remove();
    }
    socket.on('intrusion_alert', ev => {
        addEvent(ev);
        status.textContent = '🚨 警報：偵測到人員進入禁止區域！';
        document.title = '🚨 區域入侵警報 - 社區管理';
        if ('Notification' in window && Notification.permission === 'granted') {
            try { new Notification('社區禁止區域入侵警報', { body: String(ev.message || '') }); }
            catch (e) { console.warn('桌面通知未送達:', e); }
        }
        // In-page alert always works when manager page is open.
        const toast = document.createElement('div');
        toast.className = 'intrusion-toast';
        toast.textContent = String(ev.message || '有人進入禁止區域');
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 8000);
    });
    socket.on('intrusion_error', ev => setError(`偵測模組錯誤：${ev.message || '未知錯誤'}`));
    socket.on('intrusion_zone_updated', data => applyZone(data));
    if ('ResizeObserver' in window) new ResizeObserver(syncCanvas).observe(img);
    window.addEventListener('resize', syncCanvas);
    img.addEventListener('load', syncCanvas);
    Promise.all([
        api('/api/intrusion/zone'),
        api('/api/intrusion/events')
    ]).then(([zone, history]) => {
        applyZone(zone);
        for (const event of (history.events || []).slice().reverse()) addEvent(event);
        syncCanvas();
    }).catch(e => setError(`初始化失敗：${e.message}`));
    refreshButtons();
}
