import os
import sys
import pygame
from .entities import Player, SPRITE_FILES
from .config import MAX_SPEED, GRAVITY, JUMP_SPEED

WIN_W = 1280
WIN_H = 720
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

    pygame.init()
    pygame.display.set_caption(f"Уровень {level} — Breathing Game")
    screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
    clock = pygame.time.Clock()
    player = Player(x=200, y=0)

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

        except pygame.error as e:
            print(f"Не удалось загрузить спрайт: {filename}. Ошибка: {e}")
            continue

    idle_surf = sprite_cache.get("idle", pygame.Surface((64, 128)))
    player.w, player.h = idle_surf.get_size()

    # === ИГРОВЫЕ ОБЪЕКТЫ ===
    platform_w = int(WIN_W * 0.7)
    platform_rect = pygame.Rect(
        (WIN_W - platform_w) // 2,
        WIN_H - PLATFORM_HEIGHT - PLATFORM_MARGIN,
        platform_w,
        PLATFORM_HEIGHT
    )

    initial_hitbox = hitbox_cache.get("idle", pygame.Rect(0, 0, player.w, player.h))
    player.y = platform_rect.top - (initial_hitbox.y + initial_hitbox.height)
    player.prev_y = player.y
    player.prev_x = player.x

    # === ПРОСТЫЕ ФИКСЫ ===
    current_state = "idle"
    frame_in_state = 0
    GROUND_THRESHOLD = 2  # Пикселей для проверки grounded

    accumulator = 0.0
    prev_time = pygame.time.get_ticks() / 1000.0
    running = True
    frame_count = 0

    while running:
        if external_running_flag and not external_running_flag.is_set():
            running = False

        now = pygame.time.get_ticks() / 1000.0
        frame_time = min(now - prev_time, 0.25)
        prev_time = now
        accumulator += frame_time
        frame_count += 1

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_q)):
                running = False

        keys = pygame.key.get_pressed()

        while accumulator >= FIXED_DT:
            player.prev_x, player.prev_y = player.x, player.y

            # --- Горизонтальное движение ---
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                player.vx, player.facing = -MAX_SPEED, -1
            elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                player.vx, player.facing = MAX_SPEED, 1
            else:
                player.vx = 0

            # --- Прыжок ---
            if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and player.grounded:
                player.vy = -JUMP_SPEED
                player.grounded = False

            # --- Гравитация ---
            player.vy += GRAVITY * FIXED_DT

            # --- Применение скоростей ---
            player.x += player.vx * FIXED_DT
            player.y += player.vy * FIXED_DT

            # --- Ограничение по краям ---
            player.x = max(0, min(player.x, WIN_W - player.w))

            # --- Хитбокс текущего состояния ---
            current_hitbox = hitbox_cache.get(current_state, initial_hitbox)
            ph_box = pygame.Rect(
                player.x + current_hitbox.x,
                player.y + current_hitbox.y,
                current_hitbox.width,
                current_hitbox.height
            )
            prev_ph_box = pygame.Rect(
                player.prev_x + current_hitbox.x,
                player.prev_y + current_hitbox.y,
                current_hitbox.width,
                current_hitbox.height
            )

            # --- Коллизия с платформой ---
            player_on_platform = False
            if ph_box.colliderect(platform_rect) and player.vy >= 0:
                # Пересечение с платформой
                overlap = ph_box.bottom - platform_rect.top
                if 0 < overlap <= 20:  # маленькая поправка для стабильности
                    player.y -= overlap
                    player.vy = 0
                    player.grounded = True
                    player_on_platform = True

            # --- Коллизия с полом ---
            if player.y + current_hitbox.y + current_hitbox.height >= WIN_H:
                player.y = WIN_H - (current_hitbox.y + current_hitbox.height)
                player.vy = 0
                player.grounded = True
                player_on_platform = True

            # --- Логика состояний ---
            new_state = "idle"
            if not player.grounded:
                if player.vy < 0:
                    new_state = "jump_up"
                else:
                    new_state = "jump_fall"
            elif abs(player.vx) > 10:
                new_state = "run"

            # Если мы только что приземлились и были в прыжке - стабилизируем
            if "jump" in current_state and player_on_platform:
                if frame_in_state > 3:
                    new_state = "run" if abs(player.vx) > 10 else "idle"

            if new_state != current_state:
                frame_in_state = 0
                current_state = new_state
            else:
                frame_in_state += 1

            accumulator -= FIXED_DT

        # --- РЕНДЕР (интерполяция) ---
        alpha = accumulator / FIXED_DT
        interp_x = player.prev_x * (1.0 - alpha) + player.x * alpha
        interp_y = player.prev_y * (1.0 - alpha) + player.y * alpha

        screen.fill((30, 30, 30))
        pygame.draw.rect(screen, (100, 100, 100), platform_rect)

        surf = sprite_cache.get(current_state)
        if surf:
            draw_surf = pygame.transform.flip(surf, True, False) if player.facing == -1 else surf
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

                pygame.draw.line(screen, (0, 255, 0),
                                 (platform_rect.left, platform_rect.top),
                                 (platform_rect.right, platform_rect.top), 2)

        pygame.display.flip()
        clock.tick(144)

    pygame.quit()
