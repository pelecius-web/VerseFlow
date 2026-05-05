from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QLineEdit,
    QPushButton, QListView, QStyledItemDelegate, QStyle, QMenu,
    QApplication, QScrollArea, QAbstractItemView, QDialog, QDialogButtonBox,
    QFormLayout, QDateEdit, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QRect, QPoint, QSize, QMimeData, QDate
)
from PyQt6.QtGui import (
    QFont, QFontMetrics, QPainter, QColor, QIcon, QAction, QCursor, QPen
)
import json
import uuid
import icons

from document_manager import (
    MovePlaylistItemCommand, RemoveFromPlaylistCommand, AddToPlaylistCommand,
    MoveToPlaylistCommand
)
from models import safe_json_loads


class PlaylistItemDelegate(QStyledItemDelegate):
    """Custom delegate for rendering playlist items (verses and queue groups)."""

    push_requested = pyqtSignal(dict)   # verse dict
    clear_requested = pyqtSignal(dict)   # verse dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ITEM_HEIGHT = 40
        self.BUTTON_SIZE = 28
        self.BUTTON_MARGIN_RIGHT = 10
        self._live_verse_id = None  # Track which verse is currently on display

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), self.ITEM_HEIGHT)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect
        item = index.data(Qt.ItemDataRole.UserRole)
        if not item:
            painter.restore()
            return

        is_hovered = option.state & QStyle.StateFlag.State_MouseOver
        is_selected = option.state & QStyle.StateFlag.State_Selected

        # Draw background
        bg_color = QColor(200, 160, 60, 15) if is_hovered else QColor(0, 0, 0, 0)
        if is_selected:
            bg_color = QColor(200, 160, 60, 25)
        painter.fillRect(rect, bg_color)

        # Content margins
        margin = 10
        content_rect = rect.adjusted(margin, 5, -margin, -5)

        if item.get("type") == "verse":
            # 1. Draw Reference (Bold Gold)
            ref = item.get("reference", "Unknown")
            trans = item.get("translation", "")

            ref_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            painter.setFont(ref_font)
            painter.setPen(QColor("#c8a03c"))

            ref_rect = painter.drawText(content_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, ref)

            # 2. Draw Translation Badge
            if trans:
                trans_font = QFont("Segoe UI", 7, QFont.Weight.Bold)
                painter.setFont(trans_font)
                fm = QFontMetrics(trans_font)
                tw = fm.horizontalAdvance(trans)

                badge_rect = QRect(ref_rect.right() + 8, ref_rect.top() + 2, tw + 8, fm.height() + 2)
                painter.setBrush(QColor(200, 160, 60, 30))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(badge_rect, 3, 3)

                painter.setPen(QColor(200, 160, 60, 180))
                painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, trans)

            # 3. Draw Push/Clear Button
            self._draw_push_clear_button(painter, option, item)

            # 4. Draw +Q Button
            self._draw_plus_q_button(painter, option)

        elif item.get("type") == "queue_group":
            # Draw Group Folder Icon & Label
            label = item.get("label", "Queue Group")
            count = len(item.get("queue_items", []))
            icon = icons.get_folder_icon(size=16)
            icon_sz = 16
            icon_pad = 4
            icon.paint(painter, content_rect.x() + icon_pad,
                       content_rect.y() + (content_rect.height() - icon_sz) // 2,
                       icon_sz, icon_sz)
            txt_rect = QRect(content_rect.x() + icon_sz + icon_pad * 2, content_rect.y(),
                             content_rect.width() - icon_sz - icon_pad * 3, content_rect.height())
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.setPen(QColor("#4caf7d"))
            painter.drawText(txt_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)
            
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor("rgba(76, 175, 125, 0.6)"))
            painter.drawText(content_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, f"{count} verses")

        painter.restore()

    def _draw_plus_q_button(self, painter, option):
        btn_rect = self._button_rect(option)

        # Style
        painter.setBrush(QColor(76, 175, 125, 30))
        painter.setPen(QColor(76, 175, 125, 60))
        painter.drawRoundedRect(btn_rect, 5, 5)

        queue_icon = icons.get_queue_icon(size=18, color="#4caf7d")
        icon_sz = min(btn_rect.width(), btn_rect.height()) - 6
        queue_icon.paint(painter,
            btn_rect.x() + (btn_rect.width() - icon_sz) // 2,
            btn_rect.y() + (btn_rect.height() - icon_sz) // 2,
            icon_sz, icon_sz)

    def _draw_push_clear_button(self, painter, option, item):
        """Draw push/clear toggle button using SVG icons."""
        btn_rect = self._push_clear_button_rect(option)
        is_live = self._is_live(item)

        # Button background
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

    def _button_rect(self, option):
        rect = option.rect
        btn_x = rect.right() - self.BUTTON_SIZE - self.BUTTON_MARGIN_RIGHT
        btn_y = rect.y() + (self.ITEM_HEIGHT - self.BUTTON_SIZE) // 2
        return QRect(btn_x, btn_y, self.BUTTON_SIZE, self.BUTTON_SIZE)

    def _push_clear_button_rect(self, option):
        """Position push/clear button to the left of +Q button."""
        rect = option.rect
        btn_x = rect.right() - (self.BUTTON_SIZE * 2) - (self.BUTTON_MARGIN_RIGHT * 2)
        btn_y = rect.y() + (self.ITEM_HEIGHT - self.BUTTON_SIZE) // 2
        return QRect(btn_x, btn_y, self.BUTTON_SIZE, self.BUTTON_SIZE)

    def set_live_verse(self, verse: dict):
        """Set the verse currently on display."""
        self._live_verse_id = verse.get("entry_id") if verse else None
        # Trigger repaint of all items
        if self.parent():
            self.parent().viewport().update()

    def _is_live(self, item: dict) -> bool:
        """Check if this item is currently on display."""
        return item.get("entry_id") == self._live_verse_id

    def editorEvent(self, event, model, option, index):
        if event.type() in (event.Type.MouseButtonPress, event.Type.MouseButtonRelease, event.Type.MouseButtonDblClick):
            if event.button() != Qt.MouseButton.LeftButton:
                return super().editorEvent(event, model, option, index)

        item = index.data(Qt.ItemDataRole.UserRole)
        if not item or item.get("type") != "verse":
            return super().editorEvent(event, model, option, index)

        if event.type() == event.Type.MouseButtonPress:
            pos = event.position().toPoint()
            push_clear_rect = self._push_clear_button_rect(option)
            plus_q_rect = self._button_rect(option)

            if push_clear_rect.contains(pos):
                # Handle push/clear button click
                is_live = self._is_live(item)
                if is_live:
                    self.clear_requested.emit(item)
                else:
                    self.push_requested.emit(item)
                return True

            if plus_q_rect.contains(pos):
                # Emit signal via parent
                view = self.parent()
                if hasattr(view, "add_to_queue_requested"):
                    view.add_to_queue_requested.emit(item)
                return True
            return False

        if event.type() == event.Type.MouseButtonRelease:
            pos = event.position().toPoint()
            push_clear_rect = self._push_clear_button_rect(option)
            plus_q_rect = self._button_rect(option)

            if push_clear_rect.contains(pos) or plus_q_rect.contains(pos):
                return True

            # Preview request
            view = self.parent()
            if hasattr(view, "preview_requested"):
                view.preview_requested.emit(item)
            return True

        return super().editorEvent(event, model, option, index)


class PlaylistListView(QListView):
    """ListView that handles playlist interaction and drag-drop."""
    preview_requested = pyqtSignal(dict)
    add_to_queue_requested = pyqtSignal(dict)
    remove_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QListView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        self.doc_mgr = None

    def _show_context_menu(self, pos):
        index = self.indexAt(pos)
        if not index.isValid():
            return

        menu = QMenu(self)
        item = index.data(Qt.ItemDataRole.UserRole)

        if item.get("type") == "verse":
            q_action = QAction("Add to Queue", self)
            q_action.triggered.connect(lambda: self.add_to_queue_requested.emit(item))
            menu.addAction(q_action)

        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(lambda: self.remove_requested.emit(index.row()))
        menu.addAction(remove_action)
        
        menu.exec(self.viewport().mapToGlobal(pos))

    def dropEvent(self, event):
        # Internal reorder using Undo Command
        if event.source() is self and (event.dropAction() == Qt.DropAction.MoveAction or self.dragDropMode() == QListView.DragDropMode.InternalMove):
            # Extract source row from mime data (reliable) instead of currentIndex (unreliable)
            raw = bytes(event.mimeData().data("application/x-verseflow-playlist-item")).decode("utf-8")
            items = safe_json_loads(raw, [])
            if not items or not isinstance(items, list) or len(items) == 0:
                event.ignore()
                return

            # Get the first item's original row from the model (look up by id)
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

            to_row = self.indexAt(event.position().toPoint()).row()
            if to_row == -1:
                to_row = self.model().rowCount()

            if self.doc_mgr and from_row != to_row:
                cmd = MovePlaylistItemCommand(self.model(), from_row, to_row)
                self.doc_mgr.push_command(cmd)
                event.setDropAction(Qt.DropAction.IgnoreAction)
                event.accept()
                return

        # External drop
        elif event.source() != self and (event.mimeData().hasFormat("application/x-verseflow-queue-item") or event.mimeData().hasFormat("application/x-verseflow-playlist-item")):
            fmt = "application/x-verseflow-queue-item" if event.mimeData().hasFormat("application/x-verseflow-queue-item") else "application/x-verseflow-playlist-item"
            raw = bytes(event.mimeData().data(fmt)).decode("utf-8")
            items = safe_json_loads(raw, [])
            
            import logging
            logger = logging.getLogger("VerseFlow")
            
            # DEFENSIVE: Validate items is a list (not string, dict, etc.)
            if not isinstance(items, list):
                logger.warning("Drop data 'items' is not a list: %s", type(items).__name__)
                event.ignore()
                return
            
            if self.doc_mgr:
                for item in items:
                    # DEFENSIVE: Skip non-dict items in the list
                    if not isinstance(item, dict):
                        logger.warning("Skipping non-dict item in drop data: %s", type(item).__name__)
                        continue
                    # Clean the item for playlist (sets type, id, etc.)
                    item["type"] = "verse"
                    if "id" not in item:
                        item["id"] = str(uuid.uuid4())
                    
                    cmd = AddToPlaylistCommand(self.model(), item)
                    self.doc_mgr.push_command(cmd)
                
                event.setDropAction(Qt.DropAction.CopyAction)
                event.accept()
                return

        event.ignore()


class MetadataEditDialog(QDialog):
    """Dialog for editing playlist metadata."""
    def __init__(self, metadata, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Playlist Metadata")
        self.setMinimumWidth(350)
        self.setStyleSheet("background: #1a1a1a; color: #e0e0e0;")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.service_date = QDateEdit()
        self.service_date.setCalendarPopup(True)
        date_str = metadata.get("service_date", "")
        if date_str:
            self.service_date.setDate(QDate.fromString(date_str, Qt.DateFormat.ISODate))
        else:
            self.service_date.setDate(QDate.currentDate())
            
        self.preacher = QLineEdit(metadata.get("preacher", ""))
        self.church = QLineEdit(metadata.get("church", ""))
        self.tags = QLineEdit(", ".join(metadata.get("tags", [])))

        for widget in [self.service_date, self.preacher, self.church, self.tags]:
            widget.setStyleSheet("""
                QWidget {
                    background: #2a2a2a;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                    padding: 4px;
                    color: white;
                }
                QWidget:focus { border: 1px solid #c8a03c; }
            """)

        form.addRow("Service Date:", self.service_date)
        form.addRow("Preacher:", self.preacher)
        form.addRow("Church:", self.church)
        form.addRow("Tags (CSV):", self.tags)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_metadata(self):
        return {
            "service_date": self.service_date.date().toString(Qt.DateFormat.ISODate),
            "preacher": self.preacher.text(),
            "church": self.church.text(),
            "tags": [t.strip() for t in self.tags.text().split(",") if t.strip()]
        }


class PlaylistPanel(QFrame):
    """The main Playlist Panel component."""
    preview_requested = pyqtSignal(dict)
    add_to_queue_requested = pyqtSignal(dict)
    verse_pushed = pyqtSignal(dict)
    verse_cleared = pyqtSignal()
    open_requested = pyqtSignal()
    save_as_requested = pyqtSignal()

    def __init__(self, doc_mgr, display, parent=None):
        super().__init__(parent)
        self.setProperty("panel", True)
        self.doc_mgr = doc_mgr
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        # Header with Title and Metadata button
        header = QHBoxLayout()
        header.setSpacing(8)
        
        dot = QFrame()
        dot.setFixedSize(5, 5)
        dot.setStyleSheet("QFrame { background: #c8a03c; border-radius: 3px; }")
        header.addWidget(dot)

        self.title_edit = QLineEdit(doc_mgr.title)
        self.title_edit.setPlaceholderText("Playlist Title...")
        self.title_edit.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #c8a03c;
                font-weight: bold;
                font-size: 11px;
                letter-spacing: 1.5px;
            }
            QLineEdit:focus {
                background: rgba(255,255,255,0.05);
                border-radius: 4px;
            }
        """)
        self.title_edit.editingFinished.connect(self._on_title_edited)
        header.addWidget(self.title_edit, 1)

        # Actions toolbar
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(4)
        
        import icons
        for get_icon_func, fallback_label, tooltip, slot in [
            (icons.get_new_icon, "New", "New Playlist (Ctrl+N)", self._on_new),
            (icons.get_open_icon, "Open", "Open Playlist (Ctrl+O)", self.open_requested.emit),
            (icons.get_save_icon, "Save", "Save (Ctrl+S)", self._on_save),
            (icons.get_save_as_icon, "Save As", "Save As…", self.save_as_requested.emit),
            (icons.get_metadata_icon, "Meta", "Edit Metadata", self._on_edit_meta)
        ]:
            btn = QPushButton()
            icon = get_icon_func()
            btn.setIcon(icon)
            btn.setIconSize(QSize(16, 16))
            btn.setFixedHeight(26)
            btn.setFixedWidth(26)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if icon.isNull():
                # Fallback to text when icon rendering is unavailable.
                # Size to content so labels are never visually truncated.
                btn.setText(fallback_label)
                fallback_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
                btn.setFont(fallback_font)
                fm = QFontMetrics(fallback_font)
                text_w = fm.horizontalAdvance(fallback_label)
                btn.setFixedWidth(max(46, text_w + 16))
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(200,160,60,0.1);
                    border: 1px solid rgba(200,160,60,0.2);
                    border-radius: 6px;
                    padding: 0 6px;
                }
                QPushButton:hover { background: rgba(200,160,60,0.2); }
            """)
            btn.clicked.connect(slot)
            actions_layout.addWidget(btn)
        
        header.addLayout(actions_layout)
        layout.addLayout(header)

        # List View
        self.list_view = PlaylistListView(self)
        self.list_view.doc_mgr = doc_mgr
        self.delegate = PlaylistItemDelegate(self.list_view)
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.setModel(doc_mgr.playlist_model)
        
        self.list_view.preview_requested.connect(self.preview_requested.emit)
        self.list_view.add_to_queue_requested.connect(self.add_to_queue_requested.emit)
        self.list_view.remove_requested.connect(self._on_remove_item)

        # Connect delegate push/clear signals to panel signals
        self.delegate.push_requested.connect(self._on_verse_push)
        self.delegate.clear_requested.connect(self._on_verse_clear)

        self.list_view.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.list_view, 1)

        # Empty state label
        self._empty_label = QLabel("Playlist is empty.\nDrag verses here or use 'Add to Playlist'.")
        self._empty_label.setFont(QFont("Segoe UI", 8))
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            "color: rgba(200, 160, 60, 0.25); background: transparent; padding: 16px;"
        )
        layout.addWidget(self._empty_label)
        self._update_empty_state()

        # Connect model changes to empty state
        doc_mgr.playlist_model.layoutChanged.connect(self._update_empty_state)
        doc_mgr.playlist_model.rowsInserted.connect(self._update_empty_state)
        doc_mgr.playlist_model.rowsRemoved.connect(self._update_empty_state)
        doc_mgr.playlist_model.modelReset.connect(self._update_empty_state)

        # Sync title from DocMgr
        doc_mgr.title_changed.connect(self.title_edit.setText)

    def _on_title_edited(self):
        new_title = self.title_edit.text()
        if new_title != self.doc_mgr.title:
            self.doc_mgr.title = new_title

    def _on_new(self):
        if self.doc_mgr.is_dirty:
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                "Discard Changes?",
                "The current playlist has unsaved changes.\n\nDiscard changes and start fresh?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.doc_mgr.new_document()

    def _on_save(self):
        if not self.doc_mgr.current_file:
            self.save_as_requested.emit()
        else:
            from PyQt6.QtWidgets import QMessageBox
            ok, msg = self.doc_mgr.save()
            if not ok:
                detail = f"\n\nDetail: {msg}" if msg else ""
                QMessageBox.critical(self, "Save Failed", f"Failed to save playlist.{detail}")

    def _on_edit_meta(self):
        current_meta = {
            "service_date": self.doc_mgr._service_date,
            "preacher": self.doc_mgr._preacher,
            "church": self.doc_mgr._church,
            "tags": list(self.doc_mgr._tags)
        }
        dlg = MetadataEditDialog(current_meta, self)
        if dlg.exec():
            self.doc_mgr.set_metadata(dlg.get_metadata())

    def _on_remove_item(self, row):
        cmd = RemoveFromPlaylistCommand(self.doc_mgr.playlist_model, row)
        self.doc_mgr.push_command(cmd)

    def _on_verse_push(self, verse: dict):
        """Handle push button click - emit signal to display verse."""
        self.delegate.set_live_verse(verse)
        self.verse_pushed.emit(verse)

    def _on_verse_clear(self, verse: dict):
        """Handle clear button click - emit signal to clear display."""
        self.delegate.set_live_verse(None)
        self.verse_cleared.emit()

    def sync_live_state(self, verse: dict = None):
        """Sync playlist live state with display controller current verse."""
        if not verse:
            self.delegate.set_live_verse(None)
            return

        # Match by entry_id first, then by reference + translation
        verse_entry_id = verse.get("entry_id", "")
        verse_ref = verse.get("reference", "")
        verse_trans = verse.get("translation", "")

        model = self.list_view.model()
        for r in range(model.rowCount()):
            item = model.index(r).data(Qt.ItemDataRole.UserRole)
            if not item:
                continue
            if verse_entry_id and item.get("entry_id") == verse_entry_id:
                self.delegate.set_live_verse(item)
                return
            if item.get("reference") == verse_ref and item.get("translation") == verse_trans:
                self.delegate.set_live_verse(item)
                return

        # No matching verse found — clear live state
        self.delegate.set_live_verse(None)

    def add_verse(self, verse_dict):
        """External helper to add a verse (used by Move to Playlist from Queue)."""
        # DEFENSIVE: Validate input type to prevent crashes from malformed data
        if not isinstance(verse_dict, dict):
            logger.warning("add_verse received non-dict type: %s", type(verse_dict).__name__)
            return
        # Ensure it's treated as a playlist verse
        item = verse_dict.copy()
        item["type"] = "verse"
        if "id" not in item:
            item["id"] = str(uuid.uuid4())
        
        # SANITIZE: Reconstruct reference from clean book/chapter/verse to avoid mojibake
        # The database reference field may contain UTF-8 corruption (e.g., "Psalms 35:9 a£")
        # We rebuild it from the individual fields which are always clean
        if item.get("book") and item.get("chapter") is not None and item.get("verse") is not None:
            original_ref = item.get("reference", "")
            base_ref = f"{item['book']} {item['chapter']}:{item['verse']}"
            
            # Check for verse range suffix and preserve it (e.g., "-17" from "John 3:16-17")
            verse_str = str(item['verse'])
            range_marker = f":{verse_str}-"
            if range_marker in original_ref:
                try:
                    idx = original_ref.find(range_marker)
                    if idx != -1:
                        suffix_start = idx + len(range_marker)
                        suffix = original_ref[suffix_start:]
                        # Stop at space or non-digit
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
                # No range suffix, use clean base reference
                item["reference"] = base_ref
        
        cmd = AddToPlaylistCommand(self.doc_mgr.playlist_model, item)
        self.doc_mgr.push_command(cmd)

    def _update_empty_state(self):
        """Show/hide empty state label based on playlist contents."""
        has_items = self.doc_mgr.playlist_model.rowCount() > 0
        self._empty_label.setVisible(not has_items)
        # Collapse list_view when empty so empty label gets full space
        # (list_view stays visible with 0 height for drop acceptance)
        self.list_view.setMaximumHeight(16777215 if has_items else 0)
