"""
「词芽」今日面板
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from config import T
from widgets.base import GoldBtn, GhostBtn, Card, _clear_layout
from data_manager import get_today_stats, get_phrases
from review_engine import get_due_count


class DashboardPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window

        # 外层布局（只放滚动区域）
        page_lo = QVBoxLayout(self)
        page_lo.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.layout = QVBoxLayout(content)
        self.layout.setContentsMargins(T.PAGE_MARGIN, 24, T.PAGE_MARGIN, 24)
        self.layout.setSpacing(T.PAGE_SPACING)

        scroll.setWidget(content)
        page_lo.addWidget(scroll)
        self.build()

    def build(self):
        _clear_layout(self.layout)

        # ===== 顶部：日期 + 问候 =====
        from datetime import date
        today = date.today()
        weekday_names = ["一", "二", "三", "四", "五", "六", "日"]
        wd = weekday_names[today.weekday()]

        header = QLabel(f"{today.month}月{today.day}日 · 星期{wd}")
        header.setStyleSheet(f"""
            font-family: "{T.FONT_DISPLAY}"; font-size: {T.H1}px;
            font-weight: 700; color: {T.TEXT}; background: transparent; border: none;
        """)
        self.layout.addWidget(header)

        greeting = QLabel("今天也是积累的一天 🌱")
        greeting.setStyleSheet(f"font-size: {T.BODY}px; color: {T.TEXT_MUTED}; background: transparent; border: none;")
        self.layout.addWidget(greeting)

        self.layout.addSpacing(8)

        # ===== 统计卡片行 =====
        stats = get_today_stats()
        due = get_due_count(get_phrases())

        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        stats_defs = [
            ("📝", "今日录入", str(stats["phrases_added"])),
            ("🔄", "待复习", str(due)),
            ("💡", "已掌握", str(sum(1 for p in get_phrases() if p.get("mastered")))),
            ("📚", "总词库", str(len(get_phrases()))),
            ("💬", "今日对话", str(stats["dialogues_generated"])),
        ]

        for icon, label, value in stats_defs:
            stat_card = QFrame()
            stat_card.setObjectName("statCard")
            stat_card.setStyleSheet(f"""
                QFrame#statCard {{
                    background: {T.CARD};
                    border: 1px solid {T.DIVIDER};
                    border-radius: {T.RADIUS}px;
                    padding: 18px;
                }}
            """)
            sc_lo = QVBoxLayout(stat_card)
            sc_lo.setSpacing(6)

            icon_lbl = QLabel(icon)
            icon_lbl.setStyleSheet(f"font-size: 24px; background: transparent; border: none;")
            sc_lo.addWidget(icon_lbl)

            value_lbl = QLabel(value)
            value_lbl.setStyleSheet(f"""
                font-family: "{T.FONT_DISPLAY}"; font-size: 30px; font-weight: 700;
                color: {T.GOLD}; background: transparent; border: none;
            """)
            sc_lo.addWidget(value_lbl)

            label_lbl = QLabel(label)
            label_lbl.setStyleSheet(f"font-size: {T.CAPTION}px; color: {T.TEXT_MUTED}; background: transparent; border: none;")
            sc_lo.addWidget(label_lbl)

            stats_row.addWidget(stat_card)

        self.layout.addLayout(stats_row)

        self.layout.addSpacing(4)

        # ===== 快捷操作 =====
        actions_card = Card()
        actions_lo = QHBoxLayout(actions_card)
        actions_lo.setSpacing(16)

        add_btn = GoldBtn("+ 录入新词组")
        add_btn.clicked.connect(self.mw.open_add_phrase)

        review_btn = GhostBtn("去复习")
        review_btn.clicked.connect(self.mw.go_to_review)

        dialogue_btn = GhostBtn("生成对话")
        dialogue_btn.clicked.connect(lambda: self.mw.go_to_dialogue())

        actions_lo.addWidget(add_btn)
        actions_lo.addWidget(review_btn)
        actions_lo.addWidget(dialogue_btn)
        actions_lo.addStretch()

        self.layout.addWidget(actions_card)

        # ===== 今日录入的词组 =====
        self.layout.addSpacing(8)
        recent_title = QLabel("今日录入")
        recent_title.setStyleSheet(f"""
            font-family: "{T.FONT_DISPLAY}"; font-size: {T.H2}px;
            font-weight: 700; color: {T.TEXT}; background: transparent; border: none;
        """)
        self.layout.addWidget(recent_title)

        phrases = get_phrases()
        today_str = today.isoformat()
        today_phrases = [p for p in phrases if p["created"][:10] == today_str]

        if not today_phrases:
            empty = QLabel("今天还没有记录词组，点击上方按钮开始吧")
            empty.setStyleSheet(f"color: {T.TEXT_MUTED}; padding: 24px; background: transparent; border: none;")
            self.layout.addWidget(empty)
        else:
            for p in today_phrases:
                row = QFrame()
                row.setObjectName("phraseRow")
                row.setStyleSheet(f"""
                    QFrame#phraseRow {{
                        background: {T.ELEVATED};
                        border-radius: {T.RADIUS_SM}px;
                        padding: 12px 16px;
                    }}
                """)
                r_lo = QHBoxLayout(row)
                r_lo.setContentsMargins(16, 10, 16, 10)

                ph = QLabel(p["phrase"])
                ph.setStyleSheet(f"font-size: {T.H3}px; font-weight: 700; color: {T.TEXT}; background: transparent; border: none;")
                r_lo.addWidget(ph)
                r_lo.addStretch()

                me = QLabel(p["meaning"])
                me.setStyleSheet(f"font-size: {T.BODY}px; color: {T.TEXT_DIM}; background: transparent; border: none;")
                r_lo.addWidget(me)

                self.layout.addWidget(row)

        self.layout.addStretch()
