@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo   Podcast Distill - 完整管道 (过去24小时)
echo ============================================================
echo.

REM === 加载本地凭证 (credentials.cmd 不提交 git) ===
if exist credentials.cmd (
    call credentials.cmd
) else (
    echo [ERROR] 缺少 credentials.cmd，请复制 credentials.example.cmd 为 credentials.cmd 并填入真实密钥
    pause
    exit /b 1
)

REM === 使用明确的 Python，避免命中 Windows Store 占位程序 ===
if not defined PYTHON_BIN if exist "D:\ProgramData\anaconda3\python.exe" set "PYTHON_BIN=D:\ProgramData\anaconda3\python.exe"
if not defined PYTHON_BIN if exist "%CD%\.venv\Scripts\python.exe" set "PYTHON_BIN=%CD%\.venv\Scripts\python.exe"
if not exist "%PYTHON_BIN%" (
    echo [ERROR] 找不到 Python: %PYTHON_BIN%
    echo 请在 credentials.cmd 中设置 PYTHON_BIN，或创建项目 .venv
    pause
    exit /b 1
)

REM LLM 配置（可选；不配置则从完整字幕做确定性提取）
REM set LLM_BASE_URL=https://api.openai.com/v1
REM set LLM_API_KEY=sk-xxx
REM set LLM_MODEL=gpt-4o

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set TODAY=%%I
echo 日期: %TODAY%
echo 知识库: 半脑互搏
echo.

echo [1/4] 采集新内容 (YouTube + 小宇宙, 需几分钟)...
"%PYTHON_BIN%" scripts\collect_daily_items.py --date %TODAY%T06:00 --lookback-hours 24 --youtube-backend api --output-json reports\daily_items_%TODAY%.json --output-urls config\daily_urls.txt
if %errorlevel% neq 0 (
    echo [ERROR] 采集步骤失败，停止后续发布，详见 manifest
    pause
    exit /b 1
)

echo.
echo [2/4] 提取字幕...
"%PYTHON_BIN%" extract_subtitles.py --batch config\daily_urls.txt --output subtitles --youtube-probe-timeout 90 --youtube-sleep 5 --results-json subtitles\extraction_results.json --retry-urls subtitles\retry_urls.txt --asr-urls subtitles\asr_urls.txt
if %errorlevel% neq 0 echo [WARN] 字幕步骤有错误，继续

echo.
echo [3/4] 生成日报...
"%PYTHON_BIN%" scripts\generate_daily_report.py --date %TODAY% --items-json reports\daily_items_%TODAY%.json --subtitles-dir subtitles --output reports\daily-%TODAY%.md --llm-policy extractive
if %errorlevel% neq 0 echo [WARN] 日报生成有错误，继续

echo.
echo [4/4] 发布到飞书知识库 + 群通知...
"%PYTHON_BIN%" scripts\publish_feishu.py --file reports\daily-%TODAY%.md --title "%TODAY% 播客/视频更新日报"
echo.

echo ============================================================
echo   完成! 报告: reports\daily-%TODAY%.md
echo   飞书知识库已更新 + 群通知已发送
echo ============================================================
pause
