"""
「词芽」统计页面
趋势图表 + 掌握率 + 导出
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFileDialog, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from config import T
from widgets.base import GoldBtn, GhostBtn, Card, RingProgress, _clear_layout
from widgets.stats_chart import WeeklyChart
from data_manager import (
    get_phrases, get_daily_stats, export_json, export_csv,
    get_today_stats, get_all_tags,
)
from review_engine import get_due_count, get_mastery_rate
from datetime import date, timedelta


class StatsPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window

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

    def build(self):
        _clear_layout(self.layout)

        # ── 标题 ──
        title = QLabel("学习统计")
        title.setStyleSheet(f"""
            font-family: "{T.FONT_DISPLAY}"; font-size: {T.H1}px;
            font-weight: 700; color: {T.TEXT}; background: transparent; border: none;
        """)
        self.layout.addWidget(title)

        phrases = get_phrases()
        mastery = get_mastery_rate(phrases)
        due = get_due_count(phrases)

        # ── 概览卡片行：掌握率 + 数据 ──
        overview = QHBoxLayout()
        overview.setSpacing(16)

        # 环形掌握率
        ring_card = Card()
        ring_card.setMinimumWidth(220)
        ring_lo = QVBoxLayout(ring_card)
        ring_lo.setAlignment(Qt.AlignCenter)
        ring_lo.setSpacing(12)
        ring = RingProgress(size=140, thickness=12)
        ring.setProgress(mastery)
        ring_lo.addWidget(ring, alignment=Qt.AlignCenter)
        ring_label = QLabel("掌握率")
        ring_label.setAlignment(Qt.AlignCenter)
        ring_label.setStyleSheet(f"font-size: {T.CAPTION}px; color: {T.TEXT_MUTED}; background: transparent; border: none;")
        ring_lo.addWidget(ring_label)
        overview.addWidget(ring_card)

        # 数字统计卡
        num_card = Card()
        num_lo = QVBoxLayout(num_card)
        num_lo.setSpacing(16)

        stats_items = [
            ("总词库", len(phrases)),
            ("已掌握", sum(1 for p in phrases if p.get("mastered"))),
            ("待复习", due),
            ("总复习次数", sum(p.get("review_count", 0) for p in phrases)),
        ]
        for label, value in stats_items:
            row = QHBoxLayout()
            l = QLabel(label)
            l.setStyleSheet(f"font-size: {T.BODY}px; color: {T.TEXT_DIM}; background: transparent; border: none;")
            row.addWidget(l)
            row.addStretch()
            v = QLabel(str(value))
            v.setStyleSheet(f"font-size: {T.H2}px; font-weight: 700; color: {T.GOLD}; background: transparent; border: none;")
            row.addWidget(v)
            num_lo.addLayout(row)

        overview.addWidget(num_card, 1)
        self.layout.addLayout(overview)

        # ── 周统计图 ──
        chart_card = Card()
        chart_lo = QVBoxLayout(chart_card)
        chart_lo.setContentsMargins(8, 8, 8, 8)
        chart_lo.setSpacing(0)
        weekly_data = self._get_weekly_data()
        chart = WeeklyChart(weekly_data)
        chart_lo.addWidget(chart)
        self.layout.addWidget(chart_card)

        # ── 标签分布 ──
        tags = get_all_tags()
        if tags:
            tag_card = Card()
            tag_lo = QVBoxLayout(tag_card)
            tag_lo.setSpacing(12)
            tag_title = QLabel("标签分布")
            tag_title.setStyleSheet(f"font-size: {T.H3}px; font-weight: 700; color: {T.TEXT}; background: transparent; border: none;")
            tag_lo.addWidget(tag_title)

            from widgets.base import TagChip
            from PySide6.QtWidgets import QFrame
            tags_container = QFrame()
            tags_container.setStyleSheet(f"background: transparent; border: none;")
            tags_flow = QHBoxLayout(tags_container)
            tags_flow.setContentsMargins(0, 0, 0, 0)
            tags_flow.setSpacing(8)
            for tag in tags[:12]:
                count = sum(1 for p in phrases if tag in p.get("tags", []))
                chip = TagChip(f"{tag} ({count})")
                tags_flow.addWidget(chip)
            tags_flow.addStretch()
            tag_lo.addWidget(tags_container)

            self.layout.addWidget(tag_card)

        # ── 数据导出 ──
        export_card = Card()
        exp_lo = QHBoxLayout(export_card)
        exp_lo.setSpacing(16)
        exp_label = QLabel("数据导出")
        exp_label.setStyleSheet(f"font-size: {T.H3}px; font-weight: 700; color: {T.TEXT}; background: transparent; border: none;")
        exp_lo.addWidget(exp_label)
        exp_lo.addSpacing(20)

        export_json_btn = GhostBtn("导出 JSON")
        export_json_btn.clicked.connect(self._export_json)
        exp_lo.addWidget(export_json_btn)

        export_csv_btn = GhostBtn("导出 CSV")
        export_csv_btn.clicked.connect(self._export_csv)
        exp_lo.addWidget(export_csv_btn)

        exp_lo.addStretch()
        self.layout.addWidget(export_card)

        self.layout.addStretch()

    def _get_weekly_data(self):
        """构建近7天数据"""
        stats = get_daily_stats()
        result = []
        today = date.today()
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            key = d.isoformat()
            day_stats = stats.get(key, {})
            result.append({
                "label": f"{d.month}/{d.day}",
                "added": day_stats.get("phrases_added", 0),
                "reviewed": day_stats.get("phrases_reviewed", 0),
            })
        return result

    def _export_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出 JSON", "phrases.json", "JSON (*.json)")
        if path:
            export_json(path)
            self.mw.toast(f"已导出到 {path}")

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出 CSV", "phrases.csv", "CSV (*.csv)")
        if path:
            export_csv(path)
            self.mw.toast(f"已导出到 {path}")
