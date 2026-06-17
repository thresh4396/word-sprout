"""
「词芽」翻牌卡片组件
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PySide6.QtGui import QPainter, QColor, QFont

from config import T, QUALITY_LABELS


class FlashCardWidget(QWidget):
    """翻转卡片 — 正面英文，背面中文+例句"""

    rated = Signal(int)  # 评分信号 (0-5)

    def __init__(self, phrase_data, parent=None):
        super().__init__(parent)
        self.data = phrase_data
        self._flipped = False
        self._angle = 0  # 0=正面, 180=背面
        self.setMinimumHeight(420)
        self.setCursor(Qt.PointingHandCursor)

        self._build()

    def _build(self):
        if self.layout():
            from widgets.base import _clear_layout
            _clear_layout(self.layout())
        else:
            lo = QVBoxLayout(self)
            lo.setContentsMargins(0, 0, 0, 0)
            lo.setSpacing(0)

        # 卡片容器
        self.card = QWidget()
        self.card.setStyleSheet(f"""
            QWidget {{
                background: {T.CARD};
                border: 2px solid {T.DIVIDER};
                border-radius: {T.RADIUS_LG}px;
            }}
        """)
        card_lo = QVBoxLayout(self.card)
        card_lo.setContentsMargins(40, 40, 40, 40)
        card_lo.setSpacing(20)
        card_lo.setAlignment(Qt.AlignCenter)

        # 正面/背面 QStackedWidget
        from PySide6.QtWidgets import QStackedWidget
        self.stack = QStackedWidget()

        # === 正面 ===
        front = QWidget()
        f_lo = QVBoxLayout(front)
        f_lo.setContentsMargins(0, 0, 0, 0)
        f_lo.setSpacing(12)
        f_lo.setAlignment(Qt.AlignCenter)

        hint = QLabel("点击翻转查看释义")
        hint.setStyleSheet(f"font-size: {T.CAPTION}px; color: {T.TEXT_MUTED}; background: transparent; border: none;")
        hint.setAlignment(Qt.AlignCenter)
        f_lo.addWidget(hint)

        f_lo.addStretch()

        phrase_lbl = QLabel(self.data["phrase"])
        phrase_lbl.setStyleSheet(f"""
            font-family: "{T.FONT_DISPLAY}";
            font-size: 36px; font-weight: 700;
            color: {T.TEXT};
            background: transparent; border: none;
        """)
        phrase_lbl.setAlignment(Qt.AlignCenter)
        phrase_lbl.setWordWrap(True)
        f_lo.addWidget(phrase_lbl)

        f_lo.addStretch()

        if self.data.get("tags"):
            tags_lbl = QLabel(" · ".join(self.data["tags"][:3]))
            tags_lbl.setStyleSheet(f"font-size: {T.SMALL}px; color: {T.TEXT_MUTED}; background: transparent; border: none;")
            tags_lbl.setAlignment(Qt.AlignCenter)
            f_lo.addWidget(tags_lbl)

        self.stack.addWidget(front)

        # === 背面 ===
        back = QWidget()
        b_lo = QVBoxLayout(back)
        b_lo.setContentsMargins(0, 0, 0, 0)
        b_lo.setSpacing(16)
        b_lo.setAlignment(Qt.AlignCenter)

        b_lo.addStretch()

        meaning_lbl = QLabel(self.data["meaning"])
        meaning_lbl.setStyleSheet(f"""
            font-family: "{T.FONT_DISPLAY}";
            font-size: 34px; font-weight: 700;
            color: {T.GOLD};
            background: transparent; border: none;
        """)
        meaning_lbl.setAlignment(Qt.AlignCenter)
        meaning_lbl.setWordWrap(True)
        b_lo.addWidget(meaning_lbl)

        if self.data.get("example"):
            ex_lbl = QLabel(f"📝 {self.data['example']}")
            ex_lbl.setStyleSheet(f"""
                font-size: {T.BODY}px; color: {T.TEXT_DIM};
                font-style: italic;
                background: transparent; border: none;
            """)
            ex_lbl.setAlignment(Qt.AlignCenter)
            ex_lbl.setWordWrap(True)
            ex_lbl.setMaximumWidth(500)
            b_lo.addWidget(ex_lbl)

        b_lo.addStretch()

        self.stack.addWidget(back)
        card_lo.addWidget(self.stack)

        # === 评分按钮（只在背面显示） ===
        self.rating_row = QWidget()
        r_lo = QHBoxLayout(self.rating_row)
        r_lo.setSpacing(10)
        r_lo.setAlignment(Qt.AlignCenter)

        for q in [0, 2, 4, 5]:
            label, desc = QUALITY_LABELS[q]
            btn = QPushButton(f"{label}")
            btn.setToolTip(desc)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumWidth(90)
            btn.setMinimumHeight(44)
            # 颜色从红到绿
            colors = {0: T.CORAL, 2: "#e6a23c", 4: T.SAGE, 5: T.GOLD}
            c = colors[q]
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba({QColor(c).red()},{QColor(c).green()},{QColor(c).blue()},0.15);
                    color: {c};
                    border: 1px solid rgba({QColor(c).red()},{QColor(c).green()},{QColor(c).blue()},0.4);
                    border-radius: 22px;
                    font-size: {T.BODY}px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: rgba({QColor(c).red()},{QColor(c).green()},{QColor(c).blue()},0.30);
                }}
            """)
            btn.clicked.connect(lambda checked, v=q: self.rated.emit(v))
            r_lo.addWidget(btn)

        card_lo.addWidget(self.rating_row)
        self.rating_row.hide()

        self.layout().addWidget(self.card)

    def flip(self):
        """翻牌动画"""
        self._flipped = not self._flipped
        if self._flipped:
            self.stack.setCurrentIndex(1)
            self.rating_row.show()
        else:
            self.stack.setCurrentIndex(0)
            self.rating_row.hide()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self._flipped:
            self.flip()
        super().mousePressEvent(e)
