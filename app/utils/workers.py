from PyQt6.QtCore import QObject, pyqtSignal, QThread
from typing import List, Callable, Any


class AsyncWorker(QObject):
    """Generic async worker for background tasks"""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, task: Callable, *args, **kwargs):
        super().__init__()
        self.task = task
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.task(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class BatchWorker(QObject):
    """Worker for batch operations with progress reporting"""
    item_processed = pyqtSignal(int, object)  # index, result
    batch_finished = pyqtSignal(list)
    error = pyqtSignal(int, str)  # index, error message
    progress = pyqtSignal(int)  # percentage

    def __init__(self, items: List[Any], task: Callable):
        super().__init__()
        self.items = items
        self.task = task

    def run(self):
        results = []
        total = len(self.items)

        for i, item in enumerate(self.items):
            try:
                result = self.task(item)
                results.append(result)
                self.item_processed.emit(i, result)

                # Emit progress
                progress = int((i + 1) / total * 100)
                self.progress.emit(progress)

            except Exception as e:
                self.error.emit(i, str(e))
                results.append(None)

        self.batch_finished.emit(results)


def run_in_thread(task: Callable, finished_callback: Callable = None,
                  error_callback: Callable = None, *args, **kwargs) -> QThread:
    """Utility function to run a task in a separate thread"""
    thread = QThread()
    worker = AsyncWorker(task, *args, **kwargs)
    worker.moveToThread(thread)

    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    if finished_callback:
        worker.finished.connect(finished_callback)
    if error_callback:
        worker.error.connect(error_callback)

    thread.start()
    return thread