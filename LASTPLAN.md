# 這裡寫下一步規劃或是專案現狀分析

## 現狀: Quart 架構修改已完成，有小bug，須確保訪客預約可以正常運行

### 刪除人臉bug
這是 非同步資料庫操作忘記加 await 的警告。

你的 db_manager.get_db_connection() 使用的是 aiosqlite，因此以下方法都是 coroutine，必須等待執行：
cursor.execute(...)
conn.commit()
conn.close()
目前 app.py 第 311、312、315 行未加 await，所以 Python 只建立了 coroutine，沒有真正執行它們：
await cursor.execute(
    f"DELETE FROM face_recognition WHERE id IN ({placeholders})",
    tuple(face_ids)
)
await conn.commit()

deleted_count = cursor.rowcount
await conn.close()

三個警告分別代表：

Cursor.execute was never awaited：刪除 SQL 沒有執行
Connection.commit was never awaited：刪除結果沒有提交
Connection.close was never awaited：資料庫連線沒有正確關閉

因此刪除可能實際上沒有成功，且連線可能造成資源未釋放。其他程式位置（例如 face_cache.py）已採用正確的 await 寫法。
