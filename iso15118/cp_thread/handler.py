""" imports in here"""
import logging
from watchdog.events import FileSystemEventHandler
from iso15118.cp_thread.zmq_handler import zmq_run_server
from iso15118.cp_thread.value_metric import set_cp_value
PATH = "/home/sahandm96/watch_dir/"

logger = logging.getLogger(__name__)


class MyEventHandler(FileSystemEventHandler):
    """ My Handler """

    def on_moved(self, event):
        super().on_moved(event)
        zmq_run_server("on_moved")

    def on_created(self, event):
        super().on_created(event)
        zmq_run_server("on_created")

    def on_deleted(self, event):
        super().on_deleted(event)
        zmq_run_server("on_deleted")

    def on_modified(self, event):
        super().on_modified(event)
        what = 'directory' if event.is_directory else 'file'
        if what == 'file':
            if event.src_path == '/home/sahandm96/watch_dir/cp_adc':
                with open("/home/sahandm96/watch_dir/cp_adc") as file_cp_adc:
                    value = str(file_cp_adc.read()).strip()
                    set_cp_value(int(value))
                    zmq_run_server(value)

