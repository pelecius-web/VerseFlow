# Keyword Search Improvements — Implementation Plan

**Context:** The keyword search system (`db_layer.py:_keyword_search` + `home_panel.py:_do_search` + `navigator.py:KeywordResults`) works but has correctness gaps, no result ordering, no pagination, and no match highlighting. This plan addresses all five deficiency categories identified in review.

---

## Code Changes

### Change 1 — Escape LIKE Wildcards (Correctness Fix)

**File:** `db_layer.py`  
**What:** Add a `_escape_like()` helper and call it everywhere user input enters a `LIKE` clause.

**Why:** User input containing `%` or `_` currently acts as SQL wildcards. Searching `100%` matches any text containing `100` followed by anything. Searching `_od` matches `God`, `Rod`, etc. — not just the literal `_od`.

**Function to add** (top-level, near line 33):
```python
def _escape_like(term: str) -> str:
    """Escape %, _, and \\ so they are treated as literals in LIKE clauses."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
```

**Function to modify:** `_keyword_search()` (line 162–209)  
- Wrap every user-derived value with `_escape_like()` before inserting into `f"%{...}%"` patterns.  
- Append `ESCAPE '\\'` to the SQL `WHERE` clause so SQLite knows the escape character.

**Before (line 183–184):**
```python
conditions = ["(text LIKE ? OR reference LIKE ?)"]
params = [f"%{words[0]}%", f"%{words[0]}%"]
```

**After:**
```python
safe = _escape_like(words[0])
conditions = ["(text LIKE ? ESCAPE '\\' OR reference LIKE ? ESCAPE '\\')"]
params = [f"%{safe}%", f"%{safe}%"]
```

Apply the same pattern to the quoted-phrase branch (line 175–176) and the multi-word loop (line 189–190).

---

### Change 2 — Support Multiple Quoted Phrases (Correctness Fix)

**File:** `db_layer.py`  
**Function:** `_keyword_search()` (line 170–176)

**Why:** `re.findall(r'"([^"]*)"', query)` captures all quoted phrases, but only `quoted[0]` is used. `"God so" "loved the world"` silently drops the second phrase.

**Current logic (line 171–176):**
```python
quoted = re.findall(r'"([^"]*)"', query)
if quoted:
    phrase = ' '.join(quoted[0].split())
    ...single condition...
```

**New logic:**
```python
quoted = re.findall(r'"([^"]*)"', query)
if quoted:
    conditions = []
    params = []
    for raw_phrase in quoted:
        phrase = ' '.join(raw_phrase.split())
        if not phrase:
            continue
        safe = _escape_like(phrase)
        conditions.append("(text LIKE ? ESCAPE '\\' OR reference LIKE ? ESCAPE '\\')")
        params.extend([f"%{safe}%", f"%{safe}%"])
    # Also AND-in any unquoted words outside the phrases
    remainder = re.sub(r'"[^"]*"', '', query).strip()
    for word in remainder.split():
        if word:
            safe = _escape_like(word)
            conditions.append("(text LIKE ? ESCAPE '\\' OR reference LIKE ? ESCAPE '\\')")
            params.extend([f"%{safe}%", f"%{safe}%"])
    if not conditions:
        return []
```

This means `"God so" "loved the" world` → all three terms AND'd together: the two phrases plus the bare word `world`.

---

### Change 3 — Canonical Bible Order (UX Improvement)

**File:** `db_layer.py`  
**Function:** `_keyword_search()` (line 200, the SQL assembly)

**Why:** Results currently have no `ORDER BY`, so they arrive in arbitrary DB insertion order. Searching "love" might return Malachi before Genesis. Users expect canonical book order (Genesis → Revelation).

**Approach:** `constants.py` already exports `BOOK_TO_NUM` (`{"Genesis": 1, "Exodus": 2, ...}`). Build a SQL `CASE` expression for ordering.

**Add a module-level helper** (near `MAX_RESULTS`, line 31):
```python
from constants import BOOK_TO_NUM

def _book_order_sql():
    """Build a CASE expression that maps book names to canonical order numbers."""
    whens = " ".join(f"WHEN '{book}' THEN {num}" for book, num in BOOK_TO_NUM.items())
    return f"CASE book {whens} ELSE 99 END"

BOOK_ORDER_EXPR = _book_order_sql()
```

**Modify the SQL in `_keyword_search()`** (line 200):

**Before:**
```python
sql += f" LIMIT {MAX_RESULTS}"
```

**After:**
```python
sql += f" ORDER BY {BOOK_ORDER_EXPR}, chapter, verse LIMIT {MAX_RESULTS}"
```

This ensures the first 50 results are the earliest ones in Bible order, not arbitrary.

---

### Change 4 — Return Result Metadata (Count + Cap Indicator)

**File:** `db_layer.py`  
**Function:** `_keyword_search()` (line 162–209)

**Why:** Users currently get 50 results with no indication that more exist. This change lets the UI show "Showing 50 of 312 results" vs. "12 results".

**Approach:** Return a dict instead of a bare list. To avoid breaking existing callers, add a new method `_keyword_search_with_meta()` that wraps `_keyword_search`, or modify the return value and update both callers.

**Recommended: modify `_keyword_search` return type** to a dict:
```python
return {
    "verses": [...],       # list of verse dicts (up to MAX_RESULTS)
    "total": 312,          # total matching rows (uncapped)
    "capped": True,        # True when total > MAX_RESULTS
}
```

To get the total count efficiently, run a `SELECT COUNT(*)` with the same `WHERE` clause before the main query. On the ~100K row Bible table this adds negligible cost (~1ms).

**Callers to update:**

1. `db_layer.py:search()` line 160 — currently `return self._keyword_search(c, q, translation)`. Update to propagate the dict, OR unwrap:
   ```python
   result = self._keyword_search(c, q, translation)
   return result  # now returns dict with "verses", "total", "capped"
   ```

2. `home_panel.py:_do_search()` lines 992–993 and 1000–1001 — currently:
   ```python
   results = self.db.search(q, self.current_translation)
   self.keyword_results.set_verses(results)
   ```
   Update to:
   ```python
   result = self.db.search(q, self.current_translation)
   if isinstance(result, dict):
       self.keyword_results.set_verses(result["verses"], total=result["total"], capped=result["capped"])
   else:
       self.keyword_results.set_verses(result)
   ```

   The `isinstance` guard ensures backward compatibility during the transition — `search()` returns a plain list for reference lookups and a dict for keyword searches.

---

### Change 5 — Result Count Badge in UI

**File:** `navigator.py`  
**Class:** `KeywordResults` (line 618)  
**Function:** `set_verses()` (line 644)

**Why:** The user has no feedback on how many results matched or whether results were truncated.

**Add a count label** to `KeywordResults.__init__()`:
```python
self.count_label = QLabel("")
self.count_label.setFont(QFont("Segoe UI", 9))
self.count_label.setStyleSheet("color: rgba(200,160,60,0.5); background: transparent; padding: 4px 0;")
self.count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
layout.addWidget(self.count_label)  # Add ABOVE the scroll area
```

**Update `set_verses()` signature** to accept metadata:
```python
def set_verses(self, verses, total=None, capped=False):
```

**Add count display logic** at the top of `set_verses()`:
```python
if total is not None and verses:
    if capped:
        self.count_label.setText(f"Showing {len(verses)} of {total} results")
    else:
        self.count_label.setText(f"{total} result{'s' if total != 1 else ''}")
    self.count_label.setVisible(True)
else:
    self.count_label.setVisible(False)
```

---

### Change 6 — Match Highlighting in Keyword Result Cards

**File:** `navigator.py`  
**Class:** `KeywordVerseCard` (line 667)

**Why:** Users have to visually scan each result to find where their search term appears. Bolding matched terms dramatically improves scannability.

**Approach:** Pass the search query into `KeywordVerseCard` and use it to wrap matches in `<b>` tags, then render as rich text.

**Modify `KeywordVerseCard.__init__()` signature** (line 672):
```python
def __init__(self, verse, db=None, display=None, parent=None, query=""):
```

**Replace the plain text label** (line 704–708):

**Before:**
```python
text = QLabel(verse["text"])
text.setFont(QFont("Segoe UI", 11))
text.setStyleSheet("color: #d0c8b8; background: transparent;")
text.setWordWrap(True)
```

**After:**
```python
highlighted = self._highlight_matches(verse["text"], query)
text = QLabel(highlighted)
text.setFont(QFont("Segoe UI", 11))
text.setStyleSheet("color: #d0c8b8; background: transparent;")
text.setWordWrap(True)
text.setTextFormat(Qt.TextFormat.RichText)
```

**Add the highlighting helper** to `KeywordVerseCard`:
```python
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
```

**Update `KeywordResults.set_verses()`** (line 658–663) to pass the query through:
```python
def set_verses(self, verses, total=None, capped=False, query=""):
    ...
    for v in verses:
        card = KeywordVerseCard(v, self.db, self.display, query=query)
```

**Update callers in `home_panel.py:_do_search()`** to pass the query:
```python
self.keyword_results.set_verses(result["verses"], total=result["total"], capped=result["capped"], query=q)
```

---

## Order of Operations

| Step | Change | Depends On |
|------|--------|------------|
| 1 | Add `_escape_like()` helper to `db_layer.py` | — |
| 2 | Fix multi-phrase support in `_keyword_search()` | Step 1 (uses `_escape_like`) |
| 3 | Add `BOOK_ORDER_EXPR` and `ORDER BY` to `_keyword_search()` | — |
| 4 | Add count query + return dict from `_keyword_search()` | Steps 1–3 (modifies same function) |
| 5 | Update `search()` in `db_layer.py` to propagate dict for keyword results | Step 4 |
| 6 | Update `_do_search()` in `home_panel.py` to unpack dict and pass query | Step 5 |
| 7 | Add count label to `KeywordResults` in `navigator.py` | Step 6 |
| 8 | Add highlighting to `KeywordVerseCard` in `navigator.py` | Step 6 |

Steps 1–3 can be done together (all in `db_layer.py`, no dependency between them).  
Steps 7 and 8 can be done in parallel (both in `navigator.py`, different classes).

---

## Unit and Integration Tests to Add

### Test 1 — LIKE Wildcard Escaping
Verify that `_escape_like("100%")` returns `"100\\%"` and that searching for `100%` does NOT match `1000 talents` (which raw `%` would hit).

### Test 2 — Multiple Quoted Phrases
Search `"God so" "loved the"` and confirm only verses containing BOTH exact phrases are returned — not verses matching just one.

### Test 3 — Mixed Quoted + Bare Words
Search `"eternal life" believe` and confirm results contain both the exact phrase "eternal life" AND the word "believe".

### Test 4 — Canonical Ordering
Search a common word (e.g., `"light"`) and verify the first result's book is Genesis (or the earliest book in the DB containing that word), not an arbitrary book.

### Test 5 — Result Count Accuracy
Search a common word, verify `result["total"]` matches an independent `SELECT COUNT(*)`, and that `result["capped"]` is `True` when total > 50.

### Test 6 — Highlight Correctness
Call `KeywordVerseCard._highlight_matches("For God so loved the world", '"God so" world')` and verify the output contains `<b>` tags around "God so" and "world" but not around other words.

### Test 7 — Empty / Edge Cases
- Empty query returns empty results.
- Query of only quotes (`""`) returns empty results.
- Single character search (`"a"`) returns results capped at 50, ordered canonically.
- Query containing only `%` or `_` returns only literal matches (not everything).

---

## Local Verification Steps

1. **Build/launch** the application: `python main.py` (or however the project is started).
2. **Keyword search basic:** Switch to "Keyword Search" mode, type `love` — confirm results appear in Genesis → Revelation order.
3. **Wildcard escaping:** Search `100%` — confirm it does not return all verses containing `100`.
4. **Multi-phrase:** Search `"God so" "loved the"` — confirm only John 3:16 (and similar) appears, not verses with only one phrase.
5. **Mixed query:** Search `"eternal life" believe` — confirm results contain both the phrase and the word.
6. **Result count badge:** Search a common term like `the` — confirm the count label shows "Showing 50 of X results" (where X > 50).
7. **Highlight check:** In the keyword results panel, confirm search terms are visually bolded/gold in each result card's verse text.
8. **Result ordering:** Search `light` — confirm Genesis results appear before Revelation results.
9. **Regression — verse lookup:** Switch to "Verse Lookup" mode, type `John 3:16`, press Enter — confirm the chapter loads normally in the navigator. This must not be broken.
10. **Regression — search fallback:** In "Verse Lookup" mode, type a non-reference like `faith` and press Enter — confirm it falls back to keyword results gracefully.
11. **Run the test suite:** Execute existing tests to confirm no regressions.

---

## Definition of Done

The fix is complete when:

1. All existing tests pass without modification.
2. New tests (1–7 above) all pass.
3. Searching `%` or `_` returns only literal matches, not wildcard-expanded results.
4. Searching multiple quoted phrases returns only verses matching ALL phrases.
5. Keyword results are ordered Genesis → Revelation (canonical Bible order).
6. The result count badge accurately shows total count and indicates when results are capped.
7. Matched search terms are visually highlighted (bold/gold) in keyword result cards.
8. Verse Lookup mode, cross-reference clicks, history restore, and queue preview all function identically to before (no regressions in `_do_search`, `_on_xref_clicked`, `_restore_from_history`, `_preview_queued_verse`).
