import os
import sys
import pygame
from .entities import Player, SPRITE_FILES
from .config import MAX_SPEED, GRAVITY, JUMP_SPEED, FLY_SPEED, LEVELS, WIN_W, WIN_H
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

    # Начальный хитбокс (если анимация не найдена)
    initial_hitbox = pygame.Rect(0, 0, player.w, player.h)

    # === ЗАГРУЗКА ПЛАТФОРМ УРОВНЯ ===
    # Получаем конфиг уровня или дефолтный (уровень 1)
    level_config = LEVELS.get(level, LEVELS[1])
    platforms = [pygame.Rect(x, y, w, h) for (x, y, w, h) in level_config]

    # === ИГРОК НА СТАРТ ===
    # Попробуем поставить игрока на первую платформу аккуратно
    if platforms:
        first_plat = platforms[0]
        player.x = first_plat.x + 20
        player.y = first_plat.y - player.h + bottom_padding - 200 # Чуть выше, пусть упадет

    player.prev_x = player.x
    player.prev_y = player.y
    player.facing = 1

    # === Интерполяция ===
    accumulator = 0.0
    prev_time = pygame.time.get_ticks() / 1000.0

    running = True
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

            # Границы по X
            player.x = max(0, min(player.x, WIN_W - player.w))

            # Потолок
            if player.y < 0:
                player.y = 0
                if player.vy < 0:
                    player.vy = 0

            # --- КОЛЛИЗИЯ С ПЛАТФОРМАМИ ---
            # Считаем координату "ног" и хитбокс по X
            foot_y = player.y + player.h - bottom_padding
            current_hitbox_x = player.x + hitbox_offset_x

            found_platform = False

            # Проверку делаем только если летим вниз (или стоим)
            if player.vy >= 0:
                for plat in platforms:
                    # Проверяем попадание по X (хитбокс тела внутри границ платформы или пересекает их)
                    if (current_hitbox_x + hitbox_w > plat.left) and (current_hitbox_x < plat.right):
                        # Проверяем попадание по Y
                        if (foot_y >= plat.top) and (foot_y <= plat.top + PLATFORM_HEIGHT + 10): # +10 допуск
                            player.y = plat.top - player.h + bottom_padding
                            player.vy = 0
                            player.grounded = True
                            found_platform = True
                            break

            if not found_platform:
                # Если не нашли платформу, проверяем пол (низ экрана)
                if player.y + player.h - bottom_padding >= WIN_H:
                    player.y = WIN_H - player.h + bottom_padding
                    player.vy = 0
                    player.grounded = True
                else:
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

        # ===============
        #     РЕНДЕР
        # ===============
        screen.fill((30, 30, 30))

        # Рисуем все платформы
        for plat in platforms:
            pygame.draw.rect(screen, (100, 100, 100), plat)

        # Игрок
        if surf:
            draw_surf = surf
            if player.facing == -1:
                draw_surf = pygame.transform.flip(surf, True, False)
            screen.blit(draw_surf, (interp_x, interp_y))
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

    pygame.quit()
