"""db_layer.py — VerseFlow database access layer.

Owns the SQLite connection, verse lookup / search regex constants, and the
keyword search hard limit (MAX_RESULTS — distinct from constants.MAX_SEARCH_RESULTS).

Extracted from main.py in v0.7.11 modularization.
Audited v0.7.12
"""

import re
import sqlite3
from pathlib import Path

from constants import resolve_book, BOOK_TO_NUM

# ── Paths ────────────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent.parent / "3. Database" / "verseflow.db"

# ── Reference regex patterns ────────────────────────────────────────────────
REF_RE = re.compile(r'^(.+?)\s+(\d+):(\d+)$', re.IGNORECASE)

# Flexible verse look-up: matches "John 3:16", "John 3,16", etc.
VERSE_LOOKUP_RE = re.compile(
    r'^(.+?)\s*[ :;,\./\-_]+?\s*(\d+)\s*[ :;,\./\-_]+?\s*(\d+)\s*$', re.IGNORECASE
)

# Fallback for purely space-separated references: "John 3 16", "1 Samuel 3 16"
SPACE_VERSE_RE = re.compile(r'^(.+?)\s+(\d+)\s+(\d+)\s*$', re.IGNORECASE)

# Keyword-search hard limit. NOT the same as constants.MAX_SEARCH_RESULTS (100).
MAX_RESULTS = 50


def _escape_like(term: str) -> str:
    """Escape %, _, and \\ so they are treated as literals in LIKE clauses."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _book_order_sql():
    """Build a CASE expression that maps book names to canonical order numbers."""
    whens = " ".join(f"WHEN '{book}' THEN {num}" for book, num in BOOK_TO_NUM.items())
    return f"CASE book {whens} ELSE 99 END"

BOOK_ORDER_EXPR = _book_order_sql()


def abbreviate_translation(name: str) -> str:
    """Abbreviate translation name for display (e.g., 'English KJV' → 'KJV')."""
    if not name:
        return name
    # Remove 'English ' prefix for brevity
    if name.startswith("English "):
        return name[8:]
    return name


def _clean_reference(row):
    """Sanitize the reference field from a database row.
    
    The database reference column may contain UTF-8 mojibake (e.g., 'â€"' for em-dash).
    We reconstruct a clean reference from the book/chapter/verse fields which are
    always clean, preserving any verse range suffix from the original reference.
    
    Row layout: (id, translation, book, chapter, verse, text, reference)
    Indices:     0    1           2     3        4      5    6
    """
    book = row[2]
    chapter = row[3]
    verse = row[4]
    original_ref = row[6] or ""
    base_ref = f"{book} {chapter}:{verse}"
    
    # Check for verse range suffix and preserve it (e.g., "-17" from "John 3:16-17")
    verse_str = str(verse)
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
                    return base_ref + "-" + suffix[:end_idx]
        except Exception:
            pass
    return base_ref


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
        m = VERSE_LOOKUP_RE.match(q) or SPACE_VERSE_RE.match(q)
        if not m:
            return None
        raw_book = m.group(1).strip()
        book = resolve_book(raw_book)
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
        try:
            rows = c.execute(sql, params).fetchall()
            verses = [
                {"id": r[0], "translation": r[1], "book": r[2], "chapter": r[3],
                 "verse": r[4], "text": r[5], "reference": _clean_reference(r)}
                for r in rows
            ]
            return {"book": book, "chapter": chapter, "target_verse": target_verse, "verses": verses}
        finally:
            c.close()

    def search(self, query, translation=""):
        """Search by reference or keyword. Returns list (reference match) or dict (keyword)."""
        q = query.strip()
        if not q:
            return []

        c = self._conn()

        m = REF_RE.match(q) or VERSE_LOOKUP_RE.match(q) or SPACE_VERSE_RE.match(q)
        if m:
            raw_book = m.group(1).strip()
            book = resolve_book(raw_book)
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
            try:
                rows = c.execute(sql, params).fetchall()
                return [
                    {"id": r[0], "translation": r[1], "book": r[2], "chapter": r[3],
                     "verse": r[4], "text": r[5], "reference": _clean_reference(r)}
                    for r in rows
                ]
            finally:
                c.close()

        return self._keyword_search(c, q, translation)

    def _keyword_search(self, conn, query, translation=""):
        """Search verse text or reference (case-insensitive).

        Input routing:
          Quoted phrases : "God so loved" → each phrase AND'd (unchanged)
          Single word    : faith → simple LIKE match
          Multi-word     : fishers of → TWO-TIER RELEVANCE
                           Tier 1: exact phrase ("fishers of") shown first
                           Tier 2: AND-word matches not in Tier 1 shown after

        Returns dict with keys:
          "verses"  – list of verse dicts (up to MAX_RESULTS)
          "total"   – total AND-word matches (uncapped), used for count label
          "capped"  – True if total > MAX_RESULTS
        """
        try:
            quoted = re.findall(r'"([^"]*)"', query)
            if quoted:
                # ── Quoted-phrase path (unchanged) ────────────────────────────────
                conditions = []
                params = []
                for raw_phrase in quoted:
                    phrase = ' '.join(raw_phrase.split())
                    if not phrase:
                        continue
                    safe = _escape_like(phrase)
                    conditions.append("(text LIKE ? ESCAPE '\\' OR reference LIKE ? ESCAPE '\\')")
                    params.extend([f"%{safe}%", f"%{safe}%"])
                # AND-in any unquoted words outside the phrases
                remainder = re.sub(r'"[^"]*"', '', query).strip()
                for word in remainder.split():
                    if word:
                        safe = _escape_like(word)
                        conditions.append("(text LIKE ? ESCAPE '\\' OR reference LIKE ? ESCAPE '\\')")
                        params.extend([f"%{safe}%", f"%{safe}%"])
                if not conditions:
                    return {"verses": [], "total": 0, "capped": False}
                where_clause = ' AND '.join(conditions)
                # Count total matching rows (uncapped)
                count_params = list(params)
                count_sql = f"SELECT COUNT(*) FROM verses WHERE {where_clause}"
                if translation:
                    count_sql += " AND translation = ?"
                    count_params.append(translation)
                total = conn.execute(count_sql, count_params).fetchone()[0]
                # Main query with canonical ordering and limit
                sql = (
                    "SELECT id, translation, book, chapter, verse, text, reference "
                    f"FROM verses WHERE {where_clause}"
                )
                if translation:
                    sql += " AND translation = ?"
                    params.append(translation)
                sql += f" ORDER BY {BOOK_ORDER_EXPR}, chapter, verse LIMIT {MAX_RESULTS}"
                rows = conn.execute(sql, params).fetchall()
                return {
                    "verses": [
                        {"id": r[0], "translation": r[1], "book": r[2], "chapter": r[3],
                         "verse": r[4], "text": r[5], "reference": _clean_reference(r)}
                        for r in rows
                    ],
                    "total": total,
                    "capped": total > MAX_RESULTS,
                }

            # ── Unquoted path ────────────────────────────────────────────────────
            words = [w for w in query.split() if w]
            if not words:
                return {"verses": [], "total": 0, "capped": False}

            trans_filter = " AND translation = ?" if translation else ""

            if len(words) == 1:
                # Single word: no phrase to promote, simple LIKE
                safe = _escape_like(words[0])
                where = "(text LIKE ? ESCAPE '\\' OR reference LIKE ? ESCAPE '\\')"
                q_params = [f"%{safe}%", f"%{safe}%"]
                if translation:
                    q_params.append(translation)
                total = conn.execute(
                    f"SELECT COUNT(*) FROM verses WHERE {where}{trans_filter}", q_params
                ).fetchone()[0]
                rows = conn.execute(
                    f"SELECT id, translation, book, chapter, verse, text, reference "
                    f"FROM verses WHERE {where}{trans_filter} "
                    f"ORDER BY {BOOK_ORDER_EXPR}, chapter, verse LIMIT {MAX_RESULTS}",
                    q_params
                ).fetchall()
                return {
                    "verses": [
                        {"id": r[0], "translation": r[1], "book": r[2], "chapter": r[3],
                         "verse": r[4], "text": r[5], "reference": _clean_reference(r)}
                        for r in rows
                    ],
                    "total": total,
                    "capped": total > MAX_RESULTS,
                }

            # ── Multi-word: two-tier relevance ───────────────────────────────────

            # Tier 1 — exact contiguous phrase
            safe_phrase = _escape_like(" ".join(words))
            t1_where = "(text LIKE ? ESCAPE '\\' OR reference LIKE ? ESCAPE '\\')"
            t1_params = [f"%{safe_phrase}%", f"%{safe_phrase}%"]
            if translation:
                t1_params.append(translation)
            tier1_rows = conn.execute(
                f"SELECT id, translation, book, chapter, verse, text, reference "
                f"FROM verses WHERE {t1_where}{trans_filter} "
                f"ORDER BY {BOOK_ORDER_EXPR}, chapter, verse LIMIT {MAX_RESULTS}",
                t1_params
            ).fetchall()
            tier1_ids = [r[0] for r in tier1_rows]

            # Tier 2 — AND-word match, excluding Tier 1
            and_conditions = " AND ".join(
                "(text LIKE ? ESCAPE '\\' OR reference LIKE ? ESCAPE '\\')" for _ in words
            )
            t2_params = []
            for word in words:
                safe = _escape_like(word)
                t2_params.extend([f"%{safe}%", f"%{safe}%"])
            t2_where = and_conditions
            if tier1_ids:
                placeholders = ",".join("?" * len(tier1_ids))
                t2_where += f" AND id NOT IN ({placeholders})"
                t2_params.extend(tier1_ids)
            if translation:
                t2_where += " AND translation = ?"
                t2_params.append(translation)

            remaining = MAX_RESULTS - len(tier1_rows)
            tier2_rows = []
            if remaining > 0:
                tier2_rows = conn.execute(
                    f"SELECT id, translation, book, chapter, verse, text, reference "
                    f"FROM verses WHERE {t2_where} "
                    f"ORDER BY {BOOK_ORDER_EXPR}, chapter, verse LIMIT {remaining}",
                    t2_params
                ).fetchall()

            # Total = all AND-word matches (Tier 1 is a subset; combined unique = AND total)
            count_params = []
            count_conditions = []
            for word in words:
                safe = _escape_like(word)
                count_conditions.append("(text LIKE ? ESCAPE '\\' OR reference LIKE ? ESCAPE '\\')")
                count_params.extend([f"%{safe}%", f"%{safe}%"])
            count_where = " AND ".join(count_conditions)
            if translation:
                count_where += " AND translation = ?"
                count_params.append(translation)
            total = conn.execute(
                f"SELECT COUNT(*) FROM verses WHERE {count_where}", count_params
            ).fetchone()[0]

            all_rows = tier1_rows + tier2_rows
            return {
                "verses": [
                    {"id": r[0], "translation": r[1], "book": r[2], "chapter": r[3],
                     "verse": r[4], "text": r[5], "reference": _clean_reference(r)}
                    for r in all_rows
                ],
                "total": total,
                "capped": total > MAX_RESULTS,
            }
        finally:
            conn.close()

    def get_verse(self, reference, translation=""):
        """Get a single verse by reference string like 'John 3:16'."""
        m = REF_RE.match(reference.strip())
        if not m:
            m = VERSE_LOOKUP_RE.match(reference.strip())
        if m:
            raw_book = m.group(1).strip()
            book = resolve_book(raw_book)
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
                    "chapter": row[3], "verse": row[4], "text": row[5], "reference": _clean_reference(row),
                }
        return None

    def get_chapter_verses(self, book, chapter, translation=""):
        """Get all verses for a chapter, optionally filtered by translation.

        Args:
            book: Canonical book name
            chapter: Chapter number
            translation: Optional translation filter

        Returns:
            List of verse dicts ordered by verse number.
        """
        c = self._conn()
        try:
            sql = (
                "SELECT id, translation, book, chapter, verse, text, reference "
                "FROM verses WHERE book=? AND chapter=?"
            )
            params = [book, chapter]
            if translation:
                sql += " AND translation=?"
                params.append(translation)
            sql += " ORDER BY verse"
            rows = c.execute(sql, params).fetchall()
            return [
                {"id": r[0], "translation": r[1], "book": r[2], "chapter": r[3],
                 "verse": r[4], "text": r[5], "reference": _clean_reference(r)}
                for r in rows
            ]
        finally:
            c.close()
