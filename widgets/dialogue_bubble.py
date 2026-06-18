"""
「词芽」对话气泡组件
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from config import T, text_on_accent


class DialogueBubble(QWidget):
    """单条对话气泡，自适应宽度"""

    def __init__(self, speaker, text, idx, parent=None, max_width=520,
                 font_scale=1.0, font_en=None):
        super().__init__(parent)
        self._speaker = speaker
        self._text = text
        self._idx = idx
        self._is_left = (speaker == "🧑")
        self._max_w = max_width
        self._fs = font_scale
        self._font_en = font_en or T.FONT_EN
        self._build()

    def _build(self):
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 4, 0, 4)
        lo.setSpacing(0)

        body = max(12, int(T.BODY * self._fs))

        # Qt QLabel 不支持 QSS line-height，改用 HTML inline style
        bubble = QLabel(f'<div style="line-height:1.7;">{self._text}</div>')
        self._bubble_label = bubble  # 暴露给 enable_text_selection
        bubble.setWordWrap(True)
        bubble.setMaximumWidth(int(self._max_w * 0.72))
        bubble.setTextFormat(Qt.RichText)

        speaker_lbl = QLabel(self._speaker)
        speaker_lbl.setFixedWidth(max(22, int(28 * self._fs)))
        speaker_lbl.setAlignment(Qt.AlignTop)
        speaker_lbl.setStyleSheet(f"font-family:\"{self._font_en}\", \"{T.FONT_BODY}\"; font-size:{max(14, int(18*self._fs))}px; background:transparent; border:none; padding-top:10px;")

        accent_text = text_on_accent()

        # 选中高亮色 — 独立蓝色，在任何主题背景下都清晰可见
        SEL_BG = "#4a9eff"
        SEL_FG = "#ffffff"

        if self._is_left:
            bubble.setStyleSheet(f"""
                QLabel {{
                    font-family:"{self._font_en}", "{T.FONT_BODY}";
                    background: {T.ELEVATED};
                    color: {T.TEXT};
                    border: none;
                    border-radius: 16px;
                    padding: 12px 18px;
                    font-size: {body}px;
                    selection-background-color: {SEL_BG};
                    selection-color: {SEL_FG};
                }}
            """)
            lo.addWidget(speaker_lbl)
            lo.addWidget(bubble)
            lo.addSpacing(60)
        else:
            bubble.setStyleSheet(f"""
                QLabel {{
                    font-family:"{self._font_en}", "{T.FONT_BODY}";
                    background: {T.GOLD};
                    color: {accent_text};
                    border: none;
                    border-radius: 16px;
                    padding: 12px 18px;
                    font-size: {body}px;
                    selection-background-color: {SEL_BG};
                    selection-color: {SEL_FG};
                }}
            """)
            lo.addSpacing(60)
            lo.addWidget(bubble)
            lo.addWidget(speaker_lbl)

    def get_raw_text(self):
        """返回去掉 HTML 标签的纯文本"""
        import re
        return re.sub(r'<[^>]+>', '', self._text)

    def enable_text_selection(self, context_menu_handler=None):
        """启用文本选择 + 可选右键菜单"""
        self._bubble_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        if context_menu_handler:
            self._bubble_label.setContextMenuPolicy(Qt.CustomContextMenu)
            self._bubble_label.customContextMenuRequested.connect(
                lambda pos: context_menu_handler(pos, self._bubble_label)
            )

    def selectedText(self):
        """返回当前选中的文本"""
        if hasattr(self, '_bubble_label') and self._bubble_label.hasSelectedText():
            return self._bubble_label.selectedText()
        return ""


class FillBlankBubble(QWidget):
    """填空模式气泡 — 目标词组被挖空"""

    answer_submitted = Signal(bool)  # 是否正确

    def __init__(self, speaker, full_text, answer, is_left, parent=None, max_w=520):
        super().__init__(parent)
        self._speaker = speaker
        self._answer = answer
        self._is_left = is_left
        self._full_text = full_text
        self._max_w = int(max_w * 0.72)
        self._font_en = T.FONT_EN
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
        ctx_lbl.setMaximumWidth(self._max_w)
        ctx_lbl.setStyleSheet(f"font-family:\"{self._font_en}\", \"{T.FONT_BODY}\"; font-size: {T.BODY}px; color: {T.TEXT}; background: transparent; border: none;")
        b_lo.addWidget(ctx_lbl)

        # 输入框 + 提交
        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("输入缺失的词组...")
        self.input.setMinimumHeight(38)
        self.input.setStyleSheet(f"font-family:\"{self._font_en}\", \"{T.FONT_BODY}\"; font-size: {T.BODY}px;")
        self.input.returnPressed.connect(self._check)
        input_row.addWidget(self.input, 1)

        from PySide6.QtWidgets import QPushButton
        check_btn = QPushButton("✓")
        check_btn.setFixedSize(38, 38)
        check_btn.setCursor(Qt.PointingHandCursor)
        check_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T.GOLD}; color: {text_on_accent()}; border: none;
                border-radius: 19px; font-size: 16px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {T.GOLD_DIM}; }}
        """)
        check_btn.clicked.connect(self._check)
        input_row.addWidget(check_btn)

        b_lo.addLayout(input_row)

        # 反馈标签（初始隐藏）
        self.feedback = QLabel("")
        self.feedback.setStyleSheet(f"font-family:\"{self._font_en}\", \"{T.FONT_BODY}\"; font-size: {T.CAPTION}px; font-weight: 600; background: transparent; border: none;")
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
            self.feedback.setStyleSheet(f"font-family:\"{self._font_en}\", \"{T.FONT_BODY}\"; font-size: {T.CAPTION}px; font-weight: 600; color: {T.GOLD}; background: transparent; border: none;")
            self.input.setEnabled(False)
        else:
            self.feedback.setText(f"✗ 正确答案：{self._answer}")
            self.feedback.setStyleSheet(f"font-family:\"{self._font_en}\", \"{T.FONT_BODY}\"; font-size: {T.CAPTION}px; font-weight: 600; color: {T.CORAL}; background: transparent; border: none;")

        self.feedback.show()
        self.answer_submitted.emit(is_correct)


class ComprehensionQuestion(QWidget):
    """阅读理解选择题 — 选中高亮，提交后批改 + 解析"""

    answered = Signal(bool)

    TYPE_LABELS = {
        "main_idea": "📌 主旨大意题",
        "detail": "🔍 细节理解题",
        "inference": "💡 推理判断题",
        "vocabulary": "📖 词义猜测题",
        "attitude": "🎯 观点态度题",
    }

    def __init__(self, q_data, parent=None, font_scale=1.0, font_en=None):
        super().__init__(parent)
        self._data = q_data
        self._submitted = False     # 是否已提交
        self._selected_idx = -1     # 用户选择的选项
        self._fs = font_scale
        self._font_en = font_en or T.FONT_EN
        self._build()

    def _build(self):
        lo = QVBoxLayout(self)
        lo.setSpacing(10)

        cap = max(11, int(T.CAPTION * self._fs))
        h3 = max(13, int(T.H3 * self._fs))
        body = max(12, int(T.BODY * self._fs))

        # 题型标签
        q_type = self._data.get("type", "")
        type_label_text = self.TYPE_LABELS.get(q_type, "📝 阅读理解")
        self.type_lbl = QLabel(type_label_text)
        self.type_lbl.setStyleSheet(f"""
            font-family:"{self._font_en}", "{T.FONT_BODY}";
            font-size: {cap}px; font-weight: 600;
            color: {T.GOLD}; background: transparent; border: none;
            padding: 2px 0;
        """)
        lo.addWidget(self.type_lbl)

        # 题干
        q_lbl = QLabel(self._data["question"])
        q_lbl.setWordWrap(True)
        q_lbl.setStyleSheet(f"font-family:\"{self._font_en}\", \"{T.FONT_BODY}\"; font-size: {h3}px; font-weight: 600; color: {T.TEXT}; background: transparent; border: none;")
        lo.addWidget(q_lbl)

        # 选项按钮
        labels = ["A", "B", "C", "D"]
        self.btns = []
        self._body_sz = body

        from PySide6.QtWidgets import QPushButton
        for i, opt in enumerate(self._data["options"]):
            btn = QPushButton(f"  {labels[i]}.  {opt}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(max(32, int(42 * self._fs)))
            btn.setStyleSheet(self._btn_style(i, "default"))
            btn.clicked.connect(lambda checked, idx=i: self._on_select(idx))
            self.btns.append(btn)
            lo.addWidget(btn)

        # 反馈区（初始隐藏）
        self.feedback = QLabel("")
        self.feedback.setWordWrap(True)
        self.feedback.setStyleSheet(f"font-family:\"{self._font_en}\", \"{T.FONT_BODY}\"; font-size: {cap}px; font-weight: 600; background: transparent; border: none;")
        self.feedback.hide()
        lo.addWidget(self.feedback)

    # ── 按钮样式 ──

    def _btn_style(self, i, state):
        """生成按钮 QSS：default | selected | correct | wrong"""
        body = self._body_sz
        base = f"""
            QPushButton {{
                font-family:"{self._font_en}", "{T.FONT_BODY}";
                text-align: left; padding: 10px 16px;
                font-size: {body}px;
            }}
            QPushButton:hover {{ border-color: {T.GOLD}; background: {T.ELEVATED}; }}
            QPushButton:disabled {{ opacity: 0.7; }}
        """
        if state == "selected":
            return base + f"""
                QPushButton {{ background: {T.CARD}; color: {T.TEXT};
                    border: 2px solid {T.GOLD}; border-radius: {T.RADIUS_SM}px; }}
            """
        elif state == "correct":
            return base + f"""
                QPushButton {{ background: {T.CORRECT_BG}; color: {T.CORRECT_TEXT};
                    border: 2px solid {T.GOLD}; border-radius: {T.RADIUS_SM}px; }}
            """
        elif state == "wrong":
            return base + f"""
                QPushButton {{ background: {T.WRONG_BG}; color: {T.WRONG_TEXT};
                    border: 2px solid {T.CORAL}; border-radius: {T.RADIUS_SM}px; }}
            """
        else:  # default
            return base + f"""
                QPushButton {{ background: {T.CARD}; color: {T.TEXT};
                    border: 1px solid {T.DIVIDER}; border-radius: {T.RADIUS_SM}px; }}
            """

    # ── 交互 ──

    def _on_select(self, idx):
        """选中一个选项，可切换"""
        if self._submitted:
            return
        # 清除旧选中
        for i, btn in enumerate(self.btns):
            btn.setStyleSheet(self._btn_style(i, "default"))
        # 高亮新选中
        self._selected_idx = idx
        self.btns[idx].setStyleSheet(self._btn_style(idx, "selected"))

    def get_selected(self):
        """返回用户选中的选项索引，未选返回 -1"""
        return self._selected_idx

    def is_correct(self):
        """用户是否答对"""
        return self._selected_idx == self._data["answer"]

    def reveal(self):
        """提交后显示正确答案 + 解析"""
        self._submitted = True
        correct_idx = self._data["answer"]
        body = self._body_sz

        for i, btn in enumerate(self.btns):
            btn.setEnabled(False)
            if i == correct_idx:
                btn.setStyleSheet(self._btn_style(i, "correct"))
            elif i == self._selected_idx and self._selected_idx != correct_idx:
                btn.setStyleSheet(self._btn_style(i, "wrong"))

        # 反馈文字
        if self.is_correct():
            icon = "✓ 正确！"
            color = T.GOLD
        else:
            icon = "✗ 错误"
            color = T.CORAL
        explanation = self._data.get("explanation", "")
        if explanation:
            self.feedback.setText(f"{icon}  {explanation}")
        else:
            self.feedback.setText(icon)
        self.feedback.setStyleSheet(
            f"font-family:\"{self._font_en}\", \"{T.FONT_BODY}\"; font-size: {max(11, int(T.CAPTION * self._fs))}px; "
            f"font-weight: 600; color: {color}; background: transparent; border: none;"
        )
        self.feedback.show()
        self.answered.emit(self.is_correct())
