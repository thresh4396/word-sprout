"""
「词芽」快速收录生词弹窗
从沉浸式学习中选中文本 → 右键收录 → 自动翻译 → 一键保存
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer

from config import T
from widgets.base import GhostBtn, GoldBtn
from data_manager import add_phrase, find_duplicate_phrase, get_settings


# ------------------------------------------------------------
# 小型翻译线程（避免循环导入 dialogue_page.TranslateWorker）
# ------------------------------------------------------------

class _QuickTranslateWorker(QThread):
    finished = Signal(str)

    def __init__(self, text, provider, api_key, base_url, model):
        super().__init__()
        self._text = text
        self._provider = provider
        self._api_key = api_key
        self._base_url = base_url
        self._model = model

    def run(self):
        from api_client import translate_text
        try:
            result = translate_text(
                self._text, self._provider, self._api_key,
                self._base_url, self._model,
            )
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(f"Error: {str(e)}")


# ------------------------------------------------------------
# 快速收录弹窗
# ------------------------------------------------------------

class QuickAddDialog(QDialog):
    """轻量收录弹窗 — 词组 + 自动翻译 + 保存"""

    def __init__(self, phrase_text="", parent=None):
        super().__init__(parent)
        self._phrase_text = phrase_text.strip()
        self._worker = None
        self._translated = False
        self._build()

    def _build(self):
        self.setWindowTitle("快速收录生词")
        self.setMinimumWidth(420)
        self.setMaximumWidth(480)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setStyleSheet(f"background:{T.BG};")

        lo = QVBoxLayout(self)
        lo.setContentsMargins(28, 24, 28, 24)
        lo.setSpacing(14)

        # ── 标题 ──
        title = QLabel("📌 快速收录生词")
        title.setStyleSheet(f"font-size:{T.H3}px; font-weight:700; color:{T.TEXT}; background:transparent;")
        lo.addWidget(title)

        # ── 词组 ──
        ph_label = QLabel("词组")
        ph_label.setStyleSheet(f"font-size:{T.CAPTION}px; color:{T.TEXT_MUTED}; background:transparent;")
        lo.addWidget(ph_label)

        self.phrase_input = QLineEdit(self._phrase_text)
        self.phrase_input.setPlaceholderText("输入英文单词或词组...")
        self.phrase_input.setMinimumHeight(44)
        self.phrase_input.setStyleSheet(f"""
            font-family:"{T.FONT_EN}", "{T.FONT_BODY}";
            font-size:{T.BODY}px;
            font-weight:600;
        """)
        self.phrase_input.textChanged.connect(self._on_phrase_changed)
        lo.addWidget(self.phrase_input)

        # ── 释义 + 翻译按钮 ──
        meaning_header = QHBoxLayout()
        ml = QLabel("释义")
        ml.setStyleSheet(f"font-size:{T.CAPTION}px; color:{T.TEXT_MUTED}; background:transparent;")
        meaning_header.addWidget(ml)
        meaning_header.addStretch()

        self.translate_btn = QPushButton("🌐 翻译")
        self.translate_btn.setCursor(Qt.PointingHandCursor)
        self.translate_btn.setMinimumHeight(32)
        self.translate_btn.setStyleSheet(f"""
            QPushButton {{
                background:{T.ELEVATED}; color:{T.TEXT_DIM};
                border:1px solid {T.DIVIDER}; border-radius:{T.RADIUS_SM}px;
                padding:4px 14px; font-size:{T.CAPTION}px;
            }}
            QPushButton:hover {{ border-color:{T.GOLD}; color:{T.GOLD}; }}
            QPushButton:disabled {{ color:{T.TEXT_MUTED}; }}
        """)
        self.translate_btn.clicked.connect(self._do_translate)
        meaning_header.addWidget(self.translate_btn)
        lo.addLayout(meaning_header)

        self.meaning_input = QLineEdit()
        self.meaning_input.setPlaceholderText("自动翻译或手动输入释义...")
        self.meaning_input.setMinimumHeight(44)
        lo.addWidget(self.meaning_input)

        # ── 重复警告 ──
        self.dup_warning = QLabel("")
        self.dup_warning.setWordWrap(True)
        self.dup_warning.setStyleSheet(
            f"font-size:{T.SMALL}px; color:{T.CORAL}; background:transparent; padding:4px 0;"
        )
        self.dup_warning.hide()
        lo.addWidget(self.dup_warning)

        # ── 按钮 ──
        lo.addSpacing(4)
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel = GhostBtn("取消")
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)

        self.save_btn = GoldBtn("💾 保存")
        self.save_btn.clicked.connect(self._save)
        self.save_btn.setEnabled(False)
        btn_row.addWidget(self.save_btn)
        lo.addLayout(btn_row)

        # ── 打开后自动翻译 ──
        if self._phrase_text:
            self._check_duplicate()
            QTimer.singleShot(200, self._do_translate)  # 延迟等 UI 渲染完成
        # 连接保存按钮可用状态
        self.meaning_input.textChanged.connect(self._update_save_btn)
        self._update_save_btn()

    # ============================================================
    # 逻辑
    # ============================================================

    def _on_phrase_changed(self):
        """词组修改后重新检测重复"""
        self._dup_checked = False
        self.dup_warning.hide()

    def _check_duplicate(self):
        text = self.phrase_input.text().strip()
        if not text:
            return
        existing = find_duplicate_phrase(text)
        if existing:
            self.dup_warning.setText(
                f"⚠ 词库中已存在 「{text}」 → 释义：{existing.get('meaning', '')}，仍可保存为独立条目"
            )
            self.dup_warning.show()

    def _update_save_btn(self):
        """释义非空才能保存"""
        self.save_btn.setEnabled(bool(self.meaning_input.text().strip()))

    def _do_translate(self):
        """触发自动翻译"""
        text = self.phrase_input.text().strip()
        if not text:
            return

        settings = get_settings()
        api_key = settings.get("api_key", "").strip()
        if not api_key:
            self.meaning_input.setPlaceholderText("请先在设置中填入 API Key，或手动输入释义")
            return

        # 加载状态
        self.translate_btn.setText("⏳ 翻译中...")
        self.translate_btn.setEnabled(False)
        self.meaning_input.setPlaceholderText("正在翻译...")

        provider = settings.get("api_provider", "deepseek")
        base_url = settings.get("api_base_url", "")
        model = settings.get("api_model", "")

        self._worker = _QuickTranslateWorker(text, provider, api_key, base_url, model)
        self._worker.finished.connect(self._on_translation_ready)
        self._worker.start()

    def _on_translation_ready(self, result):
        """翻译完成"""
        self.translate_btn.setText("🌐 翻译")
        self.translate_btn.setEnabled(True)

        if result.startswith("Error:"):
            self.meaning_input.setPlaceholderText("翻译失败，请手动输入释义")
            return

        self.meaning_input.setText(result.strip())
        self._translated = True

    def _save(self):
        """保存词组到词库"""
        phrase = self.phrase_input.text().strip()
        meaning = self.meaning_input.text().strip()

        if not phrase or not meaning:
            return

        self._check_duplicate()
        add_phrase(phrase, meaning)
        self.accept()
