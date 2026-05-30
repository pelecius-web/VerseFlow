"""document_manager.py — VerseFlow Category 1: Document Manager

Manages the lifecycle of a .verseplaylist document:
  - New / Open / Save / Save-As file operations
  - Dirty-state tracking
  - QUndoStack integration (all model mutations go through here)
  - Provides the single shared PlaylistModel and QueueModel instances
"""

from __future__ import annotations

import json
import logging
import uuid
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QUndoStack, QUndoCommand

from models import PlaylistModel, QueueModel

logger = logging.getLogger("VerseFlow")


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
        backup_warning(str)        — emitted when auto-backup fails non-fatally
    """

    dirty_changed    = pyqtSignal(bool)
    document_changed = pyqtSignal()
    playlist_loaded  = pyqtSignal(list)
    queue_loaded     = pyqtSignal(list)
    file_path_changed = pyqtSignal(str)
    title_changed    = pyqtSignal(str)
    metadata_changed = pyqtSignal()
    backup_warning   = pyqtSignal(str)   # emitted when auto-backup fails non-fatally

    def __init__(self, parent=None):
        super().__init__(parent)

        self._current_file: Optional[Path] = None
        self._is_dirty: bool = False
        self._title: str = "Untitled Playlist"
        
        # Metadata fields
        self._service_date: str = ""
        self._preacher: str = ""
        self._church: str = ""
        self._tags: list[str] = []
        self._created_at: str = ""

        # Models — shared across the entire app
        self._playlist_model = PlaylistModel(self)
        self._queue_model = QueueModel(self)

        # Undo stack
        self._undo_stack = QUndoStack(self)
        self._undo_stack.setUndoLimit(100)

        # Track changes for dirty state via Undo Stack
        self._undo_stack.cleanChanged.connect(self._on_clean_changed)

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
            self.push_command(SetTitleCommand(self, value))

    def set_metadata(self, metadata_dict: dict):
        """Update metadata via undo command."""
        self.push_command(SetMetadataCommand(self, metadata_dict))

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
        self._service_date = ""
        self._preacher = ""
        self._church = ""
        self._tags = []
        self._created_at = datetime.now(timezone.utc).isoformat()
        self._undo_stack.setClean()
        self._set_dirty(False)
        self.file_path_changed.emit("")
        self.document_changed.emit()

    def open_file(self, path: Path) -> tuple[bool, str]:
        """Load a .verseplaylist file.

        Returns:
            (True, "")        on success.
            (False, msg)      on failure, where msg is a human-readable error.
        """
        try:
            path = Path(path)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate data structure
            if not isinstance(data, dict):
                raise ValueError(f"Invalid playlist format: expected object, got {type(data).__name__}")
            
            version = data.get("version", "1.0")
            meta = data.get("metadata", {})
            items = data.get("items", [])
            
            # Validate items is a list (not string, dict, int, etc.)
            if not isinstance(items, list):
                raise ValueError(f"Invalid 'items' field: expected list, got {type(items).__name__}")

            # Ensure every item has an id
            valid_items = []
            for it in items:
                # Skip non-dict items (null, string, etc.)
                if not isinstance(it, dict):
                    logger.warning("Skipping invalid playlist item: expected dict, got %s", type(it).__name__)
                    continue
                it.setdefault("id", str(uuid.uuid4()))
                if not isinstance(it.get("entry_id"), str) or not it.get("entry_id", "").strip():
                    it["entry_id"] = str(uuid.uuid4())
                
                # MIGRATION: Fix mojibake-corrupted references in existing saved files
                # ALWAYS reconstruct clean reference from book/chapter/verse fields
                # Only preserve verse range suffixes (e.g., "-17" from "John 3:16-17")
                if it.get("type") == "verse" and it.get("book") and it.get("chapter") is not None and it.get("verse") is not None:
                    original_ref = it.get("reference", "")
                    base_ref = f"{it['book']} {it['chapter']}:{it['verse']}"
                    
                    # Check if original has verse range suffix and preserve it
                    verse_str = str(it['verse'])
                    range_marker = f":{verse_str}-"
                    if range_marker in original_ref:
                        try:
                            idx = original_ref.find(range_marker)
                            if idx != -1:
                                # Extract suffix after "-" (e.g., "17" from "John 3:16-17")
                                suffix_start = idx + len(range_marker)
                                suffix = original_ref[suffix_start:]
                                # Stop at space or non-digit
                                end_idx = 0
                                for i, c in enumerate(suffix):
                                    if not c.isdigit():
                                        break
                                    end_idx = i + 1
                                if end_idx > 0:
                                    it["reference"] = base_ref + "-" + suffix[:end_idx]
                                else:
                                    it["reference"] = base_ref
                            else:
                                it["reference"] = base_ref
                        except Exception:
                            it["reference"] = base_ref
                    else:
                        # No range suffix, use clean base reference
                        it["reference"] = base_ref
                
                if it.get("type") == "queue_group":
                    for qi in it.get("queue_items", []):
                        qi.setdefault("id", str(uuid.uuid4()))
                        if not isinstance(qi.get("entry_id"), str) or not qi.get("entry_id", "").strip():
                            qi["entry_id"] = str(uuid.uuid4())
                        
                        # MIGRATION: Also fix references in nested queue items
                        if qi.get("type") == "verse" and qi.get("book") and qi.get("chapter") is not None and qi.get("verse") is not None:
                            qi_original = qi.get("reference", "")
                            qi_base = f"{qi['book']} {qi['chapter']}:{qi['verse']}"
                            
                            # Check for verse range suffix
                            qi_verse_str = str(qi['verse'])
                            qi_range_marker = f":{qi_verse_str}-"
                            if qi_range_marker in qi_original:
                                try:
                                    qi_idx = qi_original.find(qi_range_marker)
                                    if qi_idx != -1:
                                        qi_suffix_start = qi_idx + len(qi_range_marker)
                                        qi_suffix = qi_original[qi_suffix_start:]
                                        qi_end_idx = 0
                                        for i, c in enumerate(qi_suffix):
                                            if not c.isdigit():
                                                break
                                            qi_end_idx = i + 1
                                        if qi_end_idx > 0:
                                            qi["reference"] = qi_base + "-" + qi_suffix[:qi_end_idx]
                                        else:
                                            qi["reference"] = qi_base
                                    else:
                                        qi["reference"] = qi_base
                                except Exception:
                                    qi["reference"] = qi_base
                            else:
                                qi["reference"] = qi_base
                
                # Add processed valid item to the filtered list
                valid_items.append(it)

            self._playlist_model.set_items(valid_items)
            self._queue_model.clear_queue()
            self._undo_stack.clear()
            self._undo_stack.setClean()

            self._title = meta.get("title", path.stem)
            self._service_date = meta.get("service_date", "")
            self._preacher = meta.get("preacher", "")
            self._church = meta.get("church", "")
            self._tags = meta.get("tags", [])
            self._created_at = meta.get("created", "")
            
            self._current_file = path
            self._set_dirty(False)

            self.file_path_changed.emit(str(path))
            self.title_changed.emit(self._title)
            self.playlist_loaded.emit(valid_items)
            self.queue_loaded.emit([])
            self.document_changed.emit()

            logger.info("Opened '%s' — %d items", path.name, len(valid_items))
            return True, ""

        except Exception as e:
            import traceback
            detail = traceback.format_exc()
            msg = f"{type(e).__name__}: {e}"
            logger.error("Failed to open '%s': %s", path, detail)
            return False, msg

    def save(self) -> tuple[bool, str]:
        """Save to the current file.

        Returns:
            (True, "")         on success.
            (False, "")        if no file is set yet — caller must trigger Save As.
            (False, msg)       on I/O failure.
        """
        if self._current_file is None:
            return False, ""  # Caller should trigger a save-as dialog
        return self._write_to_file(self._current_file)

    def save_as(self, path: Path) -> tuple[bool, str]:
        """Save to a new file path.

        Returns:
            (True, "")        on success.
            (False, msg)      on failure.
        """
        path = Path(path)
        if not path.suffix:
            path = path.with_suffix(PLAYLIST_EXTENSION)
        ok, msg = self._write_to_file(path)
        if ok:
            self._current_file = path
            self.file_path_changed.emit(str(path))
        return ok, msg

    def _write_to_file(self, path: Path) -> tuple[bool, str]:
        """Serialize and write the playlist to disk.

        Returns:
            (True, "")        on success.
            (False, msg)      on failure, where msg is a human-readable error.
        """
        try:
            now = datetime.now(timezone.utc).isoformat()

            data = {
                "version": PLAYLIST_VERSION,
                "metadata": {
                    "title": self._title,
                    "created": self._created_at or now,
                    "modified": now,
                    "service_date": self._service_date,
                    "preacher": self._preacher,
                    "church": self._church,
                    "tags": self._tags,
                },
                "items": self._playlist_model.get_items(),
            }

            # Rotate backups BEFORE overwriting the existing file.
            # _rotate_backups returns False and emits backup_warning on failure,
            # but we continue with the save regardless — user data must be preserved.
            self._rotate_backups(path)

            # Write to temp file first, then rename (atomic-ish)
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            tmp.replace(path)

            self._undo_stack.setClean()
            self._set_dirty(False)
            logger.info("Saved '%s'", path.name)
            return True, ""

        except Exception as e:
            import traceback
            detail = traceback.format_exc()
            msg = f"{type(e).__name__}: {e}"
            logger.error("Failed to save '%s': %s", path, detail)
            return False, msg

    def _rotate_backups(self, path: Path) -> bool:
        """Keep up to MAX_BACKUPS rolling backups in a .backups/ subdirectory.

        Returns True on success, False if backups could not be written.
        A False return does NOT prevent the main save from proceeding.
        """
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
            return True
        except Exception as e:
            msg = f"Auto-backup failed: {e}"
            logger.warning(msg)
            self.backup_warning.emit(msg)
            return False

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

    def _on_clean_changed(self, is_clean: bool):
        """When undo stack clean state changes, update dirty state."""
        self._set_dirty(not is_clean)


# ── Undo Commands ─────────────────────────────────────────────────────────────

class AddToPlaylistCommand(QUndoCommand):
    """Insert a verse/queue-group into the playlist."""

    def __init__(self, model: PlaylistModel, item: dict, row: int = -1):
        label = f"Add '{item.get('reference', item.get('label', 'Item'))}' to Playlist"
        super().__init__(label)
        self._model = model
        self._item = dict(item)
        self._item.setdefault("id", str(uuid.uuid4()))
        self._entry_id = self._item.setdefault("entry_id", str(uuid.uuid4()))
        self._row = row if row >= 0 else model.rowCount()

    def redo(self):
        self._model.insert_item(self._row, self._item)

    def undo(self):
        if not self._entry_id:
            return
        # Find by entry_id in case list shifted
        row = self._model.find_row_by_entry_id(self._entry_id)
        if row >= 0:
            self._model.remove_item(row)


class RemoveFromPlaylistCommand(QUndoCommand):
    """Remove an item from the playlist."""

    def __init__(self, model: PlaylistModel, row: int):
        super().__init__(f"Remove Item from Playlist")
        self._model = model
        self._row = row
        self._item = model.item_at(row)
        self._entry_id = self._item.get("entry_id") if self._item else ""

    def redo(self):
        if not self._item or not self._entry_id:
            return
        row = self._model.find_row_by_entry_id(self._entry_id)
        if row >= 0:
            self._model.remove_item(row)

    def undo(self):
        if not self._item:
            return
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
        self._entry_id = self._item.setdefault("entry_id", str(uuid.uuid4()))

    def redo(self):
        self._model.add_item(self._item)

    def undo(self):
        row = self._model.find_row_by_entry_id(self._entry_id)
        if row >= 0:
            self._model.remove_item(row)


class RemoveFromQueueCommand(QUndoCommand):
    """Remove a verse from the queue."""

    def __init__(self, model: QueueModel, row: int, display=None):
        super().__init__("Remove from Queue")
        self._model = model
        self._row = row
        self._item = model.item_at(row)
        self._entry_id = self._item.get("entry_id") if self._item else ""
        self._display = display
        self._was_live = (model.live_index == row)

    def redo(self):
        row = self._model.find_row_by_entry_id(self._entry_id)
        if row >= 0:
            if self._was_live and self._display:
                self._display.push_verse({})
            self._model.remove_item(row)

    def undo(self):
        self._model.insert_item(self._row, self._item)
        if self._was_live and self._display:
            self._display.push_verse(self._item)
            self._model.set_live(self._row)


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

    def __init__(self, model: QueueModel, display=None):
        super().__init__("Clear Queue")
        self._model = model
        self._display = display
        self._snapshot: list[dict] = []
        self._live_index = model.live_index
        self._live_verse = model.item_at(model.live_index) if self._live_index >= 0 else None

    def redo(self):
        if self._live_index >= 0 and self._display:
            self._display.push_verse({})
        self._snapshot = self._model.clear_queue()

    def undo(self):
        self._model.restore_queue(self._snapshot)
        if self._live_index >= 0 and self._display:
            self._display.push_verse(self._live_verse)
            self._model.set_live(self._live_index)


class SetTitleCommand(QUndoCommand):
    """Undoable command to change playlist title."""
    def __init__(self, doc_mgr: DocumentManager, new_title: str):
        super().__init__("Set Playlist Title")
        self._doc = doc_mgr
        self._old = doc_mgr.title
        self._new = new_title

    def redo(self):
        self._doc._title = self._new
        self._doc._mark_dirty()
        self._doc.title_changed.emit(self._new)

    def undo(self):
        self._doc._title = self._old
        self._doc._mark_dirty()
        self._doc.title_changed.emit(self._old)


class SetMetadataCommand(QUndoCommand):
    """Undoable command to edit playlist metadata."""
    def __init__(self, doc_mgr: DocumentManager, new_metadata: dict):
        super().__init__("Edit Playlist Metadata")
        self._doc = doc_mgr
        self._old = {
            "service_date": doc_mgr._service_date,
            "preacher": doc_mgr._preacher,
            "church": doc_mgr._church,
            "tags": list(doc_mgr._tags),
        }
        self._new = new_metadata

    def redo(self):
        self._apply(self._new)

    def undo(self):
        self._apply(self._old)

    def _apply(self, data):
        self._doc._service_date = data.get("service_date", "")
        self._doc._preacher = data.get("preacher", "")
        self._doc._church = data.get("church", "")
        self._doc._tags = list(data.get("tags", []))
        self._doc._mark_dirty()
        self._doc.metadata_changed.emit()


class MoveToPlaylistCommand(QUndoCommand):
    """Atomic move: removes from queue and adds to playlist in one undo step."""

    def __init__(self, queue_model: QueueModel, playlist_model: PlaylistModel, row: int):
        super().__init__("Move to Playlist")
        self._queue_model = queue_model
        self._playlist_model = playlist_model
        self._row = row
        self._item = queue_model.item_at(row)
        self._queue_entry_id = self._item.get("entry_id") if self._item else ""
        self._playlist_entry_id = ""

    def redo(self):
        if not self._item or not self._queue_entry_id:
            return

        # Avoid duplicate playlist entries when redo is triggered repeatedly.
        existing = self._playlist_model.find_row_by_entry_id(self._playlist_entry_id) if self._playlist_entry_id else -1
        if existing >= 0:
            row = self._queue_model.find_row_by_entry_id(self._queue_entry_id)
            if row >= 0:
                self._queue_model.remove_item(row)
            return

        # 1. Add to playlist
        item = dict(self._item)
        item["type"] = "verse"
        item.setdefault("id", str(uuid.uuid4()))
        if not self._playlist_entry_id:
            self._playlist_entry_id = str(uuid.uuid4())
        item["entry_id"] = self._playlist_entry_id
        
        self._playlist_model.add_item(item)
        # 2. Remove from queue
        row = self._queue_model.find_row_by_entry_id(self._queue_entry_id)
        if row >= 0:
            self._queue_model.remove_item(row)

    def undo(self):
        if not self._item:
            return
        # 1. Remove from playlist (find by entry_id)
        if self._playlist_entry_id:
            row = self._playlist_model.find_row_by_entry_id(self._playlist_entry_id)
            if row >= 0:
                self._playlist_model.remove_item(row)
            
        # 2. Restore to queue at original position
        existing_queue_row = self._queue_model.find_row_by_entry_id(self._queue_entry_id)
        if existing_queue_row < 0:
            self._queue_model.insert_item(self._row, self._item)
