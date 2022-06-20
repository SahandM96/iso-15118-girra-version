""" imports in here"""
import logging
from watchdog.events import FileSystemEventHandler
from iso15118.cp_thread.zmq_handler import zmq_run_server

PATH = "/home/sahandm96/watch_dir/"

logger = logging.getLogger(__name__)


class MyEventHandler(FileSystemEventHandler):
    """ My Handler """

    def on_modified(self, event):
        what = 'directory' if event.is_directory else 'file'
        if what == 'file':
            if event.src_path == '/home/sahandm96/watch_dir/cp_adc':
                logger.info("File modified: %s", event.src_path)
                zmq_run_server
