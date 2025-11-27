import pygame
import os

pygame.init()

def analyze_image(path):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    surf = pygame.image.load(path)
    w, h = surf.get_size()
    print(f"Image: {path}")
    print(f"Size: {w}x{h}")

    # Find bottom-most non-transparent pixel
    bottom_y = -1
    for y in range(h - 1, -1, -1):
        for x in range(w):
            alpha = surf.get_at((x, y))[3]
            if alpha > 0:
                bottom_y = y
                break
        if bottom_y != -1:
            break

    if bottom_y != -1:
        padding = h - 1 - bottom_y
        print(f"Bottom non-transparent pixel at y={bottom_y}")
        print(f"Padding at bottom: {padding} pixels")
    else:
        print("Image is fully transparent")

analyze_image("resources/staying1.1.png")
