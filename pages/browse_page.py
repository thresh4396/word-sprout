"""
「词芽」词库浏览页面
搜索 + 标签过滤 + 日期分组 + 勾选功能
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QScrollArea, QFrame, QCheckBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from config import T
from widgets.base import GoldBtn, GhostBtn, TagChip, PhraseRow, Card, _clear_layout
from data_manager import get_phrases, get_all_tags, delete_phrase, get_phrase_by_id


class BrowsePage(QWidget):
    # 选中词组变化信号
    selection_changed = Signal()

    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self._search_text = ""
        self._active_tag = None
        self._selected_ids = set()
        self._phrase_rows = []

        # 外层滚动
        self.outer_scroll = QScrollArea()
        self.outer_scroll.setWidgetResizable(True)
        self.outer_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        self.layout = QVBoxLayout(inner)
        self.layout.setContentsMargins(T.PAGE_MARGIN, 24, T.PAGE_MARGIN, 24)
        self.layout.setSpacing(T.PAGE_SPACING)
        self.outer_scroll.setWidget(inner)

        main_lo = QVBoxLayout(self)
        main_lo.setContentsMargins(0, 0, 0, 0)
        main_lo.addWidget(self.outer_scroll)

        self.build()

    def build(self):
        _clear_layout(self.layout)

        # 标题
        title = QLabel("词库")
        title.setStyleSheet(f"""
            font-family: "{T.FONT_DISPLAY}"; font-size: {T.H1}px;
            font-weight: 700; color: {T.TEXT}; background: transparent; border: none;
        """)
        self.layout.addWidget(title)

        # 搜索栏
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索英文或中文...")
        self.search_input.setMinimumHeight(44)
        self.search_input.textChanged.connect(self._on_search)
        search_row.addWidget(self.search_input, 1)

        # 生成对话按钮
        self.dialogue_btn = GoldBtn("💬 生成对话")
        self.dialogue_btn.setEnabled(False)
        self.dialogue_btn.clicked.connect(self._on_generate_dialogue)
        search_row.addWidget(self.dialogue_btn)

        self.layout.addLayout(search_row)

        # 标签过滤行
        self.tags_row = QHBoxLayout()
        self.tags_row.setSpacing(8)
        self.tags_row.addStretch()
        self.layout.addLayout(self.tags_row)

        # 全选
        self.select_all_cb = QCheckBox("全选")
        self.select_all_cb.toggled.connect(self._on_select_all)
        self.layout.addWidget(self.select_all_cb)

        # 结果数量和选中数量
        self.result_label = QLabel()
        self.result_label.setStyleSheet(f"font-size: {T.CAPTION}px; color: {T.TEXT_MUTED}; background: transparent; border: none;")
        self.layout.addWidget(self.result_label)

        # 词组列表容器
        self.list_container = QWidget()
        self.list_lo = QVBoxLayout(self.list_container)
        self.list_lo.setContentsMargins(0, 0, 0, 0)
        self.list_lo.setSpacing(8)
        self.layout.addWidget(self.list_container)

        self.layout.addStretch()

        # 渲染
        self._refresh_tags()
        self._refresh_list()

    def _on_search(self, text):
        self._search_text = text.strip().lower()
        self._refresh_list()

    def _on_select_all(self, checked):
        if checked:
            phrases = self._filtered_phrases()
            self._selected_ids = {p["id"] for p in phrases}
        else:
            self._selected_ids.clear()
        self._refresh_list()
        self._update_dialogue_btn()
        self.selection_changed.emit()

    def _filtered_phrases(self):
        phrases = get_phrases()
        result = phrases

        # 搜索过滤
        if self._search_text:
            result = [
                p for p in result
                if self._search_text in p["phrase"].lower()
                or self._search_text in p["meaning"].lower()
            ]

        # 标签过滤
        if self._active_tag:
            result = [p for p in result if self._active_tag in p.get("tags", [])]

        # 按日期倒序
        result.sort(key=lambda p: p["created"], reverse=True)
        return result

    def _refresh_tags(self):
        _clear_layout(self.tags_row)
        tags = get_all_tags()

        # "全部" 标签
        all_chip = TagChip("全部", active=(self._active_tag is None))
        all_chip.mousePressEvent = lambda e: self._set_tag(None)
        self.tags_row.addWidget(all_chip)

        for tag in tags:
            chip = TagChip(tag, active=(tag == self._active_tag))
            chip.mousePressEvent = lambda e, t=tag: self._set_tag(t)
            self.tags_row.addWidget(chip)

        self.tags_row.addStretch()

    def _set_tag(self, tag):
        self._active_tag = tag
        self._refresh_tags()
        self._refresh_list()

    def _refresh_list(self):
        _clear_layout(self.list_lo)
        self._phrase_rows = []
        phrases = self._filtered_phrases()

        self.result_label.setText(f"共 {len(phrases)} 条 | 选中 {len(self._selected_ids)} 条")
        self.select_all_cb.setChecked(
            len(self._selected_ids) == len(phrases) and len(phrases) > 0
        )

        if not phrases:
            empty = QLabel("还没有词组，去录入吧 ✏️")
            empty.setStyleSheet(f"color: {T.TEXT_MUTED}; padding: 40px; font-size: {T.BODY}px; background: transparent; border: none;")
            self.list_lo.addWidget(empty)
            self.list_lo.addStretch()
            return

        for p in phrases:
            row = PhraseRow(p, show_checkbox=True)
            row.toggled.connect(lambda checked, pid=p["id"]: self._on_toggle(pid, checked))
            row.edit_requested.connect(lambda pid=p["id"]: self._on_edit(pid))
            row.delete_requested.connect(lambda pid=p["id"]: self._on_delete(pid))
            row.cb.setChecked(p["id"] in self._selected_ids)
            row._checked = p["id"] in self._selected_ids
            row._update_bg()
            self._phrase_rows.append(row)
            self.list_lo.addWidget(row)

        self.list_lo.addStretch()

    def _on_toggle(self, phrase_id, checked):
        if checked:
            self._selected_ids.add(phrase_id)
        else:
            self._selected_ids.discard(phrase_id)
        self._update_result_label()
        self._update_dialogue_btn()
        self.selection_changed.emit()

    def _on_edit(self, phrase_id):
        """打开编辑页面"""
        self.mw.open_edit_phrase(phrase_id)

    def _on_delete(self, phrase_id):
        """确认后删除词组"""
        p = get_phrase_by_id(phrase_id)
        if not p:
            return
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除「{p['phrase']}」吗？\n\n释义：{p['meaning']}\n\n此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            delete_phrase(phrase_id)
            self.mw.toast(f"已删除「{p['phrase']}」")
            self._refresh_tags()
            self._refresh_list()

    def _update_result_label(self):
        phrases = self._filtered_phrases()
        self.result_label.setText(f"共 {len(phrases)} 条 | 选中 {len(self._selected_ids)} 条")

    def _update_dialogue_btn(self):
        count = len(self._selected_ids)
        self.dialogue_btn.setEnabled(count >= 2)
        if count >= 2:
            self.dialogue_btn.setText(f"💬 生成对话 ({count})")
        else:
            self.dialogue_btn.setText("💬 生成对话")

    def _on_generate_dialogue(self):
        if len(self._selected_ids) < 2:
            self.mw.toast("请至少选择 2 个词组")
            return
        self.mw.go_to_dialogue(list(self._selected_ids))

    def get_selected_ids(self):
        return self._selected_ids
