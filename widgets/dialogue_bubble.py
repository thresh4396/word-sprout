"""
「词芽」对话气泡组件
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from config import T


class DialogueBubble(QWidget):
    """单条对话气泡"""

    def __init__(self, speaker, text, idx, parent=None):
        super().__init__(parent)
        self._speaker = speaker  # "A" or "B"
        self._text = text
        self._idx = idx
        self._is_left = (speaker == "A")
        self._build()

    def _build(self):
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 4, 0, 4)
        lo.setSpacing(0)

        bubble = QLabel(self._text)
        bubble.setWordWrap(True)
        bubble.setMaximumWidth(520)
        bubble.setTextFormat(Qt.RichText)

        if self._is_left:
            # A 左对齐
            bubble.setStyleSheet(f"""
                QLabel {{
                    background: {T.ELEVATED};
                    color: {T.TEXT};
                    border: none;
                    border-radius: 18px;
                    padding: 14px 20px;
                    font-size: {T.BODY}px;
                    line-height: 1.6;
                }}
            """)
            lo.addWidget(bubble)
            lo.addStretch()
        else:
            # B 右对齐
            bubble.setStyleSheet(f"""
                QLabel {{
                    background: {T.GOLD};
                    color: #fff;
                    border: none;
                    border-radius: 18px;
                    padding: 14px 20px;
                    font-size: {T.BODY}px;
                    line-height: 1.6;
                }}
            """)
            lo.addStretch()
            lo.addWidget(bubble)

    def get_raw_text(self):
        """返回去掉 HTML 标签的纯文本"""
        import re
        return re.sub(r'<[^>]+>', '', self._text)


class FillBlankBubble(QWidget):
    """填空模式气泡 — 目标词组被挖空"""

    answer_submitted = Signal(bool)  # 是否正确

    def __init__(self, speaker, full_text, answer, is_left, parent=None):
        super().__init__(parent)
        self._speaker = speaker
        self._answer = answer
        self._is_left = is_left
        self._full_text = full_text
        self._build()

    def _build(self):
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 4, 0, 4)
        lo.setSpacing(0)

        bubble = QWidget()
        b_lo = QVBoxLayout(bubble)
        b_lo.setContentsMargins(18, 14, 18, 14)
        b_lo.setSpacing(8)

        # 上下文文字（用下划线替代目标词）
        context_text = self._full_text.replace(self._answer, "______")
        ctx_lbl = QLabel(context_text)
        ctx_lbl.setWordWrap(True)
        ctx_lbl.setMaximumWidth(480)
        ctx_lbl.setStyleSheet(f"font-size: {T.BODY}px; color: {T.TEXT}; background: transparent; border: none;")
        b_lo.addWidget(ctx_lbl)

        # 输入框 + 提交
        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("输入缺失的词组...")
        self.input.setMinimumHeight(38)
        self.input.returnPressed.connect(self._check)
        input_row.addWidget(self.input, 1)

        from PySide6.QtWidgets import QPushButton
        check_btn = QPushButton("✓")
        check_btn.setFixedSize(38, 38)
        check_btn.setCursor(Qt.PointingHandCursor)
        check_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T.GOLD}; color: #fff; border: none;
                border-radius: 19px; font-size: 16px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {T.GOLD_DIM}; }}
        """)
        check_btn.clicked.connect(self._check)
        input_row.addWidget(check_btn)

        b_lo.addLayout(input_row)

        # 反馈标签（初始隐藏）
        self.feedback = QLabel("")
        self.feedback.setStyleSheet(f"font-size: {T.CAPTION}px; font-weight: 600; background: transparent; border: none;")
        self.feedback.hide()
        b_lo.addWidget(self.feedback)

        if self._is_left:
            bubble.setStyleSheet(f"""
                background: {T.ELEVATED}; border: none; border-radius: 18px;
            """)
            lo.addWidget(bubble)
            lo.addStretch()
        else:
            bubble.setStyleSheet(f"""
                background: rgba({QColor(T.GOLD).red()},{QColor(T.GOLD).green()},{QColor(T.GOLD).blue()},0.12);
                border: 1px solid rgba({QColor(T.GOLD).red()},{QColor(T.GOLD).green()},{QColor(T.GOLD).blue()},0.3);
                border-radius: 18px;
            """)
            lo.addStretch()
            lo.addWidget(bubble)

    def _check(self):
        user_answer = self.input.text().strip().lower()
        correct = self._answer.lower()
        is_correct = (user_answer == correct)

        if is_correct:
            self.feedback.setText("✓ 正确！")
            self.feedback.setStyleSheet(f"font-size: {T.CAPTION}px; font-weight: 600; color: {T.GOLD}; background: transparent; border: none;")
            self.input.setEnabled(False)
        else:
            self.feedback.setText(f"✗ 正确答案：{self._answer}")
            self.feedback.setStyleSheet(f"font-size: {T.CAPTION}px; font-weight: 600; color: {T.CORAL}; background: transparent; border: none;")

        self.feedback.show()
        self.answer_submitted.emit(is_correct)


class ComprehensionQuestion(QWidget):
    """阅读理解选择题 — 考试风格"""

    answered = Signal(bool)

    # 题型中文标签
    TYPE_LABELS = {
        "main_idea": "📌 主旨大意题",
        "detail": "🔍 细节理解题",
        "inference": "💡 推理判断题",
        "vocabulary": "📖 词义猜测题",
        "attitude": "🎯 观点态度题",
    }

    def __init__(self, q_data, parent=None):
        super().__init__(parent)
        self._data = q_data
        self._answered = False
        self._build()

    def _build(self):
        lo = QVBoxLayout(self)
        lo.setSpacing(10)

        # 题型标签
        q_type = self._data.get("type", "")
        type_label_text = self.TYPE_LABELS.get(q_type, "📝 阅读理解")
        self.type_lbl = QLabel(type_label_text)
        self.type_lbl.setStyleSheet(f"""
            font-size: {T.CAPTION}px; font-weight: 600;
            color: {T.GOLD}; background: transparent; border: none;
            padding: 2px 0;
        """)
        lo.addWidget(self.type_lbl)

        # 题号 + 题干
        q_lbl = QLabel(self._data["question"])
        q_lbl.setWordWrap(True)
        q_lbl.setStyleSheet(f"font-size: {T.H3}px; font-weight: 600; color: {T.TEXT}; background: transparent; border: none;")
        lo.addWidget(q_lbl)

        labels = ["A", "B", "C", "D"]
        self.btns = []

        from PySide6.QtWidgets import QPushButton
        for i, opt in enumerate(self._data["options"]):
            btn = QPushButton(f"  {labels[i]}.  {opt}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(42)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {T.CARD};
                    color: {T.TEXT};
                    border: 1px solid {T.DIVIDER};
                    border-radius: {T.RADIUS_SM}px;
                    text-align: left;
                    padding: 10px 16px;
                    font-size: {T.BODY}px;
                }}
                QPushButton:hover {{ border-color: {T.GOLD}; background: {T.ELEVATED}; }}
                QPushButton:disabled {{ opacity: 0.7; }}
            """)
            btn.clicked.connect(lambda checked, idx=i: self._on_answer(idx))
            self.btns.append(btn)
            lo.addWidget(btn)

        self.feedback = QLabel("")
        self.feedback.setStyleSheet(f"font-size: {T.CAPTION}px; font-weight: 600; background: transparent; border: none;")
        self.feedback.hide()
        lo.addWidget(self.feedback)

    def _on_answer(self, idx):
        if self._answered:
            return
        self._answered = True
        correct = (idx == self._data["answer"])

        for i, btn in enumerate(self.btns):
            btn.setEnabled(False)
            if i == self._data["answer"]:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {T.CORRECT_BG}; color: {T.CORRECT_TEXT};
                        border: 2px solid {T.GOLD}; border-radius: {T.RADIUS_SM}px;
                        text-align: left; padding: 10px 16px; font-size: {T.BODY}px;
                    }}
                """)
            elif i == idx:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {T.WRONG_BG}; color: {T.WRONG_TEXT};
                        border: 2px solid {T.CORAL}; border-radius: {T.RADIUS_SM}px;
                        text-align: left; padding: 10px 16px; font-size: {T.BODY}px;
                    }}
                """)

        self.feedback.setText("✓ 正确！" if correct else "✗ 不正确")
        self.feedback.setStyleSheet(
            f"font-size: {T.CAPTION}px; font-weight: 600; color: {T.GOLD if correct else T.CORAL}; background: transparent; border: none;"
        )
        self.feedback.show()
        self.answered.emit(correct)
