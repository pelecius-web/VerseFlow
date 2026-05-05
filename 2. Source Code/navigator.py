"""navigator.py - VerseFlow verse navigation & search widgets.

Contains:
    VerseNavigator, NavVerseCard, KeywordResults, KeywordVerseCard,
    CrossRefPanel, CrossRefCard

Extracted from main.py in v0.7.11 modularization.
Audited v0.7.12
"""

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QCheckBox, QScrollArea,
)
from db_layer import abbreviate_translation
import icons


# ── Verse Navigator (chapter navigator with highlight) ──────────────────────

class VerseNavigator(QWidget):
    """Shows a full chapter of verses in a scrollable view.
    One verse is highlighted. Arrow keys move highlight. Enter sends to display.

    State machine (BibleShow-style workflow — 2-state cycle):
    State 0: Inactive (no chapter loaded) — internal only
    State 1 (READY): Chapter loaded, verse highlighted, nothing on external screen
    State 2 (LIVE): Verse on external screen, arrow keys navigate and update screen

    Enter key cycles: 1→2→1→2... (Show/Hide toggle)
    Arrow keys in State 1: Move highlight only
    Arrow keys in State 2: Move highlight AND update screen
    """
    verse_pushed = pyqtSignal(dict)
    verse_cleared = pyqtSignal()
    state_changed = pyqtSignal(int)
    verse_went_live = pyqtSignal(dict)  # Fired ONLY on State 1 → 2 transition, for history logging
    queue_requested = pyqtSignal(dict)  # +Q button on card → add to queue
    playlist_requested = pyqtSignal(dict)  # +P button on card → add to playlist
    highlighted_verse_changed = pyqtSignal(dict)  # Fired when highlighted verse changes (feeds cross-ref panel)

    def __init__(self, db, display, parent=None):
        super().__init__(parent)
        self.db = db
        self.display = display
        self.verses = []
        self.highlighted_idx = -1
        self.cards = []
        self._state = 0  # State machine: 0=inactive (internal), 1=READY, 2=LIVE
        # StrongFocus allows getting focus from both tab key AND mouse clicks
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Chapter header with state indicator
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        self.header = QLabel("Chapter Navigator")
        self.header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.header.setStyleSheet("color: #c8a03c; background: transparent; letter-spacing: 2px;")
        header_layout.addWidget(self.header)
        
        # State indicator badge
        self.state_badge = QLabel("")
        self.state_badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.state_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_badge.setFixedSize(80, 20)
        header_layout.addWidget(self.state_badge)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        layout.addSpacing(4)

        # Scrollable verse list
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 8, 0)
        self.content_layout.setSpacing(6)

        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)
        
        # Footer hint
        self.hint = QLabel("")
        self.hint.setFont(QFont("Segoe UI", 9))
        self.hint.setStyleSheet("color: rgba(200,160,60,0.3); background: transparent; padding: 4px 0;")
        layout.addWidget(self.hint)

    def load_chapter(self, book, chapter, verses, target_verse=0):
        """Load a chapter. target_verse is the verse number (1-based) to highlight and scroll to."""
        self.clear()
        self.setUpdatesEnabled(False)
        self.scroll.setVisible(False)
        self.header.setText(f"{book} — Chapter {chapter}")
        hl_idx = self._find_verse_index(verses, target_verse)
        self._replace_cards(verses, hl_idx, state=1, emit_highlight=True)

    def _on_select(self, idx, event):
        """Click on a verse card — single click moves highlight only."""
        if idx < 0 or idx >= len(self.cards):
            return
            
        clicked_verse = self.verses[idx]
        
        for c in self.cards:
            c.highlight(False)
        self.highlighted_idx = idx
        self._refresh_hl_style(idx)
        self._update_state_badge()
        self._update_hint()
        # Notify cross-reference panel of the newly-highlighted verse
        self.highlighted_verse_changed.emit(clicked_verse)

        if self._state == 2:
            # Already live — update screen with newly selected verse
            self.display.push_verse(clicked_verse)
        
        self.state_changed.emit(self._state)
        # Return focus to navigator so keyboard continues to work
        self.setFocus()

    def _on_card_pushed(self, verse):
        """→ button click — state-dependent behavior:
        State 1: Send verse to screen (→ State 2)
        State 2: Clear screen (→ State 1)
        """
        # Find index of this verse
        idx = -1
        for i, v in enumerate(self.verses):
            if v.get('id') == verse.get('id'):
                idx = i
                break

        if idx >= 0:
            was_active = (idx == self.highlighted_idx and self._state == 2)

            # Update highlight
            for c in self.cards:
                c.highlight(False)
            self.highlighted_idx = idx

            # Apply state machine logic
            if was_active:
                # Clicked the ALREADY ACTIVE push button -> Deactivate (Clear screen)
                self.display.push_verse({})
                self._state = 1
            else:
                # Clicked an INACTIVE push button -> Activate (Send to screen)
                was_in_state_1 = (self._state == 1)
                self._state = 2
                self.display.push_verse(verse)
                
                # If we legitimately transitioned from a standby state to Live, emit for history logger
                if was_in_state_1:
                    self.verse_went_live.emit(verse)

            self._refresh_hl_style(idx)

            self._update_state_badge()
            self._update_hint()
            self.state_changed.emit(self._state)
            # Return focus to navigator
            self.setFocus()

    def _refresh_hl_style(self, idx):
        """Update highlighted card's visual state based on _state."""
        if idx < 0 or idx >= len(self.cards):
            return
        preview_active = self._state == 2
        self.cards[idx].highlight(True, preview_active)

    def _move_highlight(self, idx):
        """Move highlight without changing preview."""
        if idx < 0 or idx >= len(self.cards):
            return
        for c in self.cards:
            c.highlight(False)
        self.highlighted_idx = idx
        self._refresh_hl_style(idx)
        self._scroll_to_card(idx)
        # Notify cross-reference panel of the keyboard-navigated verse
        if 0 <= idx < len(self.verses):
            self.highlighted_verse_changed.emit(self.verses[idx])

    def _scroll_to_card(self, idx):
        """Scroll the verse list so the card at idx is visible."""
        if idx < 0 or idx >= len(self.cards):
            return
        card = self.cards[idx]
        self.scroll.ensureWidgetVisible(card, 20, 20)

    def _push_highlighted(self):
        """Enter key: Activate the currently highlighted verse's push button logic."""
        if self.highlighted_idx < 0 or self.highlighted_idx >= len(self.verses):
            return
        verse = self.verses[self.highlighted_idx]
        self._on_card_pushed(verse)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Down:
            new_idx = self.highlighted_idx + 1
            if new_idx < len(self.verses):
                self._move_highlight(new_idx)
                # In State 2, also update screen
                if self._state == 2:
                    self.display.push_verse(self.verses[new_idx])
        elif key == Qt.Key.Key_Up:
            new_idx = self.highlighted_idx - 1
            if new_idx >= 0:
                self._move_highlight(new_idx)
                # In State 2, also update screen
                if self._state == 2:
                    self.display.push_verse(self.verses[new_idx])
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._push_highlighted()
        else:
            super().keyPressEvent(event)

    def _update_state_badge(self):
        """Show state indicator badge."""
        labels = {0: "IDLE", 1: "READY", 2: "LIVE"}
        colors = {
            0: "rgba(150,150,150,0.25)",
            1: "rgba(100,180,255,0.20)",
            2: "rgba(80,220,120,0.25)",
        }
        text_colors = {
            0: "#969696",
            1: "#64b4ff",
            2: "#50dc78",
        }
        state = self._state
        self.state_badge.setText(labels.get(state, ""))
        self.state_badge.setStyleSheet(
            f"color: {text_colors.get(state, '#999')}; background: {colors.get(state, 'transparent')};"
            f"border-radius: 4px; padding: 1px 0;"
        )

    def _update_hint(self):
        """Show footer hint based on current state."""
        hints = {
            0: "",
            1: "Enter or double-click to display | Arrows to navigate",
            2: "Enter to clear | Arrows navigate and update screen",
        }
        self.hint.setText(hints.get(self._state, ""))

    def _refresh_push_button(self):
        pass  # No footer button — card-level → buttons handle individual sends

    def clear(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.verses = []
        self.cards = []
        self.highlighted_idx = -1
        self._state = 0
        self._update_state_badge()
        self._update_hint()
        self.state_changed.emit(self._state)

    def _find_verse_index(self, verses, target_verse):
        """Resolve a verse number to the matching list index, with a safe fallback."""
        if not verses:
            return -1
        target_str = str(target_verse)
        for idx, verse in enumerate(verses):
            if str(verse.get("verse", "")) == target_str:
                return idx
        return 0

    def _replace_cards(self, verses, highlight_idx, state, emit_highlight=False):
        """Finalize navigator contents and reveal them only after scroll state is correct."""
        try:
            while self.content_layout.count():
                item = self.content_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            self.verses = verses
            self.cards = []
            self.highlighted_idx = -1

            for i, verse in enumerate(verses):
                card = NavVerseCard(verse, index=i)
                card.mouse_clicked.connect(self._on_select)
                card.btn_pushed.connect(self._on_card_pushed)
                card.queue_requested.connect(self.queue_requested.emit)
                card.playlist_requested.connect(self.playlist_requested.emit)
                self.cards.append(card)
                self.content_layout.addWidget(card)

            self.content_layout.addStretch()

            if verses:
                safe_idx = min(max(highlight_idx, 0), len(verses) - 1)
                self.highlighted_idx = safe_idx
                self._refresh_hl_style(safe_idx)
            else:
                safe_idx = -1

            self._state = state
            self._update_state_badge()
            self._update_hint()
            self.state_changed.emit(self._state)
        finally:
            self.scroll.setVisible(True)
            self.setUpdatesEnabled(True)
            self.content_layout.activate()
            self.content.adjustSize()
            self.update()

        if safe_idx >= 0:
            # Scroll after the cards are visible so Qt uses final geometry.
            QTimer.singleShot(0, lambda idx=safe_idx, emit=emit_highlight: self._finalize_target_visibility(idx, emit))

    def _finalize_target_visibility(self, idx, emit_highlight):
        """Make the highlighted verse visible after layout settles."""
        if idx < 0 or idx >= len(self.cards):
            return
        self.scroll.verticalScrollBar().setValue(0)
        self._scroll_to_card(idx)
        if emit_highlight and idx < len(self.verses):
            self.highlighted_verse_changed.emit(self.verses[idx])

    def reload_translation(self, translation=""):
        """Reload the current chapter with a different translation.
        Filters navigator to show ONLY the selected translation.
        Preserves state, highlight, and focus so keyboard workflow continues."""
        if not self.verses:
            return

        # Save current state before reload
        saved_state = self._state
        saved_highlight_idx = self.highlighted_idx

        book = self.verses[0].get("book", "")
        chapter = self.verses[0].get("chapter", 0)
        target = self.verses[saved_highlight_idx].get("verse", 1) if saved_highlight_idx >= 0 else 1

        new_verses = self.db.get_chapter_verses(book, chapter, translation)
        if new_verses:
            hl_idx = self._find_verse_index(new_verses, target)
            self.setUpdatesEnabled(False)
            self.scroll.setVisible(False)
            self._replace_cards(new_verses, hl_idx, state=saved_state, emit_highlight=True)

            # Keep focus on navigator so keyboard continues to work
            QTimer.singleShot(50, lambda: self.setFocus())


class NavVerseCard(QFrame):
    """A single verse row in the navigator. Can be highlighted or normal."""
    mouse_clicked = pyqtSignal(int, object)  # index, QMouseEvent
    btn_pushed = pyqtSignal(dict)
    queue_requested = pyqtSignal(dict)
    playlist_requested = pyqtSignal(dict)

    def __init__(self, verse, index=0, parent=None):
        super().__init__(parent)
        self.verse = verse
        self.index = index
        self._highlighted = False
        self._hovered = False
        self.setProperty("panel", True)
        self.setFixedHeight(90)
        # Cards should not accept focus - let parent navigator handle keyboard events
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled)  # Enables double-click

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Verse number
        num = QLabel(str(verse["verse"]))
        num.setFixedWidth(28)
        num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        # Make children ignore mouse clicks so parent QFrame receives them
        num.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.num_label = num
        layout.addWidget(num)

        # Verse text
        text = QLabel(verse["text"])
        text.setFont(QFont("Segoe UI", 12))
        text.setWordWrap(True)
        text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.text_label = text
        layout.addWidget(text, 1)

        # Buttons layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        # Queue button (SVG plus icon)
        qbtn = QPushButton()
        qbtn.setIcon(icons.get_queue_icon(size=20))
        qbtn.setIconSize(QSize(20, 20))
        qbtn.setFixedSize(28, 28)
        qbtn.setCursor(Qt.CursorShape.PointingHandCursor)
        qbtn.setToolTip("Add to queue")
        qbtn.setStyleSheet("""
            QPushButton {
                background: rgba(76,175,125,0.12);
                border: 1px solid rgba(76,175,125,0.2);
                border-radius: 6px;
            }
            QPushButton:hover { background: rgba(76,175,125,0.25); }
        """)
        qbtn.clicked.connect(lambda: self.queue_requested.emit(self.verse))
        self.queue_btn = qbtn
        btn_layout.addWidget(qbtn)

        # Playlist button (SVG list icon)
        pbtn = QPushButton()
        pbtn.setIcon(icons.get_playlist_icon(size=20))
        pbtn.setIconSize(QSize(20, 20))
        pbtn.setFixedSize(28, 28)
        pbtn.setCursor(Qt.CursorShape.PointingHandCursor)
        pbtn.setToolTip("Add to playlist")
        pbtn.setStyleSheet("""
            QPushButton {
                background: rgba(200,160,60,0.12);
                border: 1px solid rgba(200,160,60,0.2);
                border-radius: 6px;
            }
            QPushButton:hover { background: rgba(200,160,60,0.25); }
        """)
        pbtn.clicked.connect(lambda: self.playlist_requested.emit(self.verse))
        self.playlist_btn = pbtn
        btn_layout.addWidget(pbtn)

        # Push button (arrow sends this specific verse)
        btn = QPushButton()
        btn.setIcon(icons.get_arrow_right_icon(size=20))
        btn.setIconSize(QSize(20, 20))
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(200,160,60,0.12);
                color: #c8a03c;
                border: 1px solid rgba(200,160,60,0.2);
                border-radius: 6px;
            }
            QPushButton:hover { background: rgba(200,160,60,0.25); }
        """)
        btn.clicked.connect(lambda: self.btn_pushed.emit(self.verse))
        self.push_btn = btn
        btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)

        # Always show push button internally, queue is always shown
        self.push_btn.setVisible(True)
        self.highlight(False)

    def highlight(self, state, preview_active=False):
        """Toggle the highlight state.
        preview_active=True → State 2: glowing, fully active, button visible (acts as clear)
        preview_active=False → State 1/3: highlighted but dormant, button hidden
        """
        self._highlighted = state
        if state and preview_active:
            # State 2: active — bright border, glowing button
            self.setStyleSheet("""
                QFrame[panel="true"] {
                    background: rgba(200,160,60,0.18);
                    border: 2px solid #c8a03c;
                    border-left: 4px solid #c8a03c;
                    border-radius: 8px;
                }
            """)
            self.num_label.setStyleSheet("color: #c8a03c; background: transparent; font-size: 12px; font-weight: bold;")
            self.text_label.setStyleSheet("color: #f0e8d8; background: transparent;")
            self.push_btn.setIcon(icons.get_close_icon(size=20))
            self.push_btn.setIconSize(QSize(20, 20))
            self.push_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(200,160,60,0.30);
                    color: #ffd966;
                    border: 2px solid #c8a03c;
                    border-radius: 6px;
                }
                QPushButton:hover { background: rgba(200,160,60,0.45); }
            """)
            self.push_btn.setVisible(True)  # Show button in State 2 (click to clear)
        elif state:
            # State 1 or 3: highlighted but dormant

            self.setStyleSheet("""
                QFrame[panel="true"] {
                    background: rgba(200,160,60,0.10);
                    border: 1px solid rgba(200,160,60,0.25);
                    border-left: 3px solid #c8a03c;
                    border-radius: 8px;
                }
            """)
            self.num_label.setStyleSheet("color: #c8a03c; background: transparent; font-size: 12px; font-weight: bold;")
            self.text_label.setStyleSheet("color: #d8d0c0; background: transparent;")
            self.push_btn.setIcon(icons.get_arrow_right_icon(size=20))
            self.push_btn.setIconSize(QSize(20, 20))
            self.push_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(200,160,60,0.15);
                    color: #c8a03c;
                    border: 1px solid rgba(200,160,60,0.3);
                    border-radius: 6px;
                }
                QPushButton:hover { background: rgba(200,160,60,0.25); }
            """)
            self.push_btn.setVisible(True)  # Show button in State 1/3
        else:
            # Not highlighted - show arrow button for one-click send to screen
            self._hovered = False  # Clear hover state too
            self._apply_normal_style()
            # Show button for non-highlighted verses so user can click to send
            self.push_btn.setIcon(icons.get_arrow_right_icon(size=20))
            self.push_btn.setIconSize(QSize(20, 20))
            self.push_btn.setVisible(True)
            self.push_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(200,160,60,0.12);
                    color: #c8a03c;
                    border: 1px solid rgba(200,160,60,0.2);
                    border-radius: 6px;
                }
                QPushButton:hover { background: rgba(200,160,60,0.25); }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_clicked.emit(self.index, event)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        """Mouse hover — mini highlight."""
        self._hovered = True
        self._apply_hover_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Mouse leave — remove mini highlight."""
        self._hovered = False
        if not self._highlighted:
            self._apply_normal_style()
        else:
            # Still highlighted, restore the active/highlight style
            pass  # highlight() will restyle
        super().leaveEvent(event)

    def _apply_hover_style(self):
        """Mini hover highlight — shows verse is clickable."""
        if self._highlighted:
            return  # already highlighted, keep highlight style
        self.setStyleSheet("""
            QFrame[panel="true"] {
                background: rgba(200,160,60,0.06);
                border: 1px solid rgba(200,160,60,0.18);
                border-left: 3px solid rgba(200,160,60,0.5);
                border-radius: 8px;
            }
        """)
        self.num_label.setStyleSheet("color: #c8a03c; background: transparent; font-size: 12px; font-weight: bold;")
        self.text_label.setStyleSheet("color: #d8d0c0; background: transparent;")
        self.push_btn.setStyleSheet("""
            QPushButton {
                background: rgba(200,160,60,0.12);
                color: #c8a03c;
                border: 1px solid rgba(200,160,60,0.2);
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover { background: rgba(200,160,60,0.25); }
        """)

    def _apply_normal_style(self):
        """Default non-highlighted appearance."""
        self.setStyleSheet("""
            QFrame[panel="true"] {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 8px;
            }
        """)
        self.num_label.setStyleSheet("color: rgba(200,160,60,0.3); background: transparent; font-size: 12px; font-weight: bold;")
        self.text_label.setStyleSheet("color: #c0b8a8; background: transparent;")
        self.push_btn.setStyleSheet("""
            QPushButton {
                background: rgba(200,160,60,0.12);
                color: #c8a03c;
                border: 1px solid rgba(200,160,60,0.2);
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover { background: rgba(200,160,60,0.25); }
        """)


# ── Keyword Results List ───────────────────────────────────────────────────

class KeywordResults(QWidget):
    verse_pushed = pyqtSignal(dict)
    queue_requested = pyqtSignal(dict)
    playlist_requested = pyqtSignal(dict)

    def __init__(self, db=None, display=None):
        super().__init__()
        self.db = db
        self.display = display
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.count_label = QLabel("")
        self.count_label.setFont(QFont("Segoe UI", 9))
        self.count_label.setStyleSheet("color: rgba(200,160,60,0.5); background: transparent; padding: 4px 0;")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.count_label.setVisible(False)
        layout.addWidget(self.count_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 8, 0)
        self.content_layout.setSpacing(6)

        scroll.setWidget(self.content)
        layout.addWidget(scroll)

    def set_verses(self, verses, total=None, capped=False, query=""):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        # Clear any lingering display overlays from previous search
        if self.display:
            self.display.clear_translations()
        # Update count label
        if total is not None and verses:
            if capped:
                self.count_label.setText(f"Showing {len(verses)} of {total} results")
            else:
                self.count_label.setText(f"{total} result{'s' if total != 1 else ''}")
            self.count_label.setVisible(True)
        else:
            self.count_label.setVisible(False)
        if not verses:
            empty = QLabel("No verses found.")
            empty.setFont(QFont("Segoe UI", 12))
            empty.setStyleSheet("color: rgba(200,160,60,0.25); background: transparent; padding: 30px;")
            self.content_layout.addWidget(empty)
            return
        for v in verses:
            card = KeywordVerseCard(v, self.db, self.display, query=query)
            card.pushed.connect(self.verse_pushed.emit)
            card.queue_requested.connect(self.queue_requested.emit)
            card.playlist_requested.connect(self.playlist_requested.emit)
            self.content_layout.addWidget(card)
        self.content_layout.addStretch()


class KeywordVerseCard(QFrame):
    pushed = pyqtSignal(dict)
    queue_requested = pyqtSignal(dict)
    playlist_requested = pyqtSignal(dict)

    def __init__(self, verse, db=None, display=None, parent=None, query=""):
        super().__init__(parent)
        self.verse = verse
        self.db = db
        self.display = display
        self._on_display = False  # Toggle state
        self.setProperty("panel", True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        v_layout = QVBoxLayout()
        v_layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        ref = QLabel(verse["reference"])
        ref.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        ref.setStyleSheet("color: #c8a03c; background: transparent; letter-spacing: 1px;")
        top_row.addWidget(ref)

        trans_badge = QLabel(abbreviate_translation(verse["translation"]))
        trans_badge.setFont(QFont("Segoe UI", 8))
        trans_badge.setStyleSheet(
            "color: rgba(76,175,125,0.8); background: rgba(76,175,125,0.1); "
            "border: 1px solid rgba(76,175,125,0.2); border-radius: 6px; padding: 1px 8px;"
        )
        top_row.addWidget(trans_badge)
        top_row.addStretch()
        v_layout.addLayout(top_row)

        highlighted = self._highlight_matches(verse["text"], query)
        text = QLabel(highlighted)
        text.setFont(QFont("Segoe UI", 11))
        text.setStyleSheet("color: #d0c8b8; background: transparent;")
        text.setWordWrap(True)
        text.setTextFormat(Qt.TextFormat.RichText)
        v_layout.addWidget(text)

        v_layout.addStretch()
        layout.addLayout(v_layout, 1)

        # Right side: checkbox (overlay) + push button
        right_col = QVBoxLayout()
        right_col.setSpacing(4)
        right_col.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Overlay checkbox
        self.overlay_cb = QCheckBox()
        self.overlay_cb.setFixedSize(16, 16)
        self.overlay_cb.setToolTip("Add to overlay")
        self.overlay_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.overlay_cb.setStyleSheet("""
            QCheckBox {
                spacing: 0px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
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
        self.overlay_cb.stateChanged.connect(self._on_overlay_toggle)
        right_col.addWidget(self.overlay_cb, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Queue button (SVG plus icon)
        qbtn = QPushButton()
        qbtn.setIcon(icons.get_queue_icon(size=18))
        qbtn.setIconSize(QSize(18, 18))
        qbtn.setFixedSize(24, 24)
        qbtn.setToolTip("Add to queue")
        qbtn.setCursor(Qt.CursorShape.PointingHandCursor)
        qbtn.setStyleSheet("""
            QPushButton {
                background: rgba(76,175,125,0.12);
                border: 1px solid rgba(76,175,125,0.2);
                border-radius: 5px;
            }
            QPushButton:hover { background: rgba(76,175,125,0.25); }
        """)
        qbtn.clicked.connect(lambda: self.queue_requested.emit(self.verse))
        self.queue_btn = qbtn
        right_col.addWidget(qbtn, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Playlist button (SVG list icon)
        pbtn = QPushButton()
        pbtn.setIcon(icons.get_playlist_icon(size=18))
        pbtn.setIconSize(QSize(18, 18))
        pbtn.setFixedSize(24, 24)
        pbtn.setToolTip("Add to playlist")
        pbtn.setCursor(Qt.CursorShape.PointingHandCursor)
        pbtn.setStyleSheet("""
            QPushButton {
                background: rgba(200,160,60,0.12);
                border: 1px solid rgba(200,160,60,0.2);
                border-radius: 5px;
            }
            QPushButton:hover { background: rgba(200,160,60,0.25); }
        """)
        pbtn.clicked.connect(lambda: self.playlist_requested.emit(self.verse))
        self.playlist_btn = pbtn
        right_col.addWidget(pbtn, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Push/Clear toggle button
        btn = QPushButton()
        btn.setIcon(icons.get_arrow_right_icon(size=24))
        btn.setIconSize(QSize(24, 24))
        btn.setFixedSize(32, 32)
        btn.setToolTip("Push to display")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_push_btn(btn)
        btn.clicked.connect(self._on_push_click)
        self._push_btn = btn
        right_col.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addLayout(right_col)

    def _style_push_btn(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(200,160,60,0.12);
                color: #c8a03c;
                border: 1px solid rgba(200,160,60,0.2);
                border-radius: 6px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(200,160,60,0.25);
                border: 1px solid rgba(200,160,60,0.4);
            }
            QPushButton:pressed {
                background: rgba(200,160,60,0.35);
            }
        """)

    def _style_clear_btn(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(224,92,75,0.15);
                color: #e05c4b;
                border: 1px solid rgba(224,92,75,0.3);
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(224,92,75,0.3);
                border: 1px solid rgba(224,92,75,0.5);
            }
            QPushButton:pressed {
                background: rgba(224,92,75,0.4);
            }
        """)

    def _on_push_click(self):
        if self._on_display:
            # Clear from display
            if self.display:
                self.display.push_verse({})
            self._on_display = False
            self._push_btn.setIcon(icons.get_arrow_right_icon(size=24))
            self._push_btn.setIconSize(QSize(24, 24))
            self._push_btn.setToolTip("Push to display")
            self._style_push_btn(self._push_btn)
        else:
            # Push to display
            self.pushed.emit(self.verse)
            self._on_display = True
            self._push_btn.setIcon(icons.get_close_icon(size=24))
            self._push_btn.setIconSize(QSize(24, 24))
            self._push_btn.setToolTip("Clear from display")
            self._style_clear_btn(self._push_btn)

    @staticmethod
    def _highlight_matches(text, query):
        """Wrap matched keywords/phrases in bold tags for rich-text display."""
        if not query or not text:
            return text
        import re as _re
        # Extract quoted phrases and bare words
        phrases = _re.findall(r'"([^"]*)"', query)
        remainder = _re.sub(r'"[^"]*"', '', query).strip()
        terms = [p for p in phrases if p.strip()] + [w for w in remainder.split() if w]
        if not terms:
            return text
        # Build a single regex alternation, longest terms first to avoid partial overlap
        terms.sort(key=len, reverse=True)
        escaped = [_re.escape(t) for t in terms]
        pattern = _re.compile("(" + "|".join(escaped) + ")", _re.IGNORECASE)
        return pattern.sub(r'<b style="color:#c8a03c;">\1</b>', text)

    def _on_overlay_toggle(self, state):
        """Add or remove this verse as an overlay translation."""
        if not self.db or not self.display:
            return
        trans_name = self.verse.get("translation", "")
        if state == Qt.CheckState.Checked.value:
            # Add as overlay
            self.display.add_translation(self.verse)
        else:
            # Remove this translation from overlays
            for i, ov in enumerate(self.display.secondary_translations):
                if ov.get("translation") == trans_name:
                    self.display.remove_translation(i)
                    break

