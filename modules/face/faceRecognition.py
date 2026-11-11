# ===== face_recognition 人臉辨識 =====
import os
import numpy as np
import face_recognition
import logging as log
import cv2  
import asyncio  # [修改]：引入 asyncio 來處理非同步執行緒調度
from ..config import FACE_RECOGNITION_TOLERANCE, FACE_RECOGNITION_RESIZE_WIDTH, FACE_RECOGNITION_MODEL
from .image_processor import changeRGB
from modules.face.face_cache import face_cache
from modules.databases.face_repository import get_all_face, insert_face

# ===== 人臉註冊&辨識類別 =====
class FaceRecognition:

    # ===== 註冊人臉到資料庫(住戶加入) =====
    # [修改]：因為內部使用了 await，函式必須改為 async def
    async def register_faces(self, name, folder_path, files):
        """
        註冊人臉到資料庫
        
        參數:
            db_manager: DatabaseManager 物件
            name: 人名
            folder_path: 圖片資料夾路徑
            files: 檔案名稱列表
        
        返回:
            dict: {'success': bool, 'message': str, 'count': int}
        """
        try:
            
            count = 0
            
            for f in files:
                img_path = os.path.join(folder_path, f)
                
                # 加載圖片+轉RGB三通道
                log.info(f"[註冊] 處理圖片: {f}")
                # [修改]：changeRGB 已經改為非同步，必須加上 await
                image = await changeRGB(img_path)
                
                if image is None:
                    log.warning(f"[警告] 圖片 {f} 載入失敗，跳過。")
                    continue
                
                # 提取特徵向量
                log.info("  [步驟] 手動定位人臉位置...")
                # [修改]：將 CPU 密集的臉部定位交給背景執行緒，避免阻塞 Quart
                face_locations = await asyncio.to_thread(face_recognition.face_locations, image)
                
                log.info(f"  [步驟] 提取特徵向量 (偵測到 {len(face_locations)} 張臉)...")
                # [修改]：將 CPU 密集的特徵提取交給背景執行緒
                encodings = await asyncio.to_thread(face_recognition.face_encodings, image, known_face_locations=face_locations)
                
                # 如果有特徵向量
                if len(encodings) > 0:
                    # 將 numpy array 轉成二進位 BLOB
                    encoding_blob = encodings[0].tobytes()
                    # 插入到 face_recognition 表格 (原本就已經有 await)
                    await insert_face(name, encoding_blob)

                    count += 1
                else:
                    log.warning(f"[警告] 圖片 {f} 未偵測到人臉，跳過。")
            
            
            if count > 0:
                log.info(f"[系統] 成功為 {name} 註冊了 {count} 筆特徵數據。")
                return {'success': True, 'message': f'成功註冊 {count} 筆人臉資料', 'count': count}#***
            else:
                return {'success': False, 'message': '所有圖片都未偵測到人臉', 'count': 0}#***
                
        except Exception as e:
            log.error(f"[錯誤] 註冊人臉失敗: {e}")
            return {'success': False, 'message': f'註冊失敗: {str(e)}', 'count': 0}#***

    # ===== 辨識邏輯 =====
    async def recognize_face(self, test_img_path):
        """
        辨識靜態圖片中的人臉
        """
        try:
            # 從資料庫讀取所有已知資料
            data = await get_all_face()
            
            # 如果沒有任何已註冊人臉
            if not data:
                return {'success': False, 'message': '資料庫內無任何已知人臉，請先註冊'}#***
            
            # 取出所有 id、名稱、特徵向量
            known_ids = [row[0] for row in data]
            known_names = [row[1] for row in data]
            known_encodings = [np.frombuffer(row[2], dtype=np.float64) for row in data]
            
            # 處理測試圖片
            if not os.path.exists(test_img_path):
                return {'success': False, 'message': '找不到測試圖片路徑'}#***
            
            # 加載圖片+轉RGB三通道
            # [修改]：changeRGB 已經改為非同步，加上 await
            test_image = await changeRGB(test_img_path)
            
            if test_image is None:
                return {'success': False, 'message': '測試圖片載入失敗'}#***
            
            # 提取特徵向量
            # [修改]：CPU 密集運算，丟入背景執行緒
            test_encodings = await asyncio.to_thread(face_recognition.face_encodings, test_image)
            
            # 如果測試圖片未取到特徵向量
            if len(test_encodings) == 0:
                return {'success': False, 'message': '測試圖片中未偵測到人臉'}
            
            # 比對結果列表
            results = []
            
            # [修改]：將比對的內部邏輯包裝起來，因為 compare_faces 和 face_distance 都是重度數值運算
            def _compare_encoding(unknown_encoding):
                matches = face_recognition.compare_faces(known_encodings, unknown_encoding, 
                                                    tolerance=FACE_RECOGNITION_TOLERANCE)
                if True in matches:
                    face_distances = face_recognition.face_distance(known_encodings, unknown_encoding)
                    best_match_index = np.argmin(face_distances)
                    return matches, face_distances, best_match_index
                return matches, None, None

            # 比對圖中偵測到的每一張臉
            for unknown_encoding in test_encodings:
                # [修改]：透過 asyncio.to_thread 執行包裝好的比對函式
                matches, face_distances, best_match_index = await asyncio.to_thread(_compare_encoding, unknown_encoding)
                
                # 如果有比對到相似的人臉
                if True in matches:
                    if matches[best_match_index]:
                        name = known_names[best_match_index]
                        face_id = known_ids[best_match_index]
                        confidence = 1 - face_distances[best_match_index]
                        results.append({
                            'id': face_id,
                            'name': name,
                            'confidence': f'{confidence:.2%}',
                            'distance': float(face_distances[best_match_index])
                        })
                        log.info(f"[結果] 辨識成功！此人是: {name} (ID: {face_id}, 信心距離: {face_distances[best_match_index]:.4f})")
                    else:
                        results.append({'id': None, 'name': '未知', 'confidence': 'N/A'})
                else:
                    results.append({'id': None, 'name': '未知', 'confidence': 'N/A'})

            return {'success': True, 'message': '辨識成功', 'results': results} #***
        except Exception as e:
            log.error(f"[錯誤] 辨識失敗: {e}")
            return {'success': False, 'message': f'辨識失敗: {str(e)}'} #***

    # ===== 針對即時影像幀進行人臉辨識（優化版）=====
    # [修改]：因為內部將會呼叫 await (快取與影像處理)，函式必須改為 async def
    async def recognize_face_from_frame(self, db_manager, frame, use_cache=True, resize_width=FACE_RECOGNITION_RESIZE_WIDTH, model=FACE_RECOGNITION_MODEL):
        """
        針對即時影像幀進行人臉辨識（優化版）
        """
        
        # === 1. 取得已知人臉資料（使用快取或即時查詢）===
        if use_cache:
            # 如果快取是空的，先載入
            if face_cache.is_empty():
                # [修改]：load_from_database 已經被改為非同步函式，需要 await
                await face_cache.load_from_database(db_manager)
            
            known_ids = face_cache.known_ids
            known_names = face_cache.known_names
            known_encodings = face_cache.known_encodings
        else:
            # 即時查詢資料庫 (原本就已經是 await)
            data = await get_all_face()
            
            if not data:
                return []
            
            known_ids = [row[0] for row in data]
            known_names = [row[1] for row in data]
            known_encodings = [np.frombuffer(row[2], dtype=np.float64) for row in data]
        
        # 檢查有沒有資料
        if len(known_ids) == 0:
            return []
        
        # === 2. 影像預處理：降低解析度 ===
        original_height, original_width = frame.shape[:2]
        
        if original_width > resize_width:
            scale = resize_width / original_width
            new_width = resize_width
            new_height = int(original_height * scale)
            # [修改]：resize 速度通常夠快，可以不放進 thread，但若要極致非阻塞也可放進去
            small_frame = cv2.resize(frame, (new_width, new_height))
        else:
            scale = 1.0
            small_frame = frame
        
        # === 3. 使用 changeRGB 處理 frame (BGR -> RGB) ===
        # [修改]：changeRGB 改為非同步，需加上 await
        rgb_frame = await changeRGB(small_frame)
        if rgb_frame is None:
            return []
        
        # [修改]：將 4, 5, 6 步驟全部包裝進一個獨立的 CPU 任務中
        # 這樣做可以避免迴圈中頻繁切換 thread 造成的開銷，直接讓背景執行緒做完所有特徵比對
        def _process_frame_recognition():
            # 4. 偵測人臉位置
            face_locations = face_recognition.face_locations(rgb_frame, model=model)
            if len(face_locations) == 0:
                return []
            
            # 5. 提取特徵向量
            face_encodings = face_recognition.face_encodings(rgb_frame, known_face_locations=face_locations)
            
            # 6. 辨識結果列表
            res = []
            for i, face_encoding in enumerate(face_encodings):
                matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=FACE_RECOGNITION_TOLERANCE)
                
                position = face_locations[i]
                top, right, bottom, left = position
                
                if scale != 1.0:
                    top = int(top / scale)
                    right = int(right / scale)
                    bottom = int(bottom / scale)
                    left = int(left / scale)
                
                x, y, w, h = left, top, right - left, bottom - top

                # 檢查是否有「任一筆」符合
                if True in matches:
                    face_distances = face_recognition.face_distance(known_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    
                    if matches[best_match_index]:
                        res.append({
                            'id': known_ids[best_match_index],
                            'name': known_names[best_match_index],
                            'confidence': 1 - face_distances[best_match_index],
                            'position': (x, y, w, h)
                        })
                    else:
                        res.append({'id': None, 'name': '未知', 'confidence': 0.0, 'position': (x, y, w, h)})
                else:
                    res.append({'id': None, 'name': '未知', 'confidence': 0.0, 'position': (x, y, w, h)})
            return res

        # [修改]：利用 asyncio.to_thread 執行整個比對流程
        results = await asyncio.to_thread(_process_frame_recognition)
        
        return results

    # ===== 驗證上傳的照片是否能偵測到人臉 =====
    # [修改]：由於 file_obj 讀取與影像處理，改為 async def
    async def validate_face_images(self, image_files):
        """
        驗證上傳的照片是否能偵測到人臉
        """
        try:
            failed_images = []
            
            for position, file_obj in image_files.items():
                # [修改]：在 Quart 中，request.files 物件的 read() 必須使用 await
                raw_data = await file_obj.read()
                
                # [修改]：將影像解碼與人臉辨識打包，丟到背景執行緒
                def _validate_single_image(data):
                    image_data = np.frombuffer(data, np.uint8)
                    image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
                    if image is None:
                        return False
                    # 這邊使用原本寫法，或改用已封裝好的 changeRGB（因為原本 changeRGB 是 async，不適合在 thread 內直接呼叫）
                    # 所以直接在這裡轉換 RGB
                    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    face_locations = face_recognition.face_locations(rgb_image)
                    return len(face_locations) > 0

                is_valid = await asyncio.to_thread(_validate_single_image, raw_data)
                
                if not is_valid:
                    failed_images.append(position)
            
            if len(failed_images) > 0:
                position_names = {
                    'front': '正面照',
                    'left': '左微側臉',
                    'right': '右微側臉'
                }
                failed_names = [position_names.get(pos, pos) for pos in failed_images]
                return {#***
                    'success': False,
                    'message': f'以下照片未偵測到人臉：{", ".join(failed_names)}',
                    'failed_images': failed_images
                }
            
            return {#***
                'success': True,
                'message': '所有照片驗證成功',
                'failed_images': []
            }
        
        except Exception as e:
            print(f"[驗證] 照片驗證失敗: {e}")
            return {#***
                'success': False,
                'message': f'驗證失敗: {str(e)}',
                'failed_images': []
            }

    # ===== 註冊訪客人臉（從上傳的檔案）=====
    # [修改]：使用 await 讀取檔案與寫入資料庫，改為 async def
    async def register_visitor_faces(self, visitor_name, image_files):
        """
        註冊訪客人臉到資料庫（從上傳的檔案物件）
        """
        try:
            count = 0
            first_face_id = None
            
            for position, file_obj in image_files.items():
                # [修改]：Quart 中 seek 與 read 需要 await (視使用的檔案物件而定，如果是記憶體物件可能不用，但標準做法是 await)
                file_obj.seek(0)
                raw_data = await file_obj.read()
                
                # [修改]：打包 CPU 密集運算
                def _extract_encoding(data):
                    image_data = np.frombuffer(data, np.uint8)
                    image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
                    if image is None:
                        return None
                    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    
                    face_locations = face_recognition.face_locations(rgb_image)
                    encodings = face_recognition.face_encodings(rgb_image, known_face_locations=face_locations)
                    return encodings[0].tobytes() if len(encodings) > 0 else None

                encoding_blob = await asyncio.to_thread(_extract_encoding, raw_data)
                
                if encoding_blob is not None:
                    # 原本已經有 await，保留即可
                    face_id = await insert_face(visitor_name, encoding_blob)
                    
                    if first_face_id is None:
                        first_face_id = face_id
                    
                    count += 1
            
            if count > 0:
                log.info(f"[註冊] 成功為訪客 {visitor_name} 註冊了 {count} 筆特徵數據")
                return {#***
                    'success': True,
                    'message': f'成功註冊 {count} 筆訪客人臉資料',
                    'visitor_face_id': first_face_id
                }
            else:
                return {#***
                    'success': False,
                    'message': '所有照片都未能成功提取特徵',
                    'visitor_face_id': None
                }
        
        except Exception as e:
            log.error(f"[註冊] 註冊訪客人臉失敗: {e}")
            return {#***
                'success': False,
                'message': f'註冊失敗: {str(e)}',
                'visitor_face_id': None
            }