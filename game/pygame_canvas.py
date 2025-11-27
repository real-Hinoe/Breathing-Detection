import os
import sys
import pygame
from .entities import Player
from .config import MAX_SPEED, GRAVITY, JUMP_SPEED

WIN_W = 1280
WIN_H = 720
PLATFORM_HEIGHT = 30
PLATFORM_MARGIN = 60

# Фиксированный шаг физики
FIXED_DT = 1 / 120  # 120 тиков физики в секунду


def run_pygame_level(level: int = 1, external_running_flag=None):
    """
    Запускает уровень на pygame.
    Если external_running_flag передан (PygameThread),
    то цикл периодически проверяет external_running_flag._running
    и мягко выходит, когда там станет False.
    """

    # macOS: отключаем AppNap, на винде просто ничего не произойдёт
    if sys.platform == "darwin":
        os.system("defaults write -g NSAppSleepDisabled -bool YES")

    # Немного тюнинга SDL
    os.environ["SDL_RENDER_VSYNC"] = "0"
    os.environ["SDL_HINT_RENDER_BATCHING"] = "1"
    os.environ["PYGAME_BLEND_ALPHA_SDL2"] = "1"

    pygame.init()
    pygame.display.set_caption(f"Уровень {level} — Breathing Game")

    # Без рамки, с двойной буферизацией и хардварным ускорением
    screen = pygame.display.set_mode(
        (WIN_W, WIN_H), pygame.NOFRAME | pygame.HWSURFACE | pygame.DOUBLEBUF
    )
    clock = pygame.time.Clock()

    # === ИГРОК ===
    player = Player(x=200, y=300)

    # Загружаем PNG-спрайты напрямую для pygame
    sprite_cache = {
        "idle": pygame.image.load("resources/staying.png").convert_alpha(),
        "run": pygame.image.load("resources/jump_start.png").convert_alpha(),
        "jump_up": pygame.image.load("resources/jump_up.png").convert_alpha(),
        "jump_fall": pygame.image.load("resources/jump_fall.png").convert_alpha(),
    }

    # ---------- СКЕЙЛ СПРАЙТОВ + РАЗМЕРЫ ПЕРСОНАЖА ----------
    # Подстрой коэффициент, если нужно изменить размер ниндзя
    scale = 0.35
    for name, surf in sprite_cache.items():
        w = int(surf.get_width() * scale)
        h = int(surf.get_height() * scale)
        sprite_cache[name] = pygame.transform.smoothscale(surf, (w, h))

    # Размеры игрока берём из idle-спрайта
    idle_surf = sprite_cache["idle"]
    player.w = idle_surf.get_width()
    player.h = idle_surf.get_height()
    # --------------------------------------------------------

    player.prev_x = player.x
    player.prev_y = player.y
    player.facing = 1

    # === ПЛАТФОРМА ===
    platform_w = int(WIN_W * 0.7)
    platform_x = (WIN_W - platform_w) // 2
    platform_y = WIN_H - PLATFORM_HEIGHT - PLATFORM_MARGIN
    platform_rect = pygame.Rect(platform_x, platform_y, platform_w, PLATFORM_HEIGHT)

    # === Интерполяция ===
    accumulator = 0.0
    prev_time = pygame.time.get_ticks() / 1000.0

    # Кнопка закрытия
    close_size = 40
    close_rect = pygame.Rect(WIN_W - close_size - 10, 10, close_size, close_size)

    running = True
    while running:
        # Если поток попросил остановиться — выходим
        if external_running_flag is not None and not external_running_flag._running:
            running = False

        # ======================
        #  ВЫЧИСЛЯЕМ DELTA TIME
        # ======================
        now = pygame.time.get_ticks() / 1000.0
        frame_time = now - prev_time
        prev_time = now

        if frame_time > 0.25:  # защита от дикого фриза
            frame_time = 0.25

        accumulator += frame_time

        # === СОБЫТИЯ ===
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

            if ev.type == pygame.KEYDOWN:
                # ESC / Q тоже закрывают игру
                if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False

            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if close_rect.collidepoint(ev.pos):
                    running = False

        keys = pygame.key.get_pressed()

        # =======================
        #     ФИЗИКА (fixed dt)
        # =======================
        while accumulator >= FIXED_DT:
            # сохраняем прошлую позицию
            player.prev_x = player.x
            player.prev_y = player.y

            # Горизонталь без ускорения
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                player.vx = -MAX_SPEED
                player.facing = -1
            elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                player.vx = MAX_SPEED
                player.facing = 1
            else:
                player.vx = 0

            # Прыжок
            if (
                keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]
            ) and player.grounded:
                player.vy = -JUMP_SPEED
                player.grounded = False

            # Гравитация
            player.vy += GRAVITY * FIXED_DT

            # Интеграция
            player.x += player.vx * FIXED_DT
            player.y += player.vy * FIXED_DT

            # Границы по X
            if player.x < 0:
                player.x = 0
            if player.x + player.w > WIN_W:
                player.x = WIN_W - player.w

            # Коллизия с платформой
            foot_y = player.y + player.h
            on_platform = (
                player.vy >= 0
                and foot_y >= platform_y
                and foot_y <= platform_y + PLATFORM_HEIGHT
                and (player.x + player.w) > platform_x
                and player.x < (platform_x + platform_w)
            )

            if on_platform:
                player.y = platform_y - player.h
                player.vy = 0
                player.grounded = True
            else:
                # пол внизу (ТУТ БЫЛА ОПЕЧАТКА: WIN_W → WIN_H)
                if player.y + player.h >= WIN_H:
                    player.y = WIN_H - player.h
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

        surf = sprite_cache.get(frame)

        # ===============
        #     РЕНДЕР
        # ===============
        screen.fill((30, 30, 30))

        # Платформа
        pygame.draw.rect(screen, (100, 100, 100), platform_rect)

        # Игрок
        if surf:
            draw_surf = surf
            if player.facing == -1:
                draw_surf = pygame.transform.flip(surf, True, False)
            screen.blit(draw_surf, (interp_x, interp_y))
        else:
            pygame.draw.rect(
                screen,
                (0, 200, 200),
                pygame.Rect(interp_x, interp_y, player.w, player.h),
            )

        # Кнопка закрытия (крестик)
        mouse_pos = pygame.mouse.get_pos()
        hovering = close_rect.collidepoint(mouse_pos)
        color = (230, 60, 60) if hovering else (180, 40, 40)
        pygame.draw.rect(screen, color, close_rect, border_radius=8)
        pygame.draw.line(
            screen,
            (255, 255, 255),
            (close_rect.left + 10, close_rect.top + 10),
            (close_rect.right - 10, close_rect.bottom - 10),
            3,
        )
        pygame.draw.line(
            screen,
            (255, 255, 255),
            (close_rect.left + 10, close_rect.bottom - 10),
            (close_rect.right - 10, close_rect.top + 10),
            3,
        )

        pygame.display.flip()

        # FPS рендера (физика — по FIXED_DT)
        clock.tick(144)

    pygame.quit()
