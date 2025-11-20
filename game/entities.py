from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

# Путь к папке ресурсов
RES = (Path(__file__).resolve().parents[1] / "resources").resolve()

# Список спрайтов персонажа
SPRITE_FILES = {
    "idle": "staying1.png",
    "run": "jump_start.png",
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
