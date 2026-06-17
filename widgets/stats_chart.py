"""
「词芽」统计图表组件
柱状图 + 环形图
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient

from config import T


class BarChart(QWidget):
    """简易柱状图，用于近7天统计"""

    def __init__(self, data, parent=None):
        """
        data: [{"label": "6/11", "added": 3, "reviewed": 8}, ...]
        """
        super().__init__(parent)
        self._data = data
        self.setMinimumHeight(200)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        if not self._data:
            p.end()
            return

        # 找出最大值
        max_val = max(max(d.get("added", 0), d.get("reviewed", 0)) for d in self._data)
        max_val = max(max_val, 1)

        bar_count = len(self._data)
        bar_w = (w - 80) / (bar_count * 2 + bar_count * 0.5)
        gap = bar_w * 0.5
        left_margin = 60
        bottom_margin = 40
        chart_h = h - bottom_margin - 10

        for i, d in enumerate(self._data):
            x_base = left_margin + i * (bar_w * 2 + gap + bar_w * 0.5)

            # added 柱子
            added_h = (d.get("added", 0) / max_val) * chart_h
            added_rect = QRectF(x_base, h - bottom_margin - added_h, bar_w, added_h)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(T.GOLD))
            p.drawRoundedRect(added_rect, 4, 4)

            # reviewed 柱子
            review_h = (d.get("reviewed", 0) / max_val) * chart_h
            review_rect = QRectF(x_base + bar_w + 4, h - bottom_margin - review_h, bar_w, review_h)
            p.setBrush(QColor(T.SAGE))
            p.drawRoundedRect(review_rect, 4, 4)

            # 标签
            p.setPen(QColor(T.TEXT_MUTED))
            font = QFont(T.FONT_BODY, 11)
            p.setFont(font)
            label_w = bar_w * 2 + 4
            p.drawText(
                QRectF(x_base, h - bottom_margin + 4, label_w, 20),
                Qt.AlignHCenter | Qt.AlignTop,
                d["label"]
            )

        # 图例
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T.GOLD))
        p.drawRoundedRect(QRectF(w - 180, 8, 14, 14), 3, 3)
        p.setPen(QColor(T.TEXT_DIM))
        p.drawText(QRectF(w - 162, 6, 50, 18), Qt.AlignVCenter, "录入")

        p.setBrush(QColor(T.SAGE))
        p.drawRoundedRect(QRectF(w - 100, 8, 14, 14), 3, 3)
        p.setPen(QColor(T.TEXT_DIM))
        p.drawText(QRectF(w - 82, 6, 50, 18), Qt.AlignVCenter, "复习")

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
