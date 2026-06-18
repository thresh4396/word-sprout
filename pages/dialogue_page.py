"""
「词芽」对话练习页面
勾选词组 → AI 生成对话 → 三种练习模式（纯阅读/填空/阅读理解）
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QStackedWidget, QFrame,
    QComboBox, QMessageBox, QApplication, QDialog, QMenu,
    QSpinBox, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer, QPoint

from config import T, API_PRESETS, text_on_accent
from widgets.base import GoldBtn, GhostBtn, TagChip, Card, _clear_layout
from widgets.dialogue_bubble import DialogueBubble, FillBlankBubble, ComprehensionQuestion
from widgets.quick_add_dialog import QuickAddDialog, _QuickTranslateWorker
from data_manager import (
    get_phrases, get_settings, save_settings, save_dialogue,
    get_dialogues, delete_dialogue, update_dialogue,
)


# ============================================================
# 后台 API 调用线程
# ============================================================

class DialogueWorker(QThread):
    """后台线程调用 AI API"""
    finished = Signal(object)  # 成功: dict, 失败: str
    progress = Signal(str)

    def __init__(self, phrases, content_type, provider, api_key, base_url, model, word_count=None):
        super().__init__()
        self._phrases = phrases
        self._content_type = content_type
        self._provider = provider
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._word_count = word_count

    def run(self):
        from api_client import generate_content
        try:
            label = "对话" if self._content_type == "dialogue" else "文章"
            self.progress.emit(f"正在生成{label}...")
            result = generate_content(
                self._phrases, self._content_type,
                self._provider, self._api_key,
                self._base_url, self._model,
                word_count=self._word_count,
            )
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(str(e))


class TranslateWorker(QThread):
    """后台线程调用翻译 API"""
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


# ============================================================
# 对话页面
# ============================================================

class DialoguePage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self._selected_ids = set()
        self._current_dialogue = None  # 当前显示对话数据
        self._mode = "read"  # read | blank | comprehension
        self._content_type = "dialogue"  # dialogue | article
        self._worker = None

        # 外层滚动
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        inner = QWidget()
        self.layout = QVBoxLayout(inner)
        self.layout.setContentsMargins(T.PAGE_MARGIN, 24, T.PAGE_MARGIN, 24)
        self.layout.setSpacing(T.PAGE_SPACING)
        self.scroll.setWidget(inner)

        main_lo = QVBoxLayout(self)
        main_lo.setContentsMargins(0, 0, 0, 0)
        main_lo.addWidget(self.scroll)

        self.build()

    def pre_select_phrases(self, phrase_ids):
        """外部调用：预选词组"""
        self._selected_ids = set(phrase_ids)
        self.build()

    def build(self):
        _clear_layout(self.layout)

        # 标题
        title = QLabel("对话练习")
        title.setStyleSheet(f"""
            font-family: "{T.FONT_DISPLAY}"; font-size: {T.H1}px;
            font-weight: 700; color: {T.TEXT}; background: transparent; border: none;
        """)
        self.layout.addWidget(title)

        sub = QLabel("勾选词组，AI 为你生成一段自然对话")
        sub.setStyleSheet(f"font-size: {T.BODY}px; color: {T.TEXT_MUTED}; background: transparent; border: none;")
        self.layout.addWidget(sub)

        self.layout.addSpacing(4)

        # ===== API 设置卡片 =====
        settings_card = Card()
        sc_lo = QHBoxLayout(settings_card)
        sc_lo.setSpacing(14)

        sc_lo.addWidget(QLabel("API:"))

        settings = get_settings()

        self.provider_combo = QComboBox()
        for key, preset in API_PRESETS.items():
            self.provider_combo.addItem(preset["name"], key)
        cur_provider = settings.get("api_provider", "deepseek")
        idx = self.provider_combo.findData(cur_provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_change)
        sc_lo.addWidget(self.provider_combo)

        self.model_combo = QComboBox()
        self._update_model_combo(cur_provider, settings.get("api_model", ""))
        sc_lo.addWidget(self.model_combo)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("API Key")
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setText(settings.get("api_key", ""))
        self.key_input.setMaximumWidth(240)
        sc_lo.addWidget(self.key_input)

        save_key_btn = QPushButton("保存")
        save_key_btn.setCursor(Qt.PointingHandCursor)
        save_key_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T.ELEVATED};
                border: 1px solid {T.DIVIDER};
                border-radius: 8px;
                padding: 8px 16px;
                font-size: {T.CAPTION}px;
                color: {T.TEXT};
            }}
            QPushButton:hover {{ border-color: {T.GOLD}; }}
        """)
        save_key_btn.clicked.connect(self._save_api_settings)
        sc_lo.addWidget(save_key_btn)

        sc_lo.addStretch()
        self.layout.addWidget(settings_card)

        # ===== 词组选择区 =====
        select_card = Card()
        sel_lo = QVBoxLayout(select_card)
        sel_lo.setSpacing(10)

        sel_header = QHBoxLayout()
        sel_header.addWidget(QLabel("选择要练习的词组（建议 3-8 个）："))

        select_all_btn = QPushButton("全选未掌握")
        select_all_btn.setCursor(Qt.PointingHandCursor)
        select_all_btn.clicked.connect(self._select_all_unmastered)
        sel_header.addWidget(select_all_btn)

        clear_btn = QPushButton("清除选择")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(lambda: self._set_selected(set()))
        sel_header.addWidget(clear_btn)

        # 随机选词数量
        self.random_count_spin = QSpinBox()
        self.random_count_spin.setRange(2, 100)
        self.random_count_spin.setValue(5)
        self.random_count_spin.setFixedWidth(64)
        self.random_count_spin.setStyleSheet(f"""
            QSpinBox {{
                background: {T.ELEVATED}; border: 1px solid {T.DIVIDER};
                border-radius: 8px; padding: 4px 6px; font-size: {T.CAPTION}px;
                color: {T.TEXT};
            }}
            QSpinBox:focus {{ border-color: {T.GOLD}; }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 14px; background: transparent;
            }}
        """)
        sel_header.addWidget(self.random_count_spin)

        random_btn = QPushButton("随机选词")
        random_btn.setCursor(Qt.PointingHandCursor)
        random_btn.clicked.connect(self._random_select)
        sel_header.addWidget(random_btn)

        sel_header.addStretch()

        sel_lo.addLayout(sel_header)

        # 词组勾选列表（独立滚动，最大高度 400px）
        self.phrase_check_container = QWidget()
        self.phrase_check_lo = QVBoxLayout(self.phrase_check_container)
        self.phrase_check_lo.setContentsMargins(0, 0, 0, 0)
        self.phrase_check_lo.setSpacing(3)
        phrase_scroll = QScrollArea()
        phrase_scroll.setWidgetResizable(True)
        phrase_scroll.setMaximumHeight(620)
        phrase_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        phrase_scroll.setWidget(self.phrase_check_container)
        sel_lo.addWidget(phrase_scroll)

        self._build_phrase_checkboxes()

        # 选中计数 + 内容类型 + 生成按钮
        action_row = QHBoxLayout()
        self.selection_count_lbl = QLabel()
        self._update_selection_count()
        action_row.addWidget(self.selection_count_lbl)
        action_row.addStretch()

        # 内容类型选择
        type_label = QLabel("生成：")
        type_label.setStyleSheet(f"font-size:{T.BODY}px; color:{T.TEXT_DIM}; background:transparent;")
        action_row.addWidget(type_label)
        self.type_combo = QComboBox()
        self.type_combo.addItem("💬 对话", "dialogue")
        self.type_combo.addItem("📄 文章", "article")
        self.type_combo.setCurrentIndex(0)
        self.type_combo.currentIndexChanged.connect(
            lambda: (
                setattr(self, '_content_type', self.type_combo.currentData()),
                self.generate_btn.setText("🤖 生成文章" if self.type_combo.currentData() == "article" else "🤖 生成对话"),
                self.word_count_combo.setVisible(self.type_combo.currentData() == "article"),
                self.word_count_custom.setVisible(
                    self.type_combo.currentData() == "article" and self.word_count_combo.currentData() == "custom"
                )
            )
        )
        action_row.addWidget(self.type_combo)

        # 文章字数选择
        self.word_count_combo = QComboBox()
        self.word_count_combo.addItem("短 (~200词)", "short")
        self.word_count_combo.addItem("中 (~350词)", "medium")
        self.word_count_combo.addItem("长 (~500词)", "long")
        self.word_count_combo.addItem("自定义...", "custom")
        self.word_count_combo.setCurrentIndex(1)
        self.word_count_combo.setVisible(False)
        self.word_count_combo.currentIndexChanged.connect(self._on_word_count_changed)
        action_row.addWidget(self.word_count_combo)

        # 自定义字数输入（选"自定义"时可见）
        self.word_count_custom = QSpinBox()
        self.word_count_custom.setRange(100, 2000)
        self.word_count_custom.setValue(500)
        self.word_count_custom.setSingleStep(50)
        self.word_count_custom.setSuffix(" 词")
        self.word_count_custom.setVisible(False)
        self.word_count_custom.setMinimumHeight(36)
        action_row.addWidget(self.word_count_custom)
        action_row.addSpacing(8)

        type_label_text = "🤖 生成对话"
        self.generate_btn = GoldBtn(type_label_text)
        self.generate_btn.clicked.connect(self._generate)
        self.generate_btn.setEnabled(len(self._selected_ids) >= 2)
        action_row.addWidget(self.generate_btn)

        sel_lo.addLayout(action_row)
        self.layout.addWidget(select_card)

        # ===== Loading 指示 =====
        self.loading_lbl = QLabel("")
        self.loading_lbl.setAlignment(Qt.AlignCenter)
        self.loading_lbl.setStyleSheet(f"""
            font-size: {T.H2}px; color: {T.GOLD}; font-weight: 700;
            background: transparent; border: none; padding: 40px;
        """)
        self.loading_lbl.hide()
        self.layout.addWidget(self.loading_lbl)

        # ===== 对话展示区 =====
        self.content_stack = QStackedWidget()
        self.layout.addWidget(self.content_stack, 1)  # stretch=1 to push to fill space

        # 空状态
        empty_w = QWidget()
        e_lo = QVBoxLayout(empty_w)
        e_lo.setAlignment(Qt.AlignCenter)
        e_lbl = QLabel("👆 勾选词组后点击「生成对话」")
        e_lbl.setStyleSheet(f"font-size: {T.H2}px; color: {T.TEXT_MUTED}; background: transparent; border: none;")
        e_lbl.setAlignment(Qt.AlignCenter)
        e_lo.addWidget(e_lbl)
        self.content_stack.addWidget(empty_w)

        # 对话内容区（三个模式）
        self.dialogue_display = QWidget()
        self.dialogue_display_lo = QVBoxLayout(self.dialogue_display)
        self.dialogue_display_lo.setContentsMargins(0, 0, 0, 0)
        self.dialogue_display_lo.setSpacing(16)
        self.content_stack.addWidget(self.dialogue_display)

        # ===== 历史记录 =====
        self._build_history_section()

        self.layout.addStretch()

    def _build_history_section(self):
        """构建历史记录区域"""
        dialogues = get_dialogues()
        if not dialogues:
            return

        # 分隔 + 标题
        sep = QLabel("")
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{T.DIVIDER}; border:none; margin-top:8px;")
        self.layout.addWidget(sep)

        hist_header = QLabel("📚 历史记录")
        hist_header.setStyleSheet(f"""
            font-size: {T.H3}px; font-weight: 700; color: {T.TEXT};
            background: transparent; border: none; padding-top: 12px;
        """)
        self.layout.addWidget(hist_header)

        # 最近 10 条
        for d in sorted(dialogues, key=lambda x: x.get("created", ""), reverse=True)[:10]:
            is_article = d.get("content_type") == "article"
            hist_card = QFrame()
            hist_card.setStyleSheet(f"""
                QFrame {{ background:{T.CARD}; border:1px solid {T.DIVIDER};
                    border-radius:{T.RADIUS}px; }}
                QFrame:hover {{ border-color:{T.GOLD}; }}
            """)
            h_lo = QHBoxLayout(hist_card)
            h_lo.setContentsMargins(16, 12, 16, 12)
            h_lo.setSpacing(12)

            # 标题 + 日期
            info_lo = QVBoxLayout()
            info_lo.setSpacing(2)
            title_lbl = QLabel(d.get("title", "Untitled"))
            title_lbl.setStyleSheet(f"font-size:{T.BODY}px; font-weight:600; color:{T.TEXT}; background:transparent;")
            info_lo.addWidget(title_lbl)
            date_str = d.get("date", "")[:10]
            meta = QLabel(f"{date_str} · {'文章' if is_article else '对话'} · {len(d.get('phrases_used', []))}个词组")
            meta.setStyleSheet(f"font-size:{T.SMALL}px; color:{T.TEXT_MUTED}; background:transparent;")
            info_lo.addWidget(meta)
            h_lo.addLayout(info_lo, 1)

            # 查看按钮
            view_btn = QPushButton("查看")
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.setStyleSheet(f"""
                QPushButton {{ background:{T.ELEVATED}; color:{T.TEXT};
                    border:1px solid {T.DIVIDER}; border-radius:16px;
                    padding:6px 16px; font-size:{T.SMALL}px; }}
                QPushButton:hover {{ border-color:{T.GOLD}; color:{T.GOLD}; }}
            """)
            view_btn.clicked.connect(lambda checked, dd=d: self._view_history(dd))
            h_lo.addWidget(view_btn)

            # 沉浸学习按钮
            study_btn2 = QPushButton("🎓")
            study_btn2.setCursor(Qt.PointingHandCursor)
            study_btn2.setToolTip("沉浸学习")
            study_btn2.setStyleSheet(f"""
                QPushButton {{ background:{T.ELEVATED}; color:{T.TEXT_DIM};
                    border:1px solid {T.DIVIDER}; border-radius:14px;
                    padding:4px 10px; font-size:14px; }}
                QPushButton:hover {{ border-color:{T.GOLD}; color:{T.GOLD}; }}
            """)
            study_btn2.clicked.connect(lambda checked, dd=d: (
                setattr(self, '_current_dialogue', dd),
                setattr(self, '_selected_ids', set(dd.get('phrases_used', []))),
                self._open_study_mode()
            ))
            h_lo.addWidget(study_btn2)

            # 删除按钮
            del_btn = QPushButton("×")
            del_btn.setFixedSize(28, 28)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setStyleSheet(f"""
                QPushButton {{ background:transparent; color:{T.TEXT_MUTED};
                    border:none; font-size:16px; border-radius:14px; }}
                QPushButton:hover {{ color:{T.CORAL}; background:rgba(201,125,96,0.12); }}
            """)
            del_btn.clicked.connect(lambda checked, did=d["id"]: self._delete_history(did))
            h_lo.addWidget(del_btn)

            self.layout.addWidget(hist_card)

    def _view_history(self, data):
        """查看历史记录"""
        # 恢复词组选择
        self._selected_ids = set(data.get("phrases_used", []))
        # 重建词组勾选
        self._build_phrase_checkboxes()
        self._update_selection_count()
        self.generate_btn.setEnabled(True)

        # 恢复内容类型
        self._content_type = data.get("content_type", "dialogue")
        idx = self.type_combo.findData(self._content_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        # 加载到展示区（含已保存的翻译）
        self._current_dialogue = data
        self._current_dialogue_id = data.get("id", "")
        self._mode = "read"
        if data.get("translation"):
            self._show_translation = True
            self._translation_text = data["translation"]
        else:
            self._show_translation = False
            self._translation_text = ""
        self._render_dialogue()

    def _delete_history(self, dialogue_id):
        """删除历史记录"""
        delete_dialogue(dialogue_id)
        self.build()
        self.mw.toast("已删除")

    def _build_phrase_checkboxes(self):
        from PySide6.QtWidgets import QCheckBox
        _clear_layout(self.phrase_check_lo)

        phrases = get_phrases()
        phrases.sort(key=lambda p: p["created"], reverse=True)

        self._phrase_cbs = {}  # phrase_id -> QCheckBox
        for p in phrases:
            row = QHBoxLayout()
            row.setSpacing(8)

            cb = QCheckBox()
            cb.setChecked(p["id"] in self._selected_ids)
            cb.toggled.connect(lambda checked, pid=p["id"]: self._on_phrase_toggle(pid, checked))
            row.addWidget(cb)
            self._phrase_cbs[p["id"]] = cb

            ph = QLabel(p["phrase"])
            ph.setStyleSheet(f"font-size: {T.BODY - 1}px; font-weight: 600; color: {T.TEXT}; background: transparent; border: none;")
            ph.setFixedWidth(180)
            row.addWidget(ph)

            me = QLabel(p["meaning"])
            me.setStyleSheet(f"font-size: {T.SMALL}px; color: {T.TEXT_DIM}; background: transparent; border: none;")
            row.addWidget(me, 1)

            self.phrase_check_lo.addLayout(row)

        self.phrase_check_lo.addStretch()

    def _on_phrase_toggle(self, phrase_id, checked):
        if checked:
            self._selected_ids.add(phrase_id)
        else:
            self._selected_ids.discard(phrase_id)
        self._update_selection_count()
        self.generate_btn.setEnabled(len(self._selected_ids) >= 2)

    def _set_selected(self, ids):
        self._selected_ids = set(ids)
        # 更新所有 checkbox
        for pid, cb in self._phrase_cbs.items():
            cb.setChecked(pid in self._selected_ids)
        self._update_selection_count()
        self.generate_btn.setEnabled(len(self._selected_ids) >= 2)

    def _select_all_unmastered(self):
        phrases = get_phrases()
        ids = {p["id"] for p in phrases if not p.get("mastered")}
        self._set_selected(ids)

    def _random_select(self):
        """随机选词：从词库中随机抽取指定数量"""
        import random
        phrases = get_phrases()
        n = min(self.random_count_spin.value(), len(phrases))
        if n == 0:
            return
        chosen_ids = {p["id"] for p in random.sample(phrases, n)}
        self._set_selected(chosen_ids)

    def _update_selection_count(self):
        self.selection_count_lbl.setText(f"已选 {len(self._selected_ids)} 个词组")

    def _update_model_combo(self, provider, current_model=""):
        self.model_combo.clear()
        preset = API_PRESETS.get(provider, API_PRESETS["custom"])
        for m in preset.get("models", []):
            self.model_combo.addItem(m)
        if current_model and self.model_combo.findText(current_model) >= 0:
            self.model_combo.setCurrentText(current_model)
        elif self.model_combo.count() > 0:
            self.model_combo.setCurrentIndex(0)

    def _on_provider_change(self, idx):
        provider = self.provider_combo.currentData()
        self._update_model_combo(provider)

    def _save_api_settings(self):
        settings = get_settings()
        settings["api_provider"] = self.provider_combo.currentData()
        settings["api_model"] = self.model_combo.currentText()
        settings["api_key"] = self.key_input.text().strip()
        save_settings(settings)
        self.mw.toast("API 设置已保存 ✓")

    # ============================================================
    # 生成对话
    # ============================================================

    def _on_word_count_changed(self):
        """选「自定义」时显示 QSpinBox"""
        is_custom = self.word_count_combo.currentData() == "custom"
        is_article = self.type_combo.currentData() == "article"
        self.word_count_custom.setVisible(is_custom and is_article)

    def _generate(self):
        if len(self._selected_ids) < 2:
            self.mw.toast("至少选择 2 个词组")
            return

        settings = get_settings()
        api_key = settings.get("api_key", "").strip()
        if not api_key:
            self.mw.toast("请先填写 API Key")
            return

        provider = settings.get("api_provider", "deepseek")
        base_url = settings.get("api_base_url", "")
        model = settings.get("api_model", "")
        if not model:
            model = self.model_combo.currentText()

        # 获取选中的词组
        phrases = get_phrases()
        selected_phrases = [p for p in phrases if p["id"] in self._selected_ids]

        # 禁用按钮，显示 loading
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("⏳ 生成中...")
        self.loading_lbl.setText(
            "🤖 AI 正在为你写文章..." if self._content_type == "article" else "🤖 AI 正在为你编织对话..."
        )
        self.loading_lbl.show()

        # 后台线程（传递字数偏好）
        word_count = None
        if self._content_type == "article":
            wc = self.word_count_combo.currentData()
            word_count = self.word_count_custom.value() if wc == "custom" else wc
        self._worker = DialogueWorker(selected_phrases, self._content_type, provider, api_key, base_url, model, word_count)
        self._worker.finished.connect(self._on_dialogue_ready)
        self._worker.start()

    def _on_dialogue_ready(self, result):
        self.loading_lbl.hide()
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("🤖 生成对话")

        if isinstance(result, str):
            # 错误
            QMessageBox.warning(self, "生成失败", f"API 调用失败：\n\n{result}")
            return

        # 成功
        self._current_dialogue = result
        self._mode = "read"
        self._show_translation = False
        self._translation_text = ""
        self._render_dialogue()

        # 保存到历史
        save_data = {
            "title": result.get("title", "Untitled"),
            "content_type": result.get("content_type", "dialogue"),
            "phrases_used": list(self._selected_ids),
            "comprehension_questions": result.get("comprehension_questions", []),
            "blanks": result.get("blanks", []),
        }
        if result.get("content_type") == "article":
            save_data["paragraphs"] = result.get("paragraphs", [])
        else:
            save_data["dialogue"] = result.get("dialogue", [])
        saved = save_dialogue(save_data)
        self._current_dialogue_id = saved["id"]

        self.mw.toast("对话已生成 ✓")

    # ============================================================
    # 翻译
    # ============================================================

    def _toggle_translation(self):
        if getattr(self, '_show_translation', False):
            self._show_translation = False
            self._translation_text = ""
            self._render_dialogue()
            return

        d = self._current_dialogue
        if not d:
            return

        # 已有缓存翻译，直接显示
        if d.get("translation"):
            self._show_translation = True
            self._translation_text = d["translation"]
            self._render_dialogue()
            return

        # 构建待翻译文本
        if d.get("content_type") == "article":
            text = "\n\n".join(d.get("paragraphs", []))
        else:
            text = "\n\n".join(
                f"{'A' if l['speaker']=='A' else 'B'}: {l['text']}"
                for l in d.get("dialogue", [])
            )

        settings = get_settings()
        api_key = settings.get("api_key", "").strip()
        if not api_key:
            self.mw.toast("请先填写 API Key")
            return

        provider = settings.get("api_provider", "deepseek")
        base_url = settings.get("api_base_url", "")
        model = settings.get("api_model", "")
        if not model:
            model = self.model_combo.currentText()

        self._translation_worker = TranslateWorker(
            text, provider, api_key, base_url, model
        )
        self._translation_worker.finished.connect(self._on_translation_ready)
        self._translation_worker.start()
        self.mw.toast("正在翻译...")

    def _on_translation_ready(self, result):
        if isinstance(result, str) and result.startswith("Error:"):
            QMessageBox.warning(self, "翻译失败", result[6:])
            return
        self._show_translation = True
        self._translation_text = result
        # 保存翻译到对话数据，下次不用重新翻译
        if hasattr(self, '_current_dialogue_id'):
            try:
                update_dialogue(self._current_dialogue_id, {"translation": result})
            except Exception:
                pass  # 保存失败不影响显示
        self._current_dialogue["translation"] = result
        self._render_dialogue()

    # ============================================================
    # 渲染对话
    # ============================================================

    def _render_dialogue(self):
        if not self._current_dialogue:
            return

        _clear_layout(self.dialogue_display_lo)
        d = self._current_dialogue
        is_article = d.get("content_type") == "article"

        # ── 摘要卡片 ──
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {T.CARD};
                border: 1px solid {T.DIVIDER};
                border-radius: {T.RADIUS_LG}px;
            }}
        """)
        c_lo = QVBoxLayout(card)
        c_lo.setContentsMargins(28, 24, 28, 24)
        c_lo.setSpacing(12)

        # 标题行
        title_row = QHBoxLayout()
        type_badge = QLabel("📄 文章" if is_article else "💬 对话")
        type_badge.setStyleSheet(f"""
            font-size: {T.SMALL}px; color: {T.GOLD}; background: {T.ELEVATED};
            padding: 4px 14px; border-radius: 12px; font-weight: 600;
        """)
        title_row.addWidget(type_badge)
        title_row.addSpacing(12)
        title_lbl = QLabel(d.get("title", "Untitled"))
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(f"""
            font-family: "{T.FONT_DISPLAY}"; font-size: {T.H2}px;
            font-weight: 700; color: {T.TEXT}; background: transparent; border: none;
        """)
        title_row.addWidget(title_lbl, 1)
        c_lo.addLayout(title_row)

        # 词组数
        phrases = get_phrases()
        used_count = len([p for p in phrases if p["id"] in self._selected_ids])
        info = QLabel(f"使用了 {used_count} 个词组")
        info.setStyleSheet(f"font-size: {T.CAPTION}px; color: {T.TEXT_MUTED}; background: transparent;")
        c_lo.addWidget(info)

        # 按钮行
        btn_row = QHBoxLayout()

        # 沉浸学习
        study_btn = GoldBtn("🎓 沉浸学习")
        study_btn.setCursor(Qt.PointingHandCursor)
        study_btn.setMinimumHeight(44)
        study_btn.clicked.connect(self._open_study_mode)
        btn_row.addWidget(study_btn)

        btn_row.addStretch()
        c_lo.addLayout(btn_row)

        self.dialogue_display_lo.addWidget(card)
        self.dialogue_display_lo.addStretch()
        self.content_stack.setCurrentWidget(self.dialogue_display)

    def _render_read_mode(self, dc_lo, d, max_w=520):
        """纯阅读模式：显示对话气泡，目标词组高亮"""
        dialogue = d.get("dialogue", [])
        selected_phrases_texts = {
            p["phrase"].lower()
            for p in get_phrases()
            if p["id"] in self._selected_ids
        }

        for i, line in enumerate(dialogue):
            text = line["text"]
            is_right = line["speaker"] != "A"
            hl_color = "#ffffff" if is_right else T.GOLD
            for phrase_text in selected_phrases_texts:
                import re
                pattern = re.compile(re.escape(phrase_text), re.IGNORECASE)
                text = pattern.sub(
                    lambda m, c=hl_color: f'<span style="color:{c};font-weight:700;">{m.group()}</span>',
                    text
                )

            speaker_label = "🧑" if line["speaker"] == "A" else "👤"
            bubble = DialogueBubble(speaker_label, text, i, max_w)
            dc_lo.addWidget(bubble)

    def _render_article_read(self, dc_lo, d, max_w=520):
        """文章阅读模式：段落排版，首行缩进，目标词组高亮"""
        title = d.get("title", "")
        paragraphs = d.get("paragraphs", [])

        selected_phrases_texts = {
            p["phrase"].lower()
            for p in get_phrases()
            if p["id"] in self._selected_ids
        }

        # 文章标题
        if title:
            article_title = QLabel(title)
            article_title.setWordWrap(True)
            article_title.setStyleSheet(f"""
                font-family: "{T.FONT_DISPLAY}"; font-size: 22px;
                font-weight: 700; color: {T.TEXT};
                background: transparent; border: none;
                padding-bottom: 16px;
            """)
            dc_lo.addWidget(article_title)

        # 分隔线
        sep = QLabel("")
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {T.DIVIDER}; border: none;")
        dc_lo.addWidget(sep)
        dc_lo.addSpacing(8)

        # 段落
        for para in paragraphs:
            # 高亮目标词组
            text = para
            for phrase_text in selected_phrases_texts:
                import re
                pattern = re.compile(re.escape(phrase_text), re.IGNORECASE)
                text = pattern.sub(
                    lambda m: f'<span style="color:{T.GOLD};font-weight:700;border-bottom:1px solid {T.GOLD_DIM};">{m.group()}</span>',
                    text
                )

            para_label = QLabel(f'<p style="line-height:1.9;">{text}</p>')
            para_label.setWordWrap(True)
            para_label.setMaximumWidth(max_w)
            para_label.setTextFormat(Qt.RichText)
            para_label.setStyleSheet(f"""
                QLabel {{
                    font-size: {T.BODY + 1}px; color: {T.TEXT};
                    padding: 0 0 16px 0;
                    background: transparent; border: none;
                }}
            """)
            dc_lo.addWidget(para_label)

        dc_lo.addStretch()

    def _render_blank_mode(self, dc_lo, d, max_w=520):
        """填空模式"""
        dialogue = d.get("dialogue", [])
        blanks = d.get("blanks", [])
        blanks_by_idx = {b.get("speaker_idx", -1): b.get("phrase", "") for b in blanks}

        self._blank_widgets = []
        self._blank_correct = 0
        self._blank_total = len(blanks)

        for i, line in enumerate(dialogue):
            if i in blanks_by_idx:
                target = blanks_by_idx[i]
                speaker_label = "🧑" if line["speaker"] == "A" else "👤"
                bubble = FillBlankBubble(speaker_label, line["text"], target, line["speaker"] == "A", max_w)
                bubble.answer_submitted.connect(
                    lambda correct, bid=i: self._on_blank_submitted(correct, bid)
                )
                self._blank_widgets.append(bubble)
                dc_lo.addWidget(bubble)
            else:
                plain_bubble = QLabel(line["text"])
                plain_bubble.setWordWrap(True)
                plain_bubble.setMaximumWidth(int(max_w * 0.72))
                plain_bubble.setStyleSheet(f"font-size: {T.BODY}px; color: {T.TEXT_DIM}; padding: 6px 0; background: transparent; border: none;")
                dc_lo.addWidget(plain_bubble)

        self.blank_score_lbl = QLabel(f"已完成 0 / {self._blank_total}")
        self.blank_score_lbl.setAlignment(Qt.AlignCenter)
        self.blank_score_lbl.setStyleSheet(f"font-size: {T.H3}px; color: {T.GOLD}; font-weight: 700; background: transparent; border: none;")
        dc_lo.addWidget(self.blank_score_lbl)

    def _on_blank_submitted(self, correct, idx):
        if correct:
            self._blank_correct += 1
        self.blank_score_lbl.setText(
            f"已完成 {self._blank_correct} / {self._blank_total}"
        )
        if sum(1 for w in self._blank_widgets if w.input.isEnabled()) == 0:
            # 全部完成
            self.blank_score_lbl.setText(
                f"🎉 完成！正确 {self._blank_correct} / {self._blank_total}"
            )

    def _render_comprehension_mode(self, dc_lo, d, max_w=520):
        """阅读理解模式：先展示篇章，再出考试风格的题目"""
        is_article = d.get("content_type") == "article"
        questions = d.get("comprehension_questions", [])

        # 篇章区域
        if is_article:
            passage_label = QLabel("📄 阅读下列文章，回答后面的问题")
            passage_text = "\n\n".join(d.get("paragraphs", []))
        else:
            passage_label = QLabel("📄 阅读下列对话，回答后面的问题")
            dialogue = d.get("dialogue", [])
            passage_text = "\n\n".join(
                f"{'🧑' if l['speaker']=='A' else '👤'}: {l['text']}"
                for l in dialogue
            )

        passage_label.setStyleSheet(f"""
            font-size: {T.CAPTION}px; color: {T.TEXT_MUTED}; font-weight: 600;
            background: transparent; border: none; padding: 4px 0;
        """)
        dc_lo.addWidget(passage_label)

        passage_widget = QLabel(f'<p style="line-height:1.9;">{passage_text}</p>')
        passage_widget.setWordWrap(True)
        passage_widget.setMaximumWidth(max_w)
        passage_widget.setTextFormat(Qt.RichText)
        passage_widget.setStyleSheet(f"""
            font-size: {T.BODY}px; color: {T.TEXT};
            background: {T.ELEVATED}; border: 1px solid {T.DIVIDER};
            border-radius: {T.RADIUS}px; padding: 24px;
        """)
        dc_lo.addWidget(passage_widget)
        dc_lo.addSpacing(24)

        # 题目区域
        q_header = QLabel(f"📝 阅读理解（共 {len(questions)} 小题）")
        q_header.setStyleSheet(f"""
            font-size: {T.H3}px; color: {T.TEXT}; font-weight: 700;
            background: transparent; border: none;
        """)
        dc_lo.addWidget(q_header)

        self._quiz_correct = 0
        self._quiz_total = len(questions)

        for i, q in enumerate(questions):
            num_label = QLabel(f"第 {i + 1} 题")
            num_label.setStyleSheet(f"""
                font-size: {T.SMALL}px; color: {T.TEXT_MUTED}; font-weight: 500;
                background: transparent; border: none; padding-top: 12px;
            """)
            dc_lo.addWidget(num_label)

            cq = ComprehensionQuestion(q)
            cq.answered.connect(lambda correct: self._on_quiz_answered(correct))
            dc_lo.addWidget(cq)

    def _on_quiz_answered(self, correct):
        if correct:
            self._quiz_correct += 1
        if hasattr(self, 'quiz_score_lbl'):
            self.quiz_score_lbl.setText(f"得分：{self._quiz_correct} / {self._quiz_total}")

    def _switch_mode(self, mode):
        self._mode = mode
        self._render_dialogue()

    def _open_study_mode(self):
        """打开沉浸式学习弹窗"""
        if not self._current_dialogue:
            return
        dlg = StudyDialog(self._current_dialogue, self._selected_ids, self)
        dlg.exec()


# ============================================================
# 沉浸式学习弹窗
# ============================================================

class TranslatePopup(QFrame):
    """浮动翻译卡片 — 点击外部自动关闭"""

    def __init__(self, parent, pos, query_text):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setStyleSheet(f"""
            QFrame {{
                background: {T.CARD};
                border: 1px solid {T.GOLD};
                border-radius: {T.RADIUS}px;
            }}
        """)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(18, 14, 18, 14)
        lo.setSpacing(8)

        # 原文
        src = QLabel(query_text)
        src.setWordWrap(True)
        src.setMaximumWidth(380)
        src.setStyleSheet(f"font-family:\"{T.FONT_EN}\",\"{T.FONT_BODY}\"; font-size:{T.BODY}px; color:{T.GOLD}; font-weight:600; background:transparent;")
        lo.addWidget(src)

        # 翻译结果
        self.result_lbl = QLabel("⏳ 翻译中...")
        self.result_lbl.setWordWrap(True)
        self.result_lbl.setMaximumWidth(380)
        self.result_lbl.setStyleSheet(f"font-size:{T.CAPTION}px; color:{T.TEXT_DIM}; background:transparent;")
        lo.addWidget(self.result_lbl)

        self.adjustSize()
        # 定位在光标附近（全局坐标）
        gp = parent.mapToGlobal(pos)
        x = max(10, min(gp.x(), parent.window().width() - self.width() - 20))
        y = max(10, min(gp.y() + 10, parent.window().height() - self.height() - 20))
        self.move(x, y)

    def set_result(self, text):
        self.result_lbl.setText(text)
        self.adjustSize()

    def set_error(self):
        self.result_lbl.setText("翻译失败")
        self.result_lbl.setStyleSheet(f"font-size:{T.CAPTION}px; color:{T.CORAL}; background:transparent;")
        self.adjustSize()


class StudyDialog(QDialog):
    """全屏沉浸式学习窗口"""

    def __init__(self, data, selected_ids, parent=None):
        super().__init__(parent)
        self._data = data
        self._selected_ids = selected_ids
        self._mode = "read"  # read | comprehension
        self._show_translation = bool(data.get("translation"))

        self.setWindowTitle("沉浸学习 · " + data.get("title", ""))
        self.setWindowFlags(Qt.Window)
        self.setMinimumSize(600, 500)
        self.setStyleSheet(f"background:{T.BG};")

        # 阅读模式字体/行间距调节（偏移值）
        self._read_font_extra = 0     # 相对于默认 body 的增减
        self._read_line_spacing = 0   # 相对于默认 line-height 的增减

        # 划线模式
        self._underline_mode = False
        self._underline_texts = set()  # 被划线的文本片段（纯文本）

        # 双栏列宽（仅窗口缩放时更新，翻译切换复用）
        self._col_left_w = 600
        self._col_right_w = 400
        self._update_column_widths()

        if parent:
            self.resize(parent.size())
        else:
            self.resize(1080, 820)
        if parent:
            self.move(parent.mapToGlobal(parent.rect().topLeft()))

        self._build()

    def _update_column_widths(self):
        """计算做题模式左右栏宽度（60% / 40%），仅在窗口宽度实际变化时更新"""
        avail = self.width() - 116
        # 用 _last_avail 防止翻译切换导致的重算
        if abs(avail - getattr(self, '_last_avail', 0)) > 5:
            self._col_left_w = max(300, int(avail * 0.6))
            self._col_right_w = max(200, int(avail * 0.4))
            self._last_avail = avail

    def resizeEvent(self, event):
        """窗口缩放时重渲染（列宽通过 _update_column_widths 自动更新）"""
        super().resizeEvent(event)
        # 仅在非首次渲染后响应 resize
        if hasattr(self, '_content_lo_ref'):
            self._render_content()

    def _build(self):
        main_lo = QVBoxLayout(self)
        main_lo.setContentsMargins(0, 0, 0, 0)
        main_lo.setSpacing(0)

        # ── 顶部栏 ──
        top_bar = QFrame()
        top_bar.setFixedHeight(64)
        top_bar.setStyleSheet(f"background:{T.CARD}; border-bottom:1px solid {T.DIVIDER};")
        tb_lo = QHBoxLayout(top_bar)
        tb_lo.setContentsMargins(24, 0, 24, 0)
        tb_lo.setSpacing(16)

        # 内容类型 + 标题
        is_article = self._data.get("content_type") == "article"
        badge = QLabel("📄 文章" if is_article else "💬 对话")
        badge.setStyleSheet(f"font-size:{T.SMALL}px; color:{T.GOLD}; font-weight:600; background:transparent;")
        tb_lo.addWidget(badge)
        title_lbl = QLabel(self._data.get("title", ""))
        title_lbl.setStyleSheet(f"font-size:{T.H3}px; font-weight:700; color:{T.TEXT}; background:transparent;")
        tb_lo.addWidget(title_lbl, 1)

        # 模式切换 — 保存引用以便切换时更新样式
        self._mode_btns = {}
        for mk, label in [("read", "📖 阅读"), ("comprehension", "🧠 做题")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(self._mode == mk)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(36)
            btn.clicked.connect(lambda checked, m=mk: self._switch(m))
            tb_lo.addWidget(btn)
            self._mode_btns[mk] = btn

        # 翻译按钮
        self._trans_btn = QPushButton("🌐 翻译" if not self._show_translation else "🌐 原文")
        self._trans_btn.setCursor(Qt.PointingHandCursor)
        self._trans_btn.setMinimumHeight(36)
        self._trans_btn.clicked.connect(self._toggle_trans)
        tb_lo.addWidget(self._trans_btn)

        # 快速收录按钮
        qadd_btn = QPushButton("➕ 收录")
        qadd_btn.setCursor(Qt.PointingHandCursor)
        qadd_btn.setMinimumHeight(36)
        qadd_btn.setStyleSheet(f"""
            QPushButton {{ background:{T.ELEVATED}; color:{T.TEXT_DIM};
                border:1px solid {T.DIVIDER}; border-radius:18px;
                padding:6px 16px; font-size:{T.CAPTION}px; }}
            QPushButton:hover {{ border-color:{T.GOLD}; color:{T.GOLD}; }}
        """)
        qadd_btn.clicked.connect(self._on_quick_add_btn)
        tb_lo.addWidget(qadd_btn)

        # 退出
        exit_btn = QPushButton("✕ 退出")
        exit_btn.setCursor(Qt.PointingHandCursor)
        exit_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; color:{T.TEXT_DIM}; border:none;
                font-size:{T.CAPTION}px; padding:6px 12px; }}
            QPushButton:hover {{ color:{T.CORAL}; }}
        """)
        exit_btn.clicked.connect(self.close)
        tb_lo.addWidget(exit_btn)

        main_lo.addWidget(top_bar)

        # 一次性设置所有按钮样式
        self._refresh_topbar()

        # ── 内容区 ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content = QWidget()
        content.setStyleSheet("background:transparent;")
        self._content_lo = QVBoxLayout(content)
        self._content_lo.setContentsMargins(48, 32, 48, 32)
        self._content_lo.setSpacing(24)
        scroll.setWidget(content)
        main_lo.addWidget(scroll, 1)
        self._content_lo_ref = self._content_lo

        self._render_content()

    def _refresh_topbar(self):
        """根据当前状态更新顶部栏按钮样式"""
        # 模式按钮
        for mk, btn in self._mode_btns.items():
            active = (self._mode == mk)
            btn.setChecked(active)
            btn.setStyleSheet(f"""
                QPushButton {{ background:{T.GOLD if active else T.ELEVATED};
                    color:{text_on_accent() if active else T.TEXT_DIM};
                    border:{'none' if active else f'1px solid {T.DIVIDER}'};
                    border-radius:18px; padding:6px 18px; font-size:{T.CAPTION}px; font-weight:{700 if active else 500}; }}
                QPushButton:hover {{ border-color:{T.GOLD}; }}
            """)
        # 翻译按钮
        self._trans_btn.setText("🌐 翻译" if not self._show_translation else "🌐 原文")
        self._trans_btn.setStyleSheet(f"""
            QPushButton {{ background:{T.ELEVATED}; color:{'#5b9ec4' if self._show_translation else T.TEXT_DIM};
                border:1px solid {T.DIVIDER}; border-radius:18px; padding:6px 18px;
                font-size:{T.CAPTION}px; }}
            QPushButton:hover {{ border-color:#5b9ec4; color:#5b9ec4; }}
        """)

    def _switch(self, mode):
        self._mode = mode
        self._refresh_topbar()
        self._render_content()

    def _toggle_trans(self):
        self._show_translation = not self._show_translation
        self._refresh_topbar()

        # 如果需要显示翻译但还没有缓存，调 API 翻译
        if self._show_translation and not self._data.get("translation"):
            self._do_full_translate()
        else:
            self._render_content()

    def _do_full_translate(self):
        """翻译全文"""
        d = self._data
        if d.get("content_type") == "article":
            text = "\n\n".join(d.get("paragraphs", []))
        else:
            text = "\n\n".join(
                f"{'A' if l['speaker']=='A' else 'B'}: {l['text']}"
                for l in d.get("dialogue", [])
            )

        settings = get_settings()
        api_key = settings.get("api_key", "").strip()
        if not api_key:
            self._show_translation = False
            self._refresh_topbar()
            self._render_content()
            return

        provider = settings.get("api_provider", "deepseek")
        base_url = settings.get("api_base_url", "")
        model = settings.get("api_model", "")
        self._trans_btn.setText("⏳ 翻译中...")
        self._trans_btn.setEnabled(False)

        self._full_trans_worker = TranslateWorker(
            text, provider, api_key, base_url, model
        )
        self._full_trans_worker.finished.connect(self._on_full_trans_ready)
        self._full_trans_worker.start()

    def _on_full_trans_ready(self, result):
        self._trans_btn.setEnabled(True)
        if isinstance(result, str) and result.startswith("Error:"):
            self._show_translation = False
            self._refresh_topbar()
            self._render_content()
            return
        self._data["translation"] = result
        # 保存到持久化存储
        dialog_id = None
        if hasattr(self, '_data') and self._data:
            dialog_id = self._data.get("id")
        if not dialog_id:
            # 从 parent 查找对话 ID
            p = self.parent()
            if p and hasattr(p, '_current_dialogue_id'):
                dialog_id = p._current_dialogue_id
        if dialog_id:
            try:
                update_dialogue(dialog_id, {"translation": result})
            except Exception:
                pass
        self._refresh_topbar()
        self._render_content()

    # ── 快速收录 & 划词翻译 ──

    def _on_text_context_menu(self, pos, label):
        """右键菜单：收录 + 翻译 + 划线（划线模式下）"""
        selected = label.selectedText().strip()
        if not selected:
            return
        display = selected[:40] + "..." if len(selected) > 40 else selected
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background:{T.CARD}; border:1px solid {T.DIVIDER}; border-radius:{T.RADIUS_SM}px;
                     padding:4px; color:{T.TEXT}; font-size:{T.CAPTION}px; }}
            QMenu::item {{ padding:8px 20px; border-radius:6px; }}
            QMenu::item:selected {{ background:{T.ELEVATED}; }}
        """)
        # 划线模式下优先显示划线选项
        if self._underline_mode:
            act_underline = menu.addAction(f"✏️ 划线 '{display}'")
            menu.addSeparator()
        act_add = menu.addAction(f"📌 收录 '{display}'")
        act_trans = menu.addAction(f"🌐 翻译")
        # 有划线内容时显示清除选项
        if self._underline_texts:
            menu.addSeparator()
            act_clear = menu.addAction(f"🧹 清除全部划线")
        else:
            act_clear = None
        chosen = menu.exec(label.mapToGlobal(pos))
        if self._underline_mode and chosen == act_underline:
            self._underline_texts.add(selected)
            self._render_content()
        elif chosen == act_add:
            dlg = QuickAddDialog(selected, self)
            dlg.exec()
        elif chosen == act_trans:
            self._do_inline_translate(selected, pos)
        elif act_clear and chosen == act_clear:
            self._clear_underlines()

    def _do_inline_translate(self, text, pos):
        """划词翻译：后台调用 API，结果浮动卡片展示"""
        # 会话内缓存
        if not hasattr(self, '_trans_cache'):
            self._trans_cache = {}
        if text in self._trans_cache:
            popup = TranslatePopup(self, pos, text)
            popup.set_result(self._trans_cache[text])
            popup.show()
            return

        # 显示加载中
        popup = TranslatePopup(self, pos, text)
        popup.show()

        # 后台翻译
        settings = get_settings()
        api_key = settings.get("api_key", "").strip()
        if not api_key:
            popup.set_error()
            return

        self._trans_worker = _QuickTranslateWorker(
            text, settings.get("api_provider", "deepseek"),
            api_key, settings.get("api_base_url", ""),
            settings.get("api_model", ""),
        )
        self._trans_worker.finished.connect(
            lambda result: self._on_trans_popup_ready(popup, text, result)
        )
        self._trans_worker.start()

    def _on_trans_popup_ready(self, popup, text, result):
        if result.startswith("Error:"):
            popup.set_error()
        else:
            self._trans_cache[text] = result.strip()
            popup.set_result(result.strip())

    def _on_quick_add_btn(self):
        """顶部栏「➕ 收录」按钮"""
        selected = self._get_selected_text()
        dlg = QuickAddDialog(selected, self)
        dlg.exec()

    def _on_submit_quiz(self):
        """提交所有题目，批改并显示得分"""
        if not hasattr(self, '_quiz_widgets') or not self._quiz_widgets:
            return
        # 批改
        for cq in self._quiz_widgets:
            cq.reveal()
        correct = sum(1 for cq in self._quiz_widgets if cq.is_correct())
        total = len(self._quiz_widgets)
        self._quiz_score_lbl.setText(f"得分：{correct} / {total}")
        self._quiz_score_lbl.show()
        # 按钮变为重新作答
        self._quiz_submit_btn.setText("🔁 重新作答")
        try:
            self._quiz_submit_btn.clicked.disconnect()
        except Exception:
            pass
        self._quiz_submit_btn.clicked.connect(self._reset_quiz)

    def _reset_quiz(self):
        """重新渲染做题模式"""
        self._quiz_score_lbl.hide()
        self._render_content()

    # ── 字号 / 行距调节 ──

    def _inc_font(self):
        self._read_font_extra = min(6, self._read_font_extra + 1)
        self._render_content()

    def _dec_font(self):
        self._read_font_extra = max(-4, self._read_font_extra - 1)
        self._render_content()

    def _inc_line_spacing(self):
        self._read_line_spacing = min(3, self._read_line_spacing + 1)
        self._render_content()

    def _dec_line_spacing(self):
        self._read_line_spacing = max(-2, self._read_line_spacing - 1)
        self._render_content()

    # ── 划线功能 ──

    def _toggle_underline_mode(self, checked):
        """切换划线模式，同步两个模式下的按钮状态"""
        self._underline_mode = checked
        for attr in ('_underline_btn', '_underline_btn_c'):
            btn = getattr(self, attr, None)
            if btn is None:
                continue
            try:
                btn.setChecked(checked)
            except RuntimeError:
                # C++ 对象已被删除（模式切换时），清除引用
                setattr(self, attr, None)

    def _clear_underlines(self):
        """清除所有划线"""
        self._underline_texts.clear()
        self._render_content()

    def _apply_underlines(self, text):
        """对已标记的文本片段加粗下划线（更粗 + 更靠下，方便阅读标注）"""
        import re
        for ut in self._underline_texts:
            pattern = re.compile(re.escape(ut), re.IGNORECASE)
            text = pattern.sub(
                lambda m: f'<span style="text-decoration:underline;text-underline-offset:4px;text-decoration-thickness:2.5px;">{m.group()}</span>',
                text
            )
        return text

    def _get_selected_text(self):
        """遍历内容区查找已选中的文本"""
        container = self._content_lo_ref.parentWidget()
        for label in container.findChildren(QLabel):
            if label.hasSelectedText():
                return label.selectedText().strip()
        return ""

    def _render_content(self):
        _clear_layout(self._content_lo_ref)

        # 列宽：仅在窗口宽度实际变化时更新（翻译切换复用原值，保证右栏不抖）
        self._update_column_widths()

        d = self._data
        is_article = d.get("content_type") == "article"
        # 字号和宽度都跟着窗口走（参考宽度 900px）
        font_scale = max(0.85, min(1.5, self.width() / 900))
        # 内容宽度跟随窗口，无硬上限 — 字体大了宽度自然也要跟上
        max_w = max(500, self.width() - 96)

        # 选取高亮词组
        phrases = get_phrases()
        highlight_texts = {
            p["phrase"].lower()
            for p in phrases if p["id"] in self._selected_ids
        }

        def highlight(text, is_right=False):
            """高亮目标词组：左气泡用 GOLD，右气泡用白色（与各自背景形成反差）"""
            import re
            color = "#ffffff" if is_right else T.GOLD
            for pt in highlight_texts:
                pattern = re.compile(re.escape(pt), re.IGNORECASE)
                text = pattern.sub(
                    lambda m, c=color: f'<span style="color:{c};font-weight:700;">{m.group()}</span>',
                    text
                )
            return text

        if self._mode == "read":
            self._render_read(self._content_lo_ref, d, is_article, max_w, highlight, font_scale)
        else:
            self._render_comprehension(self._content_lo_ref, d, is_article, max_w, highlight, font_scale)

        self._content_lo_ref.addStretch()

    def _render_read(self, lo, d, is_article, max_w, highlight_fn, font_scale=1.0):
        """渲染阅读模式"""
        fen = T.FONT_EN
        base_body = max(12, int(T.BODY * font_scale))
        body = base_body + self._read_font_extra  # 用户调节后的字号
        small = max(10, int(T.SMALL * font_scale))
        # 行间距：默认 2.0，用户可 ±0.3 每档
        line_h = max(1.1, round(2.0 + self._read_line_spacing * 0.3, 1))

        # ── 排版控制栏 ──
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(6)

        ctrl_hint = QLabel("🔤 字号：")
        ctrl_hint.setStyleSheet(f"font-size:{small}px; color:{T.TEXT_MUTED}; background:transparent;")
        ctrl_bar.addWidget(ctrl_hint)

        def _ctrl_btn(label, tooltip, callback):
            btn = QPushButton(label)
            btn.setFixedSize(30, 28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.setStyleSheet(f"""
                QPushButton {{ background:{T.ELEVATED}; color:{T.TEXT_DIM};
                    border:1px solid {T.DIVIDER}; border-radius:14px; font-size:{small}px; }}
                QPushButton:hover {{ border-color:{T.GOLD}; color:{T.GOLD}; }}
            """)
            btn.clicked.connect(callback)
            return btn

        ctrl_bar.addWidget(_ctrl_btn("A-", "缩小字号", self._dec_font))
        ctrl_bar.addWidget(_ctrl_btn("A+", "放大字号", self._inc_font))
        ctrl_bar.addSpacing(16)

        lh_hint = QLabel("↕ 行距：")
        lh_hint.setStyleSheet(f"font-size:{small}px; color:{T.TEXT_MUTED}; background:transparent;")
        ctrl_bar.addWidget(lh_hint)
        ctrl_bar.addWidget(_ctrl_btn("↕-", "减小行距", self._dec_line_spacing))
        ctrl_bar.addWidget(_ctrl_btn("↕+", "增加行距", self._inc_line_spacing))
        ctrl_bar.addSpacing(16)

        # 划线模式切换
        pen_hint = QLabel("🖍️")
        pen_hint.setStyleSheet(f"font-size:11px; background:transparent;")
        ctrl_bar.addWidget(pen_hint)
        self._underline_btn = QPushButton("划线")
        self._underline_btn.setCheckable(True)
        self._underline_btn.setChecked(self._underline_mode)
        self._underline_btn.setFixedSize(42, 28)
        self._underline_btn.setCursor(Qt.PointingHandCursor)
        self._underline_btn.setToolTip("划线模式：选中文字后右键划线")
        self._underline_btn.setStyleSheet(f"""
            QPushButton {{ background:{T.ELEVATED}; color:{T.TEXT_DIM};
                border:1px solid {T.DIVIDER}; border-radius:14px; font-size:{small}px; }}
            QPushButton:hover {{ border-color:{T.GOLD}; color:{T.GOLD}; }}
            QPushButton:checked {{ background:{T.GOLD}; color:{text_on_accent()}; border-color:{T.GOLD}; }}
        """)
        self._underline_btn.clicked.connect(self._toggle_underline_mode)
        ctrl_bar.addWidget(self._underline_btn)

        # 当前值标签
        self._read_params_lbl = QLabel(f"字号 {body}px · 行距 {line_h}")
        self._read_params_lbl.setStyleSheet(f"font-size:{small}px; color:{T.TEXT_MUTED}; background:transparent;")
        ctrl_bar.addWidget(self._read_params_lbl)
        ctrl_bar.addStretch()

        lo.addLayout(ctrl_bar)
        lo.addSpacing(8)

        if is_article:
            # 文章标题
            t = QLabel(d.get("title", ""))
            t.setWordWrap(True)
            t.setStyleSheet(f"font-family:\"{fen}\", \"{T.FONT_BODY}\"; font-size:{max(18, int(26*font_scale))}px; font-weight:700; color:{T.TEXT}; background:transparent;")
            lo.addWidget(t)
            lo.addSpacing(16)

            # 分隔线
            sep = QLabel("")
            sep.setFixedHeight(1)
            sep.setStyleSheet(f"background:{T.DIVIDER}; border:none; margin-bottom:8px;")
            lo.addWidget(sep)

            for i, para in enumerate(d.get("paragraphs", [])):
                text = self._apply_underlines(highlight_fn(para))
                # Qt QLabel 不支持 QSS line-height，改用 HTML inline style
                para_top = "0" if i == 0 else "16px"
                pl = QLabel(f'<p style="line-height:{line_h}; margin:0; padding-top:{para_top}; padding-bottom:4px;">{text}</p>')
                pl.setWordWrap(True)
                pl.setMaximumWidth(max_w)
                pl.setTextFormat(Qt.RichText)
                pl.setStyleSheet(f"""
                    font-family:"{fen}", "{T.FONT_BODY}";
                    font-size:{body}px; color:{T.TEXT};
                    background:transparent;
                """)
                # 文本可选 + 右键收录
                pl.setTextInteractionFlags(Qt.TextSelectableByMouse)
                pl.setContextMenuPolicy(Qt.CustomContextMenu)
                pl.customContextMenuRequested.connect(
                    lambda pos, lbl=pl: self._on_text_context_menu(pos, lbl)
                )
                lo.addWidget(pl)
        else:
            for line in d.get("dialogue", []):
                is_right = line["speaker"] != "A"
                text = highlight_fn(line["text"], is_right=is_right)
                bubble = DialogueBubble(
                    "🧑" if line["speaker"] == "A" else "👤",
                    text, 0, max_width=max_w,
                    font_scale=font_scale, font_en=fen,
                )
                bubble.enable_text_selection(self._on_text_context_menu)
                lo.addWidget(bubble)

        # 翻译
        if self._show_translation and d.get("translation"):
            lo.addSpacing(16)
            sep = QLabel(""); sep.setFixedHeight(1)
            sep.setStyleSheet(f"background:{T.DIVIDER};")
            lo.addWidget(sep)
            lo.addSpacing(12)
            th = QLabel("🌐 中文翻译")
            th.setStyleSheet(f"font-family:\"{fen}\", \"{T.FONT_BODY}\"; font-size:{small}px; color:#5b9ec4; font-weight:600; background:transparent;")
            lo.addWidget(th)
            # 翻译正文 + 独立滚动条（最大高度 400px）
            trans_scroll = QScrollArea()
            trans_scroll.setMaximumHeight(400)
            trans_scroll.setWidgetResizable(True)
            trans_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
            trans_w = QWidget()
            trans_w.setStyleSheet("background: transparent;")
            trans_lo = QVBoxLayout(trans_w)
            trans_lo.setContentsMargins(0, 0, 0, 0)
            tb = QLabel(f'<p style="line-height:{line_h};">{d["translation"]}</p>')
            tb.setWordWrap(True)
            tb.setMaximumWidth(max_w)
            tb.setTextFormat(Qt.RichText)
            tb.setStyleSheet(f"font-family:\"{fen}\", \"{T.FONT_BODY}\"; font-size:{body}px; color:{T.TEXT_DIM}; background:transparent; padding-top:8px;")
            trans_lo.addWidget(tb)
            trans_scroll.setWidget(trans_w)
            lo.addWidget(trans_scroll)

    def _render_comprehension(self, lo, d, is_article, max_w, highlight_fn, font_scale=1.0):
        """渲染做题模式：左右双栏 — 左边原文 60%，右边题目 40%
           有翻译时左栏竖向分割：原文上60% + 翻译下40%"""
        questions = d.get("comprehension_questions", [])
        fen = T.FONT_EN
        base_body = max(12, int(T.BODY * font_scale))
        body = base_body + self._read_font_extra
        cap = max(11, int(T.CAPTION * font_scale))
        h3 = max(13, int(T.H3 * font_scale))
        small = max(10, int(T.SMALL * font_scale))
        comp_line_h = max(1.1, round(1.9 + self._read_line_spacing * 0.3, 1))
        show_trans = bool(self._show_translation and d.get("translation"))

        # 使用存储的稳定列宽（resizeEvent 更新，翻译切换不复算）
        left_w = self._col_left_w
        right_w = self._col_right_w

        if is_article:
            paragraphs = d.get("paragraphs", [])
        else:
            paragraphs = [
                f"{'🧑' if l['speaker']=='A' else '👤'}: {l['text']}"
                for l in d.get("dialogue", [])
            ]

        # ── 双栏容器 ──
        cols = QHBoxLayout()
        cols.setSpacing(20)

        # ═══ 左栏 60%：阅读材料 ═══
        left_lo = QVBoxLayout()
        left_lo.setSpacing(6)

        # 排版控制栏
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(4)

        def _mini_btn(label, tip, cb):
            btn = QPushButton(label)
            btn.setFixedSize(24, 22)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tip)
            btn.setStyleSheet(f"""
                QPushButton {{ background:{T.ELEVATED}; color:{T.TEXT_DIM};
                    border:1px solid {T.DIVIDER}; border-radius:11px; font-size:9px; }}
                QPushButton:hover {{ border-color:{T.GOLD}; color:{T.GOLD}; }}
            """)
            btn.clicked.connect(cb)
            return btn

        _f = QLabel("🔤"); _f.setStyleSheet(f"font-size:10px; background:transparent;")
        ctrl_bar.addWidget(_f)
        ctrl_bar.addWidget(_mini_btn("A-", "缩小字号", self._dec_font))
        ctrl_bar.addWidget(_mini_btn("A+", "放大字号", self._inc_font))
        ctrl_bar.addSpacing(8)
        _lh = QLabel("↕"); _lh.setStyleSheet(f"font-size:10px; background:transparent;")
        ctrl_bar.addWidget(_lh)
        ctrl_bar.addWidget(_mini_btn("↕-", "减小行距", self._dec_line_spacing))
        ctrl_bar.addWidget(_mini_btn("↕+", "增加行距", self._inc_line_spacing))
        ctrl_bar.addSpacing(8)
        _pen = QLabel("🖍️"); _pen.setStyleSheet(f"font-size:10px; background:transparent;")
        ctrl_bar.addWidget(_pen)
        self._underline_btn_c = QPushButton("划线")
        self._underline_btn_c.setCheckable(True)
        self._underline_btn_c.setChecked(self._underline_mode)
        self._underline_btn_c.setFixedSize(42, 22)
        self._underline_btn_c.setCursor(Qt.PointingHandCursor)
        self._underline_btn_c.setToolTip("划线模式：选中文字后右键划线")
        self._underline_btn_c.setStyleSheet(f"""
            QPushButton {{ background:{T.ELEVATED}; color:{T.TEXT_DIM};
                border:1px solid {T.DIVIDER}; border-radius:11px; font-size:9px; }}
            QPushButton:hover {{ border-color:{T.GOLD}; color:{T.GOLD}; }}
            QPushButton:checked {{ background:{T.GOLD}; color:{text_on_accent()}; border-color:{T.GOLD}; }}
        """)
        self._underline_btn_c.clicked.connect(self._toggle_underline_mode)
        ctrl_bar.addWidget(self._underline_btn_c)
        ctrl_bar.addStretch()
        left_lo.addLayout(ctrl_bar)

        passage_hdr = QLabel("📄 阅读材料")
        passage_hdr.setStyleSheet(f"font-family:\"{fen}\", \"{T.FONT_BODY}\"; font-size:{small}px; color:{T.TEXT_MUTED}; font-weight:600; background:transparent;")
        left_lo.addWidget(passage_hdr)

        # 逐段渲染，保持段落间距
        p_scroll = QScrollArea()
        p_scroll.setWidgetResizable(True)
        p_scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        p_scroll_w = QWidget()
        p_scroll_w.setStyleSheet("background:transparent;")
        p_lo = QVBoxLayout(p_scroll_w)
        p_lo.setContentsMargins(0, 0, 0, 0)
        p_lo.setSpacing(0)

        for para in paragraphs:
            para_text = self._apply_underlines(highlight_fn(para))
            pl = QLabel(f'<p style="line-height:{comp_line_h}; margin:0; padding:6px 18px;">{para_text}</p>')
            pl.setWordWrap(True)
            pl.setMaximumWidth(left_w)
            pl.setTextFormat(Qt.RichText)
            pl.setStyleSheet(f"""
                font-family:"{fen}", "{T.FONT_BODY}";
                font-size:{body}px; color:{T.TEXT};
                background:transparent;
            """)
            pl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            pl.setContextMenuPolicy(Qt.CustomContextMenu)
            pl.customContextMenuRequested.connect(
                lambda pos, lbl=pl: self._on_text_context_menu(pos, lbl)
            )
            p_lo.addWidget(pl)

        p_lo.addStretch()
        p_scroll.setWidget(p_scroll_w)

        # 外层容器加边框
        p_frame = QFrame()
        p_frame.setStyleSheet(f"""
            QFrame {{ background:{T.ELEVATED}; border:1px solid {T.DIVIDER};
                     border-radius:{T.RADIUS}px; }}
        """)
        pf_lo = QVBoxLayout(p_frame)
        pf_lo.setContentsMargins(0, 12, 0, 12)
        pf_lo.addWidget(p_scroll)

        if show_trans:
            # ── 竖向分割：原文上 60% + 翻译下 40% ──
            left_lo.addWidget(p_frame, 6)

            # 翻译面板（独立背景 + 边框 + 滚动）
            trans_frame = QFrame()
            trans_frame.setStyleSheet(f"""
                QFrame {{ background:{T.CARD}; border:1px solid #5b9ec4;
                          border-radius:{T.RADIUS}px; }}
            """)
            tf_lo = QVBoxLayout(trans_frame)
            tf_lo.setContentsMargins(14, 12, 14, 12)
            tf_lo.setSpacing(6)

            th = QLabel("🌐 翻译")
            th.setStyleSheet(f"font-family:\"{fen}\",\"{T.FONT_BODY}\"; font-size:{small}px; color:#5b9ec4; font-weight:600; background:transparent;")
            tf_lo.addWidget(th)

            trans_scroll = QScrollArea()
            trans_scroll.setWidgetResizable(True)
            trans_scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
            trans_w_inner = QWidget()
            trans_w_inner.setStyleSheet("background:transparent;")
            t_lo = QVBoxLayout(trans_w_inner)
            t_lo.setContentsMargins(0, 0, 0, 0)
            trans_lbl = QLabel(f'<p style="line-height:{comp_line_h};">{d["translation"]}</p>')
            trans_lbl.setWordWrap(True)
            trans_lbl.setTextFormat(Qt.RichText)
            trans_lbl.setStyleSheet(f"font-family:\"{fen}\",\"{T.FONT_BODY}\"; font-size:{body - 1}px; color:{T.TEXT_DIM}; background:transparent;")
            t_lo.addWidget(trans_lbl)
            trans_scroll.setWidget(trans_w_inner)
            tf_lo.addWidget(trans_scroll, 1)

            left_lo.addWidget(trans_frame, 4)
        else:
            left_lo.addWidget(p_frame, 1)

        # 左栏容器
        left_col = QWidget()
        left_col.setLayout(left_lo)
        cols.addWidget(left_col, 6)

        # ═══ 右栏 40%：题目 ═══
        right_lo = QVBoxLayout()
        right_lo.setSpacing(10)

        q_hdr = QLabel(f"📝 阅读理解（共 {len(questions)} 题）")
        q_hdr.setStyleSheet(f"font-family:\"{fen}\", \"{T.FONT_BODY}\"; font-size:{h3}px; font-weight:700; color:{T.TEXT}; background:transparent;")
        right_lo.addWidget(q_hdr)

        # 题目放入独立滚动区
        q_scroll = QScrollArea()
        q_scroll.setWidgetResizable(True)
        q_scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        q_widget = QWidget()
        q_widget.setStyleSheet("background:transparent;")
        q_lo = QVBoxLayout(q_widget)
        q_lo.setContentsMargins(0, 0, 0, 0)
        q_lo.setSpacing(8)

        self._quiz_widgets = []
        for i, q in enumerate(questions):
            num = QLabel(f"第 {i+1} 题")
            num.setStyleSheet(f"font-family:\"{fen}\", \"{T.FONT_BODY}\"; font-size:{small}px; color:{T.TEXT_MUTED}; background:transparent;")
            q_lo.addWidget(num)
            cq = ComprehensionQuestion(q, font_scale=font_scale, font_en=fen)
            cq.setMaximumWidth(right_w)
            q_lo.addWidget(cq)
            self._quiz_widgets.append(cq)

        q_lo.addStretch()
        q_scroll.setWidget(q_widget)
        right_lo.addWidget(q_scroll, 1)

        # 提交按钮 + 得分
        self._quiz_submit_btn = GoldBtn("📝 提交答案")
        self._quiz_submit_btn.setMinimumHeight(48)
        self._quiz_submit_btn.clicked.connect(self._on_submit_quiz)
        right_lo.addWidget(self._quiz_submit_btn)

        self._quiz_score_lbl = QLabel("")
        self._quiz_score_lbl.setAlignment(Qt.AlignCenter)
        self._quiz_score_lbl.setStyleSheet(f"font-family:\"{fen}\", \"{T.FONT_BODY}\"; font-size:{h3}px; font-weight:700; color:{T.GOLD}; background:transparent;")
        self._quiz_score_lbl.hide()
        right_lo.addWidget(self._quiz_score_lbl)

        right_col = QWidget()
        right_col.setLayout(right_lo)
        cols.addWidget(right_col, 4)

        lo.addLayout(cols)
