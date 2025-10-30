from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QPainter
from .config import ACCEL, MAX_SPEED, TICK_HZ, GRAVITY, JUMP_SPEED
from .entities import Player


class GameCanvas(QWidget):
    def __init__(self, parent=None, with_gravity=True):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
        self.keys = set()
        self.dt = 1.0 / TICK_HZ
        self.with_gravity = with_gravity

        self.player = Player()
        self.player.load_sprites()
        self._platform_rect = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(int(1000 / TICK_HZ))

    def keyPressEvent(self, e):
        self.keys.add(e.key())

    def keyReleaseEvent(self, e):
        self.keys.discard(e.key())

    def mousePressEvent(self, event):
        """Перехватываем фокус при клике по игровому окну."""
        self.setFocus()
        super().mousePressEvent(event)

    def _tick(self):
        p = self.player
        ax = 0.0

        moving = False
        if Qt.Key_A in self.keys or Qt.Key_Left in self.keys:
            ax -= ACCEL
            moving = True
        if Qt.Key_D in self.keys or Qt.Key_Right in self.keys:
            ax += ACCEL
            moving = True

        # Замедление при отпускании
        if not moving:
            if abs(p.vx) < 20:
                p.vx = 0
            else:
                p.vx *= 0.85

        # Применяем горизонтальное ускорение к скорости
        p.vx += ax * self.dt

        if self.with_gravity:
            # Прыжок
            if (
                Qt.Key_Space in self.keys
                or Qt.Key_W in self.keys
                or Qt.Key_Up in self.keys
            ) and p.grounded:
                p.vy = -JUMP_SPEED
                p.grounded = False

            p.vy += GRAVITY * self.dt

            p.x += p.vx * self.dt
            p.y += p.vy * self.dt

            W = self.width()
            if p.x < 0:
                p.x, p.vx = 0, 0
            if p.x + p.w > W:
                p.x, p.vx = W - p.w, 0

            # Проверка столкновений с платформой
            self._ensure_platform()
            x, y, w, h = self._platform_rect
            ground_y = y - p.h

            if p.vy >= 0 and (p.x + p.w > x) and (p.x < x + w) and (p.y + p.h >= y):
                p.y = ground_y
                p.vy = 0
                p.grounded = True

            # Пол внизу
            H = self.height()
            if p.y + p.h >= H:
                p.y = H - p.h
                p.vy = 0
                p.grounded = True
        else:
            p.x += p.vx * self.dt

        # Ограничиваем скорость
        if p.vx > MAX_SPEED:
            p.vx = MAX_SPEED
        if p.vx < -MAX_SPEED:
            p.vx = -MAX_SPEED

        self.update()

    def _ensure_platform(self):
        """Создает плоскую платформу внизу экрана."""
        if self._platform_rect is None:
            W, H = self.width(), self.height()
            pw = int(W * 0.7)
            ph = max(12, int(H * 0.04))
            px = (W - pw) // 2
            py = H - ph - 10
            self._platform_rect = (px, py, pw, ph)

    def paintEvent(self, _):
        qp = QPainter(self)

        # Отрисовка платформы
        if self.with_gravity:
            self._ensure_platform()
            x, y, w, h = self._platform_rect
            qp.fillRect(QRectF(x, y, w, h), Qt.gray)

        # Спрайт персонажа
        pm = self._select_sprite()
        if pm:
            vx = self.player.vx
            x = int(self.player.x)
            y = int(self.player.y)
            if vx < -30:
                qp.save()
                qp.translate(x + pm.width(), y)
                qp.scale(-1, 1)
                qp.drawPixmap(0, 0, pm)
                qp.restore()
            else:
                qp.drawPixmap(x, y, pm)
        else:
            qp.fillRect(
                QRectF(self.player.x, self.player.y, self.player.w, self.player.h),
                Qt.darkCyan,
            )

    def _select_sprite(self):
        p = self.player
        if not self.with_gravity:
            return p.sprite_for("run") if abs(p.vx) > 30 else p.sprite_for("idle")

        if not p.grounded:
            if p.vy < 0:
                return p.sprite_for("jump_up") or p.sprite_for("jump_start")
            else:
                return p.sprite_for("jump_fall")
        else:
            return p.sprite_for("run") if abs(p.vx) > 30 else p.sprite_for("idle")
