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
        # Уровень 1: Паркур с меньшим количеством пропастей
        (50, WIN_H - 100, 500, PLATFORM_HEIGHT),
        (650, WIN_H - 250, 300, PLATFORM_HEIGHT),
        (1050, WIN_H - 150, 400, PLATFORM_HEIGHT),
        (1550, WIN_H - 300, 350, PLATFORM_HEIGHT),
        (2000, WIN_H - 200, 500, PLATFORM_HEIGHT),
        (2600, WIN_H - 400, 400, PLATFORM_HEIGHT),
        (3100, WIN_H - 250, 500, PLATFORM_HEIGHT),
        (3700, WIN_H - 350, 400, PLATFORM_HEIGHT),
        (4200, WIN_H - 200, 600, PLATFORM_HEIGHT), # Финишная платформа
    ],
    2: [
        # Уровень 2: Хрупкий подъем
        (50, WIN_H - 100, 400, PLATFORM_HEIGHT), # Старт
        (600, WIN_H - 250, 200, PLATFORM_HEIGHT),
        (900, WIN_H - 400, 200, PLATFORM_HEIGHT),
        # Секция с движущейся платформой
        (2000, WIN_H - 300, 300, PLATFORM_HEIGHT), # Островок перед хрупкими
        # Хрупкие платформы
        (3500, WIN_H - 200, 400, PLATFORM_HEIGHT),
        (4200, WIN_H - 150, 600, PLATFORM_HEIGHT), # Финиш
    ],
}

# Специальные платформы: уровень -> список словарей
MOVING_PLATFORMS = {
    2: [
        {"x": 1400, "y": WIN_H - 400, "w": 200, "h": PLATFORM_HEIGHT, "vx": 200, "vy": 0, "rx": 250, "ry": 0},
        {"x": 2800, "y": WIN_H - 200, "w": 200, "h": PLATFORM_HEIGHT, "vx": 0, "vy": -150, "rx": 0, "ry": 300},
    ]
}

FRAGILE_PLATFORMS = {
    2: [
        {"x": 2400, "y": WIN_H - 350, "w": 150, "h": PLATFORM_HEIGHT, "timer": 1.5},
        {"x": 2700, "y": WIN_H - 500, "w": 150, "h": PLATFORM_HEIGHT, "timer": 1.5},
        {"x": 3100, "y": WIN_H - 450, "w": 150, "h": PLATFORM_HEIGHT, "timer": 1.5},
    ]
}

# Чекпойнты: словарь level -> list of (trigger_x, spawn_x, spawn_y)
CHECKPOINTS = {
    1: [
        (1100, 1100, WIN_H - 150),
        (2650, 2650, WIN_H - 400),
    ],
    2: [
        (1000, 1000, WIN_H - 400),
        (3600, 3600, WIN_H - 200),
    ]
}

ENEMIES = {
    1: [
        ("crazy_mushroom", 1300, WIN_H - 150 - 64, 0),
        ("crazy_mushroom", 2250, WIN_H - 200 - 64, 0),
        ("wood_golem", 3300, WIN_H - 250 - 80, 200),
        ("wood_golem", 3800, WIN_H - 350 - 80, 150),
    ],
    2: [
        ("wood_golem", 2050, WIN_H - 300 - 80, 100),
    ]
}

# Опасности: шипы и т.д.
HAZARDS = {
    2: [
        {"x": 500, "y": WIN_H - 40, "w": 1000, "h": 40}, # Шипы на полу в начале
        {"x": 2000, "y": WIN_H - 300 - 30, "w": 60, "h": 30}, # Шипы на платформе
    ]
}