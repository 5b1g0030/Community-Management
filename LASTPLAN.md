# 這裡寫下一步規劃或是專案現狀分析

## 現狀: Flask->Quart 架構修改，確保能正確執行

## 一定需要修改的檔案
1.  **app.py: 這是目前問題最多的檔案，仍有多處漏掉 await。**
2. **modules/user.py**: 這個檔案完全仍是同步資料庫寫法
    如果要完整配合 Quart，建議：
        async def register_user(...)
        async def login_user(...)
3. **modules/video_streaming/faceMessage.py: 這個檔案有兩個非同步使用錯誤。**
    *錯誤一：把 async 函式放進 asyncio.to_thread*
        username = await asyncio.to_thread(
               visitor_Booking.get_visitor_by_face_name,
                name
         )
        應改成：
            username = await visitor_Booking.get_visitor_by_face_name(name)
    *錯誤二：同樣錯誤套用在快取更新*
            await asyncio.to_thread(refresh_face_cache, db_manager)
        應改成:
            await refresh_face_cache()
4. **modules/video_streaming/video_streaming.py: 仍有幾個問題**
    *錯誤一: Socket.IO 呼叫漏掉 await*:
        modules/init.py 建立的是：sio = socketio.AsyncServer(...)
        應統一成類似：from modules import sio 然後 await sio.emit('pickup_success', {...})
    *錯誤二: 相機 I/O 仍是同步操作*
        ret, frame = camera.read() 應使用 ret, frame = camera.read()
5. **utils/camera_utils.py: 這個檔案本身仍是完全同步的**
    這個檔案不一定要全部改成 async def，也可以保留同步函式，改由呼叫端使用：await asyncio.to_thread(CameraManager.find_camera, backends) (可選)
6. **utils/directory_utils.py: 影響通常不大，但若要求完整避免阻塞，應改成非同步包裝**

## 最終需要列出的未完整修改檔案
最重要的清單如下：
- app.py
- modules/user.py
- modules/video_streaming/faceMessage.py
- modules/video_streaming/video_streaming.py
- utils/camera_utils.py
- utils/directory_utils.py

其中前 4 個是會直接造成 coroutine、未等待或執行錯誤的高優先級檔案；後 2 個主要是仍可能阻塞 Quart 事件迴圈。7. 