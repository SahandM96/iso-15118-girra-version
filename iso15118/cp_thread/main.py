""" imports in here"""
import time
from watchdog.observers import Observer


from handler import MyEventHandler


PATH = "/home/sahandm96/watch_dir/"

event_handler = MyEventHandler()
observer = Observer()
observer.schedule(event_handler, PATH, recursive=True)
observer.start()

try:
    while True:
        time.sleep(0.5)
finally:
    observer.stop()
    observer.join()
