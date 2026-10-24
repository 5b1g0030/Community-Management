# ERROR - [video_streaming.py:41] - [錯誤] 影像串流處理失敗: 'coroutine' object is not iterable by video_streaming
最可能原因已經可以定位：人臉辨識函式已改成非同步 async def，但呼叫端沒有使用 await。

問題來源
在 faceRecognition.py：
async def recognize_face_from_frame(...):

這代表直接呼叫：
results = face_recognizer.recognize_face_from_frame(...)

若程式執行時還看到以下警告，也同樣是未等待 coroutine 的證據：
RuntimeWarning: coroutine 'FaceRecognition.recognize_face_from_frame' was never awaited

結論: 非同步函式的呼叫端漏了 await，導致 coroutine 物件被當成辨識結果列表迭代。
