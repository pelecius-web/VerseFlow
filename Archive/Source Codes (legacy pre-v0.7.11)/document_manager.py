"""document_manager.py — VerseFlow Category 1: Document Manager

Manages the lifecycle of a .verseplaylist document:
  - New / Open / Save / Save-As file operations
  - Dirty-state tracking
  - QUndoStack integration (all model mutations go through here)
  - Provides the single shared PlaylistModel and QueueModel instances
"""

from __future__ import annotations

import json
import uuid
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QUndoStack, QUndoCommand

from models import PlaylistModel, QueueModel


# ── File Format Constants ─────────────────────────────────────────────────────

PLAYLIST_VERSION = "1.0"
PLAYLIST_EXTENSION = ".verseplaylist"
MAX_BACKUPS = 3


# ── DocumentManager ───────────────────────────────────────────────────────────

class DocumentManager(QObject):
    """Central controller for a single .verseplaylist document.

    Signals:
        dirty_changed(bool)        — emitted when unsaved-state changes
        document_changed()         — emitted on any structural model change
        playlist_loaded(list)      — emitted after a file is loaded
        queue_loaded(list)         — emitted after queue section loads
        file_path_changed(str)     — emitted when the current file path changes
    """

    dirty_changed    = pyqtSignal(bool)
    document_changed = pyqtSignal()
    playlist_loaded  = pyqtSignal(list)
    queue_loaded     = pyqtSignal(list)
    file_path_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._current_file: Optional[Path] = None
        self._is_dirty: bool = False
        self._title: str = "Untitled Playlist"

        # Models — shared across the entire app
        self._playlist_model = PlaylistModel(self)
        self._queue_model = QueueModel(self)

        # Undo stack
        self._undo_stack = QUndoStack(self)
        self._undo_stack.setUndoLimit(100)

        # Track changes for dirty state
        self._playlist_model.items_changed.connect(self._mark_dirty)
        self._undo_stack.indexChanged.connect(self._on_undo_index_changed)

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def playlist_model(self) -> PlaylistModel:
        return self._playlist_model

    @property
    def queue_model(self) -> QueueModel:
        return self._queue_model

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack

    @property
    def is_dirty(self) -> bool:
        return self._is_dirty

    @property
    def current_file(self) -> Optional[Path]:
        return self._current_file

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str):
        if self._title != value:
            self._title = value
            self._mark_dirty()

    def display_name(self) -> str:
        """Human-readable name: filename or 'Untitled Playlist'."""
        if self._current_file:
            return self._current_file.stem
        return self._title or "Untitled Playlist"

    # ── Document Lifecycle ────────────────────────────────────────────────────

    def new_document(self):
        """Reset to a blank document."""
        self._playlist_model.clear()
        self._queue_model.clear_queue()
        self._undo_stack.clear()
        self._current_file = None
        self._title = "Untitled Playlist"
        self._set_dirty(False)
        self.file_path_changed.emit("")
        self.document_changed.emit()

    def open_file(self, path: Path) -> bool:
        """Load a .verseplaylist file. Returns True on success."""
        try:
            path = Path(path)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate version
            version = data.get("version", "1.0")
            meta = data.get("metadata", {})
            items = data.get("items", [])

            # Ensure every item has an id
            for it in items:
                it.setdefault("id", str(uuid.uuid4()))
                if it.get("type") == "queue_group":
                    for qi in it.get("queue_items", []):
                        qi.setdefault("id", str(uuid.uuid4()))

            self._playlist_model.set_items(items)
            self._queue_model.clear_queue()
            self._undo_stack.clear()

            self._title = meta.get("title", path.stem)
            self._current_file = path
            self._set_dirty(False)

            self.file_path_changed.emit(str(path))
            self.playlist_loaded.emit(items)
            self.document_changed.emit()

            print(f"[DOC] Opened '{path.name}' — {len(items)} items", flush=True)
            return True

        except Exception as e:
            print(f"[DOC] Failed to open '{path}': {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False

    def save(self) -> bool:
        """Save to the current file. Falls back to save_as if no file set."""
        if self._current_file is None:
            return False  # Caller should trigger a save-as dialog
        return self._write_to_file(self._current_file)

    def save_as(self, path: Path) -> bool:
        """Save to a new file path."""
        path = Path(path)
        if not path.suffix:
            path = path.with_suffix(PLAYLIST_EXTENSION)
        success = self._write_to_file(path)
        if success:
            self._current_file = path
            self.file_path_changed.emit(str(path))
        return success

    def _write_to_file(self, path: Path) -> bool:
        """Serialize and write the playlist to disk."""
        try:
            now = datetime.now(timezone.utc).isoformat()

            data = {
                "version": PLAYLIST_VERSION,
                "metadata": {
                    "title": self._title,
                    "created": now,   # TODO: preserve original created date
                    "modified": now,
                    "service_date": "",
                    "preacher": "",
                    "church": "",
                    "tags": [],
                },
                "items": self._playlist_model.get_items(),
            }

            # Write to temp file first, then rename (atomic-ish)
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            tmp.replace(path)

            # Rotate backups
            self._rotate_backups(path)

            self._set_dirty(False)
            print(f"[DOC] Saved '{path.name}'", flush=True)
            return True

        except Exception as e:
            print(f"[DOC] Failed to save '{path}': {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False

    def _rotate_backups(self, path: Path):
        """Keep up to MAX_BACKUPS rolling backups in a .backups/ subdirectory."""
        try:
            backup_dir = path.parent / ".backups"
            backup_dir.mkdir(exist_ok=True)
            stem = path.stem
            # Shift existing backups: .bak2 → .bak3, .bak1 → .bak2, current → .bak1
            for i in range(MAX_BACKUPS - 1, 0, -1):
                src = backup_dir / f"{stem}.bak{i}"
                dst = backup_dir / f"{stem}.bak{i + 1}"
                if src.exists():
                    src.replace(dst)
            bak1 = backup_dir / f"{stem}.bak1"
            if path.exists():
                shutil.copy2(str(path), str(bak1))
        except Exception as e:
            print(f"[DOC] Backup error: {e}", flush=True)

    # ── Undo / Redo ───────────────────────────────────────────────────────────

    def undo(self):
        self._undo_stack.undo()

    def redo(self):
        self._undo_stack.redo()

    def push_command(self, command: QUndoCommand):
        """Push a command onto the undo stack."""
        self._undo_stack.push(command)

    # ── Dirty State ───────────────────────────────────────────────────────────

    def _mark_dirty(self):
        self._set_dirty(True)

    def _set_dirty(self, dirty: bool):
        if self._is_dirty != dirty:
            self._is_dirty = dirty
            self.dirty_changed.emit(dirty)
            self.document_changed.emit()

    def _on_undo_index_changed(self, _index: int):
        """When undo stack changes, the document is modified."""
        self._mark_dirty()


# ── Undo Commands ─────────────────────────────────────────────────────────────

class AddToPlaylistCommand(QUndoCommand):
    """Insert a verse/queue-group into the playlist."""

    def __init__(self, model: PlaylistModel, item: dict, row: int = -1):
        label = f"Add '{item.get('reference', item.get('label', 'Item'))}' to Playlist"
        super().__init__(label)
        self._model = model
        self._item = dict(item)
        self._item.setdefault("id", str(uuid.uuid4()))
        self._row = row if row >= 0 else model.rowCount()

    def redo(self):
        self._model.insert_item(self._row, self._item)

    def undo(self):
        # Find by id in case list shifted
        for i in range(self._model.rowCount()):
            if self._model.item_at(i) and self._model.item_at(i).get("id") == self._item["id"]:
                self._model.remove_item(i)
                break


class RemoveFromPlaylistCommand(QUndoCommand):
    """Remove an item from the playlist."""

    def __init__(self, model: PlaylistModel, row: int):
        super().__init__(f"Remove Item from Playlist")
        self._model = model
        self._row = row
        self._item = model.item_at(row)

    def redo(self):
        for i in range(self._model.rowCount()):
            if self._model.item_at(i) and self._model.item_at(i).get("id") == self._item.get("id"):
                self._model.remove_item(i)
                break

    def undo(self):
        self._model.insert_item(self._row, self._item)


class MovePlaylistItemCommand(QUndoCommand):
    """Reorder an item in the playlist."""

    def __init__(self, model: PlaylistModel, from_row: int, to_row: int):
        super().__init__(f"Move Playlist Item")
        self._model = model
        self._from = from_row
        self._to = to_row

    def redo(self):
        self._model.move_item(self._from, self._to)

    def undo(self):
        self._model.move_item(self._to, self._from)


class AddToQueueCommand(QUndoCommand):
    """Add a verse to the queue."""

    def __init__(self, model: QueueModel, item: dict):
        label = f"Add '{item.get('reference', 'Verse')}' to Queue"
        super().__init__(label)
        self._model = model
        self._item = dict(item)
        self._item.setdefault("id", str(uuid.uuid4()))

    def redo(self):
        self._model.add_item(self._item)

    def undo(self):
        row = self._model.find_row_by_id(self._item["id"])
        if row >= 0:
            self._model.remove_item(row)


class RemoveFromQueueCommand(QUndoCommand):
    """Remove a verse from the queue."""

    def __init__(self, model: QueueModel, row: int):
        super().__init__("Remove from Queue")
        self._model = model
        self._row = row
        self._item = model.item_at(row)

    def redo(self):
        row = self._model.find_row_by_id(self._item.get("id", ""))
        if row >= 0:
            self._model.remove_item(row)

    def undo(self):
        self._model.insert_item(self._row, self._item)


class MoveQueueItemCommand(QUndoCommand):
    """Reorder an item in the queue."""

    def __init__(self, model: QueueModel, from_row: int, to_row: int):
        super().__init__("Move Queue Item")
        self._model = model
        self._from = from_row
        self._to = to_row

    def redo(self):
        self._model.move_item(self._from, self._to)

    def undo(self):
        self._model.move_item(self._to, self._from)


class ClearQueueCommand(QUndoCommand):
    """Clear the entire queue — stores full list for undo."""

    def __init__(self, model: QueueModel):
        super().__init__("Clear Queue")
        self._model = model
        self._snapshot: list[dict] = []

    def redo(self):
        self._snapshot = self._model.clear_queue()

    def undo(self):
        self._model.restore_queue(self._snapshot)
