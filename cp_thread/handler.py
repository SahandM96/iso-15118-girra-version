import zmq
import logging
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler



path = "/home/sahandm96/watch_dir/"
context = zmq.Context()


class MyEventHandler(FileSystemEventHandler):

    def on_moved(self, event):
        what = 'directory' if event.is_directory else 'file'
        if what == 'file':
            logger.info("on_moved")
            print(event)
        logging.info("Moved %s: from %s to %s", what, event.src_path,
                     event.dest_path)

    def on_created(self, event):
        what = 'directory' if event.is_directory else 'file'
        if what == 'file':
            logger.info("on_created")
            print(event)
        logging.info("Created %s: %s", what, event.src_path)

    def on_deleted(self, event):
        what = 'directory' if event.is_directory else 'file'
        if what == 'file':
            logger.info("on_deleted")
            print(event)
        logging.info("Deleted %s: %s", what, event.src_path)

    def on_modified(self, event):
        what = 'directory' if event.is_directory else 'file'
        if what == 'file':
            logger.info("on_modified")
            print(event)
        logging.info("Modified %s: %s", what, event.src_path)


event_handler = MyEventHandler()
observer = Observer()
observer.schedule(event_handler, path, recursive=True)
observer.start()

try:
    logger = logging.getLogger(__name__)
    while True:
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://localhost:5555")

        logger.info("Started")
        time.sleep(0.5)
finally:
    observer.stop()
    observer.join()
