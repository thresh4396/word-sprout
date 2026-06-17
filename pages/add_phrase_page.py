"""
「词芽」词组录入页面
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QScrollArea, QFrame,
)
from PySide6.QtCore import Qt

from config import T
from widgets.base import GoldBtn, GhostBtn, Card, _clear_layout
from data_manager import add_phrase


class AddPhrasePage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(T.PAGE_MARGIN, 24, T.PAGE_MARGIN, 24)
        self.layout.setSpacing(T.PAGE_SPACING)
        self.build()

    def build(self):
        _clear_layout(self.layout)

        # 标题
        title = QLabel("录入新词组")
        title.setStyleSheet(f"""
            font-family: "{T.FONT_DISPLAY}"; font-size: {T.H1}px;
            font-weight: 700; color: {T.TEXT}; background: transparent; border: none;
        """)
        self.layout.addWidget(title)

        sub = QLabel("每学一个新词组，就像种下一颗种子")
        sub.setStyleSheet(f"font-size: {T.BODY}px; color: {T.TEXT_MUTED}; background: transparent; border: none;")
        self.layout.addWidget(sub)
        self.layout.addSpacing(8)

        # ===== 表单卡片 =====
        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(18)

        # 英文词组
        card_layout.addWidget(QLabel("英文词组 *"))
        self.phrase_input = QLineEdit()
        self.phrase_input.setPlaceholderText("例如：take the initiative")
        self.phrase_input.setMinimumHeight(48)
        card_layout.addWidget(self.phrase_input)

        # 中文释义
        card_layout.addWidget(QLabel("中文释义 *"))
        self.meaning_input = QLineEdit()
        self.meaning_input.setPlaceholderText("例如：主动出击，采取主动")
        self.meaning_input.setMinimumHeight(48)
        card_layout.addWidget(self.meaning_input)

        # 例句
        card_layout.addWidget(QLabel("例句"))
        self.example_input = QTextEdit()
        self.example_input.setPlaceholderText("包含该词组的英文例句...")
        self.example_input.setMaximumHeight(80)
        card_layout.addWidget(self.example_input)

        # 标签
        card_layout.addWidget(QLabel("标签（用逗号分隔）"))
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("例如：商务, 动词短语, idiom")
        self.tags_input.setMinimumHeight(48)
        card_layout.addWidget(self.tags_input)

        self.layout.addWidget(card)

        # ===== 按钮区 =====
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = GhostBtn("返回")
        cancel_btn.clicked.connect(lambda: self.mw.on_nav(0))
        btn_row.addWidget(cancel_btn)

        save_btn = GoldBtn("保存词组")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        self.layout.addLayout(btn_row)
        self.layout.addStretch()

    def _save(self):
        phrase = self.phrase_input.text().strip()
        meaning = self.meaning_input.text().strip()

        if not phrase or not meaning:
            self.mw.toast("请填写英文词组和中文释义")
            return

        example = self.example_input.toPlainText().strip()
        tags_text = self.tags_input.text().strip()
        tags = [t.strip() for t in tags_text.replace("，", ",").split(",") if t.strip()]

        add_phrase(phrase, meaning, example, tags)

        self.mw.toast("词组已保存 ✓")

        # 清空表单
        self.phrase_input.clear()
        self.meaning_input.clear()
        self.example_input.clear()
        self.tags_input.clear()
        self.phrase_input.setFocus()
