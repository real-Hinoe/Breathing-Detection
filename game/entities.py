from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import pygame

# Путь к папке ресурсов
RES = (Path(__file__).resolve().parents[1] / "resources").resolve()

# Список спрайтов персонажа
SPRITE_FILES = {
    "idle": "staying2.2.png",
    "run": "running.png",
    "jump_start": "jump_start.png",
    "jump_up": "jump_up.png",
    "jump_fall": "jump_fall.png",
    "jump_land": "jump_land.png",
}

TARGET_MAX_HEIGHT = 160  # Ограничиваем высоту спрайтов


@dataclass
class Player:
    x: float = 100.0
    y: float = 100.0
    vx: float = 0.0
    vy: float = 0.0
    w: int = 48
    h: int = 48
    grounded: bool = False
    sprites: Dict[str, QPixmap] = None
    facing: int = 1

    def load_sprites(self):
        self.sprites = {}
        for key, fname in SPRITE_FILES.items():
            path = RES / fname
            if path.exists():
                pix = QPixmap(str(path))
                if not pix.isNull():
                    if TARGET_MAX_HEIGHT and pix.height() > TARGET_MAX_HEIGHT:
                        pix = pix.scaled(
                            int(pix.width() * TARGET_MAX_HEIGHT / pix.height()),
                            TARGET_MAX_HEIGHT,
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation,
                        )
                    self.sprites[key] = pix
        idle = self.sprites.get("idle")
        if idle:
            self.w, self.h = idle.width(), idle.height()

    def sprite_for(self, state: Optional[str] = None) -> Optional[QPixmap]:
        if not self.sprites:
            return None
        if state and state in self.sprites:
            return self.sprites[state]
        return self.sprites.get("idle")


@dataclass
class Platform:
    """Класс для платформ с дополнительной информацией для физики"""
    rect: pygame.Rect
    type: str = "normal"
    vx: float = 0.0
    vy: float = 0.0
    range_x: float = 0.0
    range_y: float = 0.0
    start_x: float = 0.0
    start_y: float = 0.0
    timer: float = 0.0
    is_active: bool = True
    is_slope: bool = False  # Наклонная платформа
    slope_angle: float = 0.0  # Угол наклона в градусах

    def update(self, dt: float):
        if self.type == "moving":
            # Движение по X
            if self.range_x > 0:
                self.rect.x += self.vx * dt
                if abs(self.rect.x - self.start_x) >= self.range_x:
                    self.vx *= -1
            # Движение по Y
            if self.range_y > 0:
                self.rect.y += self.vy * dt
                if abs(self.rect.y - self.start_y) >= self.range_y:
                    self.vy *= -1

        if self.type == "fragile" and self.timer > 0:
            self.timer -= dt
            if self.timer <= 0:
                self.is_active = False

    def get_collision_normal(self, player_rect: pygame.Rect) -> Tuple[float, float]:
        """Возвращает нормаль поверхности в точке столкновения"""
        if not self.is_slope:
            return (0, -1)  # Вертикальная нормаль для горизонтальной поверхности

        # Для наклонных поверхностей (пока не реализовано)
        return (0, -1)


@dataclass
class Enemy:
    type: str  # "wood_golem" or "crazy_mushroom"
    x: float
    y: float
    w: int = 60
    h: int = 60
    vx: float = 0.0
    patrol_range: float = 0.0
    start_x: float = 0.0
    direction: int = 1


@dataclass
class Hazard:
    type: str  # "spike"
    x: float
    y: float
    w: int = 40
    h: int = 40