"""build_db.py — VerseFlow Stage 1: Parse Bible XML translations into verseflow.db"""

import glob as _glob
import sqlite3
import xml.etree.ElementTree as ET
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "2. Source Code"))
from constants import BOOK_NAMES

DB_PATH = Path(__file__).parent.parent / "3. Database" / "verseflow.db"
TRANSLATIONS_DIR = Path(__file__).parent.parent / "4. Translations" / "Zefania Licensed"

INDEX_SCRIPT = """
CREATE INDEX IF NOT EXISTS idx_verses_reference ON verses(reference);
CREATE INDEX IF NOT EXISTS idx_verses_translation ON verses(translation);
CREATE INDEX IF NOT EXISTS idx_verses_book ON verses(book);
CREATE INDEX IF NOT EXISTS idx_verses_chapter ON verses(book, chapter);
CREATE INDEX IF NOT EXISTS idx_verses_text ON verses(text);
"""

VERBOSE = "-v" in sys.argv or "--verbose" in sys.argv

# XML files to skip (corrupted/malformed) — currently none
SKIP_FILES: set[str] = set()


def create_db():
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE verses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            translation TEXT NOT NULL,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            text TEXT NOT NULL,
            reference TEXT NOT NULL
        )
    """)
    conn.executescript(INDEX_SCRIPT)
    conn.commit()
    return conn


def find_xml_files():
    """Scan the translations directory for XML files, skipping known-bad ones."""
    xml_files = []
    for item in sorted(TRANSLATIONS_DIR.iterdir()):
        if item.name in SKIP_FILES:
            continue
        if item.is_file() and item.suffix.lower() == ".xml":
            xml_files.append(item)
        elif item.is_dir():
            subs = list(item.glob("*.xml"))
            if subs:
                xml_files.append(subs[0])
    return xml_files


def parse_kjb_bible(xml_path):
    """Parse <bible>/<testament>/<book>/<chapter>/<verse> format (KJV)."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    raw = root.attrib.get("translation", root.attrib.get("name", "UNKNOWN"))
    # Map XML name/translation attribute to user-friendly label
    # Derive friendly name from XML name or translation attribute
    if raw.startswith("English Amplified"):
        translation = "AMP"
    elif "Amplified" in raw:
        translation = "AMP"
    elif raw == "English KJV":
        translation = "English KJV"
    else:
        translation = raw

    verses = []
    for testament in root:
        if testament.tag != "testament":
            continue
        for book in testament:
            if book.tag != "book":
                continue
            book_num = int(book.get("number", "0"))
            book_name = BOOK_NAMES.get(book_num, f"Book{book_num}")
            for chapter in book:
                if chapter.tag != "chapter":
                    continue
                ch_num = int(chapter.get("number", "0"))
                for verse in chapter:
                    if verse.tag != "verse":
                        continue
                    v_num = int(verse.get("number", "0"))
                    text = (verse.text or "").strip()
                    if not text:
                        continue
                    verses.append({
                        "translation": translation,
                        "book": book_name,
                        "chapter": ch_num,
                        "verse": v_num,
                        "text": text,
                        "reference": f"{book_name} {ch_num}:{v_num}",
                    })
    return translation, verses


def parse_xmlbible(xml_path):
    """Parse <XMLBIBLE>/<BIBLEBOOK>/<CHAPTER>/<VERS> format (ESV/NKJV/NLT/MSG)."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    raw = root.attrib.get("biblename", "UNKNOWN").upper()
    # Derive user-friendly translation name
    name_map = {
        "ENGLISHEMP": "AMP",
        "ENGLESV": "ESV",
        "ENGLISHEBV": "EBV",
        "ENGLISHMSG": "MSG",
        "ENGLISHNKJ": "NKJV",
        "ENGLISHNLT": "NLT",
    }
    translation = name_map.get(raw, raw.replace("ENGLISH", ""))

    verses = []
    for biblebook in root.findall(".//BIBLEBOOK"):
        book_num = int(biblebook.get("bnumber", "0"))
        book_name = BOOK_NAMES.get(book_num, f"Book{book_num}")
        for chapter in biblebook.findall("CHAPTER"):
            ch_num = int(chapter.get("cnumber", "0"))
            for vers in chapter.findall("VERS"):
                v_num = int(vers.get("vnumber", "0"))
                text = (vers.text or "").strip()
                if not text:
                    continue
                verses.append({
                    "translation": translation,
                    "book": book_name,
                    "chapter": ch_num,
                    "verse": v_num,
                    "text": text,
                    "reference": f"{book_name} {ch_num}:{v_num}",
                })
    return translation, verses


def main():
    print(f"VerseFlow Stage 1 — Building {DB_PATH.resolve()}")
    print()

    xml_files = find_xml_files()
    if not xml_files:
        print("ERROR: No translation XML files found")
        sys.exit(1)

    print(f"Found {len(xml_files)} translation file(s)")
    conn = create_db()

    all_translations = []
    for xml_path in xml_files:
        print(f"\nParsing: {xml_path.name}")
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            if root.tag == "XMLBIBLE":
                translation, verses = parse_xmlbible(xml_path)
            else:
                translation, verses = parse_kjb_bible(xml_path)
        except Exception as e:
            print(f"  SKIPPED: {e}")
            continue

        if not verses:
            print(f"  SKIPPED: no verses parsed")
            continue

        print(f"  Inserting {len(verses):,} {translation} verses...")
        conn.executemany(
            "INSERT INTO verses (translation, book, chapter, verse, text, reference) "
            "VALUES (:translation, :book, :chapter, :verse, :text, :reference)",
            verses,
        )
        conn.commit()
        all_translations.append(translation)

    # Summary
    total = conn.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
    translations_in_db = conn.execute("SELECT DISTINCT translation FROM verses ORDER BY translation").fetchall()
    print(f"\n{'='*50}")
    print(f"Total: {total:,} verses across {len(translations_in_db)} translations")
    for (t,) in translations_in_db:
        cnt = conn.execute("SELECT COUNT(*) FROM verses WHERE translation=?", (t,)).fetchone()[0]
        print(f"  {t}: {cnt:,}")

    # Benchmark
    import time
    t0 = time.perf_counter()
    rows = conn.execute("SELECT reference, text, translation FROM verses WHERE reference='John 3:16'").fetchall()
    t1 = time.perf_counter()
    print(f"\nBenchmark 'John 3:16': {len(rows)} result(s) in {(t1-t0)*1000:.1f}ms")

    print(f"\nDB size: {DB_PATH.stat().st_size / 1024 / 1024:.2f} MB")
    print("Done.")


if __name__ == "__main__":
    main()
