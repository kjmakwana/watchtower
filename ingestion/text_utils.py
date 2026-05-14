# ingestion/text_utils.py

import html
import re

# Wire-service dateline attributions that appear at the start of summaries,
# e.g. "VIENNA (Reuters) — Diplomats gathered..."
_DATELINES = [
    re.compile(r"\(reuters\)\s*[-–—]?\s*"),
    re.compile(r"\(ap\)\s*[-–—]?\s*"),
    re.compile(r"\(afp\)\s*[-–—]?\s*"),
    re.compile(r"\(dpa\)\s*[-–—]?\s*"),
    re.compile(r"\(bbc\)\s*[-–—]?\s*"),
]

# End-of-text boilerplate patterns (anchored to line end via MULTILINE)
_TRAILING = [
    re.compile(r"©.*$", re.MULTILINE),
    re.compile(r"read\s+more.*$", re.MULTILINE),
    re.compile(r"full\s+story.*$", re.MULTILINE),
]

_HTML_TAG    = re.compile(r"<[^>]+>")
_URL         = re.compile(r"https?://\S+")
# Hyphens that are NOT between two alphanumeric characters are orphans
_ORPHAN_HYPHEN = re.compile(r"(?<![a-z0-9])-|-(?![a-z0-9])")
# Strip punctuation while preserving Unicode word characters (Cyrillic, Arabic,
# CJK etc. are meaningful proper nouns in geopolitical text). \w matches
# Unicode letters/digits in Python 3; underscores are caught separately.
_NON_WORD    = re.compile(r"[^\w\-\s]", re.UNICODE)
_UNDERSCORE  = re.compile(r"_")
_WHITESPACE  = re.compile(r"\s+")


def _clean_text(text: str) -> str:
    """
    Called by: build_clean_corpus (this module)
    Parameters: text (str) — raw title or summary from the Article model
    Returns: cleaned, lowercase string with structural noise removed
    Basic working: decodes HTML entities, strips tags/URLs/boilerplate,
                   lowercases, normalises punctuation and whitespace;
                   intra-word hyphens (al-Assad, anti-tank) are preserved
    """
    # Decode HTML entities first so &amp; doesn't survive as a token
    text = html.unescape(text)
    # Second-pass tag strip (entities like &lt;b&gt; are now real tags)
    text = _HTML_TAG.sub(" ", text)
    # Remove URLs before lowercasing so case doesn't affect the pattern
    text = _URL.sub(" ", text)
    # Lowercase before boilerplate patterns (patterns are lowercase)
    text = text.lower()
    for pat in _DATELINES:
        text = pat.sub(" ", text)
    for pat in _TRAILING:
        text = pat.sub(" ", text)
    # Remove hyphens that stand alone (list bullets, em-dashes, etc.)
    # but keep intra-word hyphens like "al-qaeda" or "anti-tank"
    text = _ORPHAN_HYPHEN.sub(" ", text)
    # Strip all remaining punctuation
    text = _NON_WORD.sub(" ", text)
    text = _UNDERSCORE.sub(" ", text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text


def build_clean_corpus(title: str, summary: str) -> str:
    """
    Called by: ingestion/clustering.py (_find_clusters via assign_clusters)
    Parameters:
        title   (str) — raw article title from Article model
        summary (str) — raw article summary from Article model
    Returns: cleaned string for sentence-transformer encoding
    Basic working: cleans title and summary via _clean_text, concatenates
                   with a period separator; sentence embeddings handle
                   semantic weighting, so title repetition is not needed
    """
    clean_title   = _clean_text(title or "")
    clean_summary = _clean_text(summary or "")

    if clean_summary:
        return (clean_title + ". " + clean_summary).strip()
    return clean_title
