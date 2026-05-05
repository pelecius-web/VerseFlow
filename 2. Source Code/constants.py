"""constants.py - VerseFlow shared constants

Centralized constants shared across modules to eliminate duplication.
Includes Bible book mappings, MIME types, icon sizes, and database limits.

Extracted from main.py in v0.7.11 modularization.
Audited v0.7.12
"""

# ── Bible Book Mappings ────────────────────────────────────────────────────────

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

# ── MIME Types for Drag-and-Drop ─────────────────────────────────────────────────

MIME_PLAYLIST_ITEM = "application/x-verseflow-playlist-item"
MIME_QUEUE_ITEM = "application/x-verseflow-queue-item"

# ── Display Modes ─────────────────────────────────────────────────────────────

DISPLAY_MODE_FULLSCREEN = "fullscreen"
DISPLAY_MODE_LOWER_THIRD = "lower_third"

# ── Lower-Third Layout Ratios ────────────────────────────────────────────────

LOWER_THIRD_HEIGHT_RATIO = 0.28
LOWER_THIRD_LOGO_WIDTH_RATIO = 0.16
LOWER_THIRD_LOGO_MAX_HEIGHT_RATIO = 0.70
LOWER_THIRD_SEPARATOR_WIDTH = 1
LOWER_THIRD_TEXT_MARGIN = 24
LOWER_THIRD_REF_FONT_RATIO = 0.60
LOWER_THIRD_BACKGROUND_ALPHA = 0.72

# ── Icon Sizes ───────────────────────────────────────────────────────────────────

ICON_SIZE_SMALL = (16, 16)
ICON_SIZE_MEDIUM = (24, 24)
ICON_SIZE_LARGE = (32, 32)

# ── Database Limits ───────────────────────────────────────────────────────────────

MAX_SEARCH_RESULTS = 100

# ── Book Name Aliases & Resolver ─────────────────────────────────────────────────
# Maps common abbreviations / variants → canonical DB book name.

BOOK_ALIASES = {
    "gn": "Genesis", "gen": "Genesis", "gene": "Genesis", "genes": "Genesis",
    "exo": "Exodus", "exod": "Exodus", "exodu": "Exodus",
    "lev": "Leviticus", "lv": "Leviticus", "levi": "Leviticus", "levit": "Leviticus",
    "num": "Numbers", "nb": "Numbers", "nm": "Numbers", "numb": "Numbers", "numbe": "Numbers", "number": "Numbers",
    "deu": "Deuteronomy", "dt": "Deuteronomy", "deut": "Deuteronomy", "deute": "Deuteronomy",
    "jos": "Joshua", "josh": "Joshua", "joshu": "Joshua",
    "jdg": "Judges", "judg": "Judges", "judge": "Judges",
    "rut": "Ruth",
    "1sam": "1 Samuel", "1samuel": "1 Samuel", "1sa": "1 Samuel", "1 s": "1 Samuel", "1 sm": "1 Samuel", "i sam": "1 Samuel", "i samuel": "1 Samuel",
    "2sam": "2 Samuel", "2samuel": "2 Samuel", "2sa": "2 Samuel", "2 s": "2 Samuel", "2 sm": "2 Samuel", "ii sam": "2 Samuel", "ii samuel": "2 Samuel",
    "1kin": "1 Kings", "1king": "1 Kings", "1k": "1 Kings", "1 k": "1 Kings", "i kin": "1 Kings", "i king": "1 Kings", "1 ki": "1 Kings", "1 king": "1 Kings",
    "2kin": "2 Kings", "2king": "2 Kings", "2k": "2 Kings", "2 k": "2 Kings", "ii kin": "2 Kings", "ii king": "2 Kings", "2 ki": "2 Kings", "2 king": "2 Kings",
    "1chr": "1 Chronicles", "1ch": "1 Chronicles", "1 chron": "1 Chronicles", "1 chr": "1 Chronicles", "i chr": "1 Chronicles", "i chron": "1 Chronicles", "1chron": "1 Chronicles", "1 chronicle": "1 Chronicles",
    "2chr": "2 Chronicles", "2ch": "2 Chronicles", "2 chron": "2 Chronicles", "2 chr": "2 Chronicles", "ii chr": "2 Chronicles", "ii chron": "2 Chronicles", "2chron": "2 Chronicles", "2 chronicle": "2 Chronicles",
    "ezr": "Ezra",
    "neh": "Nehemiah", "nehe": "Nehemiah", "nehem": "Nehemiah",
    "est": "Esther", "esth": "Esther", "esthe": "Esther",
    "job": "Job", "jb": "Job",
    "psa": "Psalms", "ps": "Psalms", "psalm": "Psalms", "pss": "Psalms", "psal": "Psalms",
    "pro": "Proverbs", "prov": "Proverbs", "prove": "Proverbs", "proverb": "Proverbs",
    "ecc": "Ecclesiastes", "eccl": "Ecclesiastes", "eccle": "Ecclesiastes",
    "sos": "Song of Solomon", "song": "Song of Solomon", "ss": "Song of Solomon", "sg": "Song of Solomon",
    "isa": "Isaiah", "isai": "Isaiah", "isaia": "Isaiah",
    "jer": "Jeremiah", "jere": "Jeremiah", "jerem": "Jeremiah",
    "lam": "Lamentations", "lame": "Lamentations", "lamen": "Lamentations", "lamentation": "Lamentations",
    "eze": "Ezekiel", "ezk": "Ezekiel", "ezek": "Ezekiel", "ezeki": "Ezekiel",
    "dan": "Daniel", "dn": "Daniel", "dani": "Daniel", "danie": "Daniel",
    "hos": "Hosea", "hose": "Hosea",
    "jol": "Joel", "jl": "Joel",
    "amo": "Amos",
    "obad": "Obadiah", "oba": "Obadiah", "obd": "Obadiah", "obadi": "Obadiah",
    "jon": "Jonah", "jnh": "Jonah", "jonah": "Jonah", "jona": "Jonah",
    "mic": "Micah", "mc": "Micah", "mica": "Micah",
    "nah": "Nahum", "nahu": "Nahum",
    "hab": "Habakkuk", "haba": "Habakkuk", "habak": "Habakkuk",
    "zep": "Zephaniah", "zeph": "Zephaniah", "zp": "Zephaniah", "zephania": "Zephaniah", "zepha": "Zephaniah",
    "hag": "Haggai", "hg": "Haggai", "hagg": "Haggai", "hagga": "Haggai",
    "zec": "Zechariah", "zech": "Zechariah", "zch": "Zechariah", "zecha": "Zechariah",
    "mal": "Malachi", "ml": "Malachi", "mala": "Malachi", "malac": "Malachi",
    "mat": "Matthew", "matt": "Matthew", "mt": "Matthew", "mathew": "Matthew", "mtt": "Matthew", "matth": "Matthew",
    "mar": "Mark", "mk": "Mark", "mrk": "Mark", "mr": "Mark", "mark": "Mark",
    "luk": "Luke", "lk": "Luke",
    "jhn": "John", "jn": "John", "joh": "John",
    "act": "Acts",
    "rom": "Romans", "rm": "Romans", "roma": "Romans", "roman": "Romans",
    "1cor": "1 Corinthians", "1 co": "1 Corinthians", "1cori": "1 Corinthians", "1 cor": "1 Corinthians", "1 corin": "1 Corinthians", "1 corinth": "1 Corinthians", "i cor": "1 Corinthians", "i corinth": "1 Corinthians", "1corint": "1 Corinthians", "1corinth": "1 Corinthians", "1 corinthian": "1 Corinthians",
    "2cor": "2 Corinthians", "2 co": "2 Corinthians", "2cori": "2 Corinthians", "2 cor": "2 Corinthians", "2 corin": "2 Corinthians", "2 corinth": "2 Corinthians", "ii cor": "2 Corinthians", "ii corinth": "2 Corinthians", "2corint": "2 Corinthians", "2corinth": "2 Corinthians", "2 corinthian": "2 Corinthians",
    "gal": "Galatians", "gl": "Galatians", "gala": "Galatians", "galat": "Galatians", "galatian": "Galatians",
    "eph": "Ephesians", "ephn": "Ephesians", "ephe": "Ephesians", "ephes": "Ephesians", "ephesian": "Ephesians",
    "php": "Philippians", "pp": "Philippians", "phili": "Philippians", "philippian": "Philippians",
    "col": "Colossians", "cl": "Colossians", "coloss": "Colossians", "colo": "Colossians", "colos": "Colossians", "colossian": "Colossians",
    "1thes": "1 Thessalonians", "1 th": "1 Thessalonians", "1 thess": "1 Thessalonians", "i th": "1 Thessalonians", "1thess": "1 Thessalonians", "1 the": "1 Thessalonians", "1 thessalonian": "1 Thessalonians",
    "2thes": "2 Thessalonians", "2 th": "2 Thessalonians", "2 thess": "2 Thessalonians", "ii th": "2 Thessalonians", "2thess": "2 Thessalonians", "2 the": "2 Thessalonians", "2 thessalonian": "2 Thessalonians",
    "1tim": "1 Timothy", "1 ti": "1 Timothy", "1 tim": "1 Timothy", "i tim": "1 Timothy", "1timothy": "1 Timothy",
    "2tim": "2 Timothy", "2 ti": "2 Timothy", "2 tim": "2 Timothy", "ii tim": "2 Timothy", "2timothy": "2 Timothy",
    "tit": "Titus", "titu": "Titus",
    "phm": "Philemon", "pm": "Philemon", "phile": "Philemon", "philem": "Philemon",
    "heb": "Hebrews", "hebr": "Hebrews", "hebre": "Hebrews", "hebrew": "Hebrews",
    "jas": "James", "jm": "James", "jame": "James",
    "1pet": "1 Peter", "1 pt": "1 Peter", "1 pet": "1 Peter", "i pet": "1 Peter", "1 peter": "1 Peter", "1peter": "1 Peter", "1 pe": "1 Peter",
    "2pet": "2 Peter", "2 pt": "2 Peter", "2 pet": "2 Peter", "ii pet": "2 Peter", "2 peter": "2 Peter", "2peter": "2 Peter", "2 pe": "2 Peter",
    "1jn": "1 John", "1 jo": "1 John", "1 joh": "1 John", "i jn": "1 John", "i joh": "1 John", "1john": "1 John",
    "2jn": "2 John", "2 jo": "2 John", "2 joh": "2 John", "ii jn": "2 John", "ii joh": "2 John", "2john": "2 John",
    "3jn": "3 John", "3 jo": "3 John", "3 joh": "3 John", "iii jn": "3 John", "iii joh": "3 John", "3john": "3 John",
    "jud": "Jude", "judah": "Jude", "jd": "Jude",
    "rev": "Revelation", "rv": "Revelation", "revl": "Revelation", "reve": "Revelation", "revel": "Revelation", "revelations": "Revelation",
}

BOOK_ALIAS_MAP = {}
for _alias, _canonical in BOOK_ALIASES.items():
    BOOK_ALIAS_MAP[_alias.lower()] = _canonical
for _name in BOOK_NAMES.values():
    BOOK_ALIAS_MAP[_name.lower()] = _name


def resolve_book(raw_book):
    """Resolve a user-typed book name/abbreviation to the canonical DB name."""
    key = raw_book.lower().strip()
    if key in BOOK_ALIAS_MAP:
        return BOOK_ALIAS_MAP[key]

    def _norm(s):
        return s.lower().replace(" ", "").replace(".", "").replace("-", "")

    norm_key = _norm(raw_book)
    for alias, canonical in BOOK_ALIAS_MAP.items():
        if _norm(alias) == norm_key:
            return canonical
    return None
