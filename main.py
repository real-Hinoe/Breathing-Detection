import os
import sys
import traceback
from PyQt5 import QtWidgets
from gui import MainWindow


if __name__ == "__main__":
    # чтобы убрать предупреждение TensorFlow
    os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

    def exception_hook(exctype, value, tb):
        """Custom hook to print the traceback to console."""
        traceback_formated = "".join(
            traceback.format_exception(exctype, value, tb))
        print(traceback_formated)
        # Optional: sys.exit(1) to force exit on error
        sys.exit(1)

    # Attach the hook
    sys.excepthook = exception_hook

    app = QtWidgets.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec_())
