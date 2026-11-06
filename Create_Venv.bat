@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "VENV_DIR=.venv"
set "PY=%VENV_DIR%\Scripts\python.exe"

echo =============================================================
echo 開始建立 Python 虛擬環境與安裝套件
echo =============================================================

:: 0. 檢查系統是否安裝 Python 3.11
echo [0/5] 正在檢查 Python 3.11 環境...
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 系統未檢測到 Python 3.11！
    echo 請先安裝 Python 3.11（並勾選 Python Launcher / py.exe），再重新執行此批次檔。
    goto failed
) else (
    for /f "tokens=*" %%v in ('py -3.11 --version 2^>^&1') do set "SYS_PY_VER=%%v"
    echo [成功] 檢測到系統 Python 版本：!SYS_PY_VER!
)

:: 0-1. 檢查並建立虛擬環境 (指定使用 py -3.11 建立)
if not exist "%PY%" (
    echo [1/5] 正在使用 Python 3.11 建立虛擬環境 [%VENV_DIR%]...
    py -3.11 -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [錯誤] 建立虛擬環境失敗，請檢查 Python 權限與環境變數設定。
        goto failed
    )
    *Verification:* 資料夾內應會生成包含 Python 3.11 執行檔的 `.venv` 目錄。
) else (
    echo [1/5] 已檢測到現有的虛擬環境 [%VENV_DIR%]，跳過建立步驟。
)

:: 2. 升級 pip 與基礎工具
echo [2/5] 正在升級 pip 與打包工具...
"%PY%" -m pip install --upgrade pip wheel "setuptools<70.0.0"
if errorlevel 1 goto failed

:: 3. 獨立處理 dlib 與 face-recognition 相關套件
echo [3/5] 正在安裝 dlib[windows優化版] 與人臉識別套件...
:: 強制移除可能殘留的舊版本或未完成的模組
"%PY%" -m pip uninstall -y dlib dlib-bin face-recognition face_recognition_models >nul 2>&1

"%PY%" -m pip install --no-cache-dir "face_recognition_models==0.3.0"
if errorlevel 1 goto failed

"%PY%" -m pip install --no-deps --no-cache-dir "face_recognition==1.3.0"
if errorlevel 1 goto failed

"%PY%" -m pip install --only-binary=:all: --no-cache-dir "dlib-bin==20.0.1.post1"
if errorlevel 1 goto failed

echo [暫停] 請注意：dlib 與 face-recognition 模組安裝完成後，若出現任何錯誤訊息，請確認您的系統是否符合安裝需求，並參考官方文件進行調整。   
pause

:: 4. 安裝 Quart 與非同步相關套件
echo [4/5] 正在安裝 Quart、Hypercorn 與非同步套件...
"%PY%" -m pip install quart hypercorn httpx aiosqlite
if errorlevel 1 goto failed
echo [暫停] 請注意：是否有dlib 與 face-recognition 模組相關錯誤訊息，請確認您的系統是否符合安裝需求，並參考官方文件進行調整。
pause

:: 5. 安裝其餘 requirements.txt 套件
if exist "requirements.txt" (
    echo [5/5] 正在安裝 requirements.txt 中的其餘模組...
    "%PY%" -m pip install -r requirements.txt
    if errorlevel 1 goto failed
) else (
    echo [5/5] 未找到 requirements.txt，跳過此步驟。
)

echo.
echo =============================================================
echo 所有套件安裝成功！
echo =============================================================
pause
exit /b 0

:failed
echo.
echo =============================================================
echo [錯誤] 套件安裝過程發生錯誤，請檢查上方報錯訊息。
echo =============================================================
pause
exit /b 1