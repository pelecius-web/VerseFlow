"""models.py — VerseFlow Category 1: In-Memory Data Models

PlaylistModel  — QAbstractListModel for the Service Playlist panel.
QueueModel     — QAbstractListModel for the Verse Queue panel (tracks live state).
"""

from __future__ import annotations

from PyQt6.QtCore import (
    Qt, QAbstractListModel, QModelIndex, QMimeData, pyqtSignal
)

import json
import uuid

# ── Helpers ───────────────────────────────────────────────────────────────────

def new_entry_id() -> str:
    return str(uuid.uuid4())


def safe_json_loads(raw: str, default: list = None) -> list:
    """Safely parse JSON from drag-drop MIME data.

    Returns a list if parsing succeeds, otherwise returns the default value.
    Protects against malformed JSON, type errors, and potential injection attacks.

    Args:
        raw: Raw string data to parse as JSON
        default: Default value to return on parse failure (defaults to empty list)

    Returns:
        Parsed list if successful and result is a list, otherwise default value
    """
    if default is None:
        default = []
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return default
        return data
    except (json.JSONDecodeError, TypeError, ValueError):
        return default


# ── PlaylistModel ─────────────────────────────────────────────────────────────

class PlaylistModel(QAbstractListModel):
    """Holds the ordered list of items in a Service Playlist.

    Each item is a dict with one of two shapes:
        Verse item:
            {
                "id":          str (uuid),
                "type":        "verse",
                "reference":   str,    e.g. "John 3:16"
                "translation": str,
                "text":        str,
                "notes":       str,
            }
        Queue-group item:
            {
                "id":           str (uuid),
                "type":         "queue_group",
                "label":        str,
                "queue_items":  list[dict],   # same shape as verse items
            }
    """

    items_changed = pyqtSignal()  # emitted after any structural change

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[dict] = []

    # ── QAbstractListModel interface ─────────────────────────────────────────

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            if item["type"] == "verse":
                return item.get("reference", "Unknown")
            elif item["type"] == "queue_group":
                count = len(item.get("queue_items", []))
                return f"{item.get('label', 'Queue')} ({count} verses)"
        if role == Qt.ItemDataRole.UserRole:
            return item
        return None

    def flags(self, index):
        default = super().flags(index)
        return default | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction | Qt.DropAction.CopyAction

    # ── Drag-and-drop MIME handling ──────────────────────────────────────────

    def mimeTypes(self):
        # Declare both formats so Qt allows cross-panel drops (view-level filtering)
        return ["application/x-verseflow-playlist-item", "application/x-verseflow-queue-item"]

    def mimeData(self, indexes):
        mime = QMimeData()
        rows = sorted(set(idx.row() for idx in indexes if idx.isValid()))
        payload = json.dumps([self._items[r] for r in rows]).encode("utf-8")
        mime.setData("application/x-verseflow-playlist-item", payload)
        return mime

    def canDropMimeData(self, data, action, row, column, parent):
        return data.hasFormat("application/x-verseflow-playlist-item") or \
               data.hasFormat("application/x-verseflow-queue-item")

    def dropMimeData(self, data, action, row, column, parent):
        # Data mutation is exclusively handled by PlaylistListView via QUndoCommand.
        # This prevents bypassing the undo stack and avoids the model's index shift bugs.
        return False

    def removeRows(self, row, count, parent=QModelIndex()):
        if row < 0 or count <= 0 or row + count > len(self._items):
            return False
        self.beginRemoveRows(parent, row, row + count - 1)
        del self._items[row:row+count]
        self.endRemoveRows()
        self.items_changed.emit()
        return True

    # ── Mutation API ─────────────────────────────────────────────────────────

    def add_item(self, item: dict) -> int:
        """Append an item. Returns the new row index."""
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        clone = dict(item)
        clone.setdefault("id", str(uuid.uuid4()))
        clone.setdefault("entry_id", new_entry_id())
        clone.setdefault("notes", "")
        self._items.append(clone)
        self.endInsertRows()
        self.items_changed.emit()
        return row

    def insert_item(self, row: int, item: dict):
        """Insert an item at the given row."""
        row = max(0, min(row, len(self._items)))
        self.beginInsertRows(QModelIndex(), row, row)
        clone = dict(item)
        clone.setdefault("id", str(uuid.uuid4()))
        clone.setdefault("entry_id", new_entry_id())
        clone.setdefault("notes", "")
        self._items.insert(row, clone)
        self.endInsertRows()
        self.items_changed.emit()

    def remove_item(self, row: int) -> dict | None:
        """Remove and return the item at row."""
        if row < 0 or row >= len(self._items):
            return None
        self.beginRemoveRows(QModelIndex(), row, row)
        item = self._items.pop(row)
        self.endRemoveRows()
        self.items_changed.emit()
        return item

    def move_item(self, from_row: int, to_row: int):
        """Move item from from_row to to_row."""
        if from_row == to_row:
            return
        n = len(self._items)
        if not (0 <= from_row < n and 0 <= to_row <= n):
            return
        # QAbstractItemModel::beginMoveRows rules require destination != source
        dest = to_row + 1 if to_row > from_row else to_row
        dest = min(dest, n)  # Cap so dest never exceeds rowCount()
        self.beginMoveRows(QModelIndex(), from_row, from_row, QModelIndex(), dest)
        item = self._items.pop(from_row)
        self._items.insert(to_row, item)
        self.endMoveRows()
        self.items_changed.emit()

    def clear(self):
        """Remove all items."""
        if not self._items:
            return
        self.beginResetModel()
        self._items.clear()
        self.endResetModel()
        self.items_changed.emit()

    def get_items(self) -> list[dict]:
        """Return a shallow copy of the items list."""
        return list(self._items)

    def set_items(self, items: list[dict]):
        """Replace entire contents (used on file load)."""
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()
        self.items_changed.emit()

    def item_at(self, row: int) -> dict | None:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def find_row_by_entry_id(self, entry_id: str) -> int:
        """Return the row of the item with the given entry_id, or -1."""
        if not entry_id:
            return -1
        for i, it in enumerate(self._items):
            if it.get("entry_id") == entry_id:
                return i
        return -1


# ── QueueModel ────────────────────────────────────────────────────────────────

class QueueModel(QAbstractListModel):
    """Holds the temporary staging queue of verses awaiting display.

    Each item is a verse dict (same structure as PlaylistModel verse items).
    Tracks which item is currently on the congregation display (_live_index).
    """

    live_index_changed = pyqtSignal(int)  # -1 means nothing live

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[dict] = []
        self._live_index: int = -1

    # ── QAbstractListModel interface ─────────────────────────────────────────

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return item.get("reference", "Unknown")
        if role == Qt.ItemDataRole.UserRole:
            return item
        if role == Qt.ItemDataRole.UserRole + 1:
            # Live-state role
            return index.row() == self._live_index
        return None

    def flags(self, index):
        default = super().flags(index)
        return default | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction | Qt.DropAction.CopyAction

    # ── Drag-and-drop MIME handling ──────────────────────────────────────────

    def mimeTypes(self):
        # Declare both formats so Qt allows cross-panel drops (view-level filtering)
        return ["application/x-verseflow-queue-item", "application/x-verseflow-playlist-item"]

    def mimeData(self, indexes):
        mime = QMimeData()
        rows = sorted(set(idx.row() for idx in indexes if idx.isValid()))
        payload = json.dumps([self._items[r] for r in rows]).encode("utf-8")
        mime.setData("application/x-verseflow-queue-item", payload)
        return mime

    def canDropMimeData(self, data, action, row, column, parent):
        return (data.hasFormat("application/x-verseflow-queue-item") or
                data.hasFormat("application/x-verseflow-playlist-item"))

    def dropMimeData(self, data, action, row, column, parent):
        # Data mutation is exclusively handled by QueueListView via QUndoCommand.
        # This prevents bypassing the undo stack and avoids the model's live state bugs.
        return False

    def removeRows(self, row, count, parent=QModelIndex()):
        if row < 0 or count <= 0 or row + count > len(self._items):
            return False
        
        # Check if the live item is being removed or shifted
        live_removed = False
        if self._live_index >= 0:
            if row <= self._live_index < row + count:
                live_removed = True
            elif self._live_index >= row + count:
                # Live item is after the removed block, shift it up
                self._live_index -= count

        self.beginRemoveRows(parent, row, row + count - 1)
        del self._items[row:row+count]
        self.endRemoveRows()

        if live_removed:
            self._live_index = -1
            self.live_index_changed.emit(-1)
        elif self._live_index >= row + count:
            # Emit changed signal if live index was shifted
            self.live_index_changed.emit(self._live_index)
            
        return True

    # ── Mutation API ─────────────────────────────────────────────────────────

    def add_item(self, item: dict) -> int:
        """Append a verse to the queue. Returns the new row index."""
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        clone = dict(item)
        clone.setdefault("id", str(uuid.uuid4()))
        clone.setdefault("entry_id", new_entry_id())
        self._items.append(clone)
        self.endInsertRows()
        return row

    def insert_item(self, row: int, item: dict):
        row = max(0, min(row, len(self._items)))
        self.beginInsertRows(QModelIndex(), row, row)
        clone = dict(item)
        clone.setdefault("id", str(uuid.uuid4()))
        clone.setdefault("entry_id", new_entry_id())
        self._items.insert(row, clone)
        self.endInsertRows()
        # Shift live index up when a new item is inserted at or above it
        if self._live_index >= 0 and row <= self._live_index:
            self._live_index += 1
            self.live_index_changed.emit(self._live_index)

    def remove_item(self, row: int) -> dict | None:
        if row < 0 or row >= len(self._items):
            return None
        self.beginRemoveRows(QModelIndex(), row, row)
        item = self._items.pop(row)
        self.endRemoveRows()
        # Adjust live index
        if self._live_index == row:
            self._live_index = -1
            self.live_index_changed.emit(-1)
        elif self._live_index > row:
            self._live_index -= 1
            self.live_index_changed.emit(self._live_index)
        return item

    def move_item(self, from_row: int, to_row: int):
        if from_row == to_row:
            return
        n = len(self._items)
        if not (0 <= from_row < n and 0 <= to_row <= n):
            return
        dest = to_row + 1 if to_row > from_row else to_row
        dest = min(dest, n)  # Bug #2 fix: cap so dest never exceeds rowCount()
        self.beginMoveRows(QModelIndex(), from_row, from_row, QModelIndex(), dest)
        item = self._items.pop(from_row)
        self._items.insert(to_row, item)
        # Bug #1 fix: full live-index tracking for all relative motion cases
        live = self._live_index
        if live >= 0:
            if from_row == live:
                # The live item itself was moved
                self._live_index = to_row
            elif from_row < live and to_row >= live:
                # A non-live item moved from before live to at/after it → live shifts left
                self._live_index -= 1
            elif from_row > live and to_row <= live:
                # A non-live item moved from after live to at/before it → live shifts right
                self._live_index += 1
        self.endMoveRows()

    def set_live(self, row: int):
        """Mark a row as the currently-on-display item. Pass -1 to clear."""
        old = self._live_index
        self._live_index = row
        if old != row:
            self.live_index_changed.emit(row)
            # Notify views to repaint the affected rows
            if old >= 0:
                idx = self.index(old)
                self.dataChanged.emit(idx, idx, [Qt.ItemDataRole.UserRole + 1])
            if row >= 0:
                idx = self.index(row)
                self.dataChanged.emit(idx, idx, [Qt.ItemDataRole.UserRole + 1])

    @property
    def live_index(self) -> int:
        return self._live_index

    def clear_queue(self) -> list[dict]:
        """Clear and return the full queue list (for undo support)."""
        snapshot = list(self._items)
        self.beginResetModel()
        self._items.clear()
        self._live_index = -1
        self.endResetModel()
        self.live_index_changed.emit(-1)
        return snapshot

    def restore_queue(self, items: list[dict]):
        """Restore a previously cleared queue (used by ClearQueueCommand.undo)."""
        self.beginResetModel()
        self._items = list(items)
        self._live_index = -1
        self.endResetModel()

    def get_items(self) -> list[dict]:
        return list(self._items)

    def set_items(self, items: list[dict]):
        self.beginResetModel()
        self._items = list(items)
        self._live_index = -1
        self.endResetModel()

    def item_at(self, row: int) -> dict | None:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def find_row_by_id(self, item_id: str) -> int:
        """Return the row of the item with the given id, or -1."""
        for i, it in enumerate(self._items):
            if it.get("id") == item_id:
                return i
        return -1

    def find_row_by_entry_id(self, entry_id: str) -> int:
        """Return the row of the item with the given entry_id, or -1."""
        if not entry_id:
            return -1
        for i, it in enumerate(self._items):
            if it.get("entry_id") == entry_id:
                return i
        return -1
