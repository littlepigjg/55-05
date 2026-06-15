import os
import threading
from pathlib import Path
from typing import List, Optional, Callable, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileDeletedEvent, FileModifiedEvent

from ..scanner import SUPPORTED_EXTENSIONS


class IndexFileWatcher:
    def __init__(self, watch_dirs: Optional[List[str]] = None):
        self._watch_dirs: Set[str] = set()
        self._observer: Optional[Observer] = None
        self._event_handler: Optional[_IndexEventHandler] = None
        self._running = False

        self.on_file_added: Optional[Callable[[str], None]] = None
        self.on_file_deleted: Optional[Callable[[str], None]] = None
        self.on_file_modified: Optional[Callable[[str], None]] = None

        if watch_dirs:
            for d in watch_dirs:
                self._watch_dirs.add(str(Path(d).resolve()))

    def add_watch_directory(self, directory: str):
        abs_path = str(Path(directory).resolve())
        if abs_path not in self._watch_dirs:
            self._watch_dirs.add(abs_path)
            if self._running and self._observer:
                try:
                    self._observer.schedule(self._event_handler, abs_path, recursive=True)
                except Exception:
                    pass

    def remove_watch_directory(self, directory: str):
        abs_path = str(Path(directory).resolve())
        self._watch_dirs.discard(abs_path)

    def set_watch_directories(self, directories: List[str]):
        self._watch_dirs = set(str(Path(d).resolve()) for d in directories)

    def start(self):
        if self._running:
            return

        self._event_handler = _IndexEventHandler(
            supported_extensions=SUPPORTED_EXTENSIONS,
            on_created=self._on_created,
            on_deleted=self._on_deleted,
            on_modified=self._on_modified,
        )

        self._observer = Observer()

        for directory in self._watch_dirs:
            try:
                self._observer.schedule(self._event_handler, directory, recursive=True)
            except Exception:
                continue

        self._observer.daemon = True
        self._observer.start()
        self._running = True

    def stop(self):
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
        self._running = False

    def _on_created(self, file_path: str):
        if self.on_file_added:
            self.on_file_added(file_path)

    def _on_deleted(self, file_path: str):
        if self.on_file_deleted:
            self.on_file_deleted(file_path)

    def _on_modified(self, file_path: str):
        if self.on_file_modified:
            self.on_file_modified(file_path)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def watch_directories(self) -> List[str]:
        return list(self._watch_dirs)


class _IndexEventHandler(FileSystemEventHandler):
    def __init__(
        self,
        supported_extensions: Set[str],
        on_created: Callable[[str], None],
        on_deleted: Callable[[str], None],
        on_modified: Callable[[str], None],
    ):
        self._supported_extensions = supported_extensions
        self._on_created = on_created
        self._on_deleted = on_deleted
        self._on_modified = on_modified
        self._pending_events: dict = {}
        self._debounce_time = 1.0
        self._debounce_timer: Optional[threading.Timer] = None

    def _is_supported(self, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in self._supported_extensions

    def _queue_event(self, event_type: str, file_path: str):
        key = f"{event_type}:{file_path}"
        self._pending_events[key] = (event_type, file_path)
        self._schedule_dispatch()

    def _schedule_dispatch(self):
        if self._debounce_timer:
            self._debounce_timer.cancel()
        self._debounce_timer = threading.Timer(self._debounce_time, self._dispatch_events)
        self._debounce_timer.daemon = True
        self._debounce_timer.start()

    def _dispatch_events(self):
        events = list(self._pending_events.values())
        self._pending_events.clear()

        for event_type, file_path in events:
            try:
                if event_type == "created":
                    self._on_created(file_path)
                elif event_type == "deleted":
                    self._on_deleted(file_path)
                elif event_type == "modified":
                    self._on_modified(file_path)
            except Exception:
                pass

    def on_created(self, event):
        if not event.is_directory and self._is_supported(event.src_path):
            self._queue_event("created", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and self._is_supported(event.src_path):
            self._queue_event("deleted", event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self._is_supported(event.src_path):
            self._queue_event("modified", event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            return

        src_supported = self._is_supported(event.src_path)
        dest_supported = self._is_supported(event.dest_path)

        if src_supported and dest_supported:
            self._queue_event("deleted", event.src_path)
            self._queue_event("created", event.dest_path)
        elif src_supported:
            self._queue_event("deleted", event.src_path)
        elif dest_supported:
            self._queue_event("created", event.dest_path)
