"""queue_panel.py — VerseFlow Category 1, Stage 3: Queue Panel Integration

QueuePanel: Verse staging area with preview, push-to-display, and live state tracking.
QueueItemDelegate: Custom delegate rendering verse cards with push/clear buttons.
"""

from __future__ import annotations

import json
import icons
from PyQt6.QtCore import Qt, QRect, QSize, QModelIndex, QMimeData, pyqtSignal
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QFontMetrics, QCursor,
    QAction, QKeySequence,
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QListView, QStyledItemDelegate, QApplication, QMenu, QSizePolicy,
)

from document_manager import (
    AddToQueueCommand, RemoveFromQueueCommand,
    MoveQueueItemCommand, ClearQueueCommand,
)


# ── QueueItemDelegate ─────────────────────────────────────────────────────────

class QueueItemDelegate(QStyledItemDelegate):
    """Custom delegate that paints verse cards with a push/clear button.

    Layout per item (fixed height 40px):
    ┌──────────────────────────────────────────────────────┐
    │ [Ref]  translation-badge                 [→ or ✕]   │
    └──────────────────────────────────────────────────────┘

    Click on card body  → preview (emit preview_requested)
    Click on button     → push/clear (emit push_requested)
    """

    preview_requested = pyqtSignal(dict)   # verse dict
    push_requested = pyqtSignal(int)       # row index
    remove_requested = pyqtSignal(int)     # row index

    ITEM_HEIGHT = 40
    BUTTON_SIZE = 26
    BUTTON_MARGIN_RIGHT = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hovered_row = -1

    # ── Sizing ────────────────────────────────────────────────────────────

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), self.ITEM_HEIGHT)

    # ── Painting ──────────────────────────────────────────────────────────

    def paint(self, painter: QPainter, option, index):
        """Paint a single queue item card."""
        painter.save()

        rect = option.rect
        verse = index.data(Qt.ItemDataRole.UserRole)
        if not verse:
            painter.restore()
            return

        is_live = index.data(Qt.ItemDataRole.UserRole + 1) or False
        is_hovered = (index.row() == self._hovered_row)

        # Background
        if is_live:
            bg_color = QColor(200, 160, 60, 40)
            border_color = QColor(200, 160, 60, 180)
        elif is_hovered:
            bg_color = QColor(200, 160, 60, 15)
            border_color = QColor(200, 160, 60, 60)
        else:
            bg_color = QColor(0, 0, 0, 0)
            border_color = QColor(0, 0, 0, 0)

        painter.setBrush(QBrush(bg_color))
        if border_color.alpha() > 0:
            pen = QPen(border_color, 1)
            painter.setPen(pen)
            painter.drawRoundedRect(rect.adjusted(0, 2, 0, -2), 6, 6)

        # Reference label (bold, gold)
        ref = verse.get("reference", "Unknown")
        ref_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(ref_font)
        painter.setPen(QColor(200, 160, 60))
        ref_x = rect.x() + 10
        ref_y = rect.y() + 14
        painter.drawText(ref_x, ref_y, ref)
        ref_width = QFontMetrics(ref_font).horizontalAdvance(ref)

        # Translation badge (small, green-tinted) - inline with reference
        trans = verse.get("translation", "")
        if trans:
            badge_font = QFont("Segoe UI", 7)
            painter.setFont(badge_font)
            badge_text = trans
            badge_w = QFontMetrics(badge_font).horizontalAdvance(badge_text) + 10
            badge_h = 13
            badge_x = ref_x + ref_width + 8
            badge_y = ref_y - 10
            # Badge background
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(76, 175, 125, 30)))
            painter.drawRoundedRect(badge_x, badge_y, badge_w, badge_h, 3, 3)
            # Badge text
            painter.setPen(QColor(76, 175, 125, 200))
            painter.drawText(badge_x + 5, badge_y + 10, badge_text)

        # Push/Clear button
        btn_x = rect.right() - self.BUTTON_SIZE - self.BUTTON_MARGIN_RIGHT
        btn_y = rect.y() + (self.ITEM_HEIGHT - self.BUTTON_SIZE) // 2
        btn_rect = QRect(btn_x, btn_y, self.BUTTON_SIZE, self.BUTTON_SIZE)

        # Button background and icon
        if is_live:
            btn_bg = QColor(224, 92, 75, 40)
            btn_border = QColor(224, 92, 75, 120)
            icon = icons.get_close_icon(size=self.BUTTON_SIZE)
        else:
            btn_bg = QColor(200, 160, 60, 30)
            btn_border = QColor(200, 160, 60, 80)
            icon = icons.get_arrow_right_icon(size=self.BUTTON_SIZE)

        painter.setPen(QPen(btn_border, 1))
        painter.setBrush(btn_bg)
        painter.drawRoundedRect(btn_rect, 5, 5)

        # Draw SVG icon
        pixmap = icon.pixmap(self.BUTTON_SIZE, self.BUTTON_SIZE)
        painter.drawPixmap(btn_rect, pixmap)

        painter.restore()

    def _button_rect(self, option):
        """Calculate the button rect dynamically (same as in paint)."""
        rect = option.rect
        btn_x = rect.right() - self.BUTTON_SIZE - self.BUTTON_MARGIN_RIGHT
        btn_y = rect.y() + (self.ITEM_HEIGHT - self.BUTTON_SIZE) // 2
        return QRect(btn_x, btn_y, self.BUTTON_SIZE, self.BUTTON_SIZE)

    # ── Mouse interaction ─────────────────────────────────────────────────

    def editorEvent(self, event, model, option, index):
        """Handle mouse events on the delegate item.

        Key rule: do NOT consume single left-clicks — let Qt's drag-initiation
        system handle them. Only consume button clicks and double-clicks.
        """
        if event.type() in (event.Type.MouseButtonPress, event.Type.MouseButtonRelease, event.Type.MouseButtonDblClick):
            if event.button() != Qt.MouseButton.LeftButton:
                return super().editorEvent(event, model, option, index)

        if event.type() == event.Type.MouseButtonPress:
            pos = event.position().toPoint()
            # Check if click is on the push/clear button
            btn_rect = self._button_rect(option)
            if btn_rect.contains(pos):
                self.push_requested.emit(index.row())
                return True
            # For body clicks: let Qt handle for potential drag initiation
            # Only consume on release (click without drag)
            return False

        if event.type() == event.Type.MouseButtonRelease:
            pos = event.position().toPoint()
            btn_rect = self._button_rect(option)
            if btn_rect.contains(pos):
                return True  # Already handled on press
            # Body release without drag → preview
            verse = index.data(Qt.ItemDataRole.UserRole)
            if verse:
                self.preview_requested.emit(verse)
            return True

        if event.type() == event.Type.MouseButtonDblClick:
            # Double-click: push to display
            self.push_requested.emit(index.row())
            return True

        return super().editorEvent(event, model, option, index)

    # ── Hover tracking (via parent view) ──────────────────────────────────

    def set_hovered_row(self, row: int):
        """Update hovered row for visual feedback."""
        self._hovered_row = row


# ── QueueListView ─────────────────────────────────────────────────────────────

class QueueListView(QListView):
    """QListView subclass with drag-and-drop and context menu support."""

    preview_requested = pyqtSignal(dict)
    push_requested = pyqtSignal(int)
    remove_requested = pyqtSignal(int)
    move_to_playlist_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Use DragDrop mode (allows both drag-from and drop-to)
        self.setDragDropMode(QListView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QListView.SelectionMode.SingleSelection)
        self.setUniformItemSizes(True)
        self.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Reference to the document manager (set by QueuePanel) for undo-aware moves
        self.doc_mgr = None

    def _show_context_menu(self, pos: QPoint):
        """Right-click context menu."""
        index = self.indexAt(pos)
        if not index.isValid():
            return

        verse = index.data(Qt.ItemDataRole.UserRole)
        if not verse:
            return

        menu = QMenu(self)

        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(lambda: self.remove_requested.emit(index.row()))
        menu.addAction(remove_action)

        move_action = QAction("Move to Playlist", self)
        move_action.triggered.connect(lambda: self._move_to_playlist(index.row()))
        menu.addAction(move_action)

        menu.exec(self.viewport().mapToGlobal(pos))

    def _move_to_playlist(self, row: int):
        """Signal to move verse at row to playlist via atomic undo command."""
        if self.doc_mgr:
            from document_manager import MoveToPlaylistCommand
            cmd = MoveToPlaylistCommand(self.model(), self.doc_mgr.playlist_model, row)
            self.doc_mgr.push_command(cmd)
        else:
            # Fallback (non-undo-aware or missing manager)
            verse = self.model().item_at(row)
            if verse:
                self.move_to_playlist_requested.emit(verse)
                self.remove_requested.emit(row)

    def mimeData(self, indexes):
        """Serialize verse data for drag-and-drop."""
        mime = QMimeData()
        rows = sorted(set(idx.row() for idx in indexes if idx.isValid()))
        model = self.model()
        items = []
        for r in rows:
            verse = model.index(r).data(Qt.ItemDataRole.UserRole)
            if verse:
                items.append(verse)
        mime.setData("application/x-verseflow-queue-item", json.dumps(items).encode("utf-8"))
        return mime

    def dropEvent(self, event):
        """Intercept drops to handle them via undo commands instead of direct model mutation."""
        # External drop from Playlist Panel
        if event.source() is not self and event.mimeData().hasFormat("application/x-verseflow-playlist-item"):
            raw = bytes(event.mimeData().data("application/x-verseflow-playlist-item")).decode("utf-8")
            try:
                items = json.loads(raw) if raw else []
            except json.JSONDecodeError:
                event.ignore()
                return

            if not isinstance(items, list):
                event.ignore()
                return

            if self.doc_mgr:
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") and item.get("type") != "verse":
                        continue
                    cmd = AddToQueueCommand(self.model(), item)
                    self.doc_mgr.push_command(cmd)
                event.setDropAction(Qt.DropAction.CopyAction)
                event.accept()
                return

        # Internal reorder — only when source is THIS view
        if event.source() is self and event.mimeData().hasFormat("application/x-verseflow-queue-item"):
            # Extract source row from mime data (reliable) instead of currentIndex (unreliable)
            raw = bytes(event.mimeData().data("application/x-verseflow-queue-item")).decode("utf-8")
            try:
                items = json.loads(raw) if raw else []
            except json.JSONDecodeError:
                event.ignore()
                return

            if not isinstance(items, list) or len(items) == 0:
                event.ignore()
                return

            # Get the dragged item's original row from the model
            dragged_item = items[0]
            dragged_id = dragged_item.get("id") or dragged_item.get("entry_id")
            from_row = -1
            if dragged_id:
                for row in range(self.model().rowCount()):
                    item = self.model().index(row).data(Qt.ItemDataRole.UserRole)
                    if item and (item.get("id") == dragged_id or item.get("entry_id") == dragged_id):
                        from_row = row
                        break

            if from_row == -1:
                event.ignore()
                return

            drop_index = self.indexAt(event.position().toPoint())
            to_row = drop_index.row() if drop_index.isValid() else self.model().rowCount()
            if from_row != to_row and 0 <= from_row < self.model().rowCount():
                if self.doc_mgr:
                    cmd = MoveQueueItemCommand(self.model(), from_row, to_row)
                    self.doc_mgr.push_command(cmd)
                else:
                    self.model().move_item(from_row, to_row)
                event.setDropAction(Qt.DropAction.IgnoreAction)
                event.accept()
                return

        event.ignore()


# ── QueuePanel ────────────────────────────────────────────────────────────────

class QueuePanel(QFrame):
    """Verse Queue Panel — staging area for verses before display.

    Features:
    - Preview verse on click (shows in DisplayPreview without going live)
    - Push verse to display on → button click
    - Clear verse from display on ✕ button click (when live)
    - Live state tracking (visual indicator for verse on screen)
    - Remove verses from queue
    - Clear entire queue (undo-aware)
    - Drag-and-drop reordering
    - Accept drops from navigator/keyword results
    - Right-click context menu: Remove, Move to Playlist
    """

    preview_requested = pyqtSignal(dict)
    verse_pushed = pyqtSignal(dict)
    move_to_playlist_requested = pyqtSignal(dict)

    def __init__(self, document_manager, display_controller, parent=None):
        super().__init__(parent)
        self.setProperty("panel", True)

        self.doc_mgr = document_manager
        self.display = display_controller
        self.queue_model = document_manager.queue_model

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        # Header row
        header = QHBoxLayout()
        dot = QFrame()
        dot.setFixedSize(5, 5)
        dot.setStyleSheet("QFrame { background: #4caf7d; border-radius: 3px; }")
        header.addWidget(dot)

        label = QLabel("QUEUE PANEL")
        label.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        label.setStyleSheet("color: rgba(76,175,125,0.5); background: transparent; letter-spacing: 1.5px;")
        header.addWidget(label)

        header.addStretch()

        # Clear button (Premium SVG Trash Can)
        self.btn_clear = QPushButton()
        self.btn_clear.setIcon(icons.get_trash_icon())
        self.btn_clear.setIconSize(QSize(16, 16))
        self.btn_clear.setFixedSize(24, 24)
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setToolTip("Clear Queue")
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background: rgba(224,92,75,0.12);
                color: #e05c4b;
                border: 1px solid rgba(224,92,75,0.20);
                border-radius: 6px;
            }
            QPushButton:hover { 
                background: rgba(224,92,75,0.25);
                border: 1px solid rgba(224,92,75,0.35);
            }
            QPushButton:pressed { background: rgba(224,92,75,0.35); }
        """)
        self.btn_clear.clicked.connect(self._on_clear_queue)
        header.addWidget(self.btn_clear)

        layout.addLayout(header)

        # Queue list view
        self.list_view = QueueListView(self)
        self.list_view.doc_mgr = document_manager
        self.delegate = QueueItemDelegate(self)
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.setModel(self.queue_model)

        # Connect delegate signals
        self.delegate.preview_requested.connect(self._on_preview_verse)
        self.delegate.push_requested.connect(self._on_push_verse)

        # Connect list view signals
        self.list_view.push_requested.connect(self._on_push_verse)
        self.list_view.preview_requested.connect(self._on_preview_verse)
        self.list_view.remove_requested.connect(self._on_remove_verse)
        self.list_view.move_to_playlist_requested.connect(self.move_to_playlist_requested.emit)

        # Connect live index changes for repaint
        self.queue_model.live_index_changed.connect(self._on_live_index_changed)

        self.list_view.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.list_view, 1)

        # Empty state label
        self._empty_label = QLabel("Queue is empty.\nAdd verses from the navigator.")
        self._empty_label.setFont(QFont("Segoe UI", 8))
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            "color: rgba(76,175,125,0.25); background: transparent; padding: 16px;"
        )
        self._update_empty_state()
        layout.addWidget(self._empty_label)

        # Connect model layout changes to empty state
        self.queue_model.layoutChanged.connect(self._update_empty_state)
        self.queue_model.rowsInserted.connect(self._update_empty_state)
        self.queue_model.rowsRemoved.connect(self._update_empty_state)
        self.queue_model.modelReset.connect(self._update_empty_state)

    # ── Interaction handlers ──────────────────────────────────────────────

    def _on_preview_verse(self, verse: dict):
        """Show verse in DisplayPreview without pushing to live display."""
        if not verse:
            return
        self.preview_requested.emit(verse)

    def _on_push_verse(self, row: int):
        """Emit verse_pushed so main engine handles live workflow."""
        verse = self.queue_model.item_at(row)
        if not verse:
            return
            
        self.verse_pushed.emit(verse)

    def _on_remove_verse(self, row: int):
        """Remove verse from queue via undo command."""
        if row < 0 or row >= self.queue_model.rowCount():
            return
        cmd = RemoveFromQueueCommand(self.queue_model, row, self.display)
        self.doc_mgr.push_command(cmd)

    def _on_clear_queue(self):
        """Clear entire queue via undo command."""
        if self.queue_model.rowCount() == 0:
            return
        cmd = ClearQueueCommand(self.queue_model, self.display)
        self.doc_mgr.push_command(cmd)

    def _on_live_index_changed(self, row: int):
        """Repaint items when live state changes."""
        model = self.queue_model
        for r in range(model.rowCount()):
            idx = model.index(r)
            model.dataChanged.emit(idx, idx, [Qt.ItemDataRole.UserRole + 1])

    def _update_empty_state(self):
        """Show/hide empty state label based on queue contents."""
        has_items = self.queue_model.rowCount() > 0
        self._empty_label.setVisible(not has_items)
        # Collapse list_view when empty so empty label gets full space
        self.list_view.setMaximumHeight(16777215 if has_items else 0)

    # ── Public API ────────────────────────────────────────────────────────

    def add_verse(self, verse: dict):
        """Add a verse to the queue via undo command."""
        # DEFENSIVE: Validate input type to prevent crashes from malformed data
        if not isinstance(verse, dict):
            logger.warning("add_verse received non-dict type: %s", type(verse).__name__)
            return
        if not verse:
            return
        
        # SANITIZE: Reconstruct reference from clean book/chapter/verse to avoid mojibake
        # The verse may come from saved playlist files with corrupted references
        item = verse.copy()
        if item.get("book") and item.get("chapter") is not None and item.get("verse") is not None:
            original_ref = item.get("reference", "")
            base_ref = f"{item['book']} {item['chapter']}:{item['verse']}"
            
            # Check for verse range suffix and preserve it
            verse_str = str(item['verse'])
            range_marker = f":{verse_str}-"
            if range_marker in original_ref:
                try:
                    idx = original_ref.find(range_marker)
                    if idx != -1:
                        suffix_start = idx + len(range_marker)
                        suffix = original_ref[suffix_start:]
                        end_idx = 0
                        for i, c in enumerate(suffix):
                            if not c.isdigit():
                                break
                            end_idx = i + 1
                        if end_idx > 0:
                            item["reference"] = base_ref + "-" + suffix[:end_idx]
                        else:
                            item["reference"] = base_ref
                    else:
                        item["reference"] = base_ref
                except Exception:
                    item["reference"] = base_ref
            else:
                item["reference"] = base_ref
        
        cmd = AddToQueueCommand(self.queue_model, item)
        self.doc_mgr.push_command(cmd)

    def add_verses_from_list(self, verses: list[dict]):
        """Add multiple verses to the queue."""
        # DEFENSIVE: Validate verses is a list
        if not isinstance(verses, list):
            logger.warning("add_verses_from_list received non-list type: %s", type(verses).__name__)
            return
        for v in verses:
            # add_verse handles non-dict validation internally
            self.add_verse(v)

    def sync_live_state(self, verse: dict = None):
        """Sync queue live state with display controller current verse."""
        current = self.display.current
        if not current:
            if self.queue_model.live_index >= 0:
                self.queue_model.set_live(-1)
            return

        # Find matching verse in queue
        current_ref = current.get("reference", "")
        current_trans = current.get("translation", "")
        for r in range(self.queue_model.rowCount()):
            item = self.queue_model.item_at(r)
            if item:
                item_ref = item.get("reference", "")
                item_trans = item.get("translation", "")
                if item_ref == current_ref and item_trans == current_trans:
                    self.queue_model.set_live(r)
                    return

        # No matching verse — clear live state
        if self.queue_model.live_index >= 0:
            self.queue_model.set_live(-1)
