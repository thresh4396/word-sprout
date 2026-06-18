"""
「词芽」复习页面
卡片翻面 + 选择题 双模式
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QProgressBar,
)
from PySide6.QtCore import Qt, QTimer

from config import T, text_on_accent
from widgets.base import GoldBtn, GhostBtn, _clear_layout
from widgets.flashcard import FlashCardWidget
from widgets.quiz_panel import QuizPanelWidget
from data_manager import get_phrases, update_phrase, record_review, record_review_session
from review_engine import calculate_next_review, get_due_phrases


class ReviewPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self._mode = "flashcard"  # flashcard | quiz
        self._queue = []
        self._current_idx = 0
        self._session_correct = 0
        self._session_total = 0
        self._session_quality = []

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(T.PAGE_MARGIN, 24, T.PAGE_MARGIN, 24)
        self.layout.setSpacing(T.PAGE_SPACING)
        self.build()

    def build(self):
        _clear_layout(self.layout)

        title = QLabel("复习")
        title.setStyleSheet(f"""
            font-family: "{T.FONT_DISPLAY}"; font-size: {T.H1}px;
            font-weight: 700; color: {T.TEXT}; background: transparent; border: none;
        """)
        self.layout.addWidget(title)

        # 模式切换
        mode_row = QHBoxLayout()
        mode_row.setSpacing(12)

        self.flashcard_btn = QPushButton("📇 卡片翻面")
        self.flashcard_btn.setCheckable(True)
        self.flashcard_btn.setChecked(True)
        self.flashcard_btn.setCursor(Qt.PointingHandCursor)
        self.flashcard_btn.setMinimumHeight(44)
        self.flashcard_btn.clicked.connect(lambda: self._switch_mode("flashcard"))

        self.quiz_btn = QPushButton("📝 选择题")
        self.quiz_btn.setCheckable(True)
        self.quiz_btn.setCursor(Qt.PointingHandCursor)
        self.quiz_btn.setMinimumHeight(44)
        self.quiz_btn.clicked.connect(lambda: self._switch_mode("quiz"))

        self._update_mode_btns()

        mode_row.addWidget(self.flashcard_btn)
        mode_row.addWidget(self.quiz_btn)
        mode_row.addStretch()

        # 批次信息
        self.batch_label = QLabel("")
        self.batch_label.setStyleSheet(f"font-size: {T.BODY}px; color: {T.TEXT_DIM}; background: transparent; border: none;")
        mode_row.addWidget(self.batch_label)

        self.layout.addLayout(mode_row)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background: {T.DIVIDER};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {T.GOLD};
                border-radius: 3px;
            }}
        """)
        self.layout.addWidget(self.progress)

        # 内容区（用 QStackedWidget 切换 flashcard / quiz，或显示空状态）
        self.content_stack = QStackedWidget()
        self.layout.addWidget(self.content_stack, 1)

        # 空状态
        empty = QWidget()
        e_lo = QVBoxLayout(empty)
        e_lo.setAlignment(Qt.AlignCenter)
        e_lbl = QLabel("准备开始复习")
        e_lbl.setStyleSheet(f"font-size: {T.H2}px; color: {T.TEXT_MUTED}; background: transparent; border: none;")
        e_lbl.setAlignment(Qt.AlignCenter)
        e_lo.addWidget(e_lbl)
        self.content_stack.addWidget(empty)

        # 占位（flashcard）
        self.fc_placeholder = QWidget()
        self.content_stack.addWidget(self.fc_placeholder)

        # 占位（quiz）
        self.qz_placeholder = QWidget()
        self.content_stack.addWidget(self.qz_placeholder)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.start_btn = GoldBtn("开始复习")
        self.start_btn.clicked.connect(self._start_review)
        btn_row.addWidget(self.start_btn)

        self.layout.addLayout(btn_row)
        self.layout.addStretch()

    def _update_mode_btns(self):
        active_style = f"""
            QPushButton {{
                background: {T.GOLD}; color: {text_on_accent()}; border: none;
                border-radius: 22px; padding: 10px 24px;
                font-size: {T.BODY}px; font-weight: 700;
            }}
        """
        inactive_style = f"""
            QPushButton {{
                background: {T.ELEVATED}; color: {T.TEXT_DIM};
                border: 1px solid {T.DIVIDER}; border-radius: 22px;
                padding: 10px 24px; font-size: {T.BODY}px; font-weight: 500;
            }}
            QPushButton:hover {{
                border-color: {T.GOLD};
            }}
        """
        self.flashcard_btn.setStyleSheet(active_style if self._mode == "flashcard" else inactive_style)
        self.quiz_btn.setStyleSheet(active_style if self._mode == "quiz" else inactive_style)

    def _switch_mode(self, mode):
        self._mode = mode
        self.flashcard_btn.setChecked(mode == "flashcard")
        self.quiz_btn.setChecked(mode == "quiz")
        self._update_mode_btns()
        # 如果正在复习中，重新开始
        if self._queue:
            self._start_review()

    def _start_review(self):
        phrases = get_phrases()
        due = get_due_phrases(phrases)
        if not due:
            self.mw.toast("今日没有需要复习的词组，去录入新词吧 ✨")
            return

        self._queue = due
        self._current_idx = 0
        self._session_correct = 0
        self._session_total = 0
        self._session_quality = []
        self._show_current()

    def _show_current(self):
        if self._current_idx >= len(self._queue):
            self._finish_session()
            return

        p = self._queue[self._current_idx]
        self.batch_label.setText(f"{self._current_idx + 1} / {len(self._queue)}")
        self.progress.setMaximum(len(self._queue))
        self.progress.setValue(self._current_idx)

        all_phrases = get_phrases()

        if self._mode == "flashcard":
            # 清除旧内容
            from widgets.base import _clear_layout
            _clear_layout(self.fc_placeholder.layout() if self.fc_placeholder.layout() else QVBoxLayout(self.fc_placeholder))

            fc_lo = QVBoxLayout(self.fc_placeholder) if self.fc_placeholder.layout() is None else self.fc_placeholder.layout()
            self.fc_widget = FlashCardWidget(p)
            self.fc_widget.rated.connect(self._on_rated)
            fc_lo.addWidget(self.fc_widget)

            self.content_stack.setCurrentWidget(self.fc_placeholder)
        else:
            from widgets.base import _clear_layout
            _clear_layout(self.qz_placeholder.layout() if self.qz_placeholder.layout() else QVBoxLayout(self.qz_placeholder))

            qz_lo = QVBoxLayout(self.qz_placeholder) if self.qz_placeholder.layout() is None else self.qz_placeholder.layout()
            self.qz_widget = QuizPanelWidget(p, all_phrases)
            self.qz_widget.answered.connect(self._on_quiz_answered)
            qz_lo.addWidget(self.qz_widget)

            self.content_stack.setCurrentWidget(self.qz_placeholder)

    def _on_rated(self, quality):
        p = self._queue[self._current_idx]
        p = calculate_next_review(p, quality)
        update_phrase(p["id"], p)
        record_review(p["id"], quality)

        self._session_total += 1
        if quality >= 3:
            self._session_correct += 1
        self._session_quality.append(quality)

        self._current_idx += 1
        QTimer.singleShot(400, self._show_current)

    def _on_quiz_answered(self, correct, quality):
        p = self._queue[self._current_idx]
        p = calculate_next_review(p, quality)
        update_phrase(p["id"], p)
        record_review(p["id"], quality)

        self._session_total += 1
        if correct:
            self._session_correct += 1
        self._session_quality.append(quality)

        self._current_idx += 1
        QTimer.singleShot(1200, self._show_current)

    def _finish_session(self):
        record_review_session(self._mode, self._session_total, self._session_correct)

        # 显示完成摘要
        from widgets.base import _clear_layout
        # 清除内容区
        for i in range(1, 3):
            w = self.content_stack.widget(i)
            if w and w.layout():
                _clear_layout(w.layout())

        summary = QWidget()
        s_lo = QVBoxLayout(summary)
        s_lo.setAlignment(Qt.AlignCenter)

        s_lo.addStretch()

        icon = QLabel("🎉")
        icon.setStyleSheet("font-size: 60px; background: transparent; border: none;")
        icon.setAlignment(Qt.AlignCenter)
        s_lo.addWidget(icon)

        title = QLabel("复习完成！")
        title.setStyleSheet(f"""
            font-family: "{T.FONT_DISPLAY}"; font-size: {T.H1}px; font-weight: 700;
            color: {T.TEXT}; background: transparent; border: none;
        """)
        title.setAlignment(Qt.AlignCenter)
        s_lo.addWidget(title)

        score = QLabel(f"正确 {self._session_correct} / {self._session_total}")
        score.setStyleSheet(f"font-size: {T.H2}px; color: {T.GOLD}; font-weight: 700; background: transparent; border: none;")
        score.setAlignment(Qt.AlignCenter)
        s_lo.addWidget(score)

        s_lo.addStretch()

        again_btn = GoldBtn("再来一组")
        again_btn.clicked.connect(self._start_review)
        s_lo.addWidget(again_btn, alignment=Qt.AlignCenter)

        s_lo.addStretch()

        self.content_stack.addWidget(summary)
        self.content_stack.setCurrentWidget(summary)

        self.batch_label.setText("")
        self.progress.setValue(0)

        self.mw.toast(f"复习完成！正确率 {int(self._session_correct/self._session_total*100)}%")
