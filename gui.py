from PyQt5 import QtWidgets, QtCore, QtGui


# Центрирует виджет на экране.
# - widget: любой QWidget (обычно окно)
# - width, height: желаемый размер в пикселях.
# Ничего не возвращает, просто меняет геометрию виджета.
def center_widget_on_screen(widget, width, height):
    geom = QtWidgets.QApplication.primaryScreen().availableGeometry()
    x = geom.x() + (geom.width() - width) // 2
    y = geom.y() + (geom.height() - height) // 2
    widget.setGeometry(x, y, width, height)


# AspectLabel
# - Класс нужен для того, чтобы внутри иметь "вписываемую" 16:9 область.
# - Содержит _inner (QLabel) - в него в будущем можно ставить картинку или видео.
# - При изменении размера внешнего виджета _inner автоматически центрируется
#   и сохраняет пропорцию 16:9.
class AspectLabel(QtWidgets.QLabel):
    def __init__(self, parent=None, bg_color=QtGui.QColor(200, 200, 200)):
        super().__init__(parent)
        # внутренний QLabel - сюда будут класть видео/картинку
        self._inner = QtWidgets.QLabel(self)
        self._inner.setAlignment(QtCore.Qt.AlignCenter)
        # задаём фон и рамку, чтобы было видно границы
        self._inner.setStyleSheet(f"background-color: {bg_color.name()}; border: 1px solid #444;")
        # минимум 16x9 пикселей - это не реальный размер, а защита от полного схлопывания
        # по сути уже не нужна, т.к. размеры окна у нас фиксированные
        self._inner.setMinimumSize(16, 9)

    # В этом методе вычисляем максимально возможный 16:9 прямоугольник,
    # который умещается в текущем размере внешнего QLabel, и ставим его по центру.
    def resizeEvent(self, event):
        tw, th = self.width(), self.height()
        target_w = tw
        target_h = int(target_w * 9 / 16)
        if target_h > th:
            target_h = th
            target_w = int(target_h * 16 / 9)
        x = (tw - target_w) // 2
        y = (th - target_h) // 2
        self._inner.setGeometry(x, y, target_w, target_h)
        super().resizeEvent(event)

    # Возвращает внутренний QLabel - удобно, когда нужно положить туда картинку
    # или обращаться к нему из внешнего кода.
    def inner_widget(self):
        return self._inner


# styled_tile_button
# - Простая "фабрика" кнопок одного стиля.
# - text: текст на кнопке, width/height/font_px - размеры в пикселях.
# - parent необязателен.
# Возвращает готовый QPushButton с градиентом и скруглением.
def styled_tile_button(text, width, height, font_px, parent=None):
    btn = QtWidgets.QPushButton(text, parent)
    btn.setFixedSize(width, height)
    btn.setStyleSheet(f"""
        QPushButton {{
            border: none;
            color: white;
            font-weight: 700;
            font-size: {font_px}px;
            border-radius: {max(6, height//8)}px;
            padding: 8px 16px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #3a7bd5, stop:1 #654ea3);
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #4d8ee8, stop:1 #7b5fcf);
        }}
        QPushButton:pressed {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #305ea8, stop:1 #573d86);
        }}
    """)
    return btn


# CameraWindow
# - Окно-плейсхолдер под камеру/калибровку.
# - base_size: QtCore.QSize - размер, который нужно использовать для окна.
# - btn_w, btn_h, font_px - размеры и шрифт кнопки "Вернуться".
# - Имеет сигнал closed, который испускается при закрытии окна.
class CameraWindow(QtWidgets.QMainWindow):
    closed = QtCore.pyqtSignal()

    def __init__(self, base_size: QtCore.QSize, btn_w, btn_h, font_px, parent=None):
        super().__init__(parent)
        self.btn_back = None
        self.info_label = None
        self.video_holder = None
        self.setWindowTitle("Окно калибровки (временно просто камера)")
        # ставим флаг "поверх других окон" и убираем кнопки масштабирования
        flags = self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
        flags = flags & ~QtCore.Qt.WindowMinMaxButtonsHint
        self.setWindowFlags(flags)
        self.init_ui(base_size, btn_w, btn_h, font_px)

    # Собирает UI:
    # - верхняя часть (stretch=9) - AspectLabel для видео,
    # - нижняя часть (stretch=1) - текст подсказки,
    # - кнопка "Вернуться" позиционируется в правом-низу окна.
    def init_ui(self, base_size, btn_w, btn_h, font_px):
        w, h = base_size.width(), base_size.height()
        central = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(central)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        self.video_holder = AspectLabel(bg_color=QtGui.QColor(220, 235, 255))
        self.video_holder.inner_widget().setText("Плейсхолдер камеры\n(16:9)")
        vbox.addWidget(self.video_holder, stretch=9)

        bottom = QtWidgets.QFrame()
        bottom.setFrameShape(QtWidgets.QFrame.StyledPanel)
        bottom.setMinimumHeight(max(24, int(h*0.1)))
        bl = QtWidgets.QHBoxLayout(bottom)
        bl.setContentsMargins(8, 4, 8, 4)
        # Текст здесь временный - позже сюда будут попадать подсказки от анализа видео
        self.info_label = QtWidgets.QLabel("Тут будут команды типа "
                                           "выпрямите спину, смотрите в "
                                           "камеру и т.п.")
        bl.addWidget(self.info_label)
        vbox.addWidget(bottom, stretch=1)

        self.setCentralWidget(central)

        # фиксируем размер окна, чтобы кнопка была в ожидаемом месте
        self.setFixedSize(w, h)

        # кнопка возврата в правом-низу - позиция вычисляется от размера окна
        self.btn_back = styled_tile_button("Вернуться", btn_w, btn_h, font_px, parent=self)
        margin = 12
        bx = self.width() - btn_w - margin
        by = self.height() - btn_h - margin
        self.btn_back.move(bx, by)
        self.btn_back.setParent(self)
        self.btn_back.show()

    # При показе окна - поднимаем и активируем его.
    def show(self):
        super().show()
        self.raise_()
        self.activateWindow()

    # При закрытии - испускаем сигнал closed. Владелец (MainWindow) на это подписан.
    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)


# GameWindow
# - Шаблон игрового окна.
# - base_size: QtCore.QSize - размер окна; level - номер уровня.
# - Есть верхняя игровая область (AspectLabel) и нижняя строка статуса.
# - Кнопка "Вернуться" в правом-низу закрывает окно.
# - При закрытии эмитится сигнал closed.
class GameWindow(QtWidgets.QMainWindow):
    closed = QtCore.pyqtSignal()

    def __init__(self, base_size: QtCore.QSize, level: int = 1,
                 parent=None, back_btn_w=120, back_btn_h=40, back_font=12):
        super().__init__(parent)
        self.btn_back = None
        self.status_label = None
        self.game_holder = None
        self.level = level
        self._back_btn_w = back_btn_w
        self._back_btn_h = back_btn_h
        self._back_font = back_font
        self.setWindowTitle(f"Игра - уровень {level}")
        self.init_ui(base_size)

    # Собирает игровое окно:
    # - AspectLabel сверху 9 частей,
    # - строка статуса снизу 1 часть,
    # - кнопка "Вернуться" — по правому-низу.
    def init_ui(self, base_size):
        w, h = base_size.width(), base_size.height()
        central = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(central)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        self.game_holder = AspectLabel(bg_color=QtGui.QColor(240, 240, 240))
        self.game_holder.inner_widget().setText(f"Игровая зона (уровень {self.level})\n16:9")
        vbox.addWidget(self.game_holder, stretch=9)

        bottom = QtWidgets.QFrame()
        bottom.setFrameShape(QtWidgets.QFrame.StyledPanel)
        bottom.setMinimumHeight(max(24, int(h*0.1)))
        bl = QtWidgets.QHBoxLayout(bottom)
        bl.setContentsMargins(8, 4, 8, 4)
        # Тут будут отображаться игровые значения или результаты анализа дыхания
        self.status_label = QtWidgets.QLabel("Тут игровые значения и/или "
                                             "информация о правильности дыхания")
        bl.addWidget(self.status_label)
        vbox.addWidget(bottom, stretch=1)

        self.setCentralWidget(central)
        # фиксируем размер окна
        self.setFixedSize(w, h)

        # кнопка возврата - позиционируем в правом-низу,
        # используем width/height окна, чтобы позиция не уезжала
        self.btn_back = styled_tile_button("Вернуться", self._back_btn_w,
                                           self._back_btn_h, self._back_font, parent=self)
        margin = 12
        bx = self.width() - self._back_btn_w - margin
        by = self.height() - self._back_btn_h - margin
        self.btn_back.move(bx, by)
        self.btn_back.show()
        # при нажатии - закрываем окно и эмитим сигнал closed
        self.btn_back.clicked.connect(self._on_back_clicked)

    def _on_back_clicked(self):
        self.close()
        self.closed.emit()


# MainWindow - главное окно с меню и страницами.
# - Хранит ссылки на активные окна камеры и уровня, чтобы не открывать дубликаты.
# - Размер главного окна - половина экрана, но не меньше 400x300.
# - Использует QStackedWidget для переключения между меню/выбором уровня/настройками.
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.stack = None
        self.setWindowTitle("Меню")
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        self.win_width = max(400, screen.width()//2)
        self.win_height = max(300, screen.height()//2)

        # размеры плиток и шрифта считаем пропорционально главному окну
        self.tile_w = max(260, int(self.win_width*0.55))
        self.tile_h = max(64, int(self.win_height*0.14))
        self.font_px = max(14, int(self.tile_h*0.35))

        # размеры кнопок "вернуться" в дочерних окнах
        self.child_back_w = max(120, int(self.win_width*0.18))
        self.child_back_h = max(40, int(self.win_height*0.08))
        self.child_back_font = max(12, int(self.child_back_h*0.35))

        # здесь храним единственный экземпляр окна камеры и единственный экземпляр игрового окна
        self._camera_window = None
        self._game_window = None

        self.init_ui()
        # ставим окно по центру и фиксируем его размер
        center_widget_on_screen(self, self.win_width, self.win_height)
        self.setFixedSize(self.win_width, self.win_height)

    # Собираем интерфейс главного окна.
    # - меню: Играть/Настройки/Выход,
    # - выбор уровня: кнопки 1..4 и кнопка Назад,
    # - настройки: кнопка открытия окна камеры и кнопка Назад.
    def init_ui(self):
        central = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        self.stack = QtWidgets.QStackedWidget()
        main_layout.addWidget(self.stack,stretch=1)

        # меню приложения - три крупные плитки
        menu_page = QtWidgets.QWidget()
        ml = QtWidgets.QVBoxLayout(menu_page)
        ml.setAlignment(QtCore.Qt.AlignCenter)
        ml.setSpacing(max(12, int(self.win_height*0.04)))

        btn_play = styled_tile_button("Играть", self.tile_w, self.tile_h, self.font_px)
        btn_settings = styled_tile_button("Настройки", self.tile_w, self.tile_h, self.font_px)
        btn_exit = styled_tile_button("Выход", self.tile_w, self.tile_h, self.font_px)
        ml.addWidget(btn_play, alignment=QtCore.Qt.AlignCenter)
        ml.addWidget(btn_settings, alignment=QtCore.Qt.AlignCenter)
        ml.addWidget(btn_exit, alignment=QtCore.Qt.AlignCenter)
        self.stack.addWidget(menu_page)

        # страница выбора уровня
        lvl_page = QtWidgets.QWidget()
        ll = QtWidgets.QVBoxLayout(lvl_page)
        ll.setAlignment(QtCore.Qt.AlignCenter)
        ll.setSpacing(max(10, int(self.win_height*0.03)))
        lbl = QtWidgets.QLabel("Выберите уровень")
        lbl.setAlignment(QtCore.Qt.AlignCenter)
        lbl.setStyleSheet(f"font-size:{max(14, int(self.font_px*1.0))}px;")
        ll.addWidget(lbl)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(max(12, int(self.win_width*0.02)))
        level_btn_size = max(96, int(min(self.win_width, self.win_height)*0.16))
        level_font = max(14, int(level_btn_size*0.35))
        for i in range(1, 5):
            b = styled_tile_button(str(i), level_btn_size, level_btn_size, level_font)
            b.clicked.connect(self._make_level_click_handler(i))
            row.addWidget(b)
        ll.addLayout(row)

        # кнопка Назад - центр внизу
        back = styled_tile_button("Назад", self.tile_w, self.tile_h, self.font_px)
        back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        ll.addStretch()
        ll.addWidget(back, alignment=QtCore.Qt.AlignCenter)
        self.stack.addWidget(lvl_page)

        # страница настроек
        settings_page = QtWidgets.QWidget()
        sl = QtWidgets.QVBoxLayout(settings_page)
        sl.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        sl.setSpacing(max(12, int(self.win_height*0.03)))
        lbls = QtWidgets.QLabel("Настройки")
        lbls.setAlignment(QtCore.Qt.AlignCenter)
        lbls.setStyleSheet(f"font-size:{max(14, int(self.font_px*1.0))}px;")
        sl.addWidget(lbls)
        open_cam_btn = styled_tile_button("Открыть окно камеры", self.tile_w,
                                          self.tile_h, self.font_px)
        sl.addWidget(open_cam_btn, alignment=QtCore.Qt.AlignCenter)

        back2 = styled_tile_button("Назад", self.tile_w, self.tile_h, self.font_px)
        back2.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        sl.addStretch()
        sl.addWidget(back2, alignment=QtCore.Qt.AlignCenter)
        self.stack.addWidget(settings_page)

        # место для логов/ошибок - пока просто красный текст
        info = QtWidgets.QLabel("Тут будут отображаться всякие ошибки и сбои в программе,"
                                " ну или можно просто удалить")
        info.setStyleSheet("color:red")
        main_layout.addWidget(info)
        self.setCentralWidget(central)

        # связи кнопок - показываем нужные страницы или выполняем действия
        btn_play.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_settings.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        btn_exit.clicked.connect(self.safe_exit)
        open_cam_btn.clicked.connect(self.open_camera_window)

    # Возвращает обработчик для кнопки уровня.
    # - Если уже открыт игровой экран - просто активируем его.
    # - Иначе создаём новое окно, подписываемся на closed и показываем.
    def _make_level_click_handler(self, level):
        def handler():
            if self._game_window and self._game_window.isVisible():
                self._game_window.raise_()
                self._game_window.activateWindow()
                return
            base_size = QtCore.QSize(self.win_width, self.win_height)
            gw = GameWindow(base_size, level, self, self.child_back_w,
                            self.child_back_h, self.child_back_font)
            # при закрытии игрового окна main window должен убрать ссылку на него
            gw.closed.connect(self._on_game_window_closed)
            gw.setFixedSize(base_size.width(), base_size.height())
            center_widget_on_screen(gw, base_size.width(), base_size.height())
            gw.show()
            gw.raise_()
            gw.activateWindow()
            self._game_window = gw
        return handler

    # Здесь обнуляем ссылку на игровое окно, когда оно закрылось.
    def _on_game_window_closed(self):
        self._game_window = None

    # Открывает окно камеры - один экземпляр одновременно.
    # Если окно уже запущено, поднимаем его на передний план.
    def open_camera_window(self):
        if self._camera_window and self._camera_window.isVisible():
            self._camera_window.raise_()
            self._camera_window.activateWindow()
            return
        base_size = QtCore.QSize(self.win_width, self.win_height)
        self._camera_window = CameraWindow(base_size, self.child_back_w, self.child_back_h, self.child_back_font)
        # кнопка в окне камеры возвращает сюда
        self._camera_window.btn_back.clicked.connect(self._camera_back_clicked)
        self._camera_window.closed.connect(self._on_camera_closed)
        self._camera_window.setFixedSize(base_size.width(), base_size.height())
        center_widget_on_screen(self._camera_window, base_size.width(), base_size.height())
        self._camera_window.show()
        self._camera_window.raise_()
        self._camera_window.activateWindow()

    # Закрытие окна камеры через кнопку "Вернуться"
    def _camera_back_clicked(self):
        if self._camera_window:
            self._camera_window.close()
        self.raise_()
        self.activateWindow()

    # Убираем ссылку на окно камеры после его закрытия.
    def _on_camera_closed(self):
        self._camera_window = None

    # Безопасный выход:
    # - если есть открытые дочерние окна, закрываем их
    # - затем вызываем quit приложения.
    def safe_exit(self):
        if self._game_window:
            self._game_window.close()
        if self._camera_window:
            self._camera_window.close()
        QtWidgets.QApplication.instance().quit()
