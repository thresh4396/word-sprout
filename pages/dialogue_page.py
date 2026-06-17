"""
「词芽」对话练习页面
勾选词组 → AI 生成对话 → 三种练习模式（纯阅读/填空/阅读理解）
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QStackedWidget, QFrame,
    QComboBox, QMessageBox, QApplication,
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer

from config import T, API_PRESETS
from widgets.base import GoldBtn, GhostBtn, TagChip, Card, _clear_layout
from widgets.dialogue_bubble import DialogueBubble, FillBlankBubble, ComprehensionQuestion
from data_manager import (
    get_phrases, get_settings, save_settings, save_dialogue,
    get_dialogues, delete_dialogue,
)


# ============================================================
# 后台 API 调用线程
# ============================================================

class DialogueWorker(QThread):
    """后台线程调用 AI API"""
    finished = Signal(object)  # 成功: dict, 失败: str
    progress = Signal(str)

    def __init__(self, phrases, provider, api_key, base_url, model):
        super().__init__()
        self._phrases = phrases
        self._provider = provider
        self._api_key = api_key
        self._base_url = base_url
        self._model = model

    def run(self):
        from api_client import generate_dialogue
        try:
            self.progress.emit("正在生成对话...")
            result = generate_dialogue(
                self._phrases, self._provider, self._api_key,
                self._base_url, self._model,
            )
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(str(e))


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
        self._worker = None

        # 外层滚动
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

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
        sel_header.addStretch()

        sel_lo.addLayout(sel_header)

        # 词组勾选列表
        self.phrase_check_container = QWidget()
        self.phrase_check_lo = QVBoxLayout(self.phrase_check_container)
        self.phrase_check_lo.setContentsMargins(0, 0, 0, 0)
        self.phrase_check_lo.setSpacing(6)
        sel_lo.addWidget(self.phrase_check_container)

        self._build_phrase_checkboxes()

        # 选中计数 + 生成按钮
        action_row = QHBoxLayout()
        self.selection_count_lbl = QLabel()
        self._update_selection_count()
        action_row.addWidget(self.selection_count_lbl)
        action_row.addStretch()

        self.generate_btn = GoldBtn("🤖 生成对话")
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

        self.layout.addStretch()

    def _build_phrase_checkboxes(self):
        from PySide6.QtWidgets import QCheckBox
        _clear_layout(self.phrase_check_lo)

        phrases = get_phrases()
        phrases.sort(key=lambda p: p["created"], reverse=True)

        self._phrase_cbs = {}  # phrase_id -> QCheckBox
        for p in phrases:
            row = QHBoxLayout()
            row.setSpacing(10)

            cb = QCheckBox()
            cb.setChecked(p["id"] in self._selected_ids)
            cb.toggled.connect(lambda checked, pid=p["id"]: self._on_phrase_toggle(pid, checked))
            row.addWidget(cb)
            self._phrase_cbs[p["id"]] = cb

            ph = QLabel(p["phrase"])
            ph.setStyleSheet(f"font-size: {T.BODY}px; font-weight: 600; color: {T.TEXT}; background: transparent; border: none;")
            ph.setFixedWidth(220)
            row.addWidget(ph)

            me = QLabel(p["meaning"])
            me.setStyleSheet(f"font-size: {T.CAPTION}px; color: {T.TEXT_DIM}; background: transparent; border: none;")
            row.addWidget(me, 1)

            tags = ", ".join(p.get("tags", [])[:2])
            if tags:
                tg = QLabel(tags)
                tg.setStyleSheet(f"font-size: {T.SMALL}px; color: {T.TEXT_MUTED}; background: transparent; border: none;")
                row.addWidget(tg)

            if p.get("mastered"):
                badge = QLabel("✓")
                badge.setStyleSheet(f"font-size: 14px; color: {T.GOLD}; font-weight: bold; background: transparent; border: none;")
                row.addWidget(badge)

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
        self.loading_lbl.setText("🤖 AI 正在为你编织对话...")
        self.loading_lbl.show()

        # 后台线程
        self._worker = DialogueWorker(selected_phrases, provider, api_key, base_url, model)
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
        self._render_dialogue()

        # 保存到历史
        save_dialogue({
            "title": result.get("title", "Untitled"),
            "phrases_used": list(self._selected_ids),
            "dialogue": result["dialogue"],
            "comprehension_questions": result.get("comprehension_questions", []),
            "blanks": result.get("blanks", []),
        })

        self.mw.toast("对话已生成 ✓")

    # ============================================================
    # 渲染对话
    # ============================================================

    def _render_dialogue(self):
        if not self._current_dialogue:
            return

        _clear_layout(self.dialogue_display_lo)
        d = self._current_dialogue

        # 标题
        title_lbl = QLabel(d.get("title", "Dialogue"))
        title_lbl.setStyleSheet(f"""
            font-family: "{T.FONT_DISPLAY}"; font-size: {T.H2}px;
            font-weight: 700; color: {T.GOLD}; background: transparent; border: none;
        """)
        self.dialogue_display_lo.addWidget(title_lbl)

        # 模式切换按钮
        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)

        for mode_key, label in [("read", "📖 纯阅读"), ("blank", "✏️ 填空"), ("comprehension", "🧠 阅读理解")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(self._mode == mode_key)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(38)
            active = (self._mode == mode_key)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {T.GOLD if active else T.ELEVATED};
                    color: {'#fff' if active else T.TEXT_DIM};
                    border: {'none' if active else f'1px solid {T.DIVIDER}'};
                    border-radius: 19px;
                    padding: 8px 20px;
                    font-size: {T.CAPTION}px;
                    font-weight: {700 if active else 500};
                }}
                QPushButton:hover {{
                    border-color: {T.GOLD};
                }}
            """)
            btn.clicked.connect(lambda checked, mk=mode_key: self._switch_mode(mk))
            mode_row.addWidget(btn)

        mode_row.addStretch()
        self.dialogue_display_lo.addLayout(mode_row)

        # 对话卡片
        dialogue_card = Card()
        dc_lo = QVBoxLayout(dialogue_card)
        dc_lo.setSpacing(6)

        if self._mode == "read":
            self._render_read_mode(dc_lo, d)
        elif self._mode == "blank":
            self._render_blank_mode(dc_lo, d)
        elif self._mode == "comprehension":
            self._render_comprehension_mode(dc_lo, d)

        self.dialogue_display_lo.addWidget(dialogue_card)

        # 理解题分数（仅在 comprehension 模式）
        if self._mode == "comprehension":
            self.quiz_score_lbl = QLabel("")
            self.quiz_score_lbl.setAlignment(Qt.AlignCenter)
            self.quiz_score_lbl.setStyleSheet(f"font-size: {T.H3}px; font-weight: 700; background: transparent; border: none;")
            self.dialogue_display_lo.addWidget(self.quiz_score_lbl)

        # 相关词组
        phrases = get_phrases()
        used_phrases = [p for p in phrases if p["id"] in self._selected_ids]
        if used_phrases:
            tags_row = QHBoxLayout()
            tags_row.addWidget(QLabel("练习词组："))
            for p in used_phrases:
                chip = TagChip(f"{p['phrase']}（{p['meaning']}）")
                tags_row.addWidget(chip)
            tags_row.addStretch()
            self.dialogue_display_lo.addLayout(tags_row)

        self.dialogue_display_lo.addStretch()
        self.content_stack.setCurrentWidget(self.dialogue_display)

    def _render_read_mode(self, dc_lo, d):
        """纯阅读模式：显示对话气泡，目标词组高亮"""
        dialogue = d.get("dialogue", [])
        phrases_data = {p["id"]: p for p in get_phrases()}
        selected_phrases_texts = {
            p["phrase"].lower()
            for p in get_phrases()
            if p["id"] in self._selected_ids
        }

        for i, line in enumerate(dialogue):
            text = line["text"]
            # 高亮目标词组
            for phrase_text in selected_phrases_texts:
                import re
                pattern = re.compile(re.escape(phrase_text), re.IGNORECASE)
                text = pattern.sub(
                    lambda m: f'<span style="color:{T.GOLD};font-weight:700;">{m.group()}</span>',
                    text
                )

            speaker_label = "🧑" if line["speaker"] == "A" else "👤"
            bubble = DialogueBubble(speaker_label, text, i)
            dc_lo.addWidget(bubble)

    def _render_blank_mode(self, dc_lo, d):
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
                bubble = FillBlankBubble(speaker_label, line["text"], target, line["speaker"] == "A")
                bubble.answer_submitted.connect(
                    lambda correct, bid=i: self._on_blank_submitted(correct, bid)
                )
                self._blank_widgets.append(bubble)
                dc_lo.addWidget(bubble)
            else:
                speaker_label = "🧑" if line["speaker"] == "A" else "👤"
                # 纯显示（非填空行）
                plain_bubble = QLabel(line["text"])
                plain_bubble.setWordWrap(True)
                plain_bubble.setMaximumWidth(520)
                plain_bubble.setStyleSheet(f"font-size: {T.BODY}px; color: {T.TEXT_DIM}; padding: 6px 0; background: transparent; border: none;")
                dc_lo.addWidget(plain_bubble)

        # 填空得分
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

    def _render_comprehension_mode(self, dc_lo, d):
        """阅读理解模式：先展示篇章，再出考试风格的题目"""
        dialogue = d.get("dialogue", [])
        questions = d.get("comprehension_questions", [])

        # 篇章区域（考试风格的阅读文本）
        passage_label = QLabel("📄 阅读下列对话，回答后面的问题")
        passage_label.setStyleSheet(f"""
            font-size: {T.CAPTION}px; color: {T.TEXT_MUTED}; font-weight: 600;
            background: transparent; border: none; padding: 4px 0;
        """)
        dc_lo.addWidget(passage_label)

        dialogue_text = "\n\n".join(
            f"{'🧑' if l['speaker']=='A' else '👤'}: {l['text']}"
            for l in dialogue
        )
        dialogue_preview = QLabel(dialogue_text)
        dialogue_preview.setWordWrap(True)
        dialogue_preview.setStyleSheet(f"""
            font-size: {T.BODY}px; color: {T.TEXT};
            background: {T.ELEVATED}; border: 2px solid {T.DIVIDER};
            border-radius: {T.RADIUS}px; padding: 24px;
            border: none;
            line-height: 1.8;
        """)
        dc_lo.addWidget(dialogue_preview)

        dc_lo.addSpacing(20)

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
            # 题号标签
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
