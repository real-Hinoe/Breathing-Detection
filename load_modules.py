from concurrent.futures import ThreadPoolExecutor
import importlib
import logging
import sys

# только долго запускающиеся библиотеки
modules_to_load = ['mediapipe']
logger = logging.getLogger(__name__)


def do_import(module_name: str):
    """Функция, запускающаяся с атрибутом имени импортируемого модуля
    """
    thismodule = sys.modules[__name__]

    module = importlib.import_module(module_name)
    setattr(thismodule, module_name, module)
    logger.info(f"{module_name.capitalize()} imported")


executor = ThreadPoolExecutor()
for mod in modules_to_load:
    executor.submit(do_import, mod)
