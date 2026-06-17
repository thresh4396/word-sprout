"""生成「词芽」应用图标 — 简约精致风格"""
import os, sys, math
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import (
    QPainter, QPixmap, QColor, QPen, QBrush, QFont,
    QRadialGradient, QConicalGradient, QPainterPath, QPolygonF,
)
from PySide6.QtCore import Qt, QPointF, QRectF

app = QApplication(sys.argv)

dir_path = os.path.dirname(os.path.abspath(__file__))
size = 256
pix = QPixmap(size, size)
pix.fill(Qt.transparent)

p = QPainter(pix)
p.setRenderHint(QPainter.Antialiasing)

cx, cy = size / 2, size / 2

# ===== 1. 柔光底圆 =====
for i in range(4):
    alpha = 40 - i * 10
    r_glow = 118 + i * 6
    glow = QRadialGradient(cx, cy, r_glow)
    glow.setColorAt(0, QColor(46, 204, 113, alpha))
    glow.setColorAt(1, QColor(46, 204, 113, 0))
    p.setBrush(QBrush(glow))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(cx, cy), r_glow, r_glow)

# ===== 2. 主体圆 =====
bg_grad = QRadialGradient(cx - 15, cy - 20, 120)
bg_grad.setColorAt(0, QColor("#5fe88a"))
bg_grad.setColorAt(0.5, QColor("#2ecc71"))
bg_grad.setColorAt(1, QColor("#1a8a40"))
p.setBrush(QBrush(bg_grad))
p.setPen(Qt.NoPen)
p.drawEllipse(QPointF(cx, cy), 108, 108)

# ===== 3. 金色外弧 =====
ring_grad = QConicalGradient(cx, cy, -90)
ring_grad.setColorAt(0.0, QColor("#f0d080"))
ring_grad.setColorAt(0.3, QColor("#f5e0a0"))
ring_grad.setColorAt(0.5, QColor("#e8a817"))
ring_grad.setColorAt(0.7, QColor("#f5e0a0"))
ring_grad.setColorAt(1.0, QColor("#f0d080"))
pen = QPen(QBrush(ring_grad), 7, Qt.SolidLine, Qt.RoundCap)
p.setPen(pen)
p.setBrush(Qt.NoBrush)
p.drawArc(QRectF(14, 14, 228, 228), 100 * 16, -310 * 16)

# ===== 4. 中心书页/嫩芽图形 =====
# 画一个打开的书的轮廓 + 中间长出的嫩芽

# 书页左半
p.setPen(Qt.NoPen)
p.setBrush(QColor(255, 255, 255, 230))
left_page = QPainterPath()
left_page.moveTo(cx - 2, cy - 55)
left_page.quadTo(cx - 55, cy - 45, cx - 62, cy - 10)
left_page.quadTo(cx - 55, cy + 25, cx - 2, cy + 45)
left_page.quadTo(cx - 20, cy + 20, cx - 20, cy - 20)
left_page.quadTo(cx - 20, cy - 30, cx - 2, cy - 55)
p.drawPath(left_page)

# 书页右半
right_page = QPainterPath()
right_page.moveTo(cx + 2, cy - 55)
right_page.quadTo(cx + 55, cy - 45, cx + 62, cy - 10)
right_page.quadTo(cx + 55, cy + 25, cx + 2, cy + 45)
right_page.quadTo(cx + 20, cy + 20, cx + 20, cy - 20)
right_page.quadTo(cx + 20, cy - 30, cx + 2, cy - 55)
p.drawPath(right_page)

# 书脊
p.setPen(QPen(QColor(255, 255, 255, 180), 2))
p.drawLine(QPointF(cx, cy - 56), QPointF(cx, cy + 46))

# ===== 5. 嫩芽（从书中长出）=====
# 茎
stem_color = QColor("#f0d080")
p.setPen(QPen(stem_color, 5, Qt.SolidLine, Qt.RoundCap))
p.drawLine(QPointF(cx, cy - 35), QPointF(cx, cy - 75))

# 左叶
leaf_path = QPainterPath()
leaf_path.moveTo(cx, cy - 60)
leaf_path.quadTo(cx - 30, cy - 70, cx - 22, cy - 95)
leaf_path.quadTo(cx - 5, cy - 85, cx, cy - 60)
p.setPen(Qt.NoPen)
p.setBrush(QColor("#f0d080"))
p.drawPath(leaf_path)

# 右叶
leaf_path2 = QPainterPath()
leaf_path2.moveTo(cx, cy - 68)
leaf_path2.quadTo(cx + 28, cy - 75, cx + 24, cy - 98)
leaf_path2.quadTo(cx + 6, cy - 88, cx, cy - 68)
p.drawPath(leaf_path2)

# 叶尖亮点
p.setPen(QPen(QColor("#fef9e7"), 2, Qt.SolidLine, Qt.RoundCap))
p.drawLine(QPointF(cx - 12, cy - 78), QPointF(cx - 18, cy - 90))
p.drawLine(QPointF(cx + 14, cy - 82), QPointF(cx + 20, cy - 92))

# ===== 6. 顶部小星光 =====
star_color = QColor("#f5e0a0")
for angle_deg, dist in [(300, 92), (340, 96), (20, 93), (55, 90)]:
    rad = math.radians(angle_deg)
    sx = cx + math.cos(rad) * dist
    sy = cy - math.sin(rad) * dist  # 屏幕坐标 Y 轴反转
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(245, 224, 160, 160))
    p.drawEllipse(QPointF(sx, sy), 3, 3)

p.end()

# 保存 ico
icon_path = os.path.join(dir_path, "app.ico")
pix.save(icon_path, "ICO")
print(f"Icon saved: {icon_path}")

# 同时保存 png 方便预览
png_path = os.path.join(dir_path, "app.png")
pix.save(png_path, "PNG")
print(f"PNG preview: {png_path}")
