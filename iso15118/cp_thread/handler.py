""" imports in here"""
import logging
from watchdog.events import FileSystemEventHandler
from zmq_handler import run_server
PATH = "/home/sahandm96/watch_dir/"


class MyEventHandler(FileSystemEventHandler):
    """ My Handler """

    def on_moved(self, event):
        super().on_moved(event)
        run_server("on_moved")

    def on_created(self, event):
        super().on_created(event)
        run_server("on_created")

    def on_deleted(self, event):
        super().on_deleted(event)
        run_server("on_deleted")

    def on_modified(self, event):
        super().on_modified(event)
        what = 'directory' if event.is_directory else 'file'

        if what == 'file':
            run_server(what + " on_modified")
            logging.info("on_modified")
        logging.info("Modified %s: %s", what, event.src_path)
