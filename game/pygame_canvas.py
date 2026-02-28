import os
import sys
import json
import pygame
from .entities import Player, SPRITE_FILES
from .config import MAX_SPEED, GRAVITY, JUMP_SPEED, FLY_SPEED, LEVELS, WIN_W, WIN_H, WORLD_W, WORLD_H, SPAWN_POS, CHECKPOINTS
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


SAVE_FILE = "save_data.json"

def load_save():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def write_save(data):
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


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

    # === ЧЕКПОЙНТЫ И СОХРАНЕНИЯ ===
    save_data = load_save()
    level_save = save_data.get(str(level), {})

    saved_spawn = level_save.get("spawn", SPAWN_POS)
    current_spawn = (saved_spawn[0], saved_spawn[1])
    elapsed_time_saved = level_save.get("time", 0)

    level_checkpoints = CHECKPOINTS.get(level, []).copy()
    # Убираем чекпойнты, которые уже пройдены (их x <= текущему спавну)
    level_checkpoints = [cp for cp in level_checkpoints if cp[0] > current_spawn[0]]

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
    timer_font = pygame.font.Font(None, 48)

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

                # Границы по X (Мировые)
                player.x = max(0, min(player.x, WORLD_W - player.w))

                # Потолок
                if player.y < 0:
                    player.y = 0
                    if player.vy < 0:
                        player.vy = 0

                # --- КОЛЛИЗИЯ С ПЛАТФОРМАМИ ---
                # Считаем хитбокс по X и Y
                current_hitbox_x = player.x + hitbox_offset_x

                # Координата головы и ног
                head_y = player.y + 10 # Допуск сверху
                foot_y = player.y + player.h - bottom_padding

                on_platform = False

                for plat in platforms:
                    # Проверяем попадание по X (хитбокс тела пересекает платформу)
                    if (current_hitbox_x + hitbox_w > plat.left) and (current_hitbox_x < plat.right):

                        # 1. Проверка Головы (Столкновение снизу вверх)
                        if player.vy < 0:
                            if head_y >= plat.bottom - 10 and head_y <= plat.bottom + 5:
                                player.y = plat.bottom - 10 # Отбрасываем чуть вниз
                                player.vy = 0 # Останавливаем взлет

                        # 2. Проверка Ног (Приземление)
                        elif player.vy >= 0:
                            if (foot_y >= plat.top) and (foot_y <= plat.top + PLATFORM_HEIGHT + 10):
                                player.y = plat.top - player.h + bottom_padding
                                player.vy = 0
                                player.grounded = True
                                on_platform = True

                # --- ПРОВЕРКА ЧЕКПОЙНТОВ ---
                if level_checkpoints and player.x >= level_checkpoints[0][0]:
                    cp = level_checkpoints.pop(0)
                    current_spawn = (cp[1], cp[2])

                    # Сохраняем прогресс (время и текущий спавн)
                    current_time_ms = pygame.time.get_ticks() - level_start_time + elapsed_time_saved
                    save_data[str(level)] = {
                        "spawn": current_spawn,
                        "time": current_time_ms
                    }
                    write_save(save_data)

                # --- ПРОВЕРКА СМЕРТИ (ПАДЕНИЕ) ---
                if player.y > WIN_H:
                    # Респаун на последнем чекпойнте (без сброса общего времени спавна)
                    player.x, player.y = current_spawn
                    player.y -= player.h
                    player.vx = 0
                    player.vy = 0
                    player.grounded = False

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

            # Рисуем все платформы с учетом камеры
            for plat in platforms:
                pygame.draw.rect(screen, (70, 70, 90), camera.apply(plat))
                # Добавим "толщину" платформе для красоты
                pygame.draw.rect(screen, (50, 50, 70), camera.apply(pygame.Rect(plat.x, plat.y+5, plat.width, plat.height-5)))

            # Рисуем чекпойнты (зеленые флажки)
            for cp in level_checkpoints:
                flag_rect = pygame.Rect(cp[0], cp[2] - 40, 5, 40)
                pygame.draw.rect(screen, (0, 255, 0), camera.apply(flag_rect))

            # Игрок
            if surf:
                draw_surf = surf
                if player.facing == -1:
                    draw_surf = pygame.transform.flip(surf, True, False)

                # Применяем смещение камеры к позиции игрока
                screen.blit(draw_surf, (interp_x - camera.camera.x, interp_y - camera.camera.y))

            # --- ОТРИСОВКА ТАЙМЕРА ---
            current_ticks = pygame.time.get_ticks() - level_start_time + elapsed_time_saved
            mins = current_ticks // 60000
            secs = (current_ticks % 60000) // 1000
            ms = current_ticks % 1000
            timer_text = f"{mins}:{secs:02d}:{ms:03d}"
            timer_surf = timer_font.render(timer_text, True, (255, 255, 255))
            timer_rect = timer_surf.get_rect(center=(WIN_W // 2, 30))
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
