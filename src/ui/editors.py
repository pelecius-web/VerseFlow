"""editors.py - VerseFlow editor widgets.

Contains:
    DraftEditor:     edits a draft verse; changes invisible to display until published
    TranslationMenu: dropdown translation selector with override + overlay modes

Extracted from main.py in v0.7.11 modularization.
Audited v0.7.12
"""

from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QSize, QTimer, QRect
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtWidgets import (
    QApplication, QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QScrollArea,
)
from db_layer import abbreviate_translation
import icons


# ── Draft Editor (Phase 1) ──────────────────────────────────────────────────

class DraftEditor(QFrame):
    """Editor for draft verses — changes invisible to display until published."""
    draft_changed = pyqtSignal(dict)
    publish_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("draft", True)
        self.setFixedHeight(160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Header row
        header_row = QHBoxLayout()
        hdr = QLabel("DRAFT EDITOR")
        hdr.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        hdr.setStyleSheet("color: rgba(76,175,125,0.5); background: transparent; letter-spacing: 2px;")
        header_row.addWidget(hdr)
        header_row.addStretch()

        self.publish_btn = QPushButton("Publish")
        self.publish_btn.setFixedSize(72, 26)
        self.publish_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.publish_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.publish_btn.setStyleSheet("""
            QPushButton {
                background: rgba(76,175,125,0.15);
                color: #4caf7d;
                border: 1px solid rgba(76,175,125,0.3);
                border-radius: 4px;
            }
            QPushButton:hover { background: rgba(76,175,125,0.25); }
        """)
        self.publish_btn.clicked.connect(lambda: self.publish_requested.emit())
        header_row.addWidget(self.publish_btn)
        layout.addLayout(header_row)

        # Reference
        ref_row = QHBoxLayout()
        ref_row.addWidget(QLabel("Ref:"))
        self.ref_edit = QLineEdit()
        self.ref_edit.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.ref_edit.setFixedHeight(30)
        ref_row.addWidget(self.ref_edit)
        layout.addLayout(ref_row)

        # Text
        self.text_edit = QLineEdit()
        self.text_edit.setFont(QFont("Segoe UI", 11))
        self.text_edit.setFixedHeight(34)
        self.text_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.text_edit)

        # Notes
        self.notes_edit = QLineEdit()
        self.notes_edit.setFont(QFont("Segoe UI", 9))
        self.notes_edit.setFixedHeight(28)
        self.notes_edit.setPlaceholderText("Operator notes (not displayed)...")
        layout.addWidget(self.notes_edit)

    def load_draft(self, verse):
        self.ref_edit.setText(verse.get("reference", ""))
        self.text_edit.setText(verse.get("text", ""))

    def _on_text_changed(self):
        draft = {
            "reference": self.ref_edit.text(),
            "text": self.text_edit.text(),
            "book": "",
            "chapter": 0,
            "verse": 0,
        }
        self.draft_changed.emit(draft)


class TranslationMenu(QFrame):
    """Translation selector with dropdown showing checkboxes beside each translation.
    
    Click translation text → Override mode (replaces everything)
    Click checkbox beside it → Overlay mode (adds above current, max 2)
    
    Layout mode is automatic:
    - No checkboxes checked = Single verse
    - Checkboxes checked = Multi-translation overlay (automatic)
    """
    translation_changed = pyqtSignal(str)  # Empty = remove overlay, text = add/change
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Trigger button (always visible)
        self.menu_btn = QPushButton("TRANSLATIONS")
        self.menu_btn.setIcon(icons.get_arrow_down_icon(size=16))
        self.menu_btn.setIconSize(QSize(16, 16))
        self.menu_btn.setFixedHeight(34)
        self.menu_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.setToolTip("Click translation name to override, checkbox to overlay")
        self.menu_btn.setStyleSheet("""
            QPushButton {
                background: rgba(200,160,60,0.12);
                color: #c8a03c;
                border: 1px solid rgba(200,160,60,0.25);
                border-radius: 6px;
                padding: 0 12px;
                text-align: left;
            }
            QPushButton:hover {
                background: rgba(200,160,60,0.2);
            }
        """)
        self.menu_btn.clicked.connect(self._toggle_menu)
        layout.addWidget(self.menu_btn)
        
        # Floating Dropdown Popup (using QScrollArea)
        self.popup = QScrollArea()
        self.popup.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.popup.installEventFilter(self)
        self.popup.setWidgetResizable(True)
        self.popup.setFrameShape(QFrame.Shape.NoFrame)
        # Apply theme-consistent styling to the popup container
        self.popup.setStyleSheet("""
            QScrollArea {
                background: #0f0f1a;
                border: 1px solid rgba(200,160,60,0.3);
                border-radius: 4px;
            }
        """)

        self.dropdown_panel = QFrame()
        self.dropdown_panel.setStyleSheet("background: transparent;")
        self.dropdown_layout = QVBoxLayout(self.dropdown_panel)
        self.dropdown_layout.setContentsMargins(8, 8, 8, 8)
        self.dropdown_layout.setSpacing(4)

        # Translation checkboxes
        self.translation_items = []  # List of (text, checkbox) tuples
        self.checked_translations = []  # Ordered list of checked translations (last = most recent)
        self.current_primary = "English KJV"
        self.max_overlays = 2  # Max overlays beyond the default

        self._populate_translations()
        self.popup.setWidget(self.dropdown_panel)
    
    def eventFilter(self, obj, event):
        """Handle mouse clicks on translation labels, and focus loss on popup."""
        # Auto-hide popup if it loses focus
        if obj == self.popup and event.type() == QEvent.Type.WindowDeactivate:
            # If the click that caused deactivation is on our menu_btn, do NOT auto-hide.
            # Let _toggle_menu handle the close cleanly to avoid press/release race.
            cursor_pos = QCursor.pos()
            btn_top_left = self.menu_btn.mapToGlobal(self.menu_btn.rect().topLeft())
            btn_global_rect = QRect(btn_top_left, self.menu_btn.rect().size())
            if btn_global_rect.contains(cursor_pos):
                return False  # Skip auto-hide; _toggle_menu will close on click release
            self.popup.hide()
            self.menu_btn.setIcon(icons.get_arrow_down_icon(size=16))
            return False

        if event.type() == QEvent.Type.MouseButtonPress:
            translation = obj.property("translation")
            if translation:
                self._on_text_click(translation)
                return True
                
        return super().eventFilter(obj, event)
    
    def _populate_translations(self):
        """Create translation items with checkboxes. First translation is default checked."""
        translations = self.db.get_translations()

        # Set default primary to first available if English KJV not present
        if translations and self.current_primary not in translations:
            self.current_primary = translations[0]

        for trans in translations:
            # Create horizontal layout for text + checkbox
            item_layout = QHBoxLayout()
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(8)

            # Checkbox (left)
            cb = QCheckBox()
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            cb.setStyleSheet("""
                QCheckBox {
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 2px solid rgba(200,160,60,0.5);
                    border-radius: 3px;
                    background: rgba(20,20,36,0.8);
                }
                QCheckBox::indicator:hover {
                    border-color: #c8a03c;
                    background: rgba(200,160,60,0.15);
                }
                QCheckBox::indicator:checked {
                    background: #c8a03c;
                    border-color: #c8a03c;
                }
            """)
            cb.stateChanged.connect(lambda state, t=trans: self._on_checkbox_toggle(state, t))
            item_layout.addWidget(cb)

            # Translation text (clickable to make it the new default)
            label = QLabel(abbreviate_translation(trans))
            label.setFont(QFont("Segoe UI", 11))
            label.setCursor(Qt.CursorShape.PointingHandCursor)
            label.setStyleSheet("""
                QLabel {
                    color: #e8e2d8;
                    padding: 4px 0;
                }
                QLabel:hover {
                    color: #c8a03c;
                }
            """)
            # Store translation in label property for event handling
            label.setProperty("translation", trans)
            label.installEventFilter(self)  # Install event filter
            item_layout.addWidget(label, 1)

            self.translation_items.append((trans, cb, label))
            self.dropdown_layout.addLayout(item_layout)

        # Set default translation as checked
        self._set_default_translation(self.current_primary)
    
    def _toggle_menu(self):
        """Show/hide dropdown popup with dynamic height calculation."""
        if self.popup.isVisible():
            self.popup.hide()
            self.menu_btn.setIcon(icons.get_arrow_down_icon(size=16))
            return

        # 1. Position the popup relative to the trigger button
        global_pos = self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft())
        self.popup.setFixedWidth(self.menu_btn.width())

        # 2. Dynamically calculate max height based on available screen space
        screen = QApplication.screenAt(global_pos)
        if screen:
            screen_geo = screen.geometry()
            # Calculate distance to bottom of screen (minus 20px padding)
            available_h = screen_geo.bottom() - global_pos.y() - 20
            
            # Constrain height: enough to see items, but never clipping off-screen
            # We target a comfortable max of 400px if space allows
            target_h = min(400, available_h)
            
            # Ensure at least some items are visible even in very small windows
            self.popup.setMaximumHeight(max(150, target_h))
        else:
            self.popup.setMaximumHeight(300)

        # 3. Show the popup
        self.popup.move(global_pos)
        self.popup.show()
        # Defer activateWindow to prevent focus race, but guard against manual close
        def _safe_activate():
            if self.popup.isVisible():
                self.popup.activateWindow()
        QTimer.singleShot(50, _safe_activate)
        self.menu_btn.setIcon(icons.get_arrow_up_icon(size=16))
    
    def _set_default_translation(self, translation):
        """Set the default (primary) checked translation."""
        self.current_primary = translation
        # Check the box for this translation.
        # blockSignals prevents _on_checkbox_toggle from firing for this
        # programmatic state change — only genuine user clicks should trigger it.
        for trans, cb, label in self.translation_items:
            if trans == translation:
                cb.blockSignals(True)
                cb.setChecked(True)
                cb.blockSignals(False)
                if translation not in self.checked_translations:
                    self.checked_translations.append(translation)
                break
        # Emit the change
        self.translation_changed.emit(f"default:{translation}")

    def _on_text_click(self, translation):
        """Handle clicking translation text — makes it the new default.
        Unchecks current default, checks the new one. Closes menu."""
        # Close menu
        self.popup.hide()
        self.menu_btn.setIcon(icons.get_arrow_down_icon(size=16))

        # If this is already the default, do nothing
        if translation == self.current_primary:
            return

        # Uncheck the old default.
        # blockSignals prevents the spurious 'remove:old' signal that would
        # otherwise fire _rebuild_display_overlays() with stale state BEFORE
        # the intended 'override:new' signal is emitted.
        old_primary = self.current_primary
        for trans, cb, label in self.translation_items:
            if trans == old_primary:
                cb.blockSignals(True)
                cb.setChecked(False)
                cb.blockSignals(False)
                if old_primary in self.checked_translations:
                    self.checked_translations.remove(old_primary)
                break

        # Set new default.
        # blockSignals prevents the spurious 'overlay:new' signal that would
        # otherwise fire HomePanel into overlay mode instead of override mode.
        self.current_primary = translation
        for trans, cb, label in self.translation_items:
            if trans == translation:
                cb.blockSignals(True)
                cb.setChecked(True)
                cb.blockSignals(False)
                if translation not in self.checked_translations:
                    self.checked_translations.append(translation)
                break

        # Emit override signal — the single, correct action for a text-label click.
        self.translation_changed.emit(f"override:{translation}")

    def _on_checkbox_toggle(self, state, translation):
        """Handle checkbox toggle — emits signal, HomePanel handles all updates."""
        if state == Qt.CheckState.Checked.value:
            # Add to checked list (last = most recent = new default)
            if translation in self.checked_translations:
                self.checked_translations.remove(translation)
            self.checked_translations.append(translation)
            self.current_primary = translation
            self.translation_changed.emit(f"overlay:{translation}")
        else:
            # Remove from checked list
            if translation in self.checked_translations:
                self.checked_translations.remove(translation)

            # If this was the default, pick the last remaining checked as new default
            if translation == self.current_primary and self.checked_translations:
                self.current_primary = self.checked_translations[-1]
            elif not self.checked_translations:
                all_trans = [t for t, cb, label in self.translation_items]
                self.current_primary = "English KJV" if "NKJV" in all_trans else (all_trans[0] if all_trans else "")

            self.translation_changed.emit(f"remove:{translation}")

    def get_current_primary(self):
        """Get current primary translation."""
        return self.current_primary
    
    def get_active_overlays(self):
        """Get list of active overlay translations (excluding current primary)."""
        return [t for t in self.checked_translations if t != self.current_primary]

    def clear_overlays(self):
        """Clear all overlay checkboxes."""
        self.checked_translations.clear()
        for trans, cb, label in self.translation_items:
            cb.setChecked(False)
