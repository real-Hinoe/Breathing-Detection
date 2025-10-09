from PyQt5.QtWidgets import QWidget, QPushButton, QLabel
from PyQt5.QtCore import QThread, Qt, pyqtSignal, pyqtSlot, QObject, QEvent
from PyQt5.QtGui import QPixmap, QImage
from PyQt5 import QtWidgets
import numpy as np
import cv2


class VideoThread(QThread):

    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.run_flag = True

    def run(self):
        cap = cv2.VideoCapture(0) 
        while self.run_flag:
            ret, cv_img = cap.read()
            cv2.waitKey(1)
            if ret:
                self.change_pixmap_signal.emit(cv_img)
        cap.release()

    def stop(self):
        self.run_flag = False
        self.wait()


def convert_cv_qt(cv_img):
    rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb_image.shape
    bytes_per_line = ch * w
    qimg = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
    qimg = qimg.scaled(w, h)
    return QPixmap.fromImage(qimg)


class AutoBinder(QObject):
   
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.threads = {}  
        app.installEventFilter(self)

    def eventFilter(self, obj, event):
        if isinstance(obj, QWidget):
            if event.type() == QEvent.Show:
                self.try_start(obj)
            elif event.type() in (QEvent.Hide, QEvent.Close):
                self.try_stop(obj)
        return super().eventFilter(obj, event)

    def get_label(self, window):
        try:
            holder = getattr(window, "video_holder", None)
            if holder is None or not hasattr(holder, "inner_widget"):
                return None
            return holder.inner_widget()
        except Exception:
            return None

    def try_start(self, window):
        if id(window) in self.threads:
            return
        label = self.get_label(window)
        if not isinstance(label, QLabel):
            return

        t = VideoThread()
        
        @pyqtSlot(np.ndarray)
        def update(cv_img):
            qt_img = convert_cv_qt(cv_img)
            qt_img = qt_img.scaled(label.width(), label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(qt_img)

        t.change_pixmap_signal.connect(update)
        t.start()
        self.threads[id(window)] = (t, update)

        info = getattr(window, "info_label", None)
        if isinstance(info, QLabel):
            info.setText("Камера: работает")

        btn = getattr(window, "btn_back", None)
        if isinstance(btn, QPushButton):
            try:
                btn.clicked.disconnect(self.on_back)
            except Exception:
                pass
            btn.clicked.connect(self.on_back)

    def try_stop(self, window):
        key = id(window)
        pair = self.threads.pop(key, None)
        if pair:
            t, update = pair
            try:
                t.change_pixmap_signal.disconnect(update)
            except Exception:
                pass
            t.stop()

            label = self.get_label(window)
            if isinstance(label, QLabel):
                label.setPixmap(QPixmap())

    def on_back(self):
        btn = self.sender()
        if not isinstance(btn, QPushButton):
            return
        win = btn.window()
        self.try_stop(win)
        try:
            win.close()
        except Exception:
            pass


def bootstrap():
    app = QtWidgets.QApplication.instance()
    if app is not None and not hasattr(app, "_mini_cam_binder"):
        app._mini_cam_binder = AutoBinder(app)


def patch_qapp_init_once():
    if hasattr(QtWidgets.QApplication, "__mini_cam_patched__"):
        return
    orig = QtWidgets.QApplication.__init__
    def wrapped(self, *a, **kw):
        orig(self, *a, **kw)
        bootstrap()
    QtWidgets.QApplication.__init__ = wrapped
    QtWidgets.QApplication.__mini_cam_patched__ = True


bootstrap()
patch_qapp_init_once()