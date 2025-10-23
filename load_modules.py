from concurrent.futures import ThreadPoolExecutor
import importlib
import sys

# только долго запускающиеся библиотеки
modules_to_load = ['mediapipe']


def do_import(module_name):
    """Функция, запускающаяся с атрибутом имени импортируемого модуля
    """
    thismodule = sys.modules[__name__]

    module = importlib.import_module(module_name)
    setattr(thismodule, module_name, module)
    print(module_name, 'imported')


executor = ThreadPoolExecutor()
for mod in modules_to_load:
    executor.submit(do_import, mod)
