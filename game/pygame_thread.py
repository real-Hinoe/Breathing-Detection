from PyQt5.QtCore import QThread, pyqtSignal
from .pygame_canvas import run_pygame_level


class PygameThread(QThread):
    """
    QThread, который крутит pygame-игру в отдельном потоке.
    _running используется как флаг мягкой остановки из Qt.
    """

    finished = pyqtSignal()

    def __init__(self, level: int):
        super().__init__()
        self.level = level
        self._running = True

    def run(self):
        # Передаём себя как внешний флаг; игра периодически проверяет _running
        run_pygame_level(self.level, external_running_flag=self)
        self.finished.emit()

    def stop(self):
        """Просим pygame-цикл завершиться."""
        self._running = False
