"""
「词芽」主窗口
QStackedWidget + 底部导航 + 主题切换 + 动画
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QPushButton,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont, QPalette

from config import T, THEMES, get_current_theme, apply_theme, qss
from widgets.base import NavBtn, GoldBtn, _FadeWidget, _clear_layout
from data_manager import save_settings, get_settings, sync_to_first_step


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("词芽 · WordSprout")
        self.resize(1080, 820)

        # 防白屏：设置背景色
        pal = self.palette()
        pal.setColor(pal.ColorRole.Window, QColor(T.BG))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

        # 主题脏标记
        self._theme_dirty = set()

        # ===== 中央组件 =====
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== 页面栈 =====
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 1)

        # ===== 页面占位（延迟创建避免循环导入） =====
        self.pages = [None] * 6  # 0:仪表盘 1:词库 2:复习 3:对话 4:统计 5:录入
        for i in range(6):
            placeholder = QWidget()
            placeholder.setStyleSheet(f"background: {T.BG};")
            self.stack.addWidget(placeholder)

        # ===== 底部导航栏 =====
        self.nav_bar = QWidget()
        self.nav_bar.setFixedHeight(110)
        self.nav_bar.setStyleSheet(f"""
            QWidget {{
                background: rgba({QColor(T.CARD).red()},{QColor(T.CARD).green()},{QColor(T.CARD).blue()},0.95);
                border-top: 1px solid {T.DIVIDER};
            }}
        """)
        nav_layout = QHBoxLayout(self.nav_bar)
        nav_layout.setContentsMargins(16, 4, 16, 8)
        nav_layout.setSpacing(4)

        # 占位弹簧
        nav_layout.addStretch(1)

        # 5个导航按钮
        self.nav_btns = []
        nav_defs = [
            ("📋", "今日"),
            ("📖", "词库"),
            ("🔄", "复习"),
            ("💬", "对话"),
            ("📊", "统计"),
        ]
        for icon, label in nav_defs:
            btn = NavBtn(icon, label)
            btn.clicked.connect(lambda checked, i=len(self.nav_btns): self.on_nav(i))
            nav_layout.addWidget(btn)
            self.nav_btns.append(btn)

        nav_layout.addStretch(1)

        # 主题切换按钮
        self.theme_btn = QPushButton("🎨")
        self.theme_btn.setFixedSize(48, 48)
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T.ELEVATED};
                border: 1px solid {T.DIVIDER};
                border-radius: 24px;
                font-size: 20px;
            }}
            QPushButton:hover {{
                background: {T.DIVIDER};
            }}
        """)
        self.theme_btn.clicked.connect(self.cycle_theme)
        nav_layout.addWidget(self.theme_btn)
        nav_layout.addStretch(1)

        main_layout.addWidget(self.nav_bar)

        # ===== 全局样式 =====
        self.setStyleSheet(qss())

        # ===== 初始化第一个页面 =====
        self.on_nav(0)

    # ============================================================
    # 页面导航
    # ============================================================

    def on_nav(self, idx):
        """导航按钮点击处理"""
        self.nav_bar.show()
        self.show_page(idx)

    def show_page(self, idx):
        """切换到指定页面（带动画）"""
        # 懒加载页面
        self._ensure_page(idx)

        # 主题变更后重建
        if idx in self._theme_dirty:
            page = self.stack.widget(idx)
            if page and hasattr(page, 'build'):
                page.build()
            self._theme_dirty.discard(idx)

        if self.stack.currentIndex() != idx:
            overlay = _FadeWidget(self, QColor(T.BG))
            overlay.setGeometry(self.stack.geometry())
            overlay.show()
            overlay.raise_()
            self.stack.setCurrentIndex(idx)
            overlay.fade_out()

        # 高亮当前导航按钮
        for i, btn in enumerate(self.nav_btns):
            btn.setChecked(i == idx)

    def _ensure_page(self, idx):
        """确保页面已创建（懒加载）"""
        if self.pages[idx] is not None:
            return

        if idx == 0:
            from pages.dashboard_page import DashboardPage
            page = DashboardPage(self)
        elif idx == 1:
            from pages.browse_page import BrowsePage
            page = BrowsePage(self)
        elif idx == 2:
            from pages.review_page import ReviewPage
            page = ReviewPage(self)
        elif idx == 3:
            from pages.dialogue_page import DialoguePage
            page = DialoguePage(self)
        elif idx == 4:
            from pages.stats_page import StatsPage
            page = StatsPage(self)
        elif idx == 5:
            from pages.add_phrase_page import AddPhrasePage
            page = AddPhrasePage(self)

        self.pages[idx] = page
        # 替换占位符
        old = self.stack.widget(idx)
        self.stack.removeWidget(old)
        if old:
            old.deleteLater()
        self.stack.insertWidget(idx, page)

    # ============================================================
    # 主题切换
    # ============================================================

    def cycle_theme(self):
        """循环切换主题"""
        names = list(THEMES.keys())
        cur = get_current_theme()
        next_idx = (names.index(cur) + 1) % len(names)
        next_name = names[next_idx]

        apply_theme(next_name)
        self.setStyleSheet(qss())

        # 更新导航栏
        self.nav_bar.setStyleSheet(f"""
            QWidget {{
                background: rgba({QColor(T.CARD).red()},{QColor(T.CARD).green()},{QColor(T.CARD).blue()},0.95);
                border-top: 1px solid {T.DIVIDER};
            }}
        """)
        self.theme_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T.ELEVATED};
                border: 1px solid {T.DIVIDER};
                border-radius: 24px;
                font-size: 20px;
            }}
            QPushButton:hover {{
                background: {T.DIVIDER};
            }}
        """)

        # 标记所有已加载页面需要重建
        for i, p in enumerate(self.pages):
            if p is not None:
                self._theme_dirty.add(i)

        # 更新导航按钮样式
        for btn in self.nav_btns:
            btn.refresh_style()

        # 保存设置
        settings = get_settings()
        settings["theme"] = next_name
        save_settings(settings)

        # 重建当前页面
        cur_idx = self.stack.currentIndex()
        if cur_idx in self._theme_dirty:
            page = self.stack.widget(cur_idx)
            if page and hasattr(page, 'build'):
                page.build()
            self._theme_dirty.discard(cur_idx)

    # ============================================================
    # Toast 通知
    # ============================================================

    def toast(self, message, duration=2000):
        t = QLabel(message, self)
        t.setStyleSheet(f"""
            QLabel {{
                background: {T.TEXT};
                color: {T.BG};
                padding: 14px 28px;
                border-radius: 50px;
                font-size: {T.CAPTION}px;
                font-weight: 600;
            }}
        """)
        t.adjustSize()
        t.move(
            (self.width() - t.width()) // 2,
            self.height() - 160,
        )
        t.show()
        t.raise_()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(duration, t.deleteLater)

    # ============================================================
    # 打开录入页面
    # ============================================================

    def open_add_phrase(self):
        self.show_page(5)

    def go_to_review(self):
        self.on_nav(2)

    def go_to_dialogue(self, phrase_ids=None):
        """打开对话页面，可选预选词组"""
        self.on_nav(3)
        if phrase_ids and self.pages[3]:
            self.pages[3].pre_select_phrases(phrase_ids)

    # ============================================================
    # 生命周期
    # ============================================================

    def closeEvent(self, e):
        """关闭时同步数据到第一步"""
        try:
            sync_to_first_step()
        except Exception:
            pass
        super().closeEvent(e)
