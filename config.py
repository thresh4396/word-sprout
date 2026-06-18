"""
「词芽」配置文件
设计令牌、主题、API预设、常量集中管理
"""

import os
import sys

# ---- 路径 ----
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# 数据文件
PHRASES_FILE = os.path.join(DATA_DIR, "phrases.json")
REVIEW_LOG_FILE = os.path.join(DATA_DIR, "review_log.json")
DAILY_STATS_FILE = os.path.join(DATA_DIR, "daily_stats.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
DIALOGUES_FILE = os.path.join(DATA_DIR, "dialogues.json")

# ---- API 厂商预设 ----
API_PRESETS = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-chat",
    },
    "qwen": {
        "name": "通义千问",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-plus", "qwen-max", "qwen-turbo"],
        "default_model": "qwen-plus",
    },
    "zhipu": {
        "name": "智谱 GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-4-flash", "glm-4-plus"],
        "default_model": "glm-4-flash",
    },
    "moonshot": {
        "name": "月之暗面 Kimi",
        "base_url": "https://api.moonshot.cn/v1",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "default_model": "moonshot-v1-8k",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o-mini", "gpt-4o"],
        "default_model": "gpt-4o-mini",
    },
    "custom": {
        "name": "自定义",
        "base_url": "",
        "models": [],
        "default_model": "",
    },
}

# ---- 默认设置 ----
DEFAULT_SETTINGS = {
    "theme": "薄荷",
    "api_provider": "deepseek",
    "api_key": "",
    "api_base_url": "https://api.deepseek.com/v1",
    "api_model": "deepseek-chat",
    "review_batch_size": 10,
    "daily_new_goal": 5,
    "daily_review_goal": 20,
    "first_step_data_path": "",
    "sync_enabled": True,
}

# ---- SM-2 算法参数 ----
SM2_DEFAULT_EF = 2.5
SM2_MIN_EF = 1.3
SM2_MAX_EF = 3.0          # 标准 SM-2 最大值（之前 2.5=初始值导致 EF 永不增长）
MASTERY_CORRECT_MIN = 5
MASTERY_RATIO = 0.8
MASTERY_INTERVAL_MIN = 21  # 掌握至少需要的间隔天数

# ---- 掌握等级分层 ----
MASTERY_TIERS = {
    "seedling": {
        "key": "seedling",
        "label": "新学",
        "icon": "✨",
        "dot_color": "#bdbdbd",
    },
    "sprout": {
        "key": "sprout",
        "label": "学习中",
        "icon": "🌿",
        "dot_color": "#e6a23c",
    },
    "tree": {
        "key": "tree",
        "label": "已掌握",
        "icon": "🌳",
        "dot_color": "#2ecc71",
    },
}

# ---- 复习质量映射 ----
QUALITY_LABELS = {
    0: ("忘记", "完全不记得"),
    1: ("困难", "看到答案后有印象"),
    2: ("勉强", "答错了但答案很熟悉"),
    3: ("一般", "答对了但很费劲"),
    4: ("良好", "答对了稍作犹豫"),
    5: ("轻松", "完全不假思索"),
}

# ============================================================
# 设计令牌类 T — 运行时由 apply_theme() 动态赋值
# ============================================================

class T:
    # 颜色（默认薄荷主题）
    BG = "#f0f7f4"
    CARD = "#ffffff"
    ELEVATED = "#e8f2ec"
    GOLD = "#2ecc71"
    GOLD_DIM = "#27ae60"
    CORAL = "#e67e22"
    HIGHLIGHT = "#d4696e"
    TEXT = "#1a2e23"
    TEXT_DIM = "#5a7a6a"
    TEXT_MUTED = "#8aaa9a"
    SAGE = "#1abc9c"
    DIVIDER = "#d8e8e0"
    # 特殊色
    CORRECT_BG = "#d4edda"
    CORRECT_TEXT = "#155724"
    WRONG_BG = "#f8d7da"
    WRONG_TEXT = "#721c24"
    # 标签色
    TAG_BG = "#e8f2ec"
    TAG_TEXT = "#3d7a5c"
    TAG_HOVER = "#d0e8d8"

    # 字体
    FONT_DISPLAY = "Noto Serif SC"
    FONT_BODY = "Noto Sans SC"
    FONT_EN = "Times New Roman"

    # 圆角
    RADIUS = 16
    RADIUS_LG = 24
    RADIUS_SM = 10
    RADIUS_XS = 6

    # 字号（1080p 优化）
    BASE_FONT = 17
    H1 = 38
    H2 = 28
    H3 = 20
    BODY = 17
    CAPTION = 14
    SMALL = 13
    BTN_FONT = 20
    BTN_FONT_SMALL = 16

    # 间距
    CARD_PAD = 28
    PAGE_MARGIN = 32
    PAGE_SPACING = 20


# ============================================================
# 主题定义
# ============================================================

THEMES = {
    "薄荷": {
        "BG": "#f0f7f4", "CARD": "#ffffff", "ELEVATED": "#e8f2ec",
        "GOLD": "#2ecc71", "GOLD_DIM": "#27ae60", "CORAL": "#e67e22",
        "HIGHLIGHT": "#d4696e",
        "TEXT": "#1a2e23", "TEXT_DIM": "#5a7a6a", "TEXT_MUTED": "#8aaa9a",
        "SAGE": "#1abc9c", "DIVIDER": "#d8e8e0",
        "CORRECT_BG": "#d4edda", "CORRECT_TEXT": "#155724",
        "WRONG_BG": "#f8d7da", "WRONG_TEXT": "#721c24",
        "TAG_BG": "#e8f2ec", "TAG_TEXT": "#3d7a5c", "TAG_HOVER": "#d0e8d8",
    },
    "海盐": {
        "BG": "#f5f7fa", "CARD": "#ffffff", "ELEVATED": "#edf1f5",
        "GOLD": "#5b8def", "GOLD_DIM": "#4a7ad4", "CORAL": "#e85d75",
        "HIGHLIGHT": "#e8734a",
        "TEXT": "#1a2530", "TEXT_DIM": "#5a6c7a", "TEXT_MUTED": "#8a9aaa",
        "SAGE": "#3cb8a9", "DIVIDER": "#dde3ea",
        "CORRECT_BG": "#d4edf0", "CORRECT_TEXT": "#0c5460",
        "WRONG_BG": "#f8d7e0", "WRONG_TEXT": "#721c34",
        "TAG_BG": "#edf1f5", "TAG_TEXT": "#4a6a8a", "TAG_HOVER": "#dde3ea",
    },
    "樱草": {
        "BG": "#fefcf5", "CARD": "#ffffff", "ELEVATED": "#faf5e8",
        "GOLD": "#e8a817", "GOLD_DIM": "#c88a10", "CORAL": "#d4695a",
        "HIGHLIGHT": "#2e86ab",
        "TEXT": "#2a2218", "TEXT_DIM": "#6b5c48", "TEXT_MUTED": "#9b8c78",
        "SAGE": "#6b9b4a", "DIVIDER": "#ece0d0",
        "CORRECT_BG": "#e8f5e0", "CORRECT_TEXT": "#3c5a1e",
        "WRONG_BG": "#fce4d0", "WRONG_TEXT": "#7a3a1e",
        "TAG_BG": "#faf5e8", "TAG_TEXT": "#8a6c38", "TAG_HOVER": "#f0e8d0",
    },
    "暮紫": {
        "BG": "#1a1a24", "CARD": "#242430", "ELEVATED": "#2e2e3c",
        "GOLD": "#a78bfa", "GOLD_DIM": "#8b6fe0", "CORAL": "#f472b6",
        "HIGHLIGHT": "#e2b04a",
        "TEXT": "#e8e0f0", "TEXT_DIM": "#9888b0", "TEXT_MUTED": "#685878",
        "SAGE": "#6ee7b7", "DIVIDER": "#333040",
        "CORRECT_BG": "#1a3a2a", "CORRECT_TEXT": "#8ae0a8",
        "WRONG_BG": "#3a1a2a", "WRONG_TEXT": "#e0a0b8",
        "TAG_BG": "#2e2e3c", "TAG_TEXT": "#a898d0", "TAG_HOVER": "#3e3e50",
    },
}

_current_theme = "薄荷"


def apply_theme(name):
    """应用主题：将主题色值写入 T 类属性"""
    global _current_theme
    if name not in THEMES:
        return
    _current_theme = name
    for k, v in THEMES[name].items():
        setattr(T, k, v)


def get_current_theme():
    return _current_theme


def text_on_accent():
    """
    返回适合在 T.GOLD 背景上显示的文字颜色。
    根据 T.GOLD 亮度自动选择，保证所有主题下的对比度。
    """
    hex_color = T.GOLD.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    # W3C 相对亮度
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "#1a1a1a" if luminance > 150 else "#ffffff"


def qss():
    """生成全局 QSS 样式表"""
    return f"""
    QMainWindow {{
        background: {T.BG};
    }}
    QWidget {{
        font-family: "{T.FONT_BODY}";
        font-size: {T.BODY}px;
        color: {T.TEXT};
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {T.DIVIDER};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QLineEdit {{
        background: {T.ELEVATED};
        border: 1px solid {T.DIVIDER};
        border-radius: {T.RADIUS_SM}px;
        padding: 12px 16px;
        font-size: {T.BODY}px;
        color: {T.TEXT};
    }}
    QLineEdit:focus {{
        border: 1px solid {T.GOLD};
    }}
    QTextEdit {{
        background: {T.ELEVATED};
        border: 1px solid {T.DIVIDER};
        border-radius: {T.RADIUS_SM}px;
        padding: 12px 16px;
        font-size: {T.BODY}px;
        color: {T.TEXT};
    }}
    QTextEdit:focus {{
        border: 1px solid {T.GOLD};
    }}
    QCheckBox {{
        spacing: 10px;
        font-size: {T.BODY}px;
    }}
    QCheckBox::indicator {{
        width: 22px;
        height: 22px;
        border-radius: 6px;
        border: 2px solid {T.DIVIDER};
        background: {T.CARD};
    }}
    QCheckBox::indicator:checked {{
        background: {T.GOLD};
        border-color: {T.GOLD};
    }}
    QComboBox {{
        background: {T.ELEVATED};
        border: 1px solid {T.DIVIDER};
        border-radius: {T.RADIUS_SM}px;
        padding: 10px 16px;
        font-size: {T.BODY}px;
        color: {T.TEXT};
    }}
    QComboBox:focus {{
        border: 1px solid {T.GOLD};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 30px;
    }}
    QComboBox QAbstractItemView {{
        background: {T.CARD};
        border: 1px solid {T.DIVIDER};
        selection-background-color: {T.ELEVATED};
        color: {T.TEXT};
    }}
    """
