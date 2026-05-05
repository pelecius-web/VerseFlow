"""main.py — VerseFlow Stage 3: Dual-Monitor Display (v0.7.0 — Phase 2: Presenter View)

Verse lookup opens full chapter navigator with highlight + arrow-key navigation.
Keyword search returns flat result list. Translation selector filters results.
Phase 2 additions: Dual-monitor presenter view, congregation display window,
operator control, monitor detection, fullscreen support.
"""

import re
import sys
import sqlite3
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QObject, QEvent, QPoint
from PyQt6.QtGui import QFont, QFontMetrics, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QLabel, QLineEdit, QComboBox, QScrollArea,
    QFrame, QSizePolicy, QPushButton, QCheckBox,
)

# ── Local imports (Phase 1 modular components) ───────────────────────────────
from theme import ThemeManager, DEFAULT_THEME
from crossrefs import CrossRefManager
from display_window import DisplayWindow
from settings import SettingsManager

# ── Category 1 modular components ────────────────────────────────────────────
from document_manager import DocumentManager
from models import PlaylistModel, QueueModel
from queue_panel import QueuePanel

# ── Paths ────────────────────────────────────────────────────────────────────

DB_PATH = Path(__file__).parent.parent / "3. Database" / "verseflow.db"

# Book name helpers — canonical DB names
BOOK_NAMES = {
    1: "Genesis", 2: "Exodus", 3: "Leviticus", 4: "Numbers", 5: "Deuteronomy",
    6: "Joshua", 7: "Judges", 8: "Ruth", 9: "1 Samuel", 10: "2 Samuel",
    11: "1 Kings", 12: "2 Kings", 13: "1 Chronicles", 14: "2 Chronicles",
    15: "Ezra", 16: "Nehemiah", 17: "Esther", 18: "Job", 19: "Psalms", 20: "Proverbs",
    21: "Ecclesiastes", 22: "Song of Solomon", 23: "Isaiah", 24: "Jeremiah",
    25: "Lamentations", 26: "Ezekiel", 27: "Daniel", 28: "Hosea", 29: "Joel",
    30: "Amos", 31: "Obadiah", 32: "Jonah", 33: "Micah", 34: "Nahum", 35: "Habakkuk",
    36: "Zephaniah", 37: "Haggai", 38: "Zechariah", 39: "Malachi",
    40: "Matthew", 41: "Mark", 42: "Luke", 43: "John", 44: "Acts",
    45: "Romans", 46: "1 Corinthians", 47: "2 Corinthians", 48: "Galatians",
    49: "Ephesians", 50: "Philippians", 51: "Colossians", 52: "1 Thessalonians",
    53: "2 Thessalonians", 54: "1 Timothy", 55: "2 Timothy", 56: "Titus",
    57: "Philemon", 58: "Hebrews", 59: "James", 60: "1 Peter", 61: "2 Peter",
    62: "1 John", 63: "2 John", 64: "3 John", 65: "Jude", 66: "Revelation",
}
BOOK_TO_NUM = {v: k for k, v in BOOK_NAMES.items()}

BOOK_ABBREV_MAP = {
    "Genesis": "Gen", "Exodus": "Exod", "Leviticus": "Lev", "Numbers": "Num",
    "Deuteronomy": "Deut", "Joshua": "Josh", "Judges": "Judg", "Ruth": "Ruth",
    "1 Samuel": "1 Sam", "2 Samuel": "2 Sam", "1 Kings": "1 Kgs", "2 Kings": "2 Kgs",
    "1 Chronicles": "1 Chr", "2 Chronicles": "2 Chr", "Ezra": "Ezra", "Nehemiah": "Neh",
    "Esther": "Esth", "Job": "Job", "Psalms": "Ps", "Proverbs": "Prov",
    "Ecclesiastes": "Eccl", "Song of Solomon": "Song", "Isaiah": "Isa", "Jeremiah": "Jer",
    "Lamentations": "Lam", "Ezekiel": "Ezek", "Daniel": "Dan", "Hosea": "Hos",
    "Joel": "Joel", "Amos": "Amos", "Obadiah": "Obad", "Jonah": "Jonah",
    "Micah": "Mic", "Nahum": "Nah", "Habakkuk": "Hab", "Zephaniah": "Zeph",
    "Haggai": "Hag", "Zechariah": "Zech", "Malachi": "Mal", "Matthew": "Matt",
    "Mark": "Mark", "Luke": "Luke", "John": "John", "Acts": "Acts",
    "Romans": "Rom", "1 Corinthians": "1 Cor", "2 Corinthians": "2 Cor",
    "Galatians": "Gal", "Ephesians": "Eph", "Philippians": "Phil", "Colossians": "Col",
    "1 Thessalonians": "1 Thess", "2 Thessalonians": "2 Thess", "1 Timothy": "1 Tim",
    "2 Timothy": "2 Tim", "Titus": "Titus", "Philemon": "Phlm", "Hebrews": "Heb",
    "James": "Jas", "1 Peter": "1 Pet", "2 Peter": "2 Pet", "1 John": "1 John",
    "2 John": "2 John", "3 John": "3 John", "Jude": "Jude", "Revelation": "Rev"
}

# Abbreviations & aliases for book names — maps variant → canonical DB name
BOOK_ALIASES = {
    "gen": "Genesis", "ge": "Genesis", "gn": "Genesis",
    "exo": "Exodus", "ex": "Exodus", "exod": "Exodus",
    "lev": "Leviticus", "le": "Leviticus", "lv": "Leviticus",
    "num": "Numbers", "nu": "Numbers", "nb": "Numbers", "nm": "Numbers",
    "deu": "Deuteronomy", "de": "Deuteronomy", "dt": "Deuteronomy",
    "jos": "Joshua", "josh": "Joshua",
    "jdg": "Judges", "judg": "Judges",
    "rut": "Ruth", "ru": "Ruth",
    "1sam": "1 Samuel", "1samuel": "1 Samuel", "1sa": "1 Samuel", "1 s": "1 Samuel", "1 sm": "1 Samuel", "i sam": "1 Samuel", "i samuel": "1 Samuel",
    "2sam": "2 Samuel", "2samuel": "2 Samuel", "2sa": "2 Samuel", "2 s": "2 Samuel", "2 sm": "2 Samuel", "ii sam": "2 Samuel", "ii samuel": "2 Samuel",
    "1kin": "1 Kings", "1king": "1 Kings", "1k": "1 Kings", "1 k": "1 Kings", "i kin": "1 Kings", "i king": "1 Kings",
    "2kin": "2 Kings", "2king": "2 Kings", "2k": "2 Kings", "2 k": "2 Kings", "ii kin": "2 Kings", "ii king": "2 Kings",
    "1chr": "1 Chronicles", "1ch": "1 Chronicles", "1 chron": "1 Chronicles", "1 chr": "1 Chronicles", "i chr": "1 Chronicles", "i chron": "1 Chronicles", "1chron": "1 Chronicles",
    "2chr": "2 Chronicles", "2ch": "2 Chronicles", "2 chron": "2 Chronicles", "2 chr": "2 Chronicles", "ii chr": "2 Chronicles", "ii chron": "2 Chronicles", "2chron": "2 Chronicles",
    "ezr": "Ezra", "ez": "Ezra",
    "neh": "Nehemiah", "ne": "Nehemiah",
    "est": "Esther", "es": "Esther",
    "job": "Job", "jb": "Job",
    "psa": "Psalms", "ps": "Psalms", "psalm": "Psalms", "pss": "Psalms",
    "pro": "Proverbs", "pr": "Proverbs", "prov": "Proverbs",
    "ecc": "Ecclesiastes", "ec": "Ecclesiastes", "eccl": "Ecclesiastes",
    "sos": "Song of Solomon", "song": "Song of Solomon", "ss": "Song of Solomon", "sg": "Song of Solomon",
    "isa": "Isaiah", "is": "Isaiah",
    "jer": "Jeremiah", "je": "Jeremiah",
    "lam": "Lamentations", "la": "Lamentations",
    "eze": "Ezekiel", "ezk": "Ezekiel", "ezek": "Ezekiel",
    "dan": "Daniel", "da": "Daniel", "dn": "Daniel",
    "hos": "Hosea", "ho": "Hosea",
    "jol": "Joel", "jl": "Joel",
    "amo": "Amos", "am": "Amos",
    "obad": "Obadiah", "ob": "Obadiah", "oba": "Obadiah", "obd": "Obadiah",
    "jon": "Jonah", "jnh": "Jonah", "jonah": "Jonah",
    "mic": "Micah", "mc": "Micah",
    "nah": "Nahum", "na": "Nahum",
    "hab": "Habakkuk", "hb": "Habakkuk",
    "zep": "Zephaniah", "zeph": "Zephaniah", "zp": "Zephaniah", "zephania": "Zephaniah",
    "hag": "Haggai", "hg": "Haggai",
    "zec": "Zechariah", "zech": "Zechariah", "zch": "Zechariah",
    "mal": "Malachi", "ml": "Malachi",
    "mat": "Matthew", "matt": "Matthew", "mt": "Matthew", "ma": "Matthew", "mathew": "Matthew", "mtt": "Matthew",
    "mar": "Mark", "mk": "Mark", "mrk": "Mark", "mr": "Mark", "mark": "Mark",
    "luk": "Luke", "lk": "Luke", "lu": "Luke",
    "jhn": "John", "jn": "John", "jo": "John", "joh": "John",
    "act": "Acts", "ac": "Acts",
    "rom": "Romans", "ro": "Romans", "rm": "Romans",
    "1cor": "1 Corinthians", "1 co": "1 Corinthians", "1cori": "1 Corinthians", "1 cor": "1 Corinthians", "1 corin": "1 Corinthians", "1 corinth": "1 Corinthians", "i cor": "1 Corinthians", "i corinth": "1 Corinthians", "1corint": "1 Corinthians", "1corinth": "1 Corinthians",
    "2cor": "2 Corinthians", "2 co": "2 Corinthians", "2cori": "2 Corinthians", "2 cor": "2 Corinthians", "2 corin": "2 Corinthians", "2 corinth": "2 Corinthians", "ii cor": "2 Corinthians", "ii corinth": "2 Corinthians", "2corint": "2 Corinthians", "2corinth": "2 Corinthians",
    "gal": "Galatians", "ga": "Galatians", "gl": "Galatians",
    "eph": "Ephesians", "ep": "Ephesians", "ephn": "Ephesians",
    "php": "Philippians", "phil": "Philippians", "pp": "Philippians", "phi": "Philippians",
    "col": "Colossians", "co": "Colossians", "cl": "Colossians", "coloss": "Colossians",
    "1thes": "1 Thessalonians", "1 th": "1 Thessalonians", "1 thess": "1 Thessalonians", "i th": "1 Thessalonians", "1thess": "1 Thessalonians",
    "2thes": "2 Thessalonians", "2 th": "2 Thessalonians", "2 thess": "2 Thessalonians", "ii th": "2 Thessalonians", "2thess": "2 Thessalonians",
    "1tim": "1 Timothy", "1 ti": "1 Timothy", "1 tim": "1 Timothy", "i tim": "1 Timothy", "1timothy": "1 Timothy",
    "2tim": "2 Timothy", "2 ti": "2 Timothy", "2 tim": "2 Timothy", "ii tim": "2 Timothy", "2timothy": "2 Timothy",
    "tit": "Titus", "ti": "Titus",
    "phm": "Philemon", "pm": "Philemon", "phile": "Philemon", "philem": "Philemon",
    "heb": "Hebrews", "he": "Hebrews", "hb": "Hebrews",
    "jas": "James", "ja": "James", "jm": "James",
    "1pet": "1 Peter", "1 pt": "1 Peter", "1 pet": "1 Peter", "i pet": "1 Peter", "1 peter": "1 Peter", "1peter": "1 Peter",
    "2pet": "2 Peter", "2 pt": "2 Peter", "2 pet": "2 Peter", "ii pet": "2 Peter", "2 peter": "2 Peter", "2peter": "2 Peter",
    "1jn": "1 John", "1 jo": "1 John", "1 joh": "1 John", "i jn": "1 John", "i joh": "1 John", "1john": "1 John",
    "2jn": "2 John", "2 jo": "2 John", "2 joh": "2 John", "ii jn": "2 John", "ii joh": "2 John", "2john": "2 John",
    "3jn": "3 John", "3 jo": "3 John", "3 joh": "3 John", "iii jn": "3 John", "iii joh": "3 John", "3john": "3 John",
    "jud": "Jude", "judah": "Jude", "jd": "Jude",
    "rev": "Revelation", "re": "Revelation", "rv": "Revelation", "revl": "Revelation",
}
BOOK_ALIAS_MAP = {}
for _alias, _canonical in BOOK_ALIASES.items():
    BOOK_ALIAS_MAP[_alias.lower()] = _canonical
for _name in BOOK_NAMES.values():
    BOOK_ALIAS_MAP[_name.lower()] = _name


def _resolve_book(raw_book):
    """Resolve a user-typed book name/abbreviation to the canonical DB name."""
    key = raw_book.lower().strip()
    if key in BOOK_ALIAS_MAP:
        return BOOK_ALIAS_MAP[key]
    def norm(s):
        return s.lower().replace(" ", "").replace(".", "").replace("-", "")
    norm_key = norm(raw_book)
    for alias, canonical in BOOK_ALIAS_MAP.items():
        if norm(alias) == norm_key:
            return canonical
    return None


REF_RE = re.compile(r'^(.+?)\s+(\d+):(\d+)$', re.IGNORECASE)

# Flexible verse look-up: matches "John 3:16", "John 3,16", "John 3 16", etc.
VERSE_LOOKUP_RE = re.compile(
    r'^(.+?)\s*[ :;,\./\-_]+?\s*(\d+)\s*[ :;,\./\-_]+?\s*(\d+)\s*$', re.IGNORECASE
)

MAX_RESULTS = 50


# ── Database ─────────────────────────────────────────────────────────────────

class VerseDB:
    def __init__(self, db_path=None):
        self.db_path = db_path or str(DB_PATH)

    def _conn(self, readonly=True):
        if readonly:
            return sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        return sqlite3.connect(self.db_path)

    def get_translations(self):
        c = self._conn()
        rows = c.execute("SELECT DISTINCT translation FROM verses ORDER BY translation").fetchall()
        c.close()
        return [r[0] for r in rows]

    def lookup_verse(self, query, translation=""):
        """Flexible verse look-up. Returns (book, chapter, target_verse, verses_list)."""
        q = query.strip()
        if not q:
            return None
        m = VERSE_LOOKUP_RE.match(q)
        if not m:
            return None
        raw_book = m.group(1).strip()
        book = _resolve_book(raw_book)
        if book is None:
            return None
        chapter, target_verse = int(m.group(2)), int(m.group(3))
        c = self._conn()
        sql = "SELECT id, translation, book, chapter, verse, text, reference FROM verses WHERE book=? AND chapter=?"
        params = [book, chapter]
        if translation:
            sql += " AND translation=?"
            params.append(translation)
        sql += " ORDER BY verse"
        rows = c.execute(sql, params).fetchall()
        c.close()
        verses = [
            {"id": r[0], "translation": r[1], "book": r[2], "chapter": r[3],
             "verse": r[4], "text": r[5], "reference": r[6]}
            for r in rows
        ]
        return {"book": book, "chapter": chapter, "target_verse": target_verse, "verses": verses}

    def search(self, query, translation=""):
        """Search by reference or keyword. Returns list of verse dicts."""
        q = query.strip()
        if not q:
            return []

        c = self._conn()

        m = REF_RE.match(q) or VERSE_LOOKUP_RE.match(q)
        if m:
            raw_book = m.group(1).strip()
            book = _resolve_book(raw_book)
            if book is None:
                return self._keyword_search(c, q, translation)
            chapter, verse = int(m.group(2)), int(m.group(3))
            sql = (
                "SELECT id, translation, book, chapter, verse, text, reference FROM verses"
                " WHERE book=? AND chapter=? AND verse=?"
            )
            params = [book, chapter, verse]
            if translation:
                sql += " AND translation=?"
                params.append(translation)
            rows = c.execute(sql, params).fetchall()
            c.close()
            return [
                {"id": r[0], "translation": r[1], "book": r[2], "chapter": r[3],
                 "verse": r[4], "text": r[5], "reference": r[6]}
                for r in rows
            ]

        return self._keyword_search(c, q, translation)

    def _keyword_search(self, conn, query, translation=""):
        """Search for the exact phrase in verse text or reference (case-insensitive).

        Supports quoted phrases: "God so loved" → exact phrase match
        Without quotes: "For God so" → treated as a contiguous phrase
        """
        try:
            # Check for quoted phrases
            quoted = re.findall(r'"([^"]*)"', query)
            if quoted:
                phrase = ' '.join(quoted[0].split())
            else:
                # Treat entire input as a phrase
                phrase = ' '.join(query.split())

            if not phrase:
                return []

            sql = """
                SELECT id, translation, book, chapter, verse, text, reference
                FROM verses
                WHERE (text LIKE ? OR reference LIKE ?)
            """
            params = [f"%{phrase}%", f"%{phrase}%"]
            if translation:
                sql += " AND translation = ?"
                params.append(translation)
            sql += f" LIMIT {MAX_RESULTS}"

            rows = conn.execute(sql, params).fetchall()
            return [
                {"id": r[0], "translation": r[1], "book": r[2], "chapter": r[3],
                 "verse": r[4], "text": r[5], "reference": r[6]}
                for r in rows
            ]
        finally:
            conn.close()

    def get_verse(self, reference, translation=""):
        """Get a single verse by reference string like 'John 3:16'."""
        m = REF_RE.match(reference.strip())
        if not m:
            m = VERSE_LOOKUP_RE.match(reference.strip())
        if m:
            raw_book = m.group(1).strip()
            book = _resolve_book(raw_book)
            if book is None:
                return None
            chapter, verse = int(m.group(2)), int(m.group(3))
            c = self._conn()
            sql = (
                "SELECT id, translation, book, chapter, verse, text, reference FROM verses"
                " WHERE book=? AND chapter=? AND verse=?"
            )
            params = [book, chapter, verse]
            if translation:
                sql += " AND translation=?"
                params.append(translation)
            row = c.execute(sql, params).fetchone()
            c.close()
            if row:
                return {
                    "id": row[0], "translation": row[1], "book": row[2],
                    "chapter": row[3], "verse": row[4], "text": row[5], "reference": row[6],
                }
        return None


# ── Display Controller ──────────────────────────────────────────────────────

class DisplayController(QObject):
    """Manages what's shown on the congregation display.
    Phase 1: Added draft/publish (real-time editing) and layout modes.
    Phase 2: Central IPC bus for operator/display communication.
    """
    verse_changed = pyqtSignal(dict)
    layout_changed = pyqtSignal(str)
    draft_changed = pyqtSignal(dict)
    # Phase 2: Additional signals for display window management
    display_opened = pyqtSignal()
    display_closed = pyqtSignal()
    fullscreen_toggled = pyqtSignal(bool)
    # Multi-translation overlay support
    translations_changed = pyqtSignal(list)  # List of verse dicts for overlay

    LAYOUTS = ("single", "overlay", "chapter")

    def __init__(self, parent=None, db=None, theme_mgr=None):
        super().__init__(parent)
        self.db = db  # Database reference for overlay verse lookups
        self.theme_mgr = theme_mgr  # Theme manager for display window creation
        self.current = None      # Primary verse
        self.next = None
        self.history = []
        # Phase 1: draft/publish
        self.draft = None       # unpublished verse being edited
        self.edit_notes = ""    # operator notes for current verse
        # Phase 1: layout
        self.layout_mode = "single"
        # Phase 2: display window reference (lazily created)
        self.display_window = None
        # Multi-translation support
        self.secondary_translations = []  # List of additional verses for overlay
        self._overlay_translations = []   # List of translation names for overlays

    def _ensure_display_window(self):
        """Lazily create the congregation display window when first verse goes live."""
        try:
            if self.display_window is None and self.theme_mgr:
                print("[DISPLAY] Lazily creating display window", flush=True)
                self.open_display_window(self.theme_mgr)
        except Exception as e:
            print(f"[DISPLAY] ERROR creating window: {e}", flush=True)
            import traceback
            traceback.print_exc()

    def push_verse(self, verse):
        """Push a verse to the display — becomes the new current.
        Lazily creates the congregation display window on first use.
        If overlays are active, automatically updates them to match the new verse."""
        # Lazily create display window when first verse goes live
        self._ensure_display_window()

        if self.current:
            self.history.append(self.current)
        if self.next:
            self.next = None
        self.current = verse
        self.draft = None

        # If empty verse — clear verse overlays but preserve checked translation names
        if not verse:
            self.secondary_translations = []
            # Keep _overlay_translations so overlays restore when next verse goes live
            self.verse_changed.emit({})
            return

        # Update overlay translations to match new verse reference
        if self._overlay_translations and self.db:
            ref = verse.get("reference", "")
            ref_match = re.match(r'(.+?)\s+(\d+):(\d+)', ref)
            if ref_match:
                book_name = ref_match.group(1).strip()
                chapter = int(ref_match.group(2))
                verse_num = int(ref_match.group(3))
                book = _resolve_book(book_name)

                if book:
                    new_overlays = []
                    for trans_name in self._overlay_translations:
                        overlay_verse = self.db.get_verse(f"{book} {chapter}:{verse_num}", trans_name)
                        if overlay_verse:
                            new_overlays.append(overlay_verse)
                    self.secondary_translations = new_overlays

        self.verse_changed.emit(verse)

    def set_next(self, verse):
        """Queue a verse as upcoming (preview)."""
        self.next = verse

    # ── Phase 1: Draft/Publish ───────────────────────────────────────────────

    def set_draft(self, verse):
        """Set a draft verse (operator editing live). Not yet published."""
        self.draft = verse
        self.draft_changed.emit(verse)

    def publish_draft(self):
        """Publish the current draft — becomes the current display verse."""
        if self.draft:
            self.push_verse(self.draft)
            self.draft = None

    def set_edit_notes(self, notes):
        self.edit_notes = notes

    # ── Phase 1: Layout Modes ────────────────────────────────────────────────

    def set_layout(self, mode):
        if mode in self.LAYOUTS:
            self.layout_mode = mode
            self.layout_changed.emit(mode)

    def clear(self):
        self.current = None
        self.next = None
        self.draft = None
        self.edit_notes = ""
        self.secondary_translations = []
        self._overlay_translations = []
        # Close display window when screen is cleared — monitor returns to original state (BibleShow behavior)
        if self.display_window:
            self.display_window.close()
            self.display_window = None
            self.display_closed.emit()
        self.verse_changed.emit({})

    # ── Phase 2: Display Window Management ───────────────────────────────────

    def open_display_window(self, theme_mgr, screen=None):
        """Open the congregation display window on specified screen."""
        if self.display_window is not None:
            self.display_window.close()

        from PyQt6.QtWidgets import QApplication
        screens = QApplication.screens()
        
        if len(screens) < 2:
            print("[DISPLAY] No external monitor detected. Display window will not open.", flush=True)
            return False
            
        if screen is None:
            screen = screens[1]

        if screen:
            self.display_window = DisplayWindow(self, theme_mgr)
            # Handle window closing itself (e.g., when verse is cleared)
            self.display_window.destroyed.connect(self._on_display_destroyed)
            self.display_window.show()
            # Move to target screen
            geo = screen.geometry()
            self.display_window.move(geo.x(), geo.y())
            self.display_window.resize(geo.width(), geo.height())
            self.display_opened.emit()
            return True
        return False

    def _on_display_destroyed(self):
        """Handle display window being closed/destroyed."""
        self.display_window = None
        self.display_closed.emit()

    def close_display_window(self):
        """Close the congregation display window."""
        if self.display_window:
            self.display_window.close()
            self.display_window = None
            self.display_closed.emit()

    def toggle_fullscreen(self):
        """Toggle fullscreen on display window."""
        if self.display_window:
            self.display_window.toggle_fullscreen()
            self.fullscreen_toggled.emit(self.display_window._is_fullscreen)
    
    # ── Multi-Translation Overlay Support ────────────────────────────────────

    def add_translation(self, verse):
        """Add a verse in another translation to the overlay."""
        if verse and verse not in self.secondary_translations:
            self.secondary_translations.append(verse)
            trans_name = verse.get("translation", "")
            if trans_name and trans_name not in self._overlay_translations:
                self._overlay_translations.append(trans_name)
            self.translations_changed.emit(self.secondary_translations)

    def remove_translation(self, index):
        """Remove a translation from overlay by index."""
        if 0 <= index < len(self.secondary_translations):
            removed = self.secondary_translations.pop(index)
            trans_name = removed.get("translation", "")
            if trans_name in self._overlay_translations:
                self._overlay_translations.remove(trans_name)
            self.translations_changed.emit(self.secondary_translations)

    def clear_translations(self):
        """Clear all secondary translations."""
        self.secondary_translations = []
        self._overlay_translations = []
        self.translations_changed.emit([])


# ── Main Window ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, theme_mgr):
        super().__init__()
        self.setWindowTitle("VerseFlow — Operator Control")
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)
        
        # Store theme manager reference
        self._theme_mgr = theme_mgr
        
        # Load settings
        self._settings = SettingsManager()

        self.db = VerseDB()
        self.display = DisplayController(db=self.db, theme_mgr=self._theme_mgr)
        self.xref_mgr = CrossRefManager()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # HomePanel now contains everything (search, preview, navigator, xrefs)
        self.home_panel = HomePanel(self.db, self.display, xref_mgr=self.xref_mgr)
        self.settings_panel = PlaceholderPanel("Settings", "Coming later")

        self.stack.addWidget(self.home_panel)  # Index 0: Home
        self.stack.addWidget(self.settings_panel)  # Index 1: Settings

        # Phase 2: Add display window management to status bar
        self.statusBar().showMessage("Ready — v0.7.1 Overlay Fix Active")
        
        # Phase 2: Add display controls to main window menu
        self._setup_display_controls()
        
        # Phase 2: Auto-open display window if configured
        QTimer.singleShot(500, self._auto_open_display)
    
    def _auto_open_display(self):
        """No longer auto-opens display window on launch.
        Display window is now created lazily when first verse goes live.
        """
        pass
    
    def _setup_display_controls(self):
        """Phase 2: Setup display window controls."""
        from PyQt6.QtGui import QAction
        
        # Create menu for display controls
        display_menu = self.menuBar().addMenu("&Display")
        
        # Open display window action
        open_display_action = QAction("&Open Display Window", self)
        open_display_action.setShortcut("Ctrl+D")
        open_display_action.triggered.connect(self._open_display)
        display_menu.addAction(open_display_action)
        
        # Close display window action
        close_display_action = QAction("&Close Display Window", self)
        close_display_action.setShortcut("Ctrl+Shift+D")
        close_display_action.triggered.connect(self._close_display)
        display_menu.addAction(close_display_action)
        
        # Toggle fullscreen action
        toggle_fs_action = QAction("Toggle &Fullscreen", self)
        toggle_fs_action.setShortcut("F11")
        toggle_fs_action.triggered.connect(self._toggle_display_fullscreen)
        display_menu.addAction(toggle_fs_action)
        
        display_menu.addSeparator()
        
        # Detect monitors action
        detect_monitors_action = QAction("&Detect Monitors", self)
        detect_monitors_action.triggered.connect(self._detect_monitors)
        display_menu.addAction(detect_monitors_action)
    
    def _open_display(self):
        """Open the congregation display window."""
        from PyQt6.QtWidgets import QApplication, QMessageBox
        screens = QApplication.screens()
        if len(screens) < 2:
            QMessageBox.information(
                self, "No Monitor Detected",
                "Only one monitor detected. The display window requires an external monitor to be connected."
            )
            return
        
        success = self.display.open_display_window(self._theme_mgr)
        if success:
            self.statusBar().showMessage("Display window opened — v0.7.1 Overlay Fix Active", 3000)
        else:
            self.statusBar().showMessage("Failed to open display window", 3000)
    
    def _close_display(self):
        """Close the congregation display window."""
        self.display.close_display_window()
        self.statusBar().showMessage("Display window closed", 3000)
    
    def _toggle_display_fullscreen(self):
        """Toggle fullscreen on the display window."""
        self.display.toggle_fullscreen()
    
    def _detect_monitors(self):
        """Detect and display information about connected monitors."""
        from PyQt6.QtWidgets import QApplication, QMessageBox
        screens = QApplication.screens()
        info = f"Detected {len(screens)} monitor(s):\n\n"
        for i, screen in enumerate(screens):
            geo = screen.geometry()
            info += f"Monitor {i+1}: {screen.name()}\n"
            info += f"  Resolution: {geo.width()}x{geo.height()}\n"
            info += f"  Position: ({geo.x()}, {geo.y()})\n\n"

        QMessageBox.information(self, "Monitor Detection", info)

    def closeEvent(self, event):
        """Close display window when app exits — prevent verse lingering on monitor."""
        self.display.close_display_window()
        event.accept()


class NavButton(QLabel):
    nav_clicked = pyqtSignal(int)

    def __init__(self, text, index):
        super().__init__("  " + text)
        self.nav_index = index
        self.setFixedHeight(42)
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.setStyleSheet(self._style(False))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_active(self, active):
        self.setStyleSheet(self._style(active))

    def _style(self, active):
        if active:
            return "background: rgba(200,160,60,0.08); color: #e8e2d8; border-left: 3px solid #c8a03c; padding-left: 21px; font-size: 13px; font-weight: 600; border-radius: 0;"
        return "background: transparent; color: rgba(200,160,60,0.4); border-left: 3px solid transparent; padding-left: 21px; font-size: 13px; font-weight: 400; border-radius: 0;"

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.nav_clicked.emit(self.nav_index)
        super().mousePressEvent(event)


# ── ModeToggle ───────────────────────────────────────────────────────────────

class ModeToggle(QFrame):
    """Verse Lookup | Keyword Search toggle."""
    mode_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_mode = "Verse Lookup"
        self.setFixedHeight(34)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.btn_verse = QPushButton("Verse Lookup")
        self.btn_keyword = QPushButton("Keyword Search")
        for btn in (self.btn_verse, self.btn_keyword):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont("Segoe UI", 10))
            btn.setFixedHeight(34)

        self.btn_verse.clicked.connect(lambda: self._set_mode("Verse Lookup"))
        self.btn_keyword.clicked.connect(lambda: self._set_mode("Keyword Search"))

        layout.addWidget(self.btn_verse)
        layout.addWidget(self.btn_keyword)

        self._refresh_style()

    def _set_mode(self, mode):
        self.current_mode = mode
        self._refresh_style()
        self.mode_changed.emit(mode)

    def _refresh_style(self):
        for btn, name in [(self.btn_verse, "Verse Lookup"), (self.btn_keyword, "Keyword Search")]:
            active = name == self.current_mode
            radii = "6px 0 0 6px" if btn == self.btn_verse else "0 6px 6px 0"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {"rgba(200,160,60,0.15)" if active else "rgba(20,20,36,0.5)"};
                    color: {"#c8a03c" if active else "rgba(200,160,60,0.4)"};
                    border: 1px solid {"rgba(200,160,60,0.3)" if active else "rgba(255,255,255,0.08)"};
                    border-radius: {radii};
                    padding: 0 16px;
                    font-weight: {"600" if active else "400"};
                }}
            """)


# ── Verse Navigator (chapter navigator with highlight) ───────────────────────

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
        self._state = 1  # State 1: chapter loaded
        self._just_loaded = True  # Grace period: suppress Enter auto-repeat from search
        QTimer.singleShot(300, lambda: setattr(self, '_just_loaded', False))
        self.verses = verses
        self.header.setText(f"{book} — Chapter {chapter}")
        
        # Update state badge
        self._update_state_badge()
        self._update_hint()
        self.state_changed.emit(self._state)

        for i, v in enumerate(verses):
            card = NavVerseCard(v, index=i)
            card.mouse_clicked.connect(self._on_select)
            card.btn_pushed.connect(self._on_card_pushed)
            card.queue_requested.connect(self.queue_requested.emit)
            self.cards.append(card)
            self.content_layout.addWidget(card)
        # Determine highlight from target verse number
        hl_idx = target_verse - 1
        if hl_idx < 0 or hl_idx >= len(verses):
            hl_idx = 0
        self.highlighted_idx = hl_idx
        self.content_layout.addStretch()
        self._refresh_hl_style(hl_idx)
        QTimer.singleShot(150, lambda: self._scroll_to_card(hl_idx))

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

    def _scroll_to_card(self, idx):
        """Scroll the verse list so the card at idx is visible."""
        if idx < 0 or idx >= len(self.cards):
            return
        bar = self.scroll.verticalScrollBar()
        if bar is not None:
            y = self.cards[idx].pos().y() - 20
            bar.setValue(max(0, y))

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
            # Suppress Enter during grace period after fresh chapter load
            if getattr(self, '_just_loaded', False):
                return
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
            1: "Enter or double-click to display • Arrows to navigate",
            2: "Enter or → to clear • Arrows navigate and update screen",
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
        target = saved_highlight_idx + 1 if saved_highlight_idx >= 0 else 1

        c = self.db._conn()
        sql = (
            "SELECT id, translation, book, chapter, verse, text, reference FROM verses"
            " WHERE book=? AND chapter=?"
        )
        params = [book, chapter]
        if translation:
            sql += " AND translation=?"
            params.append(translation)
        sql += " ORDER BY verse"
        rows = c.execute(sql, params).fetchall()
        c.close()
        new_verses = [
            {"id": r[0], "translation": r[1], "book": r[2], "chapter": r[3],
             "verse": r[4], "text": r[5], "reference": r[6]}
            for r in rows
        ]
        if new_verses:
            # Don't call load_chapter - it resets state!
            # Instead, manually update verses while preserving state
            while self.content_layout.count():
                item = self.content_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            self.verses = new_verses
            self.cards = []
            self.highlighted_idx = -1

            for i, v in enumerate(new_verses):
                card = NavVerseCard(v, index=i)
                card.mouse_clicked.connect(self._on_select)
                card.btn_pushed.connect(self._on_card_pushed)
                card.queue_requested.connect(self.queue_requested.emit)
                self.cards.append(card)
                self.content_layout.addWidget(card)

            # Restore highlight - adjust if verse number doesn't exist
            hl_idx = target - 1
            if hl_idx < 0 or hl_idx >= len(new_verses):
                hl_idx = min(target - 1, len(new_verses) - 1)
                if hl_idx < 0:
                    hl_idx = 0
            self.highlighted_idx = hl_idx
            self.content_layout.addStretch()
            self._refresh_hl_style(hl_idx)

            # Restore state
            self._state = saved_state
            self._update_state_badge()
            self._update_hint()

            # Keep focus on navigator so keyboard continues to work
            QTimer.singleShot(50, lambda: self.setFocus())


class NavVerseCard(QFrame):
    """A single verse row in the navigator. Can be highlighted or normal."""
    mouse_clicked = pyqtSignal(int, object)  # index, QMouseEvent
    btn_pushed = pyqtSignal(dict)
    queue_requested = pyqtSignal(dict)  # +Q button → add to queue

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
        layout.setSpacing(8)

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

        # Push button (→ sends this specific verse)
        btn = QPushButton("→")
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(200,160,60,0.12);
                color: #c8a03c;
                border: 1px solid rgba(200,160,60,0.2);
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover { background: rgba(200,160,60,0.25); }
        """)
        btn.clicked.connect(lambda: self.btn_pushed.emit(self.verse))
        self.push_btn = btn
        layout.addWidget(btn)
        btn.setVisible(True)

        # Queue button (+Q — add this verse to the queue)
        qbtn = QPushButton("+Q")
        qbtn.setFixedSize(28, 28)
        qbtn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        qbtn.setCursor(Qt.CursorShape.PointingHandCursor)
        qbtn.setToolTip("Add to queue")
        qbtn.setStyleSheet("""
            QPushButton {
                background: rgba(76,175,125,0.12);
                color: #4caf7d;
                border: 1px solid rgba(76,175,125,0.2);
                border-radius: 6px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background: rgba(76,175,125,0.25); }
        """)
        qbtn.clicked.connect(lambda: self.queue_requested.emit(self.verse))
        self.queue_btn = qbtn
        layout.addWidget(qbtn)

        self.highlight(False)

    def highlight(self, state, preview_active=False):
        """Toggle the highlight state.
        preview_active=True  → State 2: glowing, fully active, button visible (acts as clear)
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
            self.push_btn.setText("✕")
            self.push_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(200,160,60,0.30);
                    color: #ffd966;
                    border: 2px solid #c8a03c;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: bold;
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
            self.push_btn.setText("→")
            self.push_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(200,160,60,0.15);
                    color: #c8a03c;
                    border: 1px solid rgba(200,160,60,0.3);
                    border-radius: 6px;
                    font-size: 14px;
                }
                QPushButton:hover { background: rgba(200,160,60,0.25); }
            """)
            self.push_btn.setVisible(True)  # Show button in State 1/3
        else:
            # Not highlighted - show → button for one-click send to screen
            self._hovered = False  # Clear hover state too
            self._apply_normal_style()
            # Show button for non-highlighted verses so user can click to send
            self.push_btn.setText("→")
            self.push_btn.setVisible(True)
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


# ── Keyword Results List ────────────────────────────────────────────────────

class KeywordResults(QWidget):
    verse_pushed = pyqtSignal(dict)
    queue_requested = pyqtSignal(dict)  # +Q button on keyword cards → add to queue

    def __init__(self, db=None, display=None):
        super().__init__()
        self.db = db
        self.display = display
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

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

    def set_verses(self, verses):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        # Clear any lingering display overlays from previous search
        if self.display:
            self.display.secondary_translations = []
            self.display._overlay_translations = []
        if not verses:
            empty = QLabel("No verses found.")
            empty.setFont(QFont("Segoe UI", 12))
            empty.setStyleSheet("color: rgba(200,160,60,0.25); background: transparent; padding: 30px;")
            self.content_layout.addWidget(empty)
            return
        for v in verses:
            card = KeywordVerseCard(v, self.db, self.display)
            card.pushed.connect(self.verse_pushed.emit)
            card.queue_requested.connect(self.queue_requested.emit)
            self.content_layout.addWidget(card)
        self.content_layout.addStretch()


class KeywordVerseCard(QFrame):
    pushed = pyqtSignal(dict)
    queue_requested = pyqtSignal(dict)  # +Q button → add to queue

    def __init__(self, verse, db=None, display=None, parent=None):
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

        trans_badge = QLabel(verse["translation"])
        trans_badge.setFont(QFont("Segoe UI", 8))
        trans_badge.setStyleSheet(
            "color: rgba(76,175,125,0.8); background: rgba(76,175,125,0.1); "
            "border: 1px solid rgba(76,175,125,0.2); border-radius: 6px; padding: 1px 8px;"
        )
        top_row.addWidget(trans_badge)
        top_row.addStretch()
        v_layout.addLayout(top_row)

        text = QLabel(verse["text"])
        text.setFont(QFont("Segoe UI", 11))
        text.setStyleSheet("color: #d0c8b8; background: transparent;")
        text.setWordWrap(True)
        v_layout.addWidget(text)

        v_layout.addStretch()
        layout.addLayout(v_layout, 1)

        # Right side: overlay checkbox + queue button + push button
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

        # Queue button (+Q)
        qbtn = QPushButton("+Q")
        qbtn.setFixedSize(24, 24)
        qbtn.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        qbtn.setToolTip("Add to queue")
        qbtn.setCursor(Qt.CursorShape.PointingHandCursor)
        qbtn.setStyleSheet("""
            QPushButton {
                background: rgba(76,175,125,0.12);
                color: #4caf7d;
                border: 1px solid rgba(76,175,125,0.2);
                border-radius: 5px;
            }
            QPushButton:hover { background: rgba(76,175,125,0.25); }
        """)
        qbtn.clicked.connect(lambda: self.queue_requested.emit(self.verse))
        self.queue_btn = qbtn
        right_col.addWidget(qbtn, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Push/Clear toggle button
        btn = QPushButton("→")
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
            self._push_btn.setText("→")
            self._push_btn.setToolTip("Push to display")
            self._style_push_btn(self._push_btn)
        else:
            # Push to display
            self.pushed.emit(self.verse)
            self._on_display = True
            self._push_btn.setText("✕")
            self._push_btn.setToolTip("Clear from display")
            self._style_clear_btn(self._push_btn)

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


# ── Cross-Reference Panel (Phase 1) ─────────────────────────────────────────

class CrossRefPanel(QFrame):
    """Shows cross-references for the current verse. Clickable to navigate."""
    ref_clicked = pyqtSignal(str)

    def __init__(self, xref_mgr, db, parent=None):
        super().__init__(parent)
        self.xref_mgr = xref_mgr
        self.db = db
        self.setProperty("crossref", True)
        self.setFixedHeight(180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        header = QLabel("CROSS-REFERENCES")
        header.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        header.setStyleSheet("color: rgba(200,160,60,0.4); background: transparent; letter-spacing: 2px;")
        layout.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(4)

        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)

        self._empty = QLabel("Select a verse to see cross-references.")
        self._empty.setFont(QFont("Segoe UI", 10))
        self._empty.setStyleSheet("color: rgba(200,160,60,0.2); background: transparent; padding: 20px;")
        self.content_layout.addWidget(self._empty)

    def load_for_verse(self, reference):
        """Load cross-references for the given verse reference."""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        refs = self.xref_mgr.get_cross_refs(reference)
        if not refs:
            self._empty = QLabel("No cross-references found.")
            self._empty.setFont(QFont("Segoe UI", 10))
            self._empty.setStyleSheet("color: rgba(200,160,60,0.2); background: transparent; padding: 20px;")
            self.content_layout.addWidget(self._empty)
            return
        for ref in refs:
            card = CrossRefCard(ref)
            card.clicked.connect(self.ref_clicked.emit)
            self.content_layout.addWidget(card)
        self.content_layout.addStretch()


class CrossRefCard(QFrame):
    """A single cross-reference entry. Clickable."""
    clicked = pyqtSignal(str)

    def __init__(self, reference, parent=None):
        super().__init__(parent)
        self.reference = reference
        self.setFixedHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        ref_label = QLabel(reference)
        ref_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        ref_label.setStyleSheet("color: rgba(200,160,60,0.6); background: transparent;")
        layout.addWidget(ref_label)
        layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.reference)
        super().mousePressEvent(event)


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
        self.menu_btn = QPushButton("TRANSLATIONS ▼")
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
            import time
            self._last_hide_time = time.time()
            self.popup.hide()
            self.menu_btn.setText("TRANSLATIONS ▼")
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
            label = QLabel(trans)
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
        import time
        # Prevent bounce: if it auto-hid within the last 150ms from focus loss, don't reopen
        if time.time() - getattr(self, '_last_hide_time', 0) < 0.15:
            return

        if self.popup.isVisible():
            self.popup.hide()
            self.menu_btn.setText("TRANSLATIONS ▼")
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
        self.popup.activateWindow()
        self.menu_btn.setText("TRANSLATIONS ▲")
    
    def _set_default_translation(self, translation):
        """Set the default (primary) checked translation."""
        self.current_primary = translation
        # Check the box for this translation
        for trans, cb, label in self.translation_items:
            if trans == translation:
                cb.setChecked(True)
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
        self.menu_btn.setText("TRANSLATIONS ▼")

        # If this is already the default, do nothing
        if translation == self.current_primary:
            return

        # Uncheck the old default
        old_primary = self.current_primary
        for trans, cb, label in self.translation_items:
            if trans == old_primary:
                cb.setChecked(False)
                if old_primary in self.checked_translations:
                    self.checked_translations.remove(old_primary)
                break

        # Set new default
        self.current_primary = translation
        for trans, cb, label in self.translation_items:
            if trans == translation:
                cb.setChecked(True)
                if translation not in self.checked_translations:
                    self.checked_translations.append(translation)
                break

        # Emit override signal
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


# ── Home Panel (search + preview + Phase 1 components) ───────────────────────

class HomePanel(QWidget):
    """Main operator panel with left sidebar and right content area.
    
    Layout:
    ┌──────────────┬─────────────────────────────┐
    │              │   Display Preview           │
    │  Left Panel  ├─────────────────────────────┤
    │              │                             │
    │  - Search    │   Verse Navigator           │
    │  - Settings  │   (main content area)       │
    │  - Controls  │                             │
    │              ├─────────────────────────────┤
    │              │   Cross-References          │
    └──────────────┴─────────────────────────────┘
    """
    def __init__(self, db, display, xref_mgr=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.display = display
        self.xref_mgr = xref_mgr or CrossRefManager()

        # ── Category 1: Document Manager (single source of truth) ─────────────
        self.doc_manager = DocumentManager(self)
        self.doc_manager.dirty_changed.connect(self._on_dirty_changed)
        self.doc_manager.document_changed.connect(self._on_document_changed)

        # Main horizontal layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ═══════════════════════════════════════════════════════════
        # LEFT SIDEBAR (280px fixed width)
        # ═══════════════════════════════════════════════════════════
        left_sidebar = QFrame()
        left_sidebar.setProperty("sidebar", True)
        left_sidebar.setFixedWidth(280)
        left_layout = QVBoxLayout(left_sidebar)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(12)
        
        # Header with tabs at top
        header_row = QHBoxLayout()
        header_row.setSpacing(0)
        
        # Home tab button
        self.tab_home = QPushButton("Home")
        self.tab_home.setFixedHeight(32)
        self.tab_home.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.tab_home.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_home.setStyleSheet("""
            QPushButton {
                background: rgba(200,160,60,0.15);
                color: #c8a03c;
                border: 1px solid rgba(200,160,60,0.3);
                border-radius: 4px 0 0 4px;
                padding: 0 16px;
            }
        """)
        self.tab_home.clicked.connect(lambda: self.stack_nav(0))
        header_row.addWidget(self.tab_home)
        
        # Settings tab button
        self.tab_settings = QPushButton("Settings")
        self.tab_settings.setFixedHeight(32)
        self.tab_settings.setFont(QFont("Segoe UI", 10))
        self.tab_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_settings.setStyleSheet("""
            QPushButton {
                background: rgba(20,20,36,0.5);
                color: rgba(200,160,60,0.4);
                border: 1px solid rgba(255,255,255,0.08);
                border-left: none;
                border-radius: 0 4px 4px 0;
                padding: 0 12px;
            }
        """)
        self.tab_settings.clicked.connect(lambda: self.stack_nav(1))
        header_row.addWidget(self.tab_settings)
        
        left_layout.addLayout(header_row)
        
        # Version badge
        version = QLabel("v0.7.0 · Stage 3")
        version.setFont(QFont("Segoe UI", 8))
        version.setStyleSheet("color: rgba(200,160,60,0.4); background: transparent;")
        left_layout.addWidget(version)
        
        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("background: rgba(200,160,60,0.15);")
        sep1.setFixedHeight(1)
        left_layout.addWidget(sep1)
        
        # Draft editor (moved to left sidebar to occupy empty space)
        draft_header = QLabel("DRAFT EDITOR")
        draft_header.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        draft_header.setStyleSheet("color: rgba(76,175,125,0.5); background: transparent; letter-spacing: 2px;")
        left_layout.addWidget(draft_header)
        
        self.draft_editor = DraftEditor()
        self.draft_editor.draft_changed.connect(display.set_draft)
        self.draft_editor.publish_requested.connect(display.publish_draft)
        left_layout.addWidget(self.draft_editor)
        
        left_layout.addStretch()
        
        main_layout.addWidget(left_sidebar)
        
        # ═══════════════════════════════════════════════════════════
        # CENTER SPACE (320px fixed width)
        # ═══════════════════════════════════════════════════════════
        center_space = QFrame()
        center_space.setProperty("panel", True)
        center_space.setFixedWidth(320)
        center_layout = QVBoxLayout(center_space)
        center_layout.setContentsMargins(12, 12, 12, 12)
        center_layout.setSpacing(12)
        
        # Search section
        search_header = QLabel("SEARCH")
        search_header.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        search_header.setStyleSheet("color: rgba(200,160,60,0.5); background: transparent; letter-spacing: 2px;")
        center_layout.addWidget(search_header)
        
        # Translation menu (dropdown with checkboxes)
        self.trans_menu = TranslationMenu(db, parent=self)
        self.trans_menu.translation_changed.connect(self._on_translation_changed)
        center_layout.addWidget(self.trans_menu)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('e.g. "John 3:16"…')
        self.search_input.setFont(QFont("Segoe UI", 13))
        self.search_input.setMinimumHeight(40)
        self.search_input.returnPressed.connect(self._do_search)
        self.search_input.installEventFilter(self)
        center_layout.addWidget(self.search_input)
        
        # Mode toggle (compact)
        self.mode_toggle = ModeToggle()
        self.mode_toggle.mode_changed.connect(self._on_mode_changed)
        center_layout.addWidget(self.mode_toggle)
        
        # Separator
        sep_center1 = QFrame()
        sep_center1.setFrameShape(QFrame.Shape.HLine)
        sep_center1.setStyleSheet("background: rgba(200,160,60,0.15);")
        sep_center1.setFixedHeight(1)
        center_layout.addWidget(sep_center1)
        
        # Cross-References (moved here from right)
        xref_header = QLabel("CROSS-REFERENCES")
        xref_header.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        xref_header.setStyleSheet("color: rgba(200,160,60,0.5); background: transparent; letter-spacing: 2px;")
        center_layout.addWidget(xref_header)

        self.xref_panel = CrossRefPanel(self.xref_mgr, db)
        self.xref_panel.setFixedHeight(120)
        self.xref_panel.ref_clicked.connect(self._on_xref_clicked)
        center_layout.addWidget(self.xref_panel)

        # Verse Navigation Buttons (Up/Down)
        nav_buttons_header = QLabel("VERSE NAVIGATION")
        nav_buttons_header.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        nav_buttons_header.setStyleSheet("color: rgba(200,160,60,0.5); background: transparent; letter-spacing: 2px;")
        center_layout.addWidget(nav_buttons_header)

        nav_buttons_widget = QWidget()
        nav_buttons_layout = QHBoxLayout(nav_buttons_widget)
        nav_buttons_layout.setContentsMargins(0, 0, 0, 0)
        nav_buttons_layout.setSpacing(8)

        # Up button
        self.nav_up_btn = QPushButton("▲ Up")
        self.nav_up_btn.setFixedHeight(36)
        self.nav_up_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.nav_up_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.nav_up_btn.setStyleSheet("""
            QPushButton {
                background: rgba(200,160,60,0.12);
                color: #c8a03c;
                border: 1px solid rgba(200,160,60,0.25);
                border-radius: 6px;
            }
            QPushButton:hover {
                background: rgba(200,160,60,0.2);
            }
            QPushButton:pressed {
                background: rgba(200,160,60,0.3);
            }
        """)
        self.nav_up_btn.clicked.connect(self._navigate_verse_up)
        nav_buttons_layout.addWidget(self.nav_up_btn)

        # Down button
        self.nav_down_btn = QPushButton("▼ Down")
        self.nav_down_btn.setFixedHeight(36)
        self.nav_down_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.nav_down_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.nav_down_btn.setStyleSheet("""
            QPushButton {
                background: rgba(200,160,60,0.12);
                color: #c8a03c;
                border: 1px solid rgba(200,160,60,0.25);
                border-radius: 6px;
            }
            QPushButton:hover {
                background: rgba(200,160,60,0.2);
            }
            QPushButton:pressed {
                background: rgba(200,160,60,0.3);
            }
        """)
        self.nav_down_btn.clicked.connect(self._navigate_verse_down)
        nav_buttons_layout.addWidget(self.nav_down_btn)

        center_layout.addWidget(nav_buttons_widget)

        # Separator
        sep_center2 = QFrame()
        sep_center2.setFrameShape(QFrame.Shape.HLine)
        sep_center2.setStyleSheet("background: rgba(200,160,60,0.15);")
        sep_center2.setFixedHeight(1)
        center_layout.addWidget(sep_center2)

        # Display Controls: Show / Hide buttons
        display_ctrl_header = QLabel("DISPLAY CONTROLS")
        display_ctrl_header.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        display_ctrl_header.setStyleSheet("color: rgba(200,160,60,0.5); background: transparent; letter-spacing: 2px;")
        center_layout.addWidget(display_ctrl_header)

        display_controls = QHBoxLayout()
        display_controls.setSpacing(8)

        self.btn_show = QPushButton("▶ Show")
        self.btn_show.setFixedHeight(40)
        self.btn_show.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.btn_show.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_show.setStyleSheet("""
            QPushButton {
                background: rgba(76,175,125,0.20);
                color: #4caf7d;
                border: 1px solid rgba(76,175,125,0.35);
                border-radius: 6px;
            }
            QPushButton:hover { background: rgba(76,175,125,0.30); }
            QPushButton:pressed { background: rgba(76,175,125,0.40); }
        """)
        self.btn_show.clicked.connect(self._on_show)
        display_controls.addWidget(self.btn_show)

        self.btn_hide = QPushButton("■ Hide")
        self.btn_hide.setFixedHeight(40)
        self.btn_hide.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.btn_hide.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hide.setStyleSheet("""
            QPushButton {
                background: rgba(224,92,75,0.15);
                color: #e05c4b;
                border: 1px solid rgba(224,92,75,0.30);
                border-radius: 6px;
            }
            QPushButton:hover { background: rgba(224,92,75,0.25); }
            QPushButton:pressed { background: rgba(224,92,75,0.35); }
        """)
        self.btn_hide.clicked.connect(self._on_hide)
        display_controls.addWidget(self.btn_hide)

        center_layout.addLayout(display_controls)

        # Playlist Panel (NEW space for Playlists)
        self.playlist_panel = PlaylistPanel()
        center_layout.addWidget(self.playlist_panel, 1)

        main_layout.addWidget(center_space)
        
        # ═══════════════════════════════════════════════════════════
        # RIGHT CONTENT AREA (expanding, main workspace)
        # ═══════════════════════════════════════════════════════════
        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(12)
        
        # TOP: Display Preview (300px - taller to fit multiple translations)
        preview_box = QFrame()
        preview_box.setProperty("panel", True)
        preview_box.setFixedHeight(300)
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.setContentsMargins(12, 10, 12, 10)
        preview_layout.setSpacing(6)
        
        preview_header = QHBoxLayout()
        dot1 = QFrame()
        dot1.setFixedSize(6, 6)
        dot1.setStyleSheet("QFrame { background: #4caf7d; border-radius: 3px; }")
        preview_header.addWidget(dot1)
        preview_header.addSpacing(8)
        prev_title = QLabel("DISPLAY PREVIEW")
        prev_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        prev_title.setStyleSheet("color: rgba(76,175,125,0.6); background: transparent; letter-spacing: 2px;")
        preview_header.addWidget(prev_title)
        preview_header.addStretch()
        preview_layout.addLayout(preview_header)
        
        self.preview = DisplayPreview(self.display)
        preview_layout.addWidget(self.preview)
        
        right_layout.addWidget(preview_box)

        # BOTTOM: Stacked panel for navigator / keyword results
        self.result_stack = QStackedWidget()
        right_layout.addWidget(self.result_stack, 2)  # Proportionally takes 2/3 of space

        # Panel 0: Verse Navigator
        navigator_box = QFrame()
        navigator_box.setProperty("panel", True)
        navigator_layout = QVBoxLayout(navigator_box)
        navigator_layout.setContentsMargins(12, 10, 12, 10)
        navigator_layout.setSpacing(6)

        nav_header = QHBoxLayout()
        dot2 = QFrame()
        dot2.setFixedSize(6, 6)
        dot2.setStyleSheet("QFrame { background: #c8a03c; border-radius: 3px; }")
        nav_header.addWidget(dot2)
        nav_header.addSpacing(8)
        nav_title = QLabel("VERSE NAVIGATOR")
        nav_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        nav_title.setStyleSheet("color: rgba(200,160,60,0.6); background: transparent; letter-spacing: 2px;")
        nav_header.addWidget(nav_title)
        nav_header.addStretch()
        navigator_layout.addLayout(nav_header)

        self.navigator = VerseNavigator(db, display)
        self.navigator.verse_pushed.connect(self._push_verse)
        self.navigator.state_changed.connect(self._on_navigator_state_changed)
        # Removed signal connection from here due to initialization order
        navigator_layout.addWidget(self.navigator)

        self.result_stack.addWidget(navigator_box)  # index 0

        # Panel 1: Keyword Results
        keyword_box = QFrame()
        keyword_box.setProperty("panel", True)
        keyword_layout = QVBoxLayout(keyword_box)
        keyword_layout.setContentsMargins(12, 10, 12, 10)
        keyword_layout.setSpacing(6)

        kw_header = QHBoxLayout()
        dot3 = QFrame()
        dot3.setFixedSize(6, 6)
        dot3.setStyleSheet("QFrame { background: #4caf7d; border-radius: 3px; }")
        kw_header.addWidget(dot3)
        kw_header.addSpacing(8)
        kw_title = QLabel("KEYWORD RESULTS")
        kw_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        kw_title.setStyleSheet("color: rgba(76,175,125,0.6); background: transparent; letter-spacing: 2px;")
        kw_header.addWidget(kw_title)
        kw_header.addStretch()
        keyword_layout.addLayout(kw_header)

        self.keyword_results = KeywordResults(db, display)
        self.keyword_results.verse_pushed.connect(self._push_verse)
        keyword_layout.addWidget(self.keyword_results)

        self.result_stack.addWidget(keyword_box)  # index 1

        # BOTTOM: Queue & History Sub Panels (NEW location)
        bottom_sub_panels = QHBoxLayout()
        bottom_sub_panels.setSpacing(12)
        bottom_sub_panels.setContentsMargins(0, 0, 0, 0)

        # 1) Queue Panel (real implementation from queue_panel.py)
        self.queue_panel = QueuePanel(self.doc_manager, display, self.preview)
        bottom_sub_panels.addWidget(self.queue_panel, 1)

        # Wire queue_requested signals from navigator and keyword results
        self.navigator.queue_requested.connect(self.queue_panel.add_verse)
        self.keyword_results.queue_requested.connect(self.queue_panel.add_verse)

        # Sync queue live state when display verse changes
        display.verse_changed.connect(self.queue_panel.sync_live_state)

        # 2) Verse Live History Panel
        hist_container = QFrame()
        hist_container.setProperty("panel", True)
        hist_layout = QVBoxLayout(hist_container)
        hist_layout.setContentsMargins(6, 4, 6, 4)
        hist_layout.setSpacing(2)

        hist_mini_header = QHBoxLayout()
        hist_mini_header.setSpacing(4)
        dot_hist = QFrame()
        dot_hist.setFixedSize(5, 5)
        dot_hist.setStyleSheet("QFrame { background: #c8a03c; border-radius: 3px; }")
        hist_mini_header.addWidget(dot_hist)
        hist_mini_label = QLabel("LIVE HISTORY")
        hist_mini_label.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        hist_mini_label.setStyleSheet("color: rgba(200,160,60,0.5); background: transparent; letter-spacing: 1.5px;")
        hist_mini_header.addWidget(hist_mini_label)
        hist_mini_header.addStretch()

        self.btn_clear_history = QPushButton("Clear")
        self.btn_clear_history.setFixedSize(40, 16)
        self.btn_clear_history.setFont(QFont("Segoe UI", 7))
        self.btn_clear_history.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_history.setStyleSheet("""
            QPushButton {
                background: rgba(224,92,75,0.12);
                color: #e05c4b;
                border: 1px solid rgba(224,92,75,0.20);
                border-radius: 3px;
            }
            QPushButton:hover { background: rgba(224,92,75,0.18); }
        """)
        self.btn_clear_history.clicked.connect(self._clear_history)
        hist_mini_header.addWidget(self.btn_clear_history)

        hist_layout.addLayout(hist_mini_header)

        self.verse_live_history = VerseLiveHistoryPanel(self.display)
        hist_layout.addWidget(self.verse_live_history)
        
        # Connect strictly to State 1 -> 2 transitions for history logging to prevent clutter
        self.navigator.verse_went_live.connect(self.verse_live_history.add_verse)
        
        bottom_sub_panels.addWidget(hist_container, 1)

        bottom_container = QWidget()
        bottom_container.setLayout(bottom_sub_panels)
        
        # Flexibly ratio the space: Navigator gets 2/3 stretch, Bottom gets 1/3 stretch
        right_layout.addWidget(bottom_container, 1)

        main_layout.addWidget(right_content, 1)

        # Populate translations
        self._populate_translations("English KJV")

        # Current translation tracker
        self.current_translation = "English KJV"

        # Debounced search-as-you-type timer for keyword search mode
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(250)  # ms delay after typing stops
        self.search_timer.timeout.connect(self._do_search)

        # Connect text changes to timer
        self.search_input.textChanged.connect(self._on_search_text_changed)

        # Install global event filter for keyboard focus on navigator
        # This ensures arrow keys and Enter always work on navigator when active (state > 0)
        QApplication.instance().installEventFilter(self)

        # ── Undo / Redo keyboard shortcuts (Ctrl+Z, Ctrl+Shift+Z) ─────────────
        undo_sc = QShortcut(QKeySequence.StandardKey.Undo, self)
        undo_sc.activated.connect(self.doc_manager.undo)
        redo_sc = QShortcut(QKeySequence.StandardKey.Redo, self)
        redo_sc.activated.connect(self.doc_manager.redo)
    
    def stack_nav(self, index):
        """Navigate to stack page and update tab styles."""
        # Get parent MainWindow
        parent = self.parent()
        while parent and not hasattr(parent, 'stack'):
            parent = parent.parent()
        if parent and hasattr(parent, 'stack'):
            parent.stack.setCurrentIndex(index)
            # Update tab styles
            if index == 0:
                self.tab_home.setStyleSheet("""
                    QPushButton {
                        background: rgba(200,160,60,0.15);
                        color: #c8a03c;
                        border: 1px solid rgba(200,160,60,0.3);
                        border-radius: 4px 0 0 4px;
                        padding: 0 16px;
                        font-weight: bold;
                    }
                """)
                self.tab_settings.setStyleSheet("""
                    QPushButton {
                        background: rgba(20,20,36,0.5);
                        color: rgba(200,160,60,0.4);
                        border: 1px solid rgba(255,255,255,0.08);
                        border-left: none;
                        border-radius: 0 4px 4px 0;
                        padding: 0 12px;
                    }
                """)
            else:
                self.tab_home.setStyleSheet("""
                    QPushButton {
                        background: rgba(20,20,36,0.5);
                        color: rgba(200,160,60,0.4);
                        border: 1px solid rgba(255,255,255,0.08);
                        border-radius: 4px 0 0 4px;
                        padding: 0 16px;
                    }
                """)
                self.tab_settings.setStyleSheet("""
                    QPushButton {
                        background: rgba(200,160,60,0.15);
                        color: #c8a03c;
                        border: 1px solid rgba(200,160,60,0.3);
                        border-left: none;
                        border-radius: 0 4px 4px 0;
                        padding: 0 12px;
                        font-weight: bold;
                    }
                """)
    
    def _populate_translations(self, default_trans=""):
        """Populate translation selector."""
        # This is now handled by TranslationSelector
        pass

    def _navigate_verse_up(self):
        """Navigate to previous verse and update screen if in State 2 (displaying)."""
        if not self.navigator.verses or self.navigator.highlighted_idx <= 0:
            return
        
        # Move highlight up
        new_idx = self.navigator.highlighted_idx - 1
        self.navigator._move_highlight(new_idx)
        
        # If in State 2 (displaying), update screen
        if self.navigator._state == 2:
            verse = self.navigator.verses[new_idx]
            self.display.push_verse(verse)

    def _navigate_verse_down(self):
        """Navigate to next verse and update screen if in State 2 (displaying)."""
        if not self.navigator.verses or self.navigator.highlighted_idx >= len(self.navigator.verses) - 1:
            return
        
        # Move highlight down
        new_idx = self.navigator.highlighted_idx + 1
        self.navigator._move_highlight(new_idx)
        
        # If in State 2 (displaying), update screen
        if self.navigator._state == 2:
            verse = self.navigator.verses[new_idx]
            self.display.push_verse(verse)
    
    def _on_translation_changed(self, action):
        """Handle translation change.

        Action formats:
        - "default:KJV" → Set KJV as default checked translation
        - "override:KJV" → Replace everything with KJV (text click)
        - "overlay:NIV" → Add NIV as overlay (checkbox checked)
        - "remove:NIV" → Remove NIV overlay (checkbox unchecked)
        """
        if not action:
            return

        parts = action.split(":", 1)
        if len(parts) != 2:
            return

        action_type, translation = parts

        if action_type == "default":
            # Set new default — reload navigator with this translation
            self.current_translation = translation
            if self.navigator.verses:
                self.navigator.reload_translation(translation)
            # Update display
            if self.display.current:
                self.display.push_verse(self.display.current)

        elif action_type == "override":
            # Override mode: replace everything
            self.current_translation = translation
            self.trans_menu.current_primary = translation

            # Get current displayed verse reference
            current_ref = self.display.current.get("reference", "") if self.display.current else ""

            # Reload navigator with new translation (preserves state/highlight)
            if self.navigator.verses:
                self.navigator.reload_translation(translation)

            # Update the actual verse on screen to new translation
            if current_ref:
                # Parse reference to get book/chapter/verse
                ref_match = re.match(r'(.+?)\s+(\d+):(\d+)', current_ref)
                if ref_match:
                    book_name = ref_match.group(1).strip()
                    chapter = int(ref_match.group(2))
                    verse_num = int(ref_match.group(3))

                    # Resolve book name
                    book = _resolve_book(book_name)
                    if book:
                        verse_data = self.db.get_verse(f"{book} {chapter}:{verse_num}", translation)
                        if verse_data:
                            # Push new verse - this updates display.current AND emits signal
                            self.display.push_verse(verse_data)
                            # Clear overlays since we're overriding
                            self.display.clear_translations()

        elif action_type == "overlay":
            # Overlay mode: add translation above current
            # Build ALL overlays from scratch based on checked_translations order
            self._rebuild_display_overlays()

        elif action_type == "remove":
            # Remove overlay: rebuild remaining overlays
            self._rebuild_display_overlays()

    def _rebuild_display_overlays(self):
        """Rebuild all display overlays based on checked_translations order.

        checked_translations = [AMP, ESV, MSG] (in order of checking)
        current_primary = MSG (last checked = n)
        Display order (top to bottom): MSG, ESV, AMP
        """
        if not self.navigator.verses or self.navigator.highlighted_idx < 0:
            return

        checked = self.trans_menu.checked_translations[:]
        current_primary = self.trans_menu.current_primary

        # Step 0: Reload navigator with current primary
        self.navigator.reload_translation(current_primary)

        # Step 1: Look up verse in current primary
        verse = self.navigator.verses[self.navigator.highlighted_idx]
        if not verse:
            return

        primary_verse = self.db.get_verse(
            f"{verse['book']} {verse['chapter']}:{verse['verse']}", current_primary
        )
        if not primary_verse:
            return

        # Step 2: Build overlays directly (no signals)
        # Order: n-1, n-2, ..., n0 (reverse of checked, excluding primary)
        self.display.secondary_translations = []
        self.display._overlay_translations = []

        others = [t for t in checked if t != current_primary]
        others.reverse()  # n-1 first, n0 last

        for trans_name in others:
            overlay_verse = self.db.get_verse(
                f"{verse['book']} {verse['chapter']}:{verse['verse']}", trans_name
            )
            if overlay_verse:
                self.display.secondary_translations.append(overlay_verse)
                if trans_name not in self.display._overlay_translations:
                    self.display._overlay_translations.append(trans_name)

        # Step 3: Now push primary — overlays are already set
        self.display.push_verse(primary_verse)
    
    def _on_search_text_changed(self, text):
        """Restart the debounce timer on every keystroke in keyword search mode only.
        In verse lookup mode, we wait for Enter press to avoid false matches on partial input."""
        if self.mode_toggle.current_mode == "Keyword Search":
            self.search_timer.start()
        # In Verse Lookup mode, do NOT auto-search — wait for Enter

    def _on_mode_changed(self, mode):
        """Handle mode change (Verse Lookup | Keyword Search)."""
        if mode == "Verse Lookup":
            self.search_input.setPlaceholderText('e.g. "John 3:16"…')
            self.result_stack.setCurrentIndex(0)  # Show navigator
            # Don't auto-search in verse lookup — wait for Enter
        else:
            self.search_input.setPlaceholderText('e.g. "faith", "love", "light of the world"…')
            self.result_stack.setCurrentIndex(1)  # Show keyword results
            # Auto-search in keyword mode if there's text
            text = self.search_input.text().strip()
            if text:
                self._do_search()

    # ── Category 1: Document state handlers ───────────────────────────────────────

    def _on_dirty_changed(self, dirty: bool):
        """Update window title to reflect unsaved changes."""
        parent = self.parent()
        while parent and not hasattr(parent, 'setWindowTitle'):
            parent = parent.parent()
        if parent:
            name = self.doc_manager.display_name()
            dot = " ●" if dirty else ""
            parent.setWindowTitle(f"VerseFlow — {name}{dot}")

    def _on_document_changed(self):
        """Placeholder for future reactions to document-level changes."""
        pass

    def _on_navigator_state_changed(self, state):
        """Handle navigator state changes.
        Defer setEnabled calls to avoid Qt focus re-dispatch bug during
        synchronous state changes (e.g., load_chapter → state_changed.emit)."""
        if state == 0:
            QTimer.singleShot(0, lambda: (self.search_input.setEnabled(True), self.search_input.setFocus()))
        else:
            QTimer.singleShot(0, lambda: self.search_input.setEnabled(False))

    def _on_show(self):
        """Send the currently highlighted verse to external screen (same as Enter)."""
        nav = getattr(self, 'navigator', None)
        if nav and nav.highlighted_idx >= 0 and nav.highlighted_idx < len(nav.verses):
            verse = nav.verses[nav.highlighted_idx]
            if nav._state == 1:
                nav._on_card_pushed(verse)
            elif nav._state == 2:
                # Already on screen — re-push to refresh
                self.display.push_verse(verse)
        else:
            print("[SHOW] No highlighted verse to display", flush=True)

    def _on_hide(self):
        """Clear external screen, return navigator to state 1."""
        nav = getattr(self, 'navigator', None)
        if nav and nav.highlighted_idx >= 0 and nav.highlighted_idx < len(nav.verses):
            if nav._state == 2:
                verse = nav.verses[nav.highlighted_idx]
                nav._on_card_pushed(verse)

    def _clear_history(self):
        """Clear verse live history panel."""
        if self.verse_live_history:
            self.verse_live_history.clear()

    def _restore_from_history(self, verse):
        """Restore a verse from history to the display."""
        if not verse or "reference" not in verse:
            return
            
        ref = verse["reference"]
        trans = verse.get("translation", self.trans_menu.current_primary)
        
        # Note: we temporarily detach the history logic to prevent duplicate logging
        # when we push this to screen 
        
        # 1. Update translation if different
        if self.current_translation != trans:
            self._on_translation_changed(f"override:{trans}")
            
        # 2. Parse reference to retrieve exact book/chapter
        ref_match = re.match(r'(.+?)\s+(\d+):(\d+)', ref)
        if ref_match:
            book_name = ref_match.group(1).strip()
            chapter = int(ref_match.group(2))
            verse_num = int(ref_match.group(3))
            
            book = _resolve_book(book_name)
            if book:
                # 3. Disconnect briefly to avoid logging the history payload back onto itself
                self.navigator.verse_went_live.disconnect(self.verse_live_history.add_verse)
                
                # 4. Load chapter and push exact verse
                result = self.db.lookup_verse(f"{book} {chapter}:1", trans)
                if result and result.get("verses"):
                    self.navigator.load_chapter(book, chapter, result["verses"], target_verse=verse_num)
                    for i, v in enumerate(self.navigator.verses):
                        if v.get("verse") == verse_num or str(v.get("verse")) == str(verse_num):
                            self.navigator._move_highlight(i)
                            self.navigator._on_card_pushed(v)
                            break
                        
                # 5. Reconnect history logger
                self.navigator.verse_went_live.connect(self.verse_live_history.add_verse)

    def _do_search(self):
        """Execute search based on current mode."""
        import time
        try:
            q = self.search_input.text().strip()
            if not q:
                self.navigator.clear()
                self.keyword_results.set_verses([])
                return

            t0 = time.perf_counter()
            if self.mode_toggle.current_mode == "Verse Lookup":
                # Verse lookup → load chapter
                result = self.db.lookup_verse(q, self.current_translation)
                if result and result.get("verses"):
                    self.navigator.load_chapter(
                        result["book"], result["chapter"], result["verses"],
                        target_verse=result.get("target_verse", 0)
                    )
                    self.result_stack.setCurrentIndex(0)
                    elapsed = (time.perf_counter() - t0) * 1000
                    print(f"Loaded {result['book']} {result['chapter']} — {len(result['verses'])} verses in {elapsed:.1f}ms")
                    self.search_input.setEnabled(False)
                    QTimer.singleShot(200, lambda: self.navigator.setFocus())
                else:
                    # Fall back to keyword
                    results = self.db.search(q, self.current_translation)
                    self.keyword_results.set_verses(results)
                    self.result_stack.setCurrentIndex(1)
                    elapsed = (time.perf_counter() - t0) * 1000
                    print(f"{len(results)} keyword results in {elapsed:.1f}ms")
                    self.search_input.setEnabled(True)
            else:
                # Keyword search mode
                results = self.db.search(q, self.current_translation)
                self.keyword_results.set_verses(results)
                self.result_stack.setCurrentIndex(1)
                elapsed = (time.perf_counter() - t0) * 1000
                print(f"{len(results)} keyword results in {elapsed:.1f}ms")
                self.search_input.setEnabled(True)
        except Exception as e:
            print(f"CRASH in _do_search: {e}")
            import traceback
            traceback.print_exc()

    def _on_xref_clicked(self, reference):
        """Handle cross-reference click — look up and load the referenced verse in navigator."""
        verse = self.db.get_verse(reference, self.current_translation)
        if verse:
            # Load the chapter for this verse
            book = verse.get("book", "")
            chapter = verse.get("chapter", 0)
            target_verse = verse.get("verse", 0)
            result = self.db.lookup_verse(f"{book} {chapter}:1", self.current_translation)
            if result and result.get("verses"):
                self.navigator.load_chapter(
                    book, chapter, result["verses"],
                    target_verse=target_verse
                )
                self.result_stack.setCurrentIndex(0)
                self.search_input.setEnabled(False)

    def _push_verse(self, verse):
        """Push verse from keyword results — load chapter in navigator for verification first."""
        if not verse:
            return
        # Load the full chapter in the navigator
        book = verse.get("book", "")
        chapter = verse.get("chapter", 0)
        target_verse = verse.get("verse", 0)
        translation = verse.get("translation", "")

        # Look up all verses in this chapter
        verses = self.db.lookup_verse(f"{book} {chapter}:1", translation)
        if verses and verses.get("verses"):
            self.navigator.load_chapter(
                book, chapter, verses["verses"],
                target_verse=target_verse
            )
            self.result_stack.setCurrentIndex(0)  # Switch to navigator view
            self.search_input.setEnabled(False)
            
            # Find and push the exact target verse to trigger State 2
            for v in self.navigator.verses:
                if v.get("verse") == target_verse or str(v.get("verse")) == str(target_verse):
                    self.navigator._on_card_pushed(v)
                    break
    
    def eventFilter(self, obj, event):
        """Global event filter: keeps keyboard focus on navigator when active.
        Also handles Escape and mouse clicks on search input.
        """
        # Safely check for navigator attribute
        navigator = getattr(self, 'navigator', None)
        if navigator is None:
            return super().eventFilter(obj, event)
            
        et = event.type()

        # When navigator is active (state > 0), intercept arrow keys and Enter globally
        # This ensures they always work on navigator regardless of where focus is
        if navigator._state > 0:
            if et == QEvent.Type.KeyPress:
                key = event.key()
                if key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    # Forward key event directly to navigator
                    navigator.keyPressEvent(event)
                    return True  # Event handled

        # Search input specific handling
        if obj == self.search_input:
            if et == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Escape:
                    if navigator._state > 0:
                        navigator.clear()
                    self.search_input.clear()
                    self.search_input.setEnabled(True)
                    self.search_input.setFocus()
                    return True
            elif et == QEvent.Type.MouseButtonPress:
                if not self.search_input.isEnabled():
                    navigator.clear()
                    self.search_input.setEnabled(True)
                    self.search_input.setFocus()
                    return True
        return super().eventFilter(obj, event)


class DisplayPreview(QFrame):
    """Shows what's currently on the congregation display.
    Compact design optimized for 250px height.
    Supports multi-translation overlay preview.
    """
    def __init__(self, display, parent=None):
        super().__init__(parent)
        self.display = display
        self.setProperty("preview", True)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Reference label (will include translation badge inline)
        self.ref_label = QLabel("Ready")
        self.ref_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.ref_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ref_label.setStyleSheet("color: rgba(200,160,60,0.5); background: transparent; letter-spacing: 2px;")
        layout.addWidget(self.ref_label)

        # Main verse text area (scrollable for multi-translation)
        self.verse_scroll = QScrollArea()
        self.verse_scroll.setWidgetResizable(True)
        self.verse_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.verse_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.verse_content = QWidget()
        self.verse_layout = QVBoxLayout(self.verse_content)
        self.verse_layout.setContentsMargins(0, 0, 0, 0)
        self.verse_layout.setSpacing(8)

        self.verse_scroll.setWidget(self.verse_content)
        layout.addWidget(self.verse_scroll, 1)  # Expanding

        # Font fitting attributes (auto-shrink to fit viewport)
        self._fitting = False
        self._current_base_font = 16
        self._min_font = 8
        self._max_font = 24
        self._last_content_hash = None

        # Connect to display controller
        display.verse_changed.connect(self._on_verse_changed)
        display.translations_changed.connect(self._on_translations_changed)

    def _on_translations_changed(self, translations):
        """Update display when secondary translations change."""
        if self.display.current:
            self._update_verse_display()

    def _on_verse_changed(self, verse):
        if not verse:
            self.ref_label.setText("Ready")
            self.ref_label.setStyleSheet("color: rgba(200,160,60,0.5); background: transparent; letter-spacing: 2px;")
            self._clear_verse_display()
            return

        # Update reference
        ref = verse.get("reference", "")
        # Check overlays directly from display controller — not secondary_translations which may lag
        has_overlays = len(self.display.secondary_translations) > 0

        if has_overlays:
            # Overlay mode — reference only, no version
            display_ref = ref
        else:
            # Single translation — include version name
            trans = verse.get("translation", "")
            display_ref = f"{ref} — {trans}" if trans else ref
        self.ref_label.setText(display_ref)
        self.ref_label.setStyleSheet("color: #c8a03c; background: transparent; letter-spacing: 2px;")
        self._update_verse_display()
    
    def _update_verse_display(self):
        """Update verse display with current and secondary translations,
        then dynamically scale font to fit the viewport."""
        if self._fitting:
            return
        if not self.display.current:
            self._clear_verse_display()
            return
        
        self._fitting = True
        try:
            self._current_base_font = self._find_fitting_font_size()
            self._render_current(base_font=self._current_base_font)
        finally:
            self._fitting = False

    def _find_fitting_font_size(self):
        """Binary search for the largest font size that fits all content in the viewport."""
        print("[FONT_FIT] START", flush=True)
        viewport = self.verse_scroll.viewport()
        if not viewport:
            print("[FONT_FIT] no viewport, returning 14", flush=True)
            return 14

        available_width = viewport.width() - 20
        available_height = viewport.height() - 50

        if available_width <= 0 or available_height <= 30:
            print(f"[FONT_FIT] small viewport w={available_width} h={available_height}, returning 10", flush=True)
            return 10

        primary = self.display.current
        if not primary:
            print("[FONT_FIT] no current verse, returning 14", flush=True)
            return 14

        texts = [primary.get("text", "")]
        translations = [primary.get("translation", "")]
        for v in self.display.secondary_translations:
            texts.append(v.get("text", ""))
            translations.append(v.get("translation", ""))

        print(f"[FONT_FIT] avail={available_width}x{available_height} blocks={len(texts)}", flush=True)

        low, high = 8, 24
        best_font = 8

        for _ in range(10):
            if low > high:
                break
            mid = (low + high) // 2
            if self._content_fits(mid, available_width, available_height, texts, translations):
                best_font = mid
                low = mid + 1
            else:
                high = mid - 1

        result = max(8, best_font)
        print(f"[FONT_FIT] result={result}", flush=True)
        return result

    def _content_fits(self, font_size, max_width, max_height, texts, translations):
        """Return True if all text blocks fit within max_width x max_height at given font size."""
        try:
            font = QFont("Segoe UI", font_size)
            fm = QFontMetrics(font)
            line_height = fm.lineSpacing()
            total_height = 0

            for text, trans in zip(texts, translations):
                full_text = f"{trans}  {text}"
                lines = self._wrap_text(full_text, max_width, fm)
                total_height += lines * line_height

            if len(texts) > 1:
                separator_spacing = fm.height() // 2
                total_height += (len(texts) - 1) * separator_spacing

            total_height += 4  # safety margin

            return total_height <= max_height
        except Exception as e:
            print(f"[FONT_FIT] _content_fits error: {e}", flush=True)
            return False

    def _wrap_text(self, text, max_width, fm):
        """Count number of wrapped lines needed for the text."""
        if not text:
            return 1
        try:
            words = text.split()
            if not words:
                return 1
            lines = 1
            current_line_width = 0
            space_width = fm.horizontalAdvance(' ')

            for word in words:
                word_width = fm.horizontalAdvance(word)
                if current_line_width == 0:
                    current_line_width = word_width
                else:
                    if current_line_width + space_width + word_width <= max_width:
                        current_line_width += space_width + word_width
                    else:
                        lines += 1
                        current_line_width = word_width
            return lines
        except Exception as e:
            print(f"[FONT_FIT] _wrap_text error: {e}", flush=True)
            return 999

    def _render_current(self, base_font):
        """Render the appropriate view (single or overlay) with given base font."""
        if self.display.secondary_translations:
            self._render_overlay_view(base_font)
        else:
            self._render_single_view(base_font)

    def _render_single_view(self, base_font=16):
        """Render single verse view with calculated base_font size."""
        while self.verse_layout.count():
            item = self.verse_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self.display.current:
            return
        verse_font = base_font
        padding = max(4, int(base_font * 0.25))
        main_verse_label = QLabel(self.display.current.get("text", ""))
        main_verse_label.setFont(QFont("Segoe UI", verse_font))
        main_verse_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        main_verse_label.setWordWrap(True)
        main_verse_label.setStyleSheet(f"color: #e8e2d8; background: transparent; padding: {padding}px;")
        self.verse_layout.addWidget(main_verse_label)
        self.verse_layout.addStretch()

    def _render_overlay_view(self, base_font=16):
        """Render overlay view using the already-calculated base_font (no extra caps)."""
        # Clear previous content
        while self.verse_layout.count():
            item = self.verse_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.display.current:
            return

        total = 1 + len(self.display.secondary_translations)
        verse_font = base_font
        trans_font = max(8, int(base_font * 0.7))
        padding = max(2, int(base_font * 0.15))

        # Helper to create a rich-text label
        def add_verse(verse, is_primary=False):
            trans = verse.get("translation", "")
            text = verse.get("text", "")
            color = "rgba(200,160,60,0.8)" if is_primary else "rgba(212,168,75,0.8)"
            label = QLabel(
                f'<span style="color: {color}; font-size: {trans_font}px; font-weight: 700;">{trans}</span> '
                f'<span style="color: {"#e8e2d8" if is_primary else "#d0c8b8"};">{text}</span>'
            )
            label.setFont(QFont("Segoe UI", verse_font))
            label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setStyleSheet(f"background: transparent; padding: {padding}px;")
            return label

        # Primary verse (top)
        self.verse_layout.addWidget(add_verse(self.display.current, is_primary=True))

        # Overlays with separators (below primary)
        for i, v in enumerate(self.display.secondary_translations):
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("background: rgba(200,160,60,0.2);")
            sep.setFixedHeight(1)
            self.verse_layout.addWidget(sep)
            self.verse_layout.addWidget(add_verse(v, is_primary=False))

        self.verse_layout.addStretch()

    def resizeEvent(self, event):
        """Refit text when window is resized."""
        super().resizeEvent(event)
        if self.display.current and not self._fitting:
            self._fitting = True
            try:
                self._current_base_font = self._find_fitting_font_size()
                self._render_current(base_font=self._current_base_font)
            finally:
                self._fitting = False
    
    def _clear_verse_display(self):
        """Clear verse display."""
        while self.verse_layout.count():
            item = self.verse_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        placeholder = QLabel("Push a verse to preview it.")
        placeholder.setFont(QFont("Segoe UI", 14))
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: rgba(200,160,60,0.3); background: transparent;")
        self.verse_layout.addWidget(placeholder)
        self.verse_layout.addStretch()

    def set_preview_verse(self, verse):
        """Show a verse in the preview panel without pushing it to live display.
        Used by the Queue Panel for preview-on-click interaction."""
        if not verse:
            self._clear_verse_display()
            self.ref_label.setText("Ready")
            self.ref_label.setStyleSheet(
                "color: rgba(200,160,60,0.5); background: transparent; letter-spacing: 2px;"
            )
            return

        ref = verse.get("reference", "")
        trans = verse.get("translation", "")
        display_ref = f"{ref} — {trans}" if trans else ref
        self.ref_label.setText(display_ref)
        self.ref_label.setStyleSheet(
            "color: rgba(76,175,125,0.7); background: transparent; letter-spacing: 2px;"
        )

        # Render verse text
        while self.verse_layout.count():
            item = self.verse_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        text = verse.get("text", "")
        font_size = 14
        label = QLabel(text)
        label.setFont(QFont("Segoe UI", font_size))
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        label.setWordWrap(True)
        label.setStyleSheet("color: #d8d0c0; background: transparent; padding: 6px;")
        self.verse_layout.addWidget(label)
        self.verse_layout.addStretch()


# ── Placeholder Panel ───────────────────────────────────────────────────────

class PlaceholderPanel(QWidget):
    def __init__(self, title, body):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)

        header = QLabel(title)
        header.setFont(QFont("Segoe UI", 24, QFont.Weight.Light))
        header.setStyleSheet("color: #e8e2d8; background: transparent;")
        layout.addWidget(header)

        text = QLabel(body)
        text.setFont(QFont("Segoe UI", 13))
        text.setStyleSheet("color: rgba(200,160,60,0.3); background: transparent;")
        text.setWordWrap(True)
        layout.addWidget(text)
        layout.addStretch()


# ── Category 1 Placeholders ────────────────────────────────────────────────

class PlaylistPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setProperty("panel", True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)

        header = QHBoxLayout()
        dot = QFrame()
        dot.setFixedSize(5, 5)
        dot.setStyleSheet("QFrame { background: rgba(200,160,60,0.4); border-radius: 3px; }")
        header.addWidget(dot)
        label = QLabel("PLAYLIST PANEL")
        label.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        label.setStyleSheet("color: rgba(200,160,60,0.5); background: transparent; letter-spacing: 1.5px;")
        header.addWidget(label)
        header.addStretch()
        layout.addLayout(header)

        placeholder = QLabel("Reserved for Stage 3\\n(Service Playlist)")
        placeholder.setFont(QFont("Segoe UI", 8))
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: rgba(200,160,60,0.20); background: transparent; padding: 20px;")
        layout.addWidget(placeholder)
        layout.addStretch()


# ── Verse Live History Panel ───────────────────────────────────────────────

class VerseLiveHistoryPanel(QScrollArea):
    """Running log of every verse sent to the congregation screen during the current session.
    Each entry shows reference, translation, timestamp.
    Click any entry to restore that verse to display.
    """
    verse_clicked = pyqtSignal(dict)

    def __init__(self, display, parent=None):
        super().__init__(parent)
        self.display = display
        self.entries = []  # List of verse dicts with timestamp

        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(4)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.setWidget(self._container)

        # Placeholder
        self._placeholder = QLabel("No verses sent to screen yet.")
        self._placeholder.setFont(QFont("Segoe UI", 8))
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: rgba(200,160,60,0.20); background: transparent; padding: 8px;")
        self._layout.addWidget(self._placeholder)
        self._layout.addStretch()

    def add_verse(self, verse):
        """Add a verse to the history log."""
        if not verse or not verse.get("reference"):
            return

        # Hide placeholder
        if self._placeholder:
            self._placeholder.setVisible(False)

        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")

        entry = {
            "verse": verse,
            "timestamp": timestamp,
            "reference": verse.get("reference", ""),
            "translation": verse.get("translation", ""),
        }
        self.entries.append(entry)

        # Create clickable card
        card = HistoryEntryCard(entry)
        card.clicked.connect(lambda v=verse: self.verse_clicked.emit(v))
        card.clicked.connect(self._on_entry_clicked)

        # Insert before the stretch
        self._layout.insertWidget(self._layout.count() - 1, card)

        # Auto-scroll to bottom
        QTimer.singleShot(50, lambda: self.verticalScrollBar().setValue(
            self.verticalScrollBar().maximum()
        ))

    def _on_entry_clicked(self, verse):
        """Handle click on history entry — restore to display."""
        parent = self.parent()
        while parent and not hasattr(parent, '_restore_from_history'):
            parent = parent.parent()
        if parent and hasattr(parent, '_restore_from_history'):
            parent._restore_from_history(verse)

    def clear(self):
        """Clear all history entries."""
        self.entries.clear()
        # Remove all cards
        for i in reversed(range(self._layout.count())):
            item = self._layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), HistoryEntryCard):
                item.widget().deleteLater()
        # Show placeholder
        if self._placeholder:
            self._placeholder.setVisible(True)


class HistoryEntryCard(QFrame):
    """A single clickable entry in the verse live history."""
    clicked = pyqtSignal(dict)

    def __init__(self, entry, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setProperty("panel", True)
        self.setFixedHeight(22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)

        # Timestamp
        ts = QLabel(entry["timestamp"])
        ts.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
        ts.setStyleSheet("color: #c8a03c; background: transparent;")
        ts.setFixedWidth(45)
        layout.addWidget(ts)

        # Reference + translation
        ref = entry["reference"]
        book_match = re.match(r'^(.+?)\s+(\d+:\d+)$', ref)
        if book_match:
            book_name = book_match.group(1).strip()
            chap_verse = book_match.group(2)
            abbrev = BOOK_ABBREV_MAP.get(book_name, book_name)
            ref = f"{abbrev} {chap_verse}"

        trans = entry.get("translation", "")
        if trans:
            ref = f"{ref} ({trans})"
        ref_label = QLabel(ref)
        ref_label.setFont(QFont("Segoe UI", 7))
        ref_label.setStyleSheet("color: #e8e2d8; background: transparent;")
        ref_label.setWordWrap(False)
        layout.addWidget(ref_label, 1)

        # Restore icon
        restore_icon = QLabel("↺")
        restore_icon.setFont(QFont("Segoe UI", 9))
        restore_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        restore_icon.setStyleSheet("color: rgba(76,175,125,0.5); background: transparent;")
        restore_icon.setFixedWidth(16)
        layout.addWidget(restore_icon)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.entry["verse"])
        super().mousePressEvent(event)


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    import traceback
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("VerseFlow")
        app.setStyle("Fusion")

        # Apply theme via theme engine
        theme_mgr = ThemeManager()
        theme_mgr.set_theme(DEFAULT_THEME, app=app)

        window = MainWindow(theme_mgr)
        window.show()
        print("VerseFlow window created successfully")
        sys.exit(app.exec())
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
