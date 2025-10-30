import sys
from PyQt5 import QtWidgets
from gui import MainWindow


if __name__ == "__main__":
    # Загружаем тяжелые библиотеки в отдельном потоке
    exec(open("load_modules.py").read())
    app = QtWidgets.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec_())
