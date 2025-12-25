ACCEL = 1200.0  # ускорение при движении
MAX_SPEED = 500.0  # максимальная скорость по горизонтали

GRAVITY = 2500.0  # сила гравитации (падение)
JUMP_SPEED = 1100.0  # сила прыжка (импульс вверх)
FLY_SPEED = 600.0  # скорость полета вверх

TICK_HZ = 120  # частота кадров (тик-таймер)

# Новые параметры для физики
SKIN_WIDTH = 0.01  # Толщина "кожи" для проникновения при столкновениях
MAX_SLOPE_ANGLE = 45  # Максимальный угол наклона поверхности, по которой можно ходить (в градусах)

# Размеры окна
WIN_W = 1280
WIN_H = 720

# Размеры мира (могут быть больше окна)
WORLD_W = 5000
WORLD_H = WIN_H

SPAWN_POS = (100, WIN_H - 150)

PLATFORM_HEIGHT = 25

# Конфигурация уровней
# Каждый уровень — это список кортежей (x, y, w, h) для платформ
LEVELS = {
    1: [
        # Уровень 1: Хардкорный подъем и прыжки над пропастью
        (50, WIN_H - 100, 300, PLATFORM_HEIGHT),
        (500, WIN_H - 250, 150, PLATFORM_HEIGHT),
        (800, WIN_H - 150, 150, PLATFORM_HEIGHT),
        (1100, WIN_H - 300, 100, PLATFORM_HEIGHT),
        (1300, WIN_H - 450, 120, PLATFORM_HEIGHT),
        (1600, WIN_H - 350, 150, PLATFORM_HEIGHT),
        (2000, WIN_H - 200, 250, PLATFORM_HEIGHT),
        (2400, WIN_H - 400, 80, PLATFORM_HEIGHT),
        (2700, WIN_H - 250, 200, PLATFORM_HEIGHT),
        (3100, WIN_H - 350, 150, PLATFORM_HEIGHT),
        (3500, WIN_H - 150, 300, PLATFORM_HEIGHT),
        (4000, WIN_H - 400, 100, PLATFORM_HEIGHT),
        (4400, WIN_H - 200, 400, PLATFORM_HEIGHT), # Финишная платформа
    ],
    2: [
        # Уровень 2: Вертикальный паркур
        (100, WIN_H - 100, 200, PLATFORM_HEIGHT),
        (400, WIN_H - 220, 150, PLATFORM_HEIGHT),
        (150, WIN_H - 340, 150, PLATFORM_HEIGHT),
        (450, WIN_H - 460, 150, PLATFORM_HEIGHT),
        (200, WIN_H - 580, 150, PLATFORM_HEIGHT),
        (600, WIN_H - 500, 200, PLATFORM_HEIGHT),
        (900, WIN_H - 400, 150, PLATFORM_HEIGHT),
        (1200, WIN_H - 300, 200, PLATFORM_HEIGHT),
    ],
    3: [
        # Уровень 3: "Островки" с разрывом (Хардкор вариант)
        (100, WIN_H - 100, 200, PLATFORM_HEIGHT),
        (600, WIN_H - 120, 100, PLATFORM_HEIGHT),
        (1000, WIN_H - 110, 80, PLATFORM_HEIGHT),
        (1400, WIN_H - 140, 100, PLATFORM_HEIGHT),
        (1800, WIN_H - 100, 150, PLATFORM_HEIGHT),
        (2300, WIN_H - 200, 100, PLATFORM_HEIGHT),
        (2800, WIN_H - 150, 200, PLATFORM_HEIGHT),
    ],
    4: [
        # Уровень 4: Лабиринт (высокие платформы)
        (50, WIN_H - 100, 150, PLATFORM_HEIGHT),
        (300, WIN_H - 250, 120, PLATFORM_HEIGHT),
        (550, WIN_H - 400, 100, PLATFORM_HEIGHT),
        (850, WIN_H - 350, 150, PLATFORM_HEIGHT),
        (1100, WIN_H - 500, 120, PLATFORM_HEIGHT),
        (1400, WIN_H - 300, 200, PLATFORM_HEIGHT),
        (1800, WIN_H - 200, 150, PLATFORM_HEIGHT),
    ]
}