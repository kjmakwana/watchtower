"""
tests/test_text_utils.py

Run from the project root:
    pytest tests/test_text_utils.py -v

Covers:
    - ingestion/text_utils.py — _clean_text, build_clean_corpus
"""

import pytest
from ingestion.text_utils import _clean_text, build_clean_corpus, TITLE_WEIGHT


class TestCleanText:

    # --- HTML entity decoding ---

    def test_decodes_amp_entity(self):
        # &amp; decodes to & which is then stripped as punctuation
        result = _clean_text("Iran &amp; Russia")
        assert "&amp;" not in result
        assert "iran" in result
        assert "russia" in result

    def test_decodes_quote_entity(self):
        result = _clean_text("&quot;ceasefire&quot; talks")
        assert "ceasefire" in result
        assert "&quot;" not in result

    def test_decodes_apos_entity(self):
        result = _clean_text("Iran&#39;s nuclear deal")
        assert "iran" in result
        assert "&#39;" not in result

    def test_decodes_entity_that_produces_html_tag(self):
        # &lt;b&gt; → <b> → stripped by second-pass tag removal
        result = _clean_text("&lt;b&gt;Breaking&lt;/b&gt;")
        assert "<" not in result
        assert "breaking" in result

    # --- HTML tag stripping ---

    def test_strips_html_tags(self):
        result = _clean_text("<p>Troops <b>deployed</b> in eastern flank</p>")
        assert "<" not in result
        assert "troops" in result
        assert "deployed" in result

    def test_strips_self_closing_tags(self):
        result = _clean_text("Summary<br/>continues here")
        assert "<" not in result

    # --- URL removal ---

    def test_removes_https_url(self):
        result = _clean_text("Breaking: https://bbc.com/news/world-123 today")
        assert "https" not in result
        assert "bbc.com" not in result
        assert "today" in result

    def test_removes_http_url(self):
        result = _clean_text("See http://example.com/article for details")
        assert "http" not in result

    def test_keeps_non_url_text_after_url(self):
        result = _clean_text("Read https://reuters.com/story then return")
        assert "read" in result
        assert "then" in result
        assert "return" in result

    # --- Boilerplate removal ---

    def test_strips_reuters_dateline(self):
        result = _clean_text("VIENNA (Reuters) - Diplomats gathered in Vienna")
        assert "reuters" not in result
        assert "vienna" in result
        assert "diplomats" in result

    def test_strips_ap_dateline(self):
        result = _clean_text("WASHINGTON (AP) — Senate passed the bill")
        assert "ap" not in result or "ap" in "map"  # 'ap' may appear in other words
        # More specific: the parenthesised attribution should be gone
        assert "(ap)" not in result

    def test_strips_afp_dateline(self):
        result = _clean_text("PARIS (AFP) - The president announced")
        assert "(afp)" not in result

    def test_strips_copyright_notice(self):
        result = _clean_text("Ceasefire agreed. © 2025 Reuters. All rights reserved.")
        assert "©" not in result
        assert "ceasefire" in result

    def test_strips_read_more_suffix(self):
        result = _clean_text("Talks broke down. Read more at BBC World Service.")
        assert "read more" not in result
        assert "talks" in result

    # --- Lowercasing ---

    def test_output_is_lowercase(self):
        result = _clean_text("NATO Ministers Met in BRUSSELS")
        assert result == result.lower()

    def test_proper_nouns_lowercased(self):
        result = _clean_text("Iran and Russia signed an agreement")
        assert "iran" in result
        assert "Iran" not in result

    # --- Hyphen handling ---

    def test_preserves_intra_word_hyphen(self):
        result = _clean_text("anti-tank missiles deployed")
        assert "anti-tank" in result

    def test_preserves_name_hyphen(self):
        result = _clean_text("al-Assad spoke at the summit")
        assert "al-assad" in result

    def test_removes_orphan_leading_hyphen(self):
        # "- some text" style list bullets
        result = _clean_text("- Ceasefire announced - talks resumed")
        assert result.startswith("-") is False

    def test_removes_orphan_trailing_hyphen(self):
        result = _clean_text("ceasefire -")
        assert result.endswith("-") is False

    # --- Punctuation stripping ---

    def test_strips_commas(self):
        result = _clean_text("Russia, Ukraine, and Belarus")
        assert "," not in result

    def test_strips_periods(self):
        result = _clean_text("Talks ended. No deal reached.")
        assert "." not in result

    def test_strips_quotes(self):
        result = _clean_text('"Ceasefire imminent," said the minister')
        assert '"' not in result

    # --- Whitespace ---

    def test_collapses_multiple_spaces(self):
        result = _clean_text("Iran    nuclear   deal")
        assert "  " not in result

    def test_strips_leading_trailing_whitespace(self):
        result = _clean_text("  breaking news  ")
        assert result == result.strip()

    # --- Edge cases ---

    def test_empty_string_returns_empty(self):
        assert _clean_text("") == ""

    def test_non_ascii_preserved(self):
        # Arabic, Cyrillic, CJK proper nouns should survive
        result = _clean_text("Москва объявила о перемирии")
        assert len(result) > 0

    def test_all_boilerplate_returns_empty_or_short(self):
        result = _clean_text("(Reuters) - © 2025 Reuters")
        # After stripping, very little should remain
        assert len(result) < 20


class TestBuildCleanCorpus:

    def test_returns_string(self):
        result = build_clean_corpus("Iran talks", "Diplomats met in Vienna")
        assert isinstance(result, str)

    def test_title_repeated_title_weight_times(self):
        result = build_clean_corpus("ceasefire", "")
        # title repeated TITLE_WEIGHT times, joined by spaces
        tokens = result.split()
        assert tokens.count("ceasefire") == TITLE_WEIGHT

    def test_summary_appended_after_title(self):
        result = build_clean_corpus("ceasefire", "talks resumed in vienna")
        assert "ceasefire" in result
        assert "vienna" in result

    def test_empty_summary_uses_title_only(self):
        result = build_clean_corpus("Iran nuclear deal", "")
        assert "iran" in result
        assert "nuclear" in result

    def test_empty_title_uses_summary_only(self):
        result = build_clean_corpus("", "Talks resumed in Vienna")
        assert "vienna" in result

    def test_both_empty_returns_empty_string(self):
        assert build_clean_corpus("", "") == ""

    def test_none_title_handled_gracefully(self):
        # Models guarantee non-null, but defensive handling
        result = build_clean_corpus(None, "some summary")
        assert "summary" in result

    def test_none_summary_handled_gracefully(self):
        result = build_clean_corpus("some title", None)
        assert "title" in result

    def test_output_is_lowercase(self):
        result = build_clean_corpus("NATO Summit", "Ministers met in BRUSSELS")
        assert result == result.lower()

    def test_no_html_in_output(self):
        result = build_clean_corpus("<b>Breaking</b>", "<p>Talks &amp; ceasefire</p>")
        assert "<" not in result
        assert "&amp;" not in result

    def test_no_urls_in_output(self):
        result = build_clean_corpus("Story", "Full text at https://bbc.com/news/123")
        assert "https" not in result
        assert "bbc.com" not in result

    def test_title_weighted_more_than_summary(self):
        # A term appearing only in title should appear TITLE_WEIGHT times
        # A term appearing only in summary should appear once
        result = build_clean_corpus("exclusiveterm", "uniqueword")
        tokens = result.split()
        assert tokens.count("exclusiveterm") == TITLE_WEIGHT
        assert tokens.count("uniqueword") == 1
