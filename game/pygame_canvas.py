import os
import sys
import json
import pygame
from .entities import Player, Enemy, Platform, Hazard, SPRITE_FILES
from .config import (
    MAX_SPEED, GRAVITY, JUMP_SPEED, FLY_SPEED, LEVELS, WIN_W, WIN_H, WORLD_W, WORLD_H,
    SPAWN_POS, CHECKPOINTS, ENEMIES, MOVING_PLATFORMS, FRAGILE_PLATFORMS, HAZARDS
)
PLATFORM_HEIGHT = 30
PLATFORM_MARGIN = 60
FIXED_DT = 1 / 120

# =============================================================================
#           РУЧНАЯ НАСТРОЙКА ХИТБОКСОВ
# =============================================================================
MANUAL_HITBOX_ADJUSTMENTS = {
    "idle": (25, 0, 5, 0),
    "run": (15, 0, 15, 0),
    "jump_start": (15, 0, 15, 0),
    "jump_up": (20, 0, 10, 0),
    "jump_fall": (20, 0, 10, 0),
    "jump_land": (15, 0, 15, 0),
}


class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height

    def apply(self, entity):
        if isinstance(entity, pygame.Rect):
            return entity.move(-self.camera.x, -self.camera.y)
        return entity.rect.move(-self.camera.x, -self.camera.y)

    def update(self, target):
        x = target.x - int(WIN_W / 2)
        # Ограничиваем камеру границами мира
        x = max(0, min(x, WORLD_W - WIN_W))
        # По вертикали можно оставить фиксированной или тоже двигать
        y = 0
        self.camera = pygame.Rect(x, y, WIN_W, WIN_H)


def create_background_surface():
    """Создает поверхность с градиентом один раз при запуске"""
    bg = pygame.Surface((WIN_W, WIN_H))
    for y in range(WIN_H):
        r = max(0, 30 - y // 40)
        g = max(0, 30 - y // 40)
        b = max(0, 50 - y // 30)
        pygame.draw.line(bg, (r, g, b), (0, y), (WIN_W, y))
    return bg


def extract_ground_tile(surface, top_cut=0.25, bottom_cut=0.25):
    """
    Берёт центральную часть текстуры земли.
    top_cut / bottom_cut — сколько отрезать сверху и снизу.
    """
    h = surface.get_height()

    y1 = int(h * top_cut)
    y2 = int(h * (1 - bottom_cut))

    rect = pygame.Rect(0, y1, surface.get_width(), y2 - y1)

    tile = pygame.Surface(rect.size, pygame.SRCALPHA)
    tile.blit(surface, (0, 0), rect)

    return tile


def run_pygame_level(level: int = 1, draw_hitbox: bool = False, external_running_flag=None):
    """
    Запускает уровень на pygame.
    """
    if sys.platform == "darwin":
        os.system("defaults write -g NSAppSleepDisabled -bool YES")

    os.environ["SDL_RENDER_VSYNC"] = "0"
    os.environ["SDL_HINT_RENDER_BATCHING"] = "1"
    os.environ["PYGAME_BLEND_ALPHA_SDL2"] = "1"

    pygame.init()
    pygame.display.set_caption(f"Уровень {level} — Breathing Game")
    screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
    clock = pygame.time.Clock()

    bg_surf = create_background_surface()

    # === PARALLAX BACKGROUND ===
    bg_layers = []

    for i in range(1, 4):
        try:
            path = os.path.join("resources", f"background{i}.png")
            if os.path.exists(path):

                surf = pygame.image.load(path).convert_alpha()

                # масштабируем по высоте окна
                scale = WIN_H / surf.get_height()

                new_w = int(surf.get_width() * scale)
                new_h = WIN_H

                surf = pygame.transform.smoothscale(surf, (new_w, new_h))

                bg_layers.append(surf)

            else:
                bg_layers.append(None)

        except Exception as e:
            print(f"Error loading background{i}: {e}")
            bg_layers.append(None)

    # Чем меньше коэффициент — тем дальше слой
    parallax_factors = [
        0.35,  # background1 (ближе)
        0.2,  # background2
        0.1  # background3 (самый дальний)
    ]

    # === ИНИЦИАЛИЗАЦИЯ ИГРОКА ===
    # Ставим игрока в безопасное место (сверху слева, чтобы упал на платформу)
    # или можно настроить спавн для каждого уровня
    player = Player(x=100, y=0)

    # === ЗАГРУЗКА И НАСТРОЙКА РЕСУРСОВ ===
    sprite_cache = {}
    hitbox_cache = {}
    scale = 0.175

    for name, filename in SPRITE_FILES.items():
        try:
            full_path = os.path.join("resources", filename)
            surf = pygame.image.load(full_path).convert_alpha()
            w, h = int(surf.get_width() * scale), int(surf.get_height() * scale)
            scaled_surf = pygame.transform.smoothscale(surf, (w, h))
            sprite_cache[name] = scaled_surf

            bbox = scaled_surf.get_bounding_rect()
            if name in MANUAL_HITBOX_ADJUSTMENTS:
                trim_l, trim_t, trim_r, trim_b = MANUAL_HITBOX_ADJUSTMENTS[name]
                bbox.x += trim_l
                bbox.y += trim_t
                bbox.width -= (trim_l + trim_r)
                bbox.height -= (trim_t + trim_b)

            hitbox_cache[name] = bbox

        except Exception as e:
            print(f"Error loading {name}: {e}")

    # Загружаем спрайт гриба отдельно
    mushroom_sprite = None
    mushroom_bbox = None
    try:
        path = os.path.join("resources", "crazy_mushroom.png")
        if os.path.exists(path):
            surf = pygame.image.load(path).convert_alpha()
            mushroom_sprite = pygame.transform.smoothscale(surf, (64, 64))

            mushroom_bbox = mushroom_sprite.get_bounding_rect()

    except Exception as e:
        print(f"Error loading mushroom: {e}")
    # Загружаем спрайт шипа
    spike_sprite = None
    try:
        path = os.path.join("resources", "Spike.png")
        if os.path.exists(path):
            surf = pygame.image.load(path).convert_alpha()
            spike_sprite = pygame.transform.smoothscale(surf, (40, 40))
    except Exception as e:
        print(f"Error loading spike: {e}")

    # Загружаем спрайт голема
    golem_sprite = None
    golem_bbox = None
    try:
        path = os.path.join("resources", "wood_golem.png")
        if os.path.exists(path):
            surf = pygame.image.load(path).convert_alpha()
            golem_sprite = pygame.transform.smoothscale(surf, (80, 80))
            golem_bbox = golem_sprite.get_bounding_rect()
    except Exception as e:
        print(f"Error loading golem: {e}")

    # === СПРАЙТЫ ПЛАТФОРМ ===
    platform_sprites = []

    for i in range(1, 5):
        try:
            path = os.path.join("resources", f"platform{i}.png")
            if os.path.exists(path):
                surf = pygame.image.load(path).convert_alpha()
                platform_sprites.append(surf)
        except Exception as e:
            print(f"Error loading platform{i}: {e}")

    # === СПРАЙТЫ ЗЕМЛИ ===
    ground_tiles = {}

    for i in (2, 4):
        try:
            path = os.path.join("resources", f"ground{i}.png")
            if os.path.exists(path):
                surf = pygame.image.load(path).convert_alpha()

                # берём только середину
                ground_tiles[i] = extract_ground_tile(
                    surf,
                    top_cut=0.35,
                    bottom_cut=0.15
                )

        except Exception as e:
            print(f"Error loading ground{i}: {e}")

    # === СПРАЙТЫ ЧЕКПОИНТОВ ===
    checkpoint_inactive = None
    checkpoint_active = None

    try:
        path = os.path.join("resources", "check_point_inactive.png")
        if os.path.exists(path):
            checkpoint_inactive = pygame.image.load(path).convert_alpha()
    except Exception as e:
        print("Error loading checkpoint inactive:", e)

    try:
        path = os.path.join("resources", "check_point_active.png")
        if os.path.exists(path):
            checkpoint_active = pygame.image.load(path).convert_alpha()
    except Exception as e:
        print("Error loading checkpoint active:", e)

    # Размеры игрока берём из idle-спрайта
    if "idle" in sprite_cache:
        idle_surf = sprite_cache["idle"]
        player.w = idle_surf.get_width()
        player.h = idle_surf.get_height()

        # Инфо для коллизии (отступ снизу)
        idle_rect = idle_surf.get_bounding_rect()
        bottom_padding = player.h - idle_rect.bottom
    else:
        # Фолбэк если картинки нет
        player.w = 50
        player.h = 100
        bottom_padding = 0

    # Хитбокс для коллизий (уже, чем спрайт)
    hitbox_w = int(player.w * 0.4)
    hitbox_offset_x = (player.w - hitbox_w) // 2

    # Хитбокс по вертикали (от головы до ног с учетом паддинга)
    hitbox_offset_y = 10
    hitbox_h = player.h - bottom_padding - hitbox_offset_y

    # Начальный хитбокс (если анимация не найдена)
    initial_hitbox = pygame.Rect(0, 0, player.w, player.h)

    # === ЗАГРУЗКА ПЛАТФОРМ УРОВНЯ ===
    # Получаем конфиг уровня или дефолтный (уровень 1)
    level_config = LEVELS.get(level, LEVELS[1])
    platforms = []

    # 1. Обычные платформы
    for (x, y, w, h) in level_config:
        platforms.append(Platform(rect=pygame.Rect(x, y, w, h)))

    # 2. Движущиеся
    moving_cfg = MOVING_PLATFORMS.get(level, [])
    for p in moving_cfg:
        platforms.append(Platform(
            rect=pygame.Rect(p["x"], p["y"], p["w"], p["h"]),
            type="moving",
            vx=p["vx"], vy=p["vy"],
            range_x=p["rx"], range_y=p["ry"],
            start_x=p["x"], start_y=p["y"]
        ))

    # 3. Хрупкие
    fragile_cfg = FRAGILE_PLATFORMS.get(level, [])
    for p in fragile_cfg:
        platforms.append(Platform(
            rect=pygame.Rect(p["x"], p["y"], p["w"], p["h"]),
            type="fragile",
            timer=0  # Таймер запустится при контакте
        ))

    # Сразу инициализируем лимит времени для хрупких в конфиге
    fragile_limits = { (p["x"], p["y"]): p["timer"] for p in fragile_cfg }

    # === ЗАГРУЗКА ОПАСНОСТЕЙ ===
    hazards = []
    hazard_cfg = HAZARDS.get(level, [])
    for h_data in hazard_cfg:
        hazards.append(Hazard(type="spike", x=h_data["x"], y=h_data["y"], w=h_data["w"], h=h_data["h"]))

    # === ЧЕКПОЙНТЫ (ТОЛЬКО ДЛЯ ТЕКУЩЕЙ СЕССИИ) ===
    current_spawn = SPAWN_POS
    active_checkpoint = None

    level_checkpoints = CHECKPOINTS.get(level, []).copy()
    # Все чекпойнты доступны изначально при заходе на уровень
    level_checkpoints = [cp for cp in level_checkpoints]

    # === ИНИЦИАЛИЗАЦИЯ ВРАГОВ ===
    enemies = []
    enemies_config = ENEMIES.get(level, [])
    for etype, ex, ey, erad in enemies_config:
        if etype == "crazy_mushroom":
            enemies.append(Enemy(type=etype, x=ex, y=ey, w=64, h=64))
        elif etype == "wood_golem":
            enemies.append(Enemy(type=etype, x=ex, y=ey, w=80, h=80, patrol_range=erad, start_x=ex, direction=1))

    # === МАЯК ФИНИША ===
    finish_rect = pygame.Rect(WORLD_W - 100, WIN_H - 125, 60, 100)

    # === ИГРОК НА СТАРТ ===
    player.x, player.y = current_spawn
    player.y -= player.h # Чтобы не был в платформе если спавн на ней

    player.prev_x = player.x
    player.prev_y = player.y
    player.facing = 1

    # === Интерполяция и Камера ===
    camera = Camera(WORLD_W, WORLD_H)
    accumulator = 0.0
    prev_time = pygame.time.get_ticks() / 1000.0

    level_start_time = pygame.time.get_ticks()
    timer_font = pygame.font.SysFont("Menlo, Monaco, Courier New, monospace", 40, bold=True)

    running = True
    try:
        while running:
            if external_running_flag is not None and not external_running_flag._running:
                running = False

            # ======================
            #  ВЫЧИСЛЯЕМ DELTA TIME
            # ======================
            now = pygame.time.get_ticks() / 1000.0
            frame_time = now - prev_time
            prev_time = now

            if frame_time > 0.25:
                frame_time = 0.25

            accumulator += frame_time

            # === СОБЫТИЯ ===
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False

            keys = pygame.key.get_pressed()

            # =======================
            #     ФИЗИКА (fixed dt)
            # =======================
            while accumulator >= FIXED_DT:
                player.prev_x = player.x
                player.prev_y = player.y

                # Горизонтальное движение
                if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                    player.vx = -MAX_SPEED
                    player.facing = -1
                elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                    player.vx = MAX_SPEED
                    player.facing = 1
                else:
                    player.vx = 0

                # Полет (Джетпак)
                is_flying = keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]
                if is_flying:
                    player.vy = -FLY_SPEED
                    player.grounded = False
                else:
                    if player.vy < 0:
                        player.vy = 0

                # Гравитация
                player.vy += GRAVITY * FIXED_DT

                # Интеграция
                player.x += player.vx * FIXED_DT
                player.y += player.vy * FIXED_DT

                for plat in platforms:
                    plat.update(FIXED_DT)

                # Границы по X (Мировые)
                player.x = max(0, min(player.x, WORLD_W - player.w))

                # Потолок
                if player.y < 0:
                    player.y = 0
                    if player.vy < 0:
                        player.vy = 0

                death_triggered = False
                player_rect = pygame.Rect(player.x, player.y, player.w, player.h)
                for haz in hazards:
                    haz_rect = pygame.Rect(haz.x, haz.y, haz.w, haz.h)
                    if player_rect.colliderect(haz_rect):
                        death_triggered = True
                        break

                if death_triggered:
                    player.x, player.y = current_spawn
                    player.y -= player.h
                    player.vx = 0
                    player.vy = 0
                    player.grounded = False

                    # Сбрасываем хрупкие платформы при смерти
                    for plat in platforms:
                        if plat.type == "fragile":
                            plat.is_active = True
                            plat.timer = 0

                    accumulator = 0
                    continue

                # --- КОЛЛИЗИЯ С ПЛАТФОРМАМИ ---
                # Считаем хитбокс по X и Y
                current_hitbox_x = player.x + hitbox_offset_x
                current_hitbox_y = player.y + hitbox_offset_y
                player_rect_physics = pygame.Rect(current_hitbox_x, current_hitbox_y, hitbox_w, hitbox_h)

                # --- КОЛЛИЗИЯ С ВРАГАМИ ---
                death_triggered = False
                full_player_rect = pygame.Rect(player.x, player.y, player.w, player.h)

                for en in enemies:
                    if en.type == "crazy_mushroom" and mushroom_sprite:
                        enemy_rect = mushroom_bbox.move(en.x, en.y)
                        if full_player_rect.colliderect(enemy_rect):
                            death_triggered = True
                    elif en.type == "wood_golem" and golem_sprite:
                        # Движение голема (только здесь, внутри цикла физики)
                        if en.patrol_range > 0:
                            en.vx = 100 * en.direction
                            en.x += en.vx * FIXED_DT
                            if abs(en.x - en.start_x) >= en.patrol_range:
                                en.direction *= -1

                        enemy_rect = golem_bbox.move(en.x, en.y)
                        if full_player_rect.colliderect(enemy_rect):
                            death_triggered = True

                    if death_triggered:
                        player.x, player.y = current_spawn
                        player.y -= player.h
                        player.vx = 0
                        player.vy = 0
                        player.grounded = False
                        break

                if death_triggered:
                    accumulator = 0
                    continue

                # Координата головы и ног (для платформенной логики)
                head_y = player.y + hitbox_offset_y
                foot_y = head_y + hitbox_h

                on_platform = False
                platform_to_stick = None

                for plat in platforms:
                    if not plat.is_active:
                        continue

                    p_rect = plat.rect
                    # Проверяем попадание по X (хитбокс тела пересекает платформу)
                    if (current_hitbox_x + hitbox_w > p_rect.left) and (current_hitbox_x < p_rect.right):

                        # 1. Проверка Головы (Столкновение снизу вверх)
                        if player.vy < 0:
                            if head_y >= p_rect.bottom - 10 and head_y <= p_rect.bottom + 5:
                                player.y = p_rect.bottom - hitbox_offset_y # Отбрасываем вниз
                                player.vy = 0 # Останавливаем взлет

                        # 2. Проверка Ног (Приземление)
                        elif player.vy >= 0:
                            if (foot_y >= p_rect.top) and (foot_y <= p_rect.top + PLATFORM_HEIGHT + 10):
                                player.y = p_rect.top - player.h + bottom_padding
                                player.vy = 0
                                player.grounded = True
                                on_platform = True
                                platform_to_stick = plat

                                # Если платформа хрупкая и еще не запущена - запускаем
                                if plat.type == "fragile" and plat.timer <= 0:
                                    key = (plat.start_x if hasattr(plat, "start_x") else plat.rect.x,
                                           plat.start_y if hasattr(plat, "start_y") else plat.rect.y)
                                    # Находим лимит времени из конфига (мы сохранили их ранее в fragile_limits)
                                    # Или просто захардкодим/найдем в начале
                                    limit = fragile_limits.get( (plat.rect.x, plat.rect.y), 1.0 )
                                    plat.timer = limit

                # Если стоим на движущейся платформе - наследуем её движение
                if on_platform and platform_to_stick and platform_to_stick.type == "moving":
                    player.x += platform_to_stick.vx * FIXED_DT
                    player.y += platform_to_stick.vy * FIXED_DT

                # --- ПРОВЕРКА ЧЕКПОЙНТОВ ---
                if level_checkpoints and player.x >= level_checkpoints[0][0]:
                    cp = level_checkpoints.pop(0)
                    current_spawn = (cp[1], cp[2])
                    active_checkpoint = cp

                # --- ПРОВЕРКА ЗАВЕРШЕНИЯ УРОВНЯ (МАЯК) ---
                player_rect = pygame.Rect(player.x, player.y, player.w, player.h)
                if player_rect.colliderect(finish_rect):
                    # Отбрасываем в начало и сбрасываем всё
                    player.x, player.y = SPAWN_POS
                    player.y -= player.h
                    player.vx = 0
                    player.vy = 0
                    player.grounded = False

                    current_spawn = SPAWN_POS
                    level_start_time = pygame.time.get_ticks()
                    level_checkpoints = CHECKPOINTS.get(level, []).copy()

                # --- ПРОВЕРКА СМЕРТИ (ПАДЕНИЕ) ---
                if player.y > WIN_H:
                    # Респаун на последнем чекпойнте (без сброса общего времени спавна)
                    player.x, player.y = current_spawn
                    player.y -= player.h
                    player.vx = 0
                    player.vy = 0
                    player.grounded = False

                    for plat in platforms:
                        if plat.type == "fragile":
                            plat.is_active = True
                            plat.timer = 0

                if not on_platform and player.vy > 0:
                    player.grounded = False

                accumulator -= FIXED_DT

            # ==========================
            #    ИНТЕРПОЛЯЦИЯ ДЛЯ РЕНДЕРА
            # ==========================
            alpha = accumulator / FIXED_DT
            interp_x = player.prev_x + (player.x - player.prev_x) * alpha
            interp_y = player.prev_y + (player.y - player.prev_y) * alpha

            # === Выбор спрайта ===
            if not player.grounded:
                frame = "jump_up" if player.vy < 0 else "jump_fall"
            else:
                frame = "run" if abs(player.vx) > 10 else "idle"

            current_state = frame
            surf = sprite_cache.get(frame)

            # Обновляем камеру по интерполированной позиции игрока
            dummy_target = type('obj', (object,), {'x': interp_x, 'y': interp_y})
            camera.update(dummy_target)

            # ===============
            #     РЕНДЕР
            # ===============
            screen.blit(bg_surf, (0, 0))

            # === PARALLAX RENDER ===
            # for i in reversed(range(len(bg_layers))):
            #     layer = bg_layers[i]
            for i, layer in enumerate(bg_layers):

                if layer:

                    factor = parallax_factors[i]

                    # смещение слоя
                    offset_x = -camera.camera.x * factor

                    layer_w = layer.get_width()

                    # рисуем несколько копий чтобы фон не заканчивался
                    start_x = int(offset_x) % layer_w - layer_w

                    x = start_x
                    while x < WIN_W:
                        screen.blit(layer, (x, 0))
                        x += layer_w

            # Рисуем все платформы с учетом камеры
            for i, plat in enumerate(platforms):
                if not plat.is_active:
                    continue

                p_rect = plat.rect
                if platform_sprites:
                    sprite_index = i % len(platform_sprites)
                    sprite = platform_sprites[sprite_index]

                    scale = p_rect.width / sprite.get_width()
                    new_w = p_rect.width
                    new_h = int(sprite.get_height() * scale)

                    scaled = pygame.transform.smoothscale(sprite, (new_w, new_h))

                    # Визуальное затухание для хрупких платформ
                    if plat.type == "fragile" and plat.timer > 0:
                        alpha = int(255 * (plat.timer / fragile_limits.get((plat.rect.x, plat.rect.y), 1.0)))
                        scaled.set_alpha(alpha)

                    draw_x = p_rect.x - camera.camera.x

                    # platform2.png поднимаем выше
                    if sprite_index == 1:
                        offset = 0.3
                    if sprite_index == 3:
                        offset = 0.25
                    else:
                        offset = 0.4

                    draw_y = p_rect.y - camera.camera.y - int(new_h * offset)
                    screen.blit(scaled, (draw_x, draw_y))

                    # ====================================================
                    #          ДОСТРАИВАЕМ ЗЕМЛЮ ДО НИЗА ЭКРАНА
                    # ====================================================
                    ground_index = sprite_index + 1

                    if ground_index in ground_tiles:

                        tile = ground_tiles[ground_index]

                        scale = plat.rect.width / tile.get_width()
                        tile_w = plat.rect.width
                        tile_h = int(tile.get_height() * scale)

                        tile_scaled = pygame.transform.smoothscale(
                            tile,
                            (tile_w, tile_h)
                        )

                        # 🔥 ВАЖНО:
                        # начинаем ЧУТЬ ВЫШЕ чтобы земля
                        # залезла под остров
                        ground_y = draw_y + new_h - int(tile_h * 0.6)

                        while ground_y < WIN_H:
                            screen.blit(tile_scaled, (draw_x, ground_y))
                            ground_y += tile_h

                else:
                    color = (70, 70, 90)
                    if plat.type == "moving": color = (100, 100, 150)
                    elif plat.type == "fragile": color = (150, 100, 100)
                    pygame.draw.rect(screen, color, camera.apply(p_rect))

            # Рисуем опасности (шипы)
            for haz in hazards:
                if haz.type == "spike" and spike_sprite:
                    # Шипы могут быть широкими, рисуем их плиткой
                    haz_w = haz.w
                    spike_w = spike_sprite.get_width()
                    num_spikes = (haz_w + spike_w - 1) // spike_w
                    for s_idx in range(num_spikes):
                        draw_x = haz.x + s_idx * spike_w - camera.camera.x
                        draw_y = haz.y - camera.camera.y
                        screen.blit(spike_sprite, (draw_x, draw_y))
                else:
                    pygame.draw.rect(screen, (255, 0, 0), camera.apply(pygame.Rect(haz.x, haz.y, haz.w, haz.h)))

            # Рисуем врагов
            for en in enemies:
                if en.type == "crazy_mushroom" and mushroom_sprite:
                    screen.blit(mushroom_sprite, (en.x - camera.camera.x, en.y - camera.camera.y))
                elif en.type == "wood_golem" and golem_sprite:
                    draw_surf = golem_sprite
                    if en.direction == -1:
                        draw_surf = pygame.transform.flip(golem_sprite, True, False)
                    # Костыль для центрирования если нужно, но пока просто блит
                    screen.blit(draw_surf, (en.x - camera.camera.x, en.y - camera.camera.y))

            # Рисуем чекпойнты (зеленые флажки)
            for cp in CHECKPOINTS.get(level, []):

                x = cp[0]
                y = cp[2]

                is_active = (active_checkpoint == cp)

                sprite = checkpoint_active if is_active else checkpoint_inactive

                if sprite:
                    target_height = 100
                    scale = target_height / sprite.get_height()

                    new_w = int(sprite.get_width() * scale)
                    new_h = target_height

                    scaled = pygame.transform.smoothscale(sprite, (new_w, new_h))

                    draw_x = x - camera.camera.x
                    draw_y = y - new_h - camera.camera.y

                    screen.blit(scaled, (draw_x, draw_y))

            # Рисуем маяк финиша (синий флаг)
            # Основание
            pygame.draw.rect(screen, (100, 100, 100), camera.apply(pygame.Rect(finish_rect.x + 25, finish_rect.y, 10, 100)))
            # Флаг
            pygame.draw.rect(screen, (0, 100, 255), camera.apply(pygame.Rect(finish_rect.x + 35, finish_rect.y, 40, 30)))

            # Игрок
            if surf:
                draw_surf = surf
                if player.facing == -1:
                    draw_surf = pygame.transform.flip(surf, True, False)

                # Применяем смещение камеры к позиции игрока
                screen.blit(draw_surf, (interp_x - camera.camera.x, interp_y - camera.camera.y))

            # --- ОТРИСОВКА ТАЙМЕРА ---
            current_ticks = pygame.time.get_ticks() - level_start_time
            mins = current_ticks // 60000
            secs = (current_ticks % 60000) // 1000
            ms = current_ticks % 1000
            ms_rounded = ms // 10
            timer_text = f"{mins}:{secs:02d}:{ms_rounded:02d}"
            timer_surf = timer_font.render(timer_text, True, (255, 255, 255))
            timer_rect = timer_surf.get_rect(topleft=(WIN_W // 2 - 85, 20))
            timer_shadow = timer_font.render(timer_text, True, (0, 0, 0))
            screen.blit(timer_shadow, timer_rect.move(2, 2))
            screen.blit(timer_surf, timer_rect)

            if draw_hitbox:
                current_hitbox = hitbox_cache.get(current_state, initial_hitbox)

                # Физическое смещение для отрисовки (учёт flip)
                if player.facing == -1:
                    # При повороте по горизонтали хитбокс смещается относительно правого края спрайта
                    hitbox_x_offset = sprite_cache[current_state].get_width() - (
                                current_hitbox.x + current_hitbox.width)
                else:
                    hitbox_x_offset = current_hitbox.x

                debug_rect = pygame.Rect(
                    interp_x + hitbox_x_offset,
                    interp_y + current_hitbox.y,  # вертикальное смещение не меняем
                    current_hitbox.width,
                    current_hitbox.height
                )
                pygame.draw.rect(screen, (255, 0, 0), debug_rect, 2)

                font = pygame.font.Font(None, 24)
                state_text = font.render(f"State: {current_state}", True, (255, 255, 255))
                ground_text = font.render(f"Grounded: {player.grounded}", True, (255, 255, 255))
                vel_text = font.render(f"Velocity: ({player.vx:.1f}, {player.vy:.1f})", True, (255, 255, 255))
                pos_text = font.render(f"Position: ({player.x:.1f}, {player.y:.1f})", True, (255, 255, 255))
                screen.blit(state_text, (10, 10))
                screen.blit(ground_text, (10, 40))
                screen.blit(vel_text, (10, 70))
                screen.blit(pos_text, (10, 100))

            pygame.display.flip()
            clock.tick(144)
    except KeyboardInterrupt:
        pass
    finally:
        pygame.quit()
