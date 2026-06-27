# 🎧 Podcast Distill — 播客/视频日报自动化

> 每天早上 5 点（北京时间），自动抓取你关注的播客和视频频道，提取完整字幕，用 AI 生成结构化中文摘要，发布到飞书知识库，并推送到飞书群。

## 📖 日报在哪里看

所有日报自动发布到飞书知识库，每日更新：

👉 **[点击查看每日播客/视频日报](https://my.feishu.cn/wiki/space/7655607441056337129?ccm_open_type=lark_wiki_spaceLink&open_tab_from=wiki_home)**

## ✨ 它能做什么

- **多源采集**：自动从小宇宙播客、YouTube 频道、B 站等平台抓取每日更新
- **字幕提取**：优先获取官方字幕，无字幕时使用 Whisper.cpp 本地语音识别转录
- **智能摘要**：利用大语言模型对完整转录内容进行深度分析，生成结构化摘要
- **分类整理**：按「科技/AI/VC」「商业/财经/投资」「产品/创业/管理」「新闻/时评/全球议题」「文化/社会/人文」五大板块分类
- **自动发布**：每日凌晨自动运行，日报直接写入飞书知识库，并通过飞书群机器人通知

## 📋 日报包含什么

每则内容包含：

- **基本信息**：原始标题、栏目/频道、平台、更新时间、分类、推荐星级
- **嘉宾与机构**：出场人物和相关机构
- **一句话摘要**：快速了解核心内容
- **完整摘要**：详细内容概括
- **核心观点**：提炼关键论点
- **关键内容**：值得记录的细节与数据
- **值得后续整理的问题**：启发思考的延伸话题

## ⏰ 运行时间

- **每日北京时间 05:00** 自动运行
- 采集窗口为前一天 06:00 至当天 06:00 的更新
- 也支持手动触发，可指定日期补跑

## 🛠 技术栈

- **字幕提取**：yt-dlp（视频元数据/字幕）+ Whisper.cpp（ASR 语音识别，small-q5_1 量化模型）
- **摘要生成**：OpenAI 兼容 API（通义千问）
- **文档发布**：飞书开放 API + lark-cli
- **自动化**：GitHub Actions 定时调度
- **运行环境**：GitHub Actions Ubuntu CI + Windows 本地预编译 Whisper 二进制

## 📁 项目结构

```
podcast-distill/
├── .github/workflows/    # GitHub Actions 工作流
├── config/               # 播客源配置（urls.txt, podcasts.txt 等）
├── scripts/              # 核心脚本
│   ├── collect_daily_items.py   # 每日更新采集
│   ├── generate_daily_report.py # AI 摘要生成
│   └── publish_feishu.py        # 飞书文档发布
├── templates/            # 日报格式规范
├── whisper-bin-x64/      # Windows Whisper 预编译二进制+模型
├── extract_subtitles.py  # 字幕提取主程序
└── requirements.txt      # Python 依赖
```
