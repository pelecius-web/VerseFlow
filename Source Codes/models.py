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
        return ["application/x-verseflow-playlist-item"]

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
        if row < 0:
            row = self.rowCount()

        if data.hasFormat("application/x-verseflow-playlist-item"):
            raw = bytes(data.data("application/x-verseflow-playlist-item")).decode("utf-8")
            items = json.loads(raw)
            # Remove originals (move) then insert at target
            if action == Qt.DropAction.MoveAction:
                item_ids = {it["id"] for it in items}
                self._items = [it for it in self._items if it["id"] not in item_ids]
                # Adjust row after removal
                row = min(row, len(self._items))
            for i, it in enumerate(items):
                self._items.insert(row + i, it)
            self.layoutChanged.emit()
            self.items_changed.emit()
            return True

        if data.hasFormat("application/x-verseflow-queue-item"):
            # Drop from queue → copy verse into playlist
            raw = bytes(data.data("application/x-verseflow-queue-item")).decode("utf-8")
            items = json.loads(raw)
            for i, it in enumerate(items):
                it["type"] = "verse"
                it.setdefault("id", str(uuid.uuid4()))
                it.setdefault("notes", "")
                self._items.insert(row + i, it)
            self.layoutChanged.emit()
            self.items_changed.emit()
            return True

        return False

    # ── Mutation API ─────────────────────────────────────────────────────────

    def add_item(self, item: dict) -> int:
        """Append an item. Returns the new row index."""
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        clone = dict(item)
        clone.setdefault("id", str(uuid.uuid4()))
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
        if not (0 <= from_row < n and 0 <= to_row < n):
            return
        # QAbstractItemModel::beginMoveRows rules require destination != source
        dest = to_row + 1 if to_row > from_row else to_row
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
        return ["application/x-verseflow-queue-item"]

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
        if row < 0:
            row = self.rowCount()

        fmt = None
        if data.hasFormat("application/x-verseflow-queue-item"):
            fmt = "application/x-verseflow-queue-item"
        elif data.hasFormat("application/x-verseflow-playlist-item"):
            fmt = "application/x-verseflow-playlist-item"
        else:
            return False

        raw = bytes(data.data(fmt)).decode("utf-8")
        items = json.loads(raw)

        if action == Qt.DropAction.MoveAction and fmt == "application/x-verseflow-queue-item":
            item_ids = {it["id"] for it in items}
            self._items = [it for it in self._items if it["id"] not in item_ids]
            row = min(row, len(self._items))

        for i, it in enumerate(items):
            clone = dict(it)
            clone.setdefault("id", str(uuid.uuid4()))
            self._items.insert(row + i, clone)

        self._live_index = -1  # reset live state on reorder
        self.layoutChanged.emit()
        return True

    # ── Mutation API ─────────────────────────────────────────────────────────

    def add_item(self, item: dict) -> int:
        """Append a verse to the queue. Returns the new row index."""
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        clone = dict(item)
        clone.setdefault("id", str(uuid.uuid4()))
        self._items.append(clone)
        self.endInsertRows()
        return row

    def insert_item(self, row: int, item: dict):
        row = max(0, min(row, len(self._items)))
        self.beginInsertRows(QModelIndex(), row, row)
        clone = dict(item)
        clone.setdefault("id", str(uuid.uuid4()))
        self._items.insert(row, clone)
        self.endInsertRows()

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
        if not (0 <= from_row < n and 0 <= to_row < n):
            return
        dest = to_row + 1 if to_row > from_row else to_row
        self.beginMoveRows(QModelIndex(), from_row, from_row, QModelIndex(), dest)
        item = self._items.pop(from_row)
        self._items.insert(to_row, item)
        # Track live index position after move
        if self._live_index == from_row:
            self._live_index = to_row
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
