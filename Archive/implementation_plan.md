# VerseFlow Bug-Fix Plan — Part 1: Fix the Bugs
**Staged for sequential execution. Each stage is independently verifiable.**

---

## Overview

| Stage | File | Bug # | Description |
|-------|------|-------|-------------|
| A1 | `models.py` | #1 | Fix `QueueModel.insert_item` — missing live-index shift |
| A2 | `models.py` | #1 + #2 | Fix `QueueModel.move_item` — full live-index tracking + bounds cap |
| A3 | `models.py` | #2 | Fix `PlaylistModel.move_item` — bounds cap only |
| A4 | `models.py` | — | **Compile & import verification checkpoint** |
| B1 | `playlist_panel.py` | #3 | Fix `dropEvent` — empty-list drop computes `to_row = -1` |
| B2 | `playlist_panel.py` | — | **Compile & import verification checkpoint** |
| C1 | `document_manager.py` | #4 | Add `backup_warning` signal + fix `_rotate_backups` return value |
| C2 | `document_manager.py` | #4 | Fix `open_file` — return `tuple[bool, str]` |
| C3 | `document_manager.py` | #4 | Fix `_write_to_file`, `save`, `save_as` — propagate tuple |
| C4 | `main.py` | #4 | Update `MainWindow._save_playlist` caller |
| C5 | `main.py` | #4 | Update `HomePanel._on_playlist_open` + `_on_playlist_save_as` callers + wire `backup_warning` |
| C6 | Both | — | **Final compile & launch verification** |

> [!CAUTION]
> Execute stages in exact order. Do **not** skip the verification checkpoints.
> Each stage modifies **one file only** unless explicitly stated.

---

## Group A — `models.py` Fixes (Bugs #1 & #2)

---

### Stage A1 — Fix `QueueModel.insert_item` Missing Live-Index Shift

**File:** `models.py`
**Lines:** 323–330
**Bug:** When a new item is inserted at or above the current live row, `_live_index`
is not incremented, so the gold "now live" indicator drifts to the wrong card.

#### Current Code (lines 323–330)
```python
def insert_item(self, row: int, item: dict):
    row = max(0, min(row, len(self._items)))
    self.beginInsertRows(QModelIndex(), row, row)
    clone = dict(item)
    clone.setdefault("id", str(uuid.uuid4()))
    clone.setdefault("entry_id", new_entry_id())
    self._items.insert(row, clone)
    self.endInsertRows()
```

#### Replacement Code
```python
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
```

> [!NOTE]
> The two new lines must go **after** `endInsertRows()`. Qt requires the model
> notification to be complete before any secondary state updates.

---

### Stage A2 — Fix `QueueModel.move_item` Live-Index Tracking + Bounds Cap

**File:** `models.py`
**Lines:** 347–360
**Bug 1 (#1):** When a non-live item is dragged past the live row, `_live_index` is
not adjusted, causing it to point to the wrong card after the move.
**Bug 2 (#2):** When dragging an item to the very last position, `dest` is computed as
`rowCount() + 1`, which violates Qt's `beginMoveRows` contract and is silently rejected.

#### Current Code (lines 347–360)
```python
def move_item(self, from_row: int, to_row: int):
    if from_row == to_row:
        return
    n = len(self._items)
    if not (0 <= from_row < n and 0 <= to_row <= n):
        return
    dest = to_row + 1 if to_row > from_row else to_row
    self.beginMoveRows(QModelIndex(), from_row, from_row, QModelIndex(), dest)
    item = self._items.pop(from_row)
    self._items.insert(to_row, item)
    # Track live index position after move
    if self._live_index == from_row:
        self._live_index = to_row
    self.endMoveRows()
```

#### Replacement Code
```python
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
```

> [!IMPORTANT]
> The live-index update block sits **before** `endMoveRows()`. This is the correct
> position — after the list is mutated but before view invalidation fires.

---

### Stage A3 — Fix `PlaylistModel.move_item` Bounds Cap

**File:** `models.py`
**Lines:** 168–181
**Bug (#2):** Same `beginMoveRows` boundary violation as `QueueModel`. `PlaylistModel`
has no live-index concept so only the single-line cap is needed here.

#### Current Code (lines 168–181)
```python
def move_item(self, from_row: int, to_row: int):
    """Move item from from_row to to_row."""
    if from_row == to_row:
        return
    n = len(self._items)
    if not (0 <= from_row < n and 0 <= to_row <= n):
        return
    # QAbstractItemModel::beginMoveRows rules require destination != source
    dest = to_row + 1 if to_row > from_row else to_row
    self.beginMoveRows(QModelIndex(), from_row, from_row, QModelIndex(), dest)
    item = self._items.pop(from_row)
    self._items.insert(to_row, item)
    self.endMoveRows()
    self.items_changed.emit()
```

#### Replacement Code
```python
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
```

---

### Stage A4 — Verification Checkpoint: `models.py`

Run the following two commands from the `2. Source Code` directory.
Both **must** exit with no output and return code 0.

```powershell
# From: c:\Users\GENESIS\Desktop\VerseFlow Antigravity\VerseFlow\2. Source Code

# 1. Compile check
.venv\Scripts\python.exe -m py_compile models.py
echo "Exit: $LASTEXITCODE"

# 2. Import check (launches Python, imports the module, exits)
.venv\Scripts\python.exe -c "from models import PlaylistModel, QueueModel; print('models.py OK')"
```

**Expected output:**
```
Exit: 0
models.py OK
```

**If either command fails:** Stop. Do not proceed to Group B. Re-read the
changed sections and check for indentation errors.

---

## Group B — `playlist_panel.py` Fix (Bug #3)

---

### Stage B1 — Fix `PlaylistListView.dropEvent` Empty-List Drop

**File:** `playlist_panel.py`
**Line:** 209
**Bug:** When a user drops onto empty space (including into an empty playlist),
`indexAt()` returns `-1`. The fallback `rowCount() - 1` becomes `-1` when the
list is empty. This causes `MovePlaylistItemCommand` to silently reject the drop.

The correct semantic for "dropped below all items" is `rowCount()` — an append.

#### Current Code (lines 203–215)
```python
def dropEvent(self, event):
    # Internal reorder using Undo Command
    if event.source() == self and (event.dropAction() == Qt.DropAction.MoveAction or self.dragDropMode() == QListView.DragDropMode.InternalMove):
        from_row = self.currentIndex().row()
        to_row = self.indexAt(event.position().toPoint()).row()
        if to_row == -1:
            to_row = self.model().rowCount() - 1   # ← BUG
        
        if self.doc_mgr and from_row != to_row:
            cmd = MovePlaylistItemCommand(self.model(), from_row, to_row)
            self.doc_mgr.push_command(cmd)
            event.accept()
            return
```

#### Replacement Code (lines 203–215)
```python
def dropEvent(self, event):
    # Internal reorder using Undo Command
    if event.source() == self and (event.dropAction() == Qt.DropAction.MoveAction or self.dragDropMode() == QListView.DragDropMode.InternalMove):
        from_row = self.currentIndex().row()
        to_row = self.indexAt(event.position().toPoint()).row()
        if to_row == -1:
            to_row = self.model().rowCount()   # ← FIX: append semantic
        
        if self.doc_mgr and from_row != to_row:
            cmd = MovePlaylistItemCommand(self.model(), from_row, to_row)
            self.doc_mgr.push_command(cmd)
            event.accept()
            return
```

**Change summary:** Remove the `- 1` from line 209. One character change.

---

### Stage B2 — Verification Checkpoint: `playlist_panel.py`

```powershell
# From: c:\Users\GENESIS\Desktop\VerseFlow Antigravity\VerseFlow\2. Source Code

.venv\Scripts\python.exe -m py_compile playlist_panel.py
echo "Exit: $LASTEXITCODE"

.venv\Scripts\python.exe -c "from playlist_panel import PlaylistPanel, PlaylistListView; print('playlist_panel.py OK')"
```

**Expected output:**
```
Exit: 0
playlist_panel.py OK
```

---

## Group C — `document_manager.py` + `main.py` Fixes (Bug #4)

> [!WARNING]
> This group has **5 stages** across 2 files. Complete C1→C3 (all `document_manager.py`
> changes) before touching `main.py`. If you modify `main.py` first, callers will
> call the old API and you will get run-time `TypeError` exceptions.

---

### Stage C1 — Add `backup_warning` Signal + Fix `_rotate_backups`

**File:** `document_manager.py`

#### Change 1 of 2 — Add signal (lines 45–51)

**Current code:**
```python
    dirty_changed    = pyqtSignal(bool)
    document_changed = pyqtSignal()
    playlist_loaded  = pyqtSignal(list)
    queue_loaded     = pyqtSignal(list)
    file_path_changed = pyqtSignal(str)
    title_changed    = pyqtSignal(str)
    metadata_changed = pyqtSignal()
```

**Replacement:**
```python
    dirty_changed    = pyqtSignal(bool)
    document_changed = pyqtSignal()
    playlist_loaded  = pyqtSignal(list)
    queue_loaded     = pyqtSignal(list)
    file_path_changed = pyqtSignal(str)
    title_changed    = pyqtSignal(str)
    metadata_changed = pyqtSignal()
    backup_warning   = pyqtSignal(str)   # emitted when auto-backup fails non-fatally
```

Also update the class docstring block (lines 37–43) to add the new signal:
```python
    """Central controller for a single .verseplaylist document.

    Signals:
        dirty_changed(bool)        — emitted when unsaved-state changes
        document_changed()         — emitted on any structural model change
        playlist_loaded(list)      — emitted after a file is loaded
        queue_loaded(list)         — emitted after queue section loads
        file_path_changed(str)     — emitted when the current file path changes
        backup_warning(str)        — emitted when auto-backup fails non-fatally
    """
```

#### Change 2 of 2 — Fix `_rotate_backups` to return `bool` (lines 247–263)

**Current code:**
```python
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
```

**Replacement:**
```python
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
            print(f"[DOC] {msg}", flush=True)
            self.backup_warning.emit(msg)
            return False
```

---

### Stage C2 — Fix `open_file` Return Type

**File:** `document_manager.py`
**Lines:** 138–188

**Current code:**
```python
    def open_file(self, path: Path) -> bool:
        """Load a .verseplaylist file. Returns True on success."""
        try:
            ...
            print(f"[DOC] Opened '{path.name}' — {len(items)} items", flush=True)
            return True

        except Exception as e:
            print(f"[DOC] Failed to open '{path}': {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False
```

**Replacement — change signature, success return, and failure return only:**
```python
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

            # Validate version
            version = data.get("version", "1.0")
            meta = data.get("metadata", {})
            items = data.get("items", [])

            # Ensure every item has an id
            for it in items:
                it.setdefault("id", str(uuid.uuid4()))
                if not isinstance(it.get("entry_id"), str) or not it.get("entry_id", "").strip():
                    it["entry_id"] = str(uuid.uuid4())
                if it.get("type") == "queue_group":
                    for qi in it.get("queue_items", []):
                        qi.setdefault("id", str(uuid.uuid4()))
                        if not isinstance(qi.get("entry_id"), str) or not qi.get("entry_id", "").strip():
                            qi["entry_id"] = str(uuid.uuid4())

            self._playlist_model.set_items(items)
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
            self.playlist_loaded.emit(items)
            self.queue_loaded.emit([])
            self.document_changed.emit()

            print(f"[DOC] Opened '{path.name}' — {len(items)} items", flush=True)
            return True, ""

        except Exception as e:
            import traceback
            detail = traceback.format_exc()
            msg = f"{type(e).__name__}: {e}"
            print(f"[DOC] Failed to open '{path}': {detail}", flush=True)
            return False, msg
```

---

### Stage C3 — Fix `_write_to_file`, `save`, and `save_as`

**File:** `document_manager.py`

#### Change 1 of 3 — Fix `_write_to_file` (lines 207–245)

**Current code:**
```python
    def _write_to_file(self, path: Path) -> bool:
        """Serialize and write the playlist to disk."""
        try:
            ...
            self._rotate_backups(path)
            ...
            print(f"[DOC] Saved '{path.name}'", flush=True)
            return True

        except Exception as e:
            print(f"[DOC] Failed to save '{path}': {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False
```

**Replacement:**
```python
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
            print(f"[DOC] Saved '{path.name}'", flush=True)
            return True, ""

        except Exception as e:
            import traceback
            detail = traceback.format_exc()
            msg = f"{type(e).__name__}: {e}"
            print(f"[DOC] Failed to save '{path}': {detail}", flush=True)
            return False, msg
```

#### Change 2 of 3 — Fix `save` (lines 190–194)

**Current code:**
```python
    def save(self) -> bool:
        """Save to the current file. Falls back to save_as if no file set."""
        if self._current_file is None:
            return False  # Caller should trigger a save-as dialog
        return self._write_to_file(self._current_file)
```

**Replacement:**
```python
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
```

#### Change 3 of 3 — Fix `save_as` (lines 196–205)

**Current code:**
```python
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
```

**Replacement:**
```python
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
```

---

### Stage C4 — Update `MainWindow._save_playlist` in `main.py`

**File:** `main.py`
**Lines:** 707–725

**Current code:**
```python
    def _save_playlist(self):
        """Save current playlist — prompts for path if file is new."""
        from PyQt6.QtWidgets import QFileDialog
        from pathlib import Path
        doc = self.home_panel.doc_manager
        if doc.current_file:
            success = doc.save()
            if success:
                self.statusBar().showMessage(f"Saved '{doc.display_name()}'.", 3000)
            else:
                self.statusBar().showMessage("Save failed — check permissions.", 4000)
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Playlist", "", "VerseFlow Playlists (*.verseplaylist)"
            )
            if path:
                success = doc.save_as(Path(path))
                if success:
                    self.statusBar().showMessage(f"Saved '{Path(path).stem}'.", 3000)
```

**Replacement:**
```python
    def _save_playlist(self):
        """Save current playlist — prompts for path if file is new."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from pathlib import Path
        doc = self.home_panel.doc_manager
        if doc.current_file:
            ok, msg = doc.save()
            if ok:
                self.statusBar().showMessage(f"Saved '{doc.display_name()}'.", 3000)
            else:
                err = f"Failed to save '{doc.display_name()}'.\n\n{msg}" if msg else \
                      "Save failed — check file permissions."
                QMessageBox.critical(self, "Save Failed", err)
                self.statusBar().showMessage("Save failed.", 4000)
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Playlist", "", "VerseFlow Playlists (*.verseplaylist)"
            )
            if path:
                ok, msg = doc.save_as(Path(path))
                if ok:
                    self.statusBar().showMessage(f"Saved '{Path(path).stem}'.", 3000)
                else:
                    err = f"Failed to save to:\n{path}\n\n{msg}" if msg else \
                          f"Failed to save to:\n{path}"
                    QMessageBox.critical(self, "Save Failed", err)
```

---

### Stage C5 — Update `HomePanel` Callers + Wire `backup_warning`

**File:** `main.py`

#### Change 1 of 3 — Fix `HomePanel._on_playlist_open` (lines 3155–3168)

**Current code:**
```python
    def _on_playlist_open(self):
        """Open a .verseplaylist file."""
        if not self._maybe_save_changes():
            return
            
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Playlist", "", "VerseFlow Playlists (*.verseplaylist)"
        )
        if path:
            ok = self.doc_manager.open_file(Path(path))
            if not ok:
                QMessageBox.critical(self, "Open Failed", f"Failed to open playlist:\n{path}")
            else:
                self.statusBar().showMessage(f"Opened '{Path(path).stem}'.", 3000)
```

**Replacement:**
```python
    def _on_playlist_open(self):
        """Open a .verseplaylist file."""
        if not self._maybe_save_changes():
            return
            
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Playlist", "", "VerseFlow Playlists (*.verseplaylist)"
        )
        if path:
            ok, msg = self.doc_manager.open_file(Path(path))
            if not ok:
                detail = f"\n\nDetail: {msg}" if msg else ""
                QMessageBox.critical(
                    self, "Open Failed",
                    f"Failed to open playlist:\n{path}{detail}"
                )
            else:
                self.statusBar().showMessage(f"Opened '{Path(path).stem}'.", 3000)
```

#### Change 2 of 3 — Fix `HomePanel._on_playlist_save_as` (lines 3170–3180)

**Current code:**
```python
    def _on_playlist_save_as(self):
        """Save current playlist to a new file."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Playlist As", "", "VerseFlow Playlists (*.verseplaylist)"
        )
        if path:
            ok = self.doc_manager.save_as(Path(path))
            if not ok:
                QMessageBox.critical(self, "Save Failed", f"Failed to save playlist to:\n{path}")
            else:
                self.statusBar().showMessage(f"Saved '{Path(path).stem}'.", 3000)
```

**Replacement:**
```python
    def _on_playlist_save_as(self):
        """Save current playlist to a new file."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Playlist As", "", "VerseFlow Playlists (*.verseplaylist)"
        )
        if path:
            ok, msg = self.doc_manager.save_as(Path(path))
            if not ok:
                detail = f"\n\nDetail: {msg}" if msg else ""
                QMessageBox.critical(
                    self, "Save Failed",
                    f"Failed to save playlist to:\n{path}{detail}"
                )
            else:
                self.statusBar().showMessage(f"Saved '{Path(path).stem}'.", 3000)
```

#### Change 3 of 3 — Wire `backup_warning` in `MainWindow.__init__` (after line 597)

**Locate this block** (lines 594–597):
```python
        self.home_panel.doc_manager.dirty_changed.connect(self._update_window_title)
        self.home_panel.doc_manager.file_path_changed.connect(self._update_window_title)
        self.home_panel.doc_manager.title_changed.connect(self._update_window_title)
        self._update_window_title()
```

**Append one line immediately after `self._update_window_title()`:**
```python
        self.home_panel.doc_manager.dirty_changed.connect(self._update_window_title)
        self.home_panel.doc_manager.file_path_changed.connect(self._update_window_title)
        self.home_panel.doc_manager.title_changed.connect(self._update_window_title)
        self._update_window_title()
        # Surface non-fatal backup warnings to the operator via the status bar
        self.home_panel.doc_manager.backup_warning.connect(
            lambda msg: self.statusBar().showMessage(f"⚠ {msg}", 6000)
        )
```

---

### Stage C6 — Final Verification Checkpoint

Run all three checks from the `2. Source Code` directory.

```powershell
# From: c:\Users\GENESIS\Desktop\VerseFlow Antigravity\VerseFlow\2. Source Code

# 1. Compile all modified files
.venv\Scripts\python.exe -m py_compile models.py
.venv\Scripts\python.exe -m py_compile document_manager.py
.venv\Scripts\python.exe -m py_compile playlist_panel.py
.venv\Scripts\python.exe -m py_compile main.py
echo "All compile checks exit: $LASTEXITCODE"

# 2. Full import chain check
.venv\Scripts\python.exe -c "
from models import PlaylistModel, QueueModel
from document_manager import DocumentManager
from playlist_panel import PlaylistPanel
print('All module imports: OK')
"

# 3. API signature check — confirms tuple returns are intact
.venv\Scripts\python.exe -c "
import inspect
from document_manager import DocumentManager
dm_hints = {}
for name in ('open_file', 'save', 'save_as', '_write_to_file'):
    hints = inspect.get_annotations(getattr(DocumentManager, name))
    dm_hints[name] = hints.get('return', 'missing')
print('Return type annotations:', dm_hints)
"
```

**Expected output (final check):**
```
Return type annotations: {
  'open_file': tuple[bool, str],
  'save': tuple[bool, str],
  'save_as': tuple[bool, str],
  '_write_to_file': tuple[bool, str]
}
```

**After all checks pass**, launch the app manually via `VerseFlow.bat` and perform
the manual scenarios from the verification table:

| Manual Test | Verifies |
|-------------|----------|
| Add 3 verses to Queue. Push verse 2 live. Drag verse 1 below verse 3. Confirm gold indicator stays on verse 2. | Bug #1 — insert |
| Add 3 verses to Queue. Push verse 2 live. Drag verse 3 to above verse 1. Confirm gold indicator stays on verse 2. | Bug #1 — move |
| Open a Playlist. Drag the last item and drop it below itself into blank space. Confirm it moves, no Qt warnings in console. | Bug #2 |
| Create New Playlist. Drag a verse from Queue into the empty Playlist panel. Confirm it appears. | Bug #3 |
| Attempt to open a file with invalid JSON (create a test file, delete part of it). Confirm the error dialog shows the JSON parse error detail, not just "Failed to open". | Bug #4 |

---

## Summary of All Files Changed

| File | Stages | Lines Touched |
|------|--------|---------------|
| `models.py` | A1, A2, A3 | 323–330, 347–360, 168–181 |
| `playlist_panel.py` | B1 | 209 |
| `document_manager.py` | C1, C2, C3 | 37–51, 138–188, 190–205, 207–263 |
| `main.py` | C4, C5 | 707–725, 597–598, 3155–3180 |
