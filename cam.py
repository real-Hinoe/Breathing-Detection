# Камеры в OpenCV индексируются с 0, где 0 обычно соответствует встроенной камере (например, на ноутбуках),
# 1 — первой внешней USB-камере, 2 — второй внешней и так далее.
# На Windows и Linux такое соответствие обычно стабильно.

import platform
import time
from typing import List, Optional, Tuple

import cv2 as cv


def is_macos() -> bool:
    return platform.system().lower() in ("darwin", "mac", "macos")


def pick_backend() -> int:
    system = platform.system().lower()
    if "windows" in system:
        return cv.CAP_DSHOW
    if "darwin" in system or "mac" in system:
        return cv.CAP_AVFOUNDATION
    # Linux/other
    return cv.CAP_V4L2

def try_open_device(index: int, backend: int, width: Optional[int]=None, height: Optional[int]=None):
    # На macOS AVFoundation поддерживает только индекс 0, остальные индексы считаются невалидными.
    if is_macos() and index != 0:
        return None
    cap = cv.VideoCapture(index, backend)
    if not cap.isOpened():
        return None
    # Опционально пытаемся поставить желаемое разрешение
    # Важно: ширина и высота — это только "запросы" драйверу, он может их игнорировать.
    # Это полезно для управления качеством и производительностью.
    if width:  cap.set(cv.CAP_PROP_FRAME_WIDTH,  int(width))
    if height: cap.set(cv.CAP_PROP_FRAME_HEIGHT, int(height))
    # Проверка чтения первого кадра
    ok, frame = cap.read()
    if not ok or frame is None:
        # Освобождаем устройство, иначе оно останется занятым и недоступным для других попыток.
        cap.release()
        return None
    return cap


def list_devices(max_probe: int = 10, backend: Optional[int] = None) -> List[int]:
    """Пробник устройств: пытаемся открыть индексы 0..max_probe-1.

    Это нужно, чтобы найти все доступные камеры и потом позволить переключаться между ними по TAB.
    """
    backend = backend if backend is not None else pick_backend()
    # On macOS, AVFoundation doesn't enumerate by index beyond 0; limit probing to a single index.
    if is_macos():
        max_probe = 1
    found = []
    for i in range(max_probe):
        cap = cv.VideoCapture(i, backend)
        if cap.isOpened():
            ok, frame = cap.read()
            if ok and frame is not None:
                found.append(i)
            cap.release()
    return found


def put_label(img, text: str, org: Tuple[int, int], scale=0.6, thickness=2):
    cv.putText(img, text, org, cv.FONT_HERSHEY_SIMPLEX, scale, (0,0,0), thickness+3, cv.LINE_AA)
    cv.putText(img, text, org, cv.FONT_HERSHEY_SIMPLEX, scale, (255,255,255), thickness, cv.LINE_AA)


def overlay_status(frame, status: str, color: Tuple[int,int,int]):
    h, w = frame.shape[:2]
    pad = 12
    text = f" {status} "
    (tw, th), _ = cv.getTextSize(text, cv.FONT_HERSHEY_SIMPLEX, 1.0, 2)
    x = (w - tw) // 2 - pad
    y = 40
    cv.rectangle(frame, (x, y - th - pad), (x + tw + 2*pad, y + pad), color, -1)
    cv.putText(frame, text, (x + pad, y), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,0), 3, cv.LINE_AA)
    cv.putText(frame, text, (x + pad, y), cv.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2, cv.LINE_AA)


def overlay_hint(frame, lines):
    y = 80
    for line in lines:
        put_label(frame, line, (20, y), scale=0.6, thickness=1)
        y += 26


def draw_header(frame, info: str):
    # полупрозрачная плашка сверху
    overlay = frame.copy()
    cv.rectangle(overlay, (0,0), (frame.shape[1], 28), (0,0,0), -1)
    frame[:] = cv.addWeighted(overlay, 0.35, frame, 0.65, 0)
    put_label(frame, info, (10, 20), scale=0.55, thickness=1)


def make_canvas(w: int, h: int):
    import numpy as np
    return np.zeros((h, w, 3), dtype=np.uint8)


BUTTONS = {}
def draw_buttons(frame):
    # Рисуем две кнопки в правом верхнем углу
    h, w = frame.shape[:2]
    pad = 10
    btn_h = 28
    labels = [("Next", (200, 200, 200)), ("Close", (80, 80, 80))]
    rects = []
    x = w - pad
    for text, color in reversed(labels):
        (tw, th), _ = cv.getTextSize(text, cv.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        bw = tw + 20
        x0 = x - bw
        y0 = pad
        x1 = x
        y1 = pad + btn_h
        cv.rectangle(frame, (x0, y0), (x1, y1), color, -1)
        put_label(frame, text, (x0 + 10, y0 + 19), scale=0.55, thickness=1)
        rects.append((text, (x0, y0, x1, y1)))
        x -= (bw + 8)
    # сохраняем актуальные области
    BUTTONS.clear()
    for name, rect in rects:
        BUTTONS[name] = rect


def on_mouse(event, x, y, flags, userdata):
    if event != cv.EVENT_LBUTTONDOWN:
        return
    for name, (x0, y0, x1, y1) in BUTTONS.items():
        if x0 <= x <= x1 and y0 <= y <= y1:
            if name.startswith("✕"):
                userdata["running"][0] = False
            elif name.startswith("Next"):
                userdata["switch_device"][0] = True


def main():
    # Конфиг по умолчанию
    cfg = {
        "device": None,       # индекс камеры или None для авто
        "width": None,        # желаемая ширина (или None)
        "height": None,       # желаемая высота (или None)
        "max_probe": 8,       # сколько индексов пробовать при поиске
        "title": "Camera Toggle",  # заголовок окна
    }

    backend = pick_backend()
    devices = list_devices(cfg["max_probe"], backend)
    if not devices:
        print("Камеры не найдены. На macOS дайте доступ к камере: System Settings → Privacy & Security → Camera → включите для Terminal/VS Code. "
              "Если запрос не появляется, выполните в терминале: `tccutil reset Camera` (при необходимости: `tccutil reset Camera com.apple.Terminal` или `tccutil reset Camera com.microsoft.VSCode`) и перезапустите приложение. "
              "Также закройте другие приложения, использующие камеру (FaceTime/Zoom/Meet).")
        return

    # Выбор устройства
    current_idx = cfg["device"] if cfg["device"] is not None else devices[0]
    if current_idx not in devices:
        print(f"Камера {current_idx} недоступна. Доступные: {devices}")
        current_idx = devices[0]

    cap = try_open_device(current_idx, backend, cfg["width"], cfg["height"])
    permission_mode = False
    if cap is None:
        # Не удаётся открыть сразу — возможно, нет разрешения или устройство занято.
        permission_mode = True
        # создаём холст и окно сразу, чтобы показать подсказку
        cv.namedWindow(cfg["title"], cv.WINDOW_NORMAL)
        cv.resizeWindow(cfg["title"], 960, 540)
    else:
        cv.namedWindow(cfg["title"], cv.WINDOW_NORMAL)
        cv.resizeWindow(cfg["title"], 960, 540)

    shared = {"running": [True], "switch_device": [False]}
    cv.setMouseCallback(cfg["title"], on_mouse, shared)
    running = shared["running"][0]

    last_time = time.time()
    fps = 0.0
    frame_count = 0

    backend_name = {
        cv.CAP_DSHOW: "DShow",
        cv.CAP_V4L2: "V4L2",
        cv.CAP_AVFOUNDATION: "AVF",
    }.get(backend, f"{backend}")

    while running:
        running = shared["running"][0]

        # Режим подсказки разрешений / занятости устройства 
        if permission_mode:
            w = cfg["width"] or 640
            h = cfg["height"] or 480
            frame = make_canvas(w, h)
            overlay_status(frame, "NO PERMISSION" if is_macos() else "DEVICE BUSY", (0, 0, 180))
            hint_lines = [
                "Камера недоступна. Вероятно нет разрешения или устройство занято.",
            ]
            if is_macos():
                hint_lines += [
                    "macOS: System Settings → Privacy & Security → Camera",
                    "Включите доступ для Terminal/VS Code.",
                    "Если запрос не появляется: tccutil reset Camera",
                    "Нажмите TAB или кнопку Next, чтобы переключить устройство.",
                ]
            else:
                hint_lines += [
                    "Закройте приложения, которые используют камеру (Zoom/FaceTime/Meet).",
                    "Нажмите TAB или кнопку Next, чтобы переключить устройство.",
                ]
            draw_header(frame, f"Dev {current_idx} | Backend: {backend_name} | WAITING")
            overlay_hint(frame, hint_lines)
            draw_buttons(frame)
            cv.imshow(cfg["title"], frame)

            key = cv.waitKey(60) & 0xFF
            if key in (27, ord('q')):
                shared["running"][0] = False
                continue
            if key == 9 or shared["switch_device"][0]:
                shared["switch_device"][0] = False
                # переключить устройство
                if cap and cap.isOpened():
                    cap.release()
                if not devices:
                    devices = list_devices(cfg["max_probe"], backend)
                    if not devices:
                        print("Нет доступных камер.")
                        continue
                if current_idx not in devices:
                    current_idx = devices[0]
                else:
                    pos = devices.index(current_idx)
                    current_idx = devices[(pos + 1) % len(devices)]
                print(f"Переключаюсь на устройство {current_idx}")
                cap = try_open_device(current_idx, backend, cfg["width"], cfg["height"])
                if cap is None:
                    print(f"Не удалось открыть {current_idx}, остаёмся в режиме ожидания.")
                    permission_mode = True
                else:
                    permission_mode = False
            continue

        # Обычный режим работы
        ok, frame = cap.read()
        if not ok or frame is None:
            # Камера пропала/занята? Переходим в режим подсказки.
            permission_mode = True
            continue

        # FPS расчёт
        now = time.time()
        frame_count += 1
        if now - last_time >= 0.5:
            fps = frame_count / (now - last_time)
            frame_count = 0
            last_time = now

        w = int(cap.get(cv.CAP_PROP_FRAME_WIDTH)) if cap.isOpened() else (cfg["width"] or 640)
        h = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT)) if cap.isOpened() else (cfg["height"] or 480)
        info = f"Dev {current_idx} | {w}x{h} | Backend: {backend_name} | FPS: {fps:.1f}"
        draw_header(frame, info)
        overlay_status(frame, "LIVE", (0,140,0))

        draw_buttons(frame)

        cv.imshow(cfg["title"], frame)
        key = cv.waitKey(1) & 0xFF

        if key in (27, ord('q')):
            shared["running"][0] = False
        elif key == 9 or shared["switch_device"][0]:
            shared["switch_device"][0] = False
            if cap.isOpened():
                cap.release()
            if not devices:
                devices = list_devices(cfg["max_probe"], backend)
                if not devices:
                    print("Нет доступных камер.")
                    continue
            if current_idx not in devices:
                current_idx = devices[0]
            else:
                pos = devices.index(current_idx)
                current_idx = devices[(pos + 1) % len(devices)]
            print(f"Переключаюсь на устройство {current_idx}")
            cap = try_open_device(current_idx, backend, cfg["width"], cfg["height"])
            if cap is None:
                print(f"Не удалось открыть {current_idx}, переходим в режим ожидания.")
                permission_mode = True

    # Чистое завершение
    if cap and cap.isOpened():
        cap.release()
    cv.destroyAllWindows()


if __name__ == "__main__":
    main()