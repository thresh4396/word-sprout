"""
「词芽」选择题面板
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor

from config import T, QUALITY_LABELS
from review_engine import generate_quiz_options


class QuizPanelWidget(QWidget):
    """四选一选择题"""

    answered = Signal(bool, int)  # (是否正确, 选项索引)

    def __init__(self, phrase_data, all_phrases, parent=None):
        super().__init__(parent)
        self.data = phrase_data
        self._options, self._correct_idx = generate_quiz_options(phrase_data, all_phrases)
        self._answered = False
        self.setMinimumHeight(380)

        self._build()

    def _build(self):
        if self.layout():
            from widgets.base import _clear_layout
            _clear_layout(self.layout())
        else:
            lo = QVBoxLayout(self)
            lo.setContentsMargins(0, 0, 0, 0)
            lo.setSpacing(24)
            lo.setAlignment(Qt.AlignCenter)

        # 题干
        lo.addStretch()

        q_lbl = QLabel(f"「{self.data['phrase']}」的中文意思是？")
        q_lbl.setStyleSheet(f"""
            font-family: "{T.FONT_DISPLAY}"; font-size: 28px; font-weight: 700;
            color: {T.TEXT}; background: transparent; border: none;
        """)
        q_lbl.setAlignment(Qt.AlignCenter)
        q_lbl.setWordWrap(True)
        lo.addWidget(q_lbl)

        lo.addSpacing(8)

        # 选项按钮
        self.option_btns = []
        labels = ["A", "B", "C", "D"]

        for i, (label, option) in enumerate(zip(labels, self._options)):
            btn = QPushButton(f"  {label}.  {option}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(56)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {T.CARD};
                    color: {T.TEXT};
                    border: 2px solid {T.DIVIDER};
                    border-radius: {T.RADIUS}px;
                    text-align: left;
                    padding: 14px 24px;
                    font-size: {T.H3}px;
                }}
                QPushButton:hover {{
                    border-color: {T.GOLD};
                    background: {T.ELEVATED};
                }}
                QPushButton:disabled {{
                    opacity: 0.7;
                }}
            """)
            btn.clicked.connect(lambda checked, idx=i: self._on_answer(idx))
            self.option_btns.append(btn)
            lo.addWidget(btn)

        lo.addStretch()

        # 反馈标签
        self.feedback_lbl = QLabel("")
        self.feedback_lbl.setAlignment(Qt.AlignCenter)
        self.feedback_lbl.setStyleSheet(f"font-size: {T.H3}px; font-weight: 700; background: transparent; border: none;")
        self.feedback_lbl.hide()
        lo.addWidget(self.feedback_lbl)

    def _on_answer(self, idx):
        if self._answered:
            return
        self._answered = True
        correct = (idx == self._correct_idx)

        # 高亮正确答案
        for i, btn in enumerate(self.option_btns):
            btn.setEnabled(False)
            if i == self._correct_idx:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {T.CORRECT_BG};
                        color: {T.CORRECT_TEXT};
                        border: 2px solid {T.GOLD};
                        border-radius: {T.RADIUS}px;
                        text-align: left;
                        padding: 14px 24px;
                        font-size: {T.H3}px;
                    }}
                """)
            elif i == idx and not correct:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {T.WRONG_BG};
                        color: {T.WRONG_TEXT};
                        border: 2px solid {T.CORAL};
                        border-radius: {T.RADIUS}px;
                        text-align: left;
                        padding: 14px 24px;
                        font-size: {T.H3}px;
                    }}
                """)

        # 反馈
        if correct:
            self.feedback_lbl.setText("✓ 正确！")
            self.feedback_lbl.setStyleSheet(f"font-size: {T.H3}px; font-weight: 700; color: {T.GOLD}; background: transparent; border: none;")
        else:
            self.feedback_lbl.setText(f"✗ 正确答案：{self._options[self._correct_idx]}")
            self.feedback_lbl.setStyleSheet(f"font-size: {T.H3}px; font-weight: 700; color: {T.CORAL}; background: transparent; border: none;")
        self.feedback_lbl.show()

        # ── 质量评级按钮 ──
        rating_row = QWidget()
        r_lo = QHBoxLayout(rating_row)
        r_lo.setSpacing(10)
        r_lo.setAlignment(Qt.AlignCenter)

        hint = QLabel("你的记忆程度？")
        hint.setStyleSheet(f"font-size: {T.CAPTION}px; color: {T.TEXT_MUTED}; background: transparent; border: none;")
        r_lo.addWidget(hint)

        color_map = {0: T.CORAL, 2: "#e6a23c", 4: T.SAGE, 5: T.GOLD}
        for q in [0, 2, 4, 5]:
            label, desc = QUALITY_LABELS[q]
            btn = QPushButton(label)
            btn.setToolTip(desc)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumWidth(80)
            btn.setMinimumHeight(40)
            c = color_map[q]
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba({QColor(c).red()},{QColor(c).green()},{QColor(c).blue()},0.15);
                    color: {c};
                    border: 1px solid rgba({QColor(c).red()},{QColor(c).green()},{QColor(c).blue()},0.4);
                    border-radius: 20px;
                    font-size: {T.CAPTION}px; font-weight: 600;
                }}
                QPushButton:hover {{
                    background: rgba({QColor(c).red()},{QColor(c).green()},{QColor(c).blue()},0.30);
                }}
            """)
            btn.clicked.connect(lambda checked, v=q: self._emit_answer(correct, v))
            r_lo.addWidget(btn)

        self.layout().addWidget(rating_row)
        self._rating_row = rating_row

    def _emit_answer(self, correct, quality):
        if hasattr(self, '_rating_row'):
            self._rating_row.hide()
        self.answered.emit(correct, quality)
