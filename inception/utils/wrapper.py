"""
Simple wrappers of various Python standard library modules
"""

import threading
import traceback


class FuncThread(threading.Thread):
    """
    thread of calling a partial function, based on the regular thread
    by adding a shared-with-others exception queue
    """
    def __init__(self, func, exception_queue):
        threading.Thread.__init__(self)
        self._func = func
        self._exception_queue = exception_queue

    def run(self):
        """
        Call the function, and put exception in queue if any
        """
        try:
            self._func()
        except Exception:
            func_info = (str(self._func.func) + " " + str(self._func.args) +
                         " " + str(self._func.keywords))
            info = (self.name, func_info, traceback.format_exc())
            print info
            self._exception_queue.put(info)
