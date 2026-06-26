@echo off
chcp 65001 >nul
cd /d "D:\桌面\A自媒体账号\podcast-distill"

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

REM LLM 配置（可选，不配置则用 scaffold 占位模式）
REM set LLM_BASE_URL=https://api.openai.com/v1
REM set LLM_API_KEY=sk-xxx
REM set LLM_MODEL=gpt-4o

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set dt=%%I
set TODAY=%dt:~0,4%-%dt:~4,2%-%dt:~6,2%
echo 日期: %TODAY%
echo 知识库: 半脑互搏 (space_id=7655607441056337129)
echo.

echo [1/4] 采集新内容 (YouTube + 小宇宙, 需几分钟)...
python scripts\collect_daily_items.py --date %TODAY% --lookback-hours 24 --output-json reports\daily_items_%TODAY%.json --output-urls config\daily_urls.txt
if %errorlevel% neq 0 echo [WARN] 采集步骤有错误，继续

echo.
echo [2/4] 提取字幕...
python extract_subtitles.py --batch config\daily_urls.txt --output subtitles --no-asr
if %errorlevel% neq 0 echo [WARN] 字幕步骤有错误，继续

echo.
echo [3/4] 生成日报...
python scripts\generate_daily_report.py --date %TODAY% --items-json reports\daily_items_%TODAY%.json --subtitles-dir subtitles --output reports\daily-%TODAY%.md
if %errorlevel% neq 0 echo [WARN] 日报生成有错误，继续

echo.
echo [4/4] 发布到飞书知识库 + 群通知...
python scripts\publish_feishu.py --file reports\daily-%TODAY%.md --title "%TODAY% 播客/视频更新日报"
echo.

echo ============================================================
echo   完成! 报告: reports\daily-%TODAY%.md
echo   飞书知识库已更新 + 群通知已发送
echo ============================================================
pause
