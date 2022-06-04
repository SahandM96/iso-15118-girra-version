""" imports in here"""
import time
from watchdog.observers import Observer
from iso15118.cp_thread.value_metric import set_cp_value
from iso15118.cp_thread.handler import MyEventHandler

PATH = "/home/sahandm96/watch_dir/"
set_cp_value(500)
event_handler = MyEventHandler()
observer = Observer()
observer.schedule(event_handler, PATH, recursive=True)


def run_cp_thread():
    observer.start()
    try:
        while True:
            time.sleep(0.5)
    finally:
        observer.stop()
        observer.join()
