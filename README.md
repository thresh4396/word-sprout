# 🌱 词芽 · WordSprout

> 英语词组积累与 AI 对话复习 — 基于 PySide6 的桌面学习工具

![词芽](app.png)

## ✨ 功能

| 模块 | 说明 |
|------|------|
| 📋 **今日** | 仪表盘概览，今日目标进度、待复习数量一目了然 |
| 📖 **词库** | 浏览、搜索、管理所有词组，支持标签分类 |
| 🔄 **复习** | 基于 **SM-2 间隔重复算法** 的闪卡复习，科学安排复习节奏 |
| 💬 **对话** | 勾选词组 → **AI 自动生成自然对话**，覆盖所有目标词组 |
| 📊 **统计** | 学习数据可视化，追踪每日积累 |

### 🧠 AI 对话的三种练习模式

1. **📖 纯阅读** — 阅读 AI 生成的对话，目标词组高亮
2. **✏️ 填空** — 完形填空形式，检验词组拼写和应用
3. **🧠 阅读理解** — 5 道标准阅读理解题（主旨/细节/推理/词义/态度）

### 🎨 4 套主题

| 薄荷 | 海盐 | 樱草 | 暮紫 |
|------|------|------|------|
| 清新绿 | 科技蓝 | 暖米色 | 深色暗紫 |

## 🚀 快速开始

### 1. 环境要求

- **Python** ≥ 3.10
- **PySide6**（Qt for Python）

```bash
pip install PySide6
```

### 2. 运行

```bash
python app.py
```

或者双击 `start.vbs` 一键启动（Windows）。

### 3. 打包为 exe（可选）

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=app.ico --name="词芽" app.py
```

## 🔑 API Key 配置

词芽的「AI 对话生成」功能需要调用大语言模型 API，**你需要自行获取 API Key**。

### 支持的厂商

| 厂商 | 获取 Key 地址 | 免费额度 |
|------|-------------|---------|
| **DeepSeek**（推荐） | [platform.deepseek.com](https://platform.deepseek.com/) | ✅ 新用户赠送 |
| **通义千问** | [dashscope.aliyun.com](https://dashscope.aliyun.com/) | ✅ 有免费额度 |
| **智谱 GLM** | [open.bigmodel.cn](https://open.bigmodel.cn/) | ✅ 新用户赠送 |
| **月之暗面 Kimi** | [platform.moonshot.cn](https://platform.moonshot.cn/) | ✅ 新用户赠送 |
| **OpenAI** | [platform.openai.com](https://platform.openai.com/) | ❌ 需付费 |
| **自定义** | 任意兼容 OpenAI 格式的 API | — |

### 配置步骤

1. 打开词芽，点击底部 **💬 对话** 标签
2. 在页面顶部找到 **API 设置卡片**
3. 选择厂商 → 粘贴 API Key → 点击 **保存**
4. 勾选词组后点击「生成对话」即可

> 💡 API Key 保存在本地的 `data/settings.json` 中，不会上传到任何服务器。

## 📁 项目结构

```
word-sprout/
├── app.py                 # 入口
├── main_window.py         # 主窗口 + 导航
├── config.py              # 主题 / API 预设 / 设计令牌
├── api_client.py          # AI API 客户端（兼容 OpenAI 格式）
├── data_manager.py        # 数据持久化（JSON） + SM-2 算法
├── review_engine.py       # 复习调度引擎
├── pages/
│   ├── dashboard_page.py  # 今日概览
│   ├── browse_page.py     # 词库浏览
│   ├── review_page.py     # 闪卡复习
│   ├── dialogue_page.py   # AI 对话生成 + 练习
│   ├── stats_page.py      # 学习统计
│   └── add_phrase_page.py # 录入词组
├── widgets/
│   ├── base.py            # 基础组件（按钮/卡片/标签等）
│   ├── flashcard.py       # 闪卡组件
│   ├── dialogue_bubble.py # 对话气泡 / 填空 / 理解题
│   ├── quiz_panel.py      # 测验面板
│   └── stats_chart.py     # 统计图表
├── data/                  # 本地数据（不上传 Git）
└── start.vbs              # Windows 一键启动脚本
```

## 🛠 技术栈

- **GUI**: PySide6（Qt for Python）
- **AI API**: 兼容 OpenAI Chat Completions 格式
- **复习算法**: SM-2（SuperMemo 2）
- **数据存储**: 本地 JSON 文件

## 📄 License

MIT
