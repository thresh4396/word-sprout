"""
「词芽」共享组件库
从第一步复用并适配：Card, GoldBtn, GhostBtn, NavBtn, _FadeWidget, _clear_layout
新增：TagChip, PhraseRow
"""

from PySide6.QtWidgets import (
    QFrame, QPushButton, QWidget, QLabel, QHBoxLayout, QVBoxLayout,
    QLayout, QSpacerItem, QSizePolicy, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, Signal, Property, QEasingCurve, QPropertyAnimation
from PySide6.QtGui import QPainter, QColor, QFont, QCursor

from config import T


# ============================================================
# 工具函数
# ============================================================

def _clear_layout(lo):
    """递归清空 layout 中所有子 widget 和子 layout"""
    if lo is None:
        return
    while lo.count():
        item = lo.takeAt(0)
        w = item.widget()
        if w is not None:
            w.hide()
            w.deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())


# ============================================================
# 页面切换动画遮罩
# ============================================================

class _FadeWidget(QWidget):
    """纯 paintEvent 实现淡入淡出遮罩"""

    def __init__(self, parent, color):
        super().__init__(parent)
        self._color = QColor(color)
        self._alpha = 255
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def setAlpha(self, a):
        self._alpha = max(0, min(255, a))
        self.update()

    alpha = Property(int, lambda s: s._alpha, setAlpha)

    def fade_out(self):
        self._anim = QPropertyAnimation(self, b"alpha")
        self._anim.setDuration(150)
        self._anim.setStartValue(220)
        self._anim.setEndValue(0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self.deleteLater)
        self._anim.start()

    def paintEvent(self, e):
        p = QPainter(self)
        c = QColor(self._color)
        c.setAlpha(self._alpha)
        p.fillRect(self.rect(), c)


# ============================================================
# 基础组件
# ============================================================

class Card(QFrame):
    """圆角卡片容器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(f"""
            QFrame#card {{
                background: {T.CARD};
                border: 1px solid {T.DIVIDER};
                border-radius: {T.RADIUS_LG}px;
                padding: {T.CARD_PAD}px;
            }}
        """)


class GoldBtn(QPushButton):
    """主操作按钮（主题色填充）"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(52)
        self._update_style()

    def _update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background: {T.GOLD};
                color: #fff;
                border: none;
                border-radius: 50px;
                padding: 14px 36px;
                font-size: {T.BTN_FONT}px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {T.GOLD_DIM};
            }}
            QPushButton:pressed {{
                opacity: 0.85;
            }}
            QPushButton:disabled {{
                background: {T.DIVIDER};
                color: {T.TEXT_MUTED};
            }}
        """)


class GhostBtn(QPushButton):
    """次要按钮（透明底 + 主题色边框）"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(48)
        self._update_style()

    def _update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {T.GOLD};
                border: 2px solid {T.GOLD};
                border-radius: 50px;
                padding: 12px 32px;
                font-size: {T.BTN_FONT_SMALL}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: rgba({QColor(T.GOLD).red()},{QColor(T.GOLD).green()},{QColor(T.GOLD).blue()},0.10);
            }}
            QPushButton:pressed {{
                background: rgba({QColor(T.GOLD).red()},{QColor(T.GOLD).green()},{QColor(T.GOLD).blue()},0.20);
            }}
        """)


class NavBtn(QPushButton):
    """底部导航按钮"""

    def __init__(self, icon, label, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(140, 82)
        self.setCursor(Qt.PointingHandCursor)
        self._icon = icon
        self._label = label
        self.setText(f"{icon}\n{label}")
        self._update_style()

    def _update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {T.TEXT_MUTED};
                border: none;
                border-radius: {T.RADIUS}px;
                font-size: {T.CAPTION}px;
                font-weight: 500;
                padding: 8px;
            }}
            QPushButton:hover {{
                color: {T.TEXT_DIM};
                background: rgba({QColor(T.GOLD).red()},{QColor(T.GOLD).green()},{QColor(T.GOLD).blue()},0.06);
            }}
            QPushButton:checked {{
                color: {T.GOLD};
                font-weight: 700;
            }}
        """)

    def refresh_style(self):
        self._update_style()


# ============================================================
# 标签胶囊
# ============================================================

class TagChip(QLabel):
    """小圆角标签，用于显示和筛选"""

    def __init__(self, text, active=False, parent=None):
        super().__init__(text, parent)
        self._active = active
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(32)
        self.update_style()

    def update_style(self):
        if self._active:
            bg = T.GOLD
            fg = "#fff"
        else:
            bg = T.TAG_BG
            fg = T.TAG_TEXT
        self.setStyleSheet(f"""
            QLabel {{
                background: {bg};
                color: {fg};
                border: none;
                border-radius: 16px;
                padding: 4px 14px;
                font-size: {T.CAPTION}px;
                font-weight: 500;
            }}
        """)

    def set_active(self, active):
        self._active = active
        self.update_style()

    @property
    def active(self):
        return self._active


# ============================================================
# 词组行组件
# ============================================================

class PhraseRow(QFrame):
    """词库列表中的一行词组"""

    toggled = Signal(bool)  # 勾选/取消勾选
    edit_requested = Signal(str)    # 请求编辑 → 传 phrase_id
    delete_requested = Signal(str)  # 请求删除 → 传 phrase_id

    def __init__(self, phrase_data, show_checkbox=False, parent=None):
        super().__init__(parent)
        self.data = phrase_data
        self._checked = False
        self._show_checkbox = show_checkbox
        self.setCursor(Qt.PointingHandCursor)
        self._build()

    def _build(self):
        if self.layout():
            _clear_layout(self.layout())
        else:
            lo = QHBoxLayout(self)
            lo.setContentsMargins(20, 14, 20, 14)
            lo.setSpacing(14)

        # 勾选框（可选）
        if self._show_checkbox:
            from PySide6.QtWidgets import QCheckBox
            self.cb = QCheckBox()
            self.cb.setChecked(self._checked)
            self.cb.toggled.connect(lambda v: self.toggled.emit(v))
            self.cb.toggled.connect(lambda v: setattr(self, '_checked', v))
            self.layout().addWidget(self.cb)

        # 词组英文
        phrase_label = QLabel(self.data["phrase"])
        phrase_label.setStyleSheet(f"""
            font-size: {T.H3}px; font-weight: 700; color: {T.TEXT};
            background: transparent; border: none;
        """)
        phrase_label.setFixedWidth(280)

        # 中文释义
        meaning_label = QLabel(self.data["meaning"])
        meaning_label.setStyleSheet(f"""
            font-size: {T.BODY}px; color: {T.TEXT_DIM};
            background: transparent; border: none;
        """)
        meaning_label.setWordWrap(True)

        # 标签
        tags_widget = QWidget()
        tags_lo = QHBoxLayout(tags_widget)
        tags_lo.setContentsMargins(0, 0, 0, 0)
        tags_lo.setSpacing(6)
        for tag in self.data.get("tags", [])[:3]:
            chip = TagChip(tag)
            tags_lo.addWidget(chip)
        tags_lo.addStretch()

        # 状态指示
        if self.data.get("mastered"):
            status = QLabel("✓")
            status.setStyleSheet(f"color: {T.GOLD}; font-size: 18px; font-weight: bold;")
        else:
            status = QLabel("")

        self.layout().addWidget(phrase_label)
        self.layout().addWidget(meaning_label, 1)
        self.layout().addWidget(tags_widget)
        self.layout().addWidget(status)

        # ---- 编辑 / 删除按钮 ----
        btn_style = f"""
            QPushButton {{
                background: transparent; border: 1px solid {T.DIVIDER};
                border-radius: 14px; font-size: 14px;
                min-width: 28px; max-width: 28px;
                min-height: 28px; max-height: 28px;
            }}
            QPushButton:hover {{
                background: {T.ELEVATED}; border-color: {T.GOLD};
            }}
        """

        edit_btn = QPushButton("✏️")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet(btn_style)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.data["id"]))
        self.layout().addWidget(edit_btn)

        del_btn = QPushButton("🗑️")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet(btn_style)
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.data["id"]))
        self.layout().addWidget(del_btn)

        self._update_bg()

    def _update_bg(self):
        border_color = T.GOLD if self._checked else T.DIVIDER
        self.setStyleSheet(f"""
            PhraseRow {{
                background: {T.CARD};
                border: 1px solid {border_color};
                border-radius: {T.RADIUS}px;
            }}
            PhraseRow:hover {{
                background: {T.ELEVATED};
            }}
        """)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self._show_checkbox:
            self._checked = not self._checked
            if hasattr(self, 'cb'):
                self.cb.setChecked(self._checked)
            self.toggled.emit(self._checked)
            self._update_bg()
        super().mousePressEvent(e)

    @property
    def checked(self):
        return self._checked


# ============================================================
# 统计用环形进度
# ============================================================

class RingProgress(QWidget):
    """环形进度条，用于统计页面展示掌握率等"""

    def __init__(self, parent=None, size=160, thickness=12):
        super().__init__(parent)
        self._progress = 0.0  # 0.0 ~ 1.0
        self._size = size
        self._thickness = thickness
        self.setFixedSize(size, size)

    def setProgress(self, v):
        self._progress = max(0.0, min(1.0, v))
        self.update()

    progress = Property(float, lambda s: s._progress, setProgress)

    def paintEvent(self, e):
        from PySide6.QtCore import QRectF, QPointF
        from PySide6.QtGui import QPen, QConicalGradient

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        cx, cy = self._size / 2, self._size / 2
        r = (self._size - self._thickness) / 2
        rect = QRectF(cx - r, cy - r, r * 2, r * 2)

        # 背景环
        p.setPen(QPen(QColor(T.DIVIDER), self._thickness, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawArc(rect, 90 * 16, 360 * 16)

        if self._progress <= 0:
            p.end()
            return

        # 进度渐变环
        grad = QConicalGradient(cx, cy, 90)
        grad.setColorAt(0, QColor(T.GOLD))
        grad.setColorAt(0.5, QColor(T.SAGE))
        grad.setColorAt(1, QColor(T.GOLD))
        p.setPen(QPen(grad, self._thickness, Qt.SolidLine, Qt.RoundCap))
        span = int(-360 * self._progress * 16)
        p.drawArc(rect, 90 * 16, span)

        # 中心百分比
        p.setPen(QColor(T.TEXT))
        font = QFont(T.FONT_DISPLAY, 28, QFont.Bold)
        p.setFont(font)
        pct = f"{int(self._progress * 100)}%"
        p.drawText(self.rect(), Qt.AlignCenter, pct)

        p.end()
