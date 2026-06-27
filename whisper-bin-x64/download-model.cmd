@echo off
chcp 65001 >nul
echo ============================================
echo   Whisper 模型下载脚本
echo ============================================
echo.

set "MODEL_DIR=%~dp0models"
set "MODEL_FILE=%MODEL_DIR%\ggml-small-q5_1.bin"
set "MODEL_URL=https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small-q5_1.bin"
set "MODEL_SIZE=181 MB"

if not exist "%MODEL_DIR%" mkdir "%MODEL_DIR%"

if exist "%MODEL_FILE%" (
    echo [INFO] 模型文件已存在: %MODEL_FILE%
    echo [INFO] 如需重新下载，请先删除该文件。
    pause
    exit /b 0
)

echo [INFO] 正在下载 ggml-small-q5_1.bin (%MODEL_SIZE%) ...
echo [INFO] 下载地址: %MODEL_URL%
echo [INFO] 保存到: %MODEL_FILE%
echo.

curl -L -o "%MODEL_FILE%" "%MODEL_URL%"

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] 下载失败！请检查网络连接。
    echo [TIP]  如果无法访问 HuggingFace，可以使用镜像:
    echo        https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-small-q5_1.bin
    pause
    exit /b 1
)

echo.
echo [OK] 模型下载完成！
echo [OK] 文件位置: %MODEL_FILE%
echo.
echo 你现在可以使用 whisper-cli.exe 进行语音识别了。
pause
