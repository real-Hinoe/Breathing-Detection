import sys
import logging
from PyQt5.QtCore import QObject, pyqtSignal

MODULE_NAMES = ["__main__", "load_modules", "gui", "cam"]  # логируемые модули
FMT = "[%(asctime)s][%(name)s][%(levelname)s] > %(message)s"
DATEFMT = "%Y-%m-%d %H:%M:%S"
# Дублирование в стандартный вывод
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=FMT)


class LogHandler(QObject, logging.Handler):
    """
    Потокобезопасный обработчик логгера, эмитирующий сигнал при получении записи.
    """
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.log_signal.connect(self._append_to_log)
        self.text_edit = None
        # Задаем формат записи
        formatter = logging.Formatter(fmt=FMT, datefmt=DATEFMT)
        self.setFormatter(formatter)

    def emit(self, record):
        """Эта функция может вызываться из любого потока"""
        msg = self.format(record)
        # Передаём сообщение в GUI-поток через сигнал
        self.log_signal.emit(msg)

    def _append_to_log(self, msg):
        """Слот, выполняемый в GUI-потоке."""
        if hasattr(self, 'text_edit') and self.text_edit:
            self.text_edit.append(msg)

    def set_text_edit(self, text_edit):
        """Привязать QTextEdit для вывода."""
        self.text_edit = text_edit
