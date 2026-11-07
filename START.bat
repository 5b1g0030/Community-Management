@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "VENV_DIR=.venv"
set "HYPERCORN=%VENV_DIR%\Scripts\hypercorn.exe"
set "PY=%VENV_DIR%\Scripts\python.exe"

echo =============================================================
echo 正在啟動 Hypercorn 伺服器...
echo =============================================================

:: 檢查虛擬環境是否存在
if not exist "%PY%" (
    echo [錯誤] 未檢測到虛擬環境 [%VENV_DIR%]！
    echo 請先執行環境安裝批次檔建立 .venv 虛擬環境後再試。
    echo.
    pause
    exit /b 1
)

:: 嘗試直接執行虛擬環境內的 hypercorn，若無則使用 python -m hypercorn
:: -w 4: 指定使用 4 個工作進程(CPU)
if exist "%HYPERCORN%" (
    "%HYPERCORN%" app:app --bind 127.0.0.1:5000 
) else (
    "%PY%" -m hypercorn app:app --bind 127.0.0.1:5000
)

if errorlevel 1 (
    echo.
    echo [錯誤] 伺服器異常終止，請檢查上方錯誤訊息。
    pause
    exit /b 1
)