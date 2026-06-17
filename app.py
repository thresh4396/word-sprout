"""
「词芽」WordSprout — 英语词组积累与复习
"""

import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QPalette, QColor

from config import T, apply_theme, get_current_theme
from data_manager import get_settings

# 确保 project 根目录在 path 中（PyInstaller 兼容）
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("词芽")
    app.setApplicationDisplayName("词芽 · WordSprout")

    # 全局字体
    font = QFont(T.FONT_BODY, T.BASE_FONT)
    app.setFont(font)

    # 加载设置中的主题
    settings = get_settings()
    saved_theme = settings.get("theme", "薄荷")
    apply_theme(saved_theme)

    # 延迟导入，避免循环依赖
    from main_window import MainWindow
    win = MainWindow()
    win.show()

    # 先让 Qt 处理一次事件循环，确保窗口真正渲染出来
    app.processEvents()

    # ---- 强制将窗口弹到最前端（Win32 API） ----
    import ctypes

    hwnd = int(win.winId())

    # 先确保窗口不是最小化状态
    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE

    # 尝试 AttachThreadInput 绕过 Windows 前台焦点锁定
    foreground = ctypes.windll.user32.GetForegroundWindow()
    cur_thread = ctypes.windll.kernel32.GetCurrentThreadId()
    fg_thread = ctypes.windll.user32.GetWindowThreadProcessId(foreground, None)

    if cur_thread != fg_thread:
        ctypes.windll.user32.AttachThreadInput(cur_thread, fg_thread, True)

    ctypes.windll.user32.SetForegroundWindow(hwnd)
    ctypes.windll.user32.BringWindowToTop(hwnd)

    if cur_thread != fg_thread:
        ctypes.windll.user32.AttachThreadInput(cur_thread, fg_thread, False)

    # 兜底：Qt 层面再激活一次
    win.raise_()
    win.activateWindow()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
