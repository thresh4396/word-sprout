"""
「词芽」统计图表组件
柱状图 + 环形图
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient

from config import T


class BarChart(QWidget):
    """柱状图，用于近7天统计（录入 + 复习双柱）"""

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self._data = data
        self.setMinimumHeight(280)
        self.setStyleSheet(f"background: transparent;")

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        if not self._data:
            p.end()
            return

        bar_count = len(self._data)
        padding_top = 30      # 顶部留白
        padding_bottom = 56   # 底部留白给日期标签
        left_margin = 52
        right_margin = 32
        chart_w = w - left_margin - right_margin
        chart_h = h - padding_top - padding_bottom

        max_val = max(max(d.get("added", 0), d.get("reviewed", 0)) for d in self._data)
        max_val = max(max_val, 1)

        # 竖线刻度背景
        p.setPen(QPen(QColor(T.DIVIDER), 1, Qt.DashLine))
        for i in range(5):
            y = padding_top + chart_h * i / 4
            p.drawLine(QPointF(left_margin, y), QPointF(w - right_margin, y))

        # 每组两柱，柱间留足间距
        group_w = chart_w / bar_count        # 每组占宽
        bar_w = group_w * 0.22               # 单柱宽度（更细）
        pair_gap = group_w * 0.16            # 录入/复习两柱间距（更宽）

        for i, d in enumerate(self._data):
            group_center = left_margin + group_w * i + group_w / 2
            bar1_x = group_center - bar_w - pair_gap / 2
            bar2_x = group_center + pair_gap / 2

            # 录入柱（金色）
            added_val = d.get("added", 0)
            added_h = (added_val / max_val) * chart_h if added_val > 0 else 0
            if added_h > 0:
                added_rect = QRectF(bar1_x, padding_top + chart_h - added_h, bar_w, added_h)
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(T.GOLD))
                p.drawRoundedRect(added_rect, 5, 5)

            # 复习柱（蓝色，与金色形成对比）
            review_val = d.get("reviewed", 0)
            review_h = (review_val / max_val) * chart_h if review_val > 0 else 0
            if review_h > 0:
                review_rect = QRectF(bar2_x, padding_top + chart_h - review_h, bar_w, review_h)
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#5b9ec4"))
                p.drawRoundedRect(review_rect, 5, 5)

            # 日期标签
            p.setPen(QColor(T.TEXT_MUTED))
            font = QFont(T.FONT_BODY, 11)
            p.setFont(font)
            label_rect = QRectF(group_center - group_w * 0.45, h - padding_bottom + 8, group_w * 0.9, 20)
            p.drawText(label_rect, Qt.AlignHCenter | Qt.AlignTop, d["label"])

        # 图例（右上角，更紧凑）
        legend_y = 8
        legend_font = QFont(T.FONT_BODY, 12)
        p.setFont(legend_font)

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T.GOLD))
        p.drawRoundedRect(QRectF(w - 165, legend_y, 12, 12), 3, 3)
        p.setPen(QColor(T.TEXT_DIM))
        p.drawText(QRectF(w - 149, legend_y - 2, 36, 16), Qt.AlignVCenter, "录入")

        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#5b9ec4"))
        p.drawRoundedRect(QRectF(w - 92, legend_y, 12, 12), 3, 3)
        p.setPen(QColor(T.TEXT_DIM))
        p.drawText(QRectF(w - 76, legend_y - 2, 36, 16), Qt.AlignVCenter, "复习")

        p.end()


class WeeklyChart(QWidget):
    """封装标题 + BarChart 的完整组件"""

    def __init__(self, data, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(8)

        title = QLabel("近 7 天学习统计")
        title.setStyleSheet(f"font-size: {T.H3}px; font-weight: 700; color: {T.TEXT}; background: transparent; border: none;")
        lo.addWidget(title)

        self.chart = BarChart(data)
        lo.addWidget(self.chart)
