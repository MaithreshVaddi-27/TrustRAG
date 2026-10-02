"""
TRUSTRAG — Text Preprocessing, Lexical Analysis, Zoning, and Stemming Pipeline.

Provides:
  - Text normalization & de-hyphenation (repairing PDF artifact breaks)
  - Canonical rule-based Porter Stemmer (Martin Porter, 1980)
  - Configurable stopwords (core grammatical + conversational query-noise filters)
  - Document Zoning (Title, Header, Summary, Body, Metadata) with zone-weight scoring
  - Multi-word N-Gram (Bigram) phrase extraction
"""

from __future__ import annotations

import functools
import re
import threading
import unicodedata
from enum import StrEnum

# ─── Contraction Mapping ──────────────────────────────────────────────────────

CONTRACTIONS: dict[str, str] = {
    "can't": "can not",
    "cannot": "can not",
    "won't": "will not",
    "n't": " not",
    "'re": " are",
    "'s": " is",
    "'d": " would",
    "'ll": " will",
    "'ve": " have",
    "'m": " am",
}

# ─── Standard IR & Query Noise Stopwords ─────────────────────────────────────

CORE_STOPWORDS: set[str] = {
    "a",
    "about",
    "above",
    "after",
    "again",
    "against",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "aren't",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "can",
    "can't",
    "cannot",
    "could",
    "couldn't",
    "did",
    "didn't",
    "do",
    "does",
    "doesn't",
    "doing",
    "don't",
    "down",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "had",
    "hadn't",
    "has",
    "hasn't",
    "have",
    "haven't",
    "having",
    "he",
    "he'd",
    "he'll",
    "he's",
    "her",
    "here",
    "here's",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "how's",
    "i",
    "i'd",
    "i'll",
    "i'm",
    "i've",
    "if",
    "in",
    "into",
    "is",
    "isn't",
    "it",
    "it's",
    "its",
    "itself",
    "let's",
    "me",
    "more",
    "most",
    "mustn't",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "ought",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "same",
    "shan't",
    "she",
    "she'd",
    "she'll",
    "she's",
    "should",
    "shouldn't",
    "so",
    "some",
    "such",
    "than",
    "that",
    "that's",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "there's",
    "these",
    "they",
    "they'd",
    "they'll",
    "they're",
    "they've",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "very",
    "was",
    "wasn't",
    "we",
    "we'd",
    "we'll",
    "we're",
    "we've",
    "were",
    "weren't",
    "what",
    "what's",
    "when",
    "when's",
    "where",
    "where's",
    "which",
    "while",
    "who",
    "who's",
    "whom",
    "why",
    "why's",
    "with",
    "won't",
    "would",
    "wouldn't",
    "you",
    "you'd",
    "you'll",
    "you're",
    "you've",
    "your",
    "yours",
    "yourself",
    "yourselves",
}

# Conversational query fillers filtered out during query-time sparse search
# so search weights focus on topical content words rather than conversational wrappers
QUERY_NOISE_STOPWORDS: set[str] = {
    "tell",
    "please",
    "explain",
    "describe",
    "show",
    "summary",
    "summarize",
    "give",
    "detail",
    "details",
    "information",
    "document",
    "know",
    "like",
    "help",
    "provide",
    "list",
    "find",
    "mean",
    "meaning",
    "regard",
    "regarding",
    "discuss",
    "brief",
    "briefly",
}


def get_stopwords(include_query_noise: bool = False) -> set[str]:
    """Return stopword set, optionally including conversational query noise."""
    if include_query_noise:
        return CORE_STOPWORDS | QUERY_NOISE_STOPWORDS
    return CORE_STOPWORDS


# ─── Document Zoning ─────────────────────────────────────────────────────────


class ZoneType(StrEnum):
    """Document functional zones for Information Retrieval zone indexing and scoring."""

    TITLE = "title"
    HEADER = "header"
    SUMMARY = "summary"
    BODY = "body"
    METADATA = "metadata"


# Zone weight multiplier boosts for sparse BM25 index scoring
# Matches in Title and Header zones represent higher topical salience
ZONE_WEIGHT_BOOSTS: dict[str, float] = {
    ZoneType.TITLE.value: 2.0,
    ZoneType.HEADER.value: 1.5,
    ZoneType.SUMMARY.value: 1.3,
    ZoneType.BODY.value: 1.0,
    ZoneType.METADATA.value: 0.8,
}


def detect_chunk_zone(text: str, page: int = 1) -> str:
    """
    Detect the functional zone of a text chunk:
      - title: Page 1 document title or structural outline block
      - header: Section headers, topic titles, markdown headings
      - metadata: Leading key/value front-matter (dates, versions, ids, authors)
      - summary: Abstract, summary, overview sections
      - body: Standard paragraph and explanatory content

    Detection is STRUCTURAL, never subject-specific. An earlier revision
    matched literal keywords ("UNIT-", "CHAPTER", "COURSE", "SYLLABUS",
    "ISBN:", "DOI:", "effective from"), which silently classified every
    non-textbook, non-policy corpus as BODY — the zone weights below then
    never applied. Code, contracts, papers and prose all use the same shapes:
    a short first-page title line, and a leading `label: value` field.
    """
    text_stripped = text.strip()
    if not text_stripped:
        return ZoneType.BODY.value

    first_lines = text_stripped.split("\n")[:3]
    first_text = " ".join(first_lines).strip()
    first_upper = first_text.upper()
    first_line = first_lines[0].strip()

    # 1. Metadata Zone: a leading `label: value` front-matter field. Checked
    #    BEFORE the title test — a `label: value` line is front-matter by
    #    construction and is never a document title, whereas a short
    #    capitalized line like "Effective: 2026-01-01" would otherwise look
    #    exactly like a one-word Title Case title. Tested on the FIRST LINE
    #    only: a field is a single line, and joining following lines into the
    #    value would defeat the value-shape checks below.
    if _looks_like_metadata_field(first_line):
        return ZoneType.METADATA.value

    # 2. Title Zone: a structural outline marker, or a page-1 title line.
    #    Outline markers require a section NUMBER and must lead the line, and a
    #    heading does not end in a period — which is what separates
    #    "CHAPTER 3 Methods" from "Section 12 of the agreement applies."
    if page == 1 and (
        (not first_line.endswith(".") and _OUTLINE_MARKER_RE.match(first_upper))
        or _looks_like_title_line(first_line)
    ):
        return ZoneType.TITLE.value

    # 3. Summary Zone
    if any(first_text.lower().startswith(p) for p in _SUMMARY_PREFIXES):
        return ZoneType.SUMMARY.value

    # 4. Header Zone: Markdown # headers or short all-caps topic lines
    if re.match(r"^(?:#+\s+|[A-Z0-9\s:\--]{4,50}\n)", text_stripped):
        return ZoneType.HEADER.value

    return ZoneType.BODY.value


# Structural outline markers. These are section-numbering conventions shared by
# textbooks, specifications, contracts and manuals — kept because they are
# structural, not because any one subject is assumed. Two constraints keep
# them from firing on ordinary prose: a NUMBER is required (a bare substring
# test for "SECTION" would fire on the English word "section"), and the marker
# must LEAD the line (an outline marker introduces a document's structure, so
# "Section 12 of the agreement applies." is a sentence, not an outline).
_OUTLINE_MARKER_RE = re.compile(
    r"^(?:#{1,6}\s*)?"
    r"(?:UNIT|CHAPTER|SECTION|PART|APPENDIX|ARTICLE|CLAUSE|EXHIBIT)"
    r"[\s\-#]*(?:[0-9]+|[IVXLC]+)\b"
    r"|^\s*SYLLABUS\b"
)

# Leading `label: value` field. Label is 2-28 word-ish chars; value must look
# structured (date / version / hash / id / number), which keeps ordinary prose
# that happens to contain a colon out of the metadata zone.
_METADATA_FIELD_RE = re.compile(r"^[A-Za-z][A-Za-z ._/&-]{1,27}:\s*(\S.*)$")
_METADATA_VALUE_RE = re.compile(
    r"^(?:"
    r"\d{4}-\d{2}-\d{2}"  # ISO date
    r"|\d{1,2}[/.]\d{1,2}[/.]\d{2,4}"  # other date shapes
    r"|v?\d+(?:\.\d+)+"  # semantic version
    r"|[0-9a-f]{7,40}"  # short hash / hex id
    r"|\d[\w.:/-]*"  # bare identifier or number
    r")\s*$",
    re.IGNORECASE,
)


def _looks_like_metadata_field(line: str) -> bool:
    """True when a leading line is front-matter (`label: value`), not prose.

    Two independent signals, either sufficient:
      1. the value itself is structured (date / version / hash / number); or
      2. the line is a short, single-clause field — a brief capitalized label
         followed by a brief value.
    A long sentence beginning "Note:" fails both and stays BODY.
    """
    match = _METADATA_FIELD_RE.match(line.strip())
    if not match:
        return False
    label = line.split(":", 1)[0].strip()
    value = match.group(1).strip()
    if not value or len(value) > 80:
        return False
    if _METADATA_VALUE_RE.match(value):
        return True
    # Short field line: at most 3 words on each side of the colon.
    if len(label.split()) <= 3 and len(value.split()) <= 6 and not value.endswith("."):
        return True
    return False


# Section labels that introduce prose, not a metadata field.
_SUMMARY_PREFIXES = ("summary:", "abstract:", "overview:", "executive summary:")


def _looks_like_title_line(line: str) -> bool:
    """True when a first-page line reads as a document title rather than prose.

    Shape-based: short, no terminal sentence punctuation, not a `label: value`
    field, and either ALL CAPS or Title Case. Works for "Acme Corp Refund
    Policy", "Getting Started", "ORDER OF SERVICE", and "System Design
    Document" alike.
    """
    if not line or len(line) > 120:
        return False
    if ":" in line:
        return False  # front-matter field or prose with a clause, never a title
    if line.endswith("."):
        return False
    words = line.split()
    if len(words) > 14:
        return False
    if not any(c.isalpha() for c in line):
        return False
    if line.upper() == line and len(line) > 3:
        return True
    # Title Case: most words start uppercase (ignoring small connective words).
    minor = {"a", "an", "and", "as", "at", "by", "for", "in", "of", "on", "or", "the", "to"}
    significant = [w for w in words if w.lower().strip(".,:;") not in minor]
    if not significant:
        return False
    return sum(1 for w in significant if w[:1].isupper()) >= max(1, len(significant) - 1)


# ─── Text Normalization ───────────────────────────────────────────────────────


def normalize_text(text: str) -> str:
    """
    Perform lexical normalization on raw text:
      - NFKD Unicode normalization
      - Stripping PDF bullet characters and non-printable symbols (e.g. \uf0d8, \u2022)
      - Repairing hyphenated line breaks (e.g. "docu-\\nment" -> "documentation")
      - Expanding contractions
      - Normalizing irregular whitespace
    """
    if not text:
        return ""

    # 1. Unicode NFKD normalization
    normalized = unicodedata.normalize("NFKD", text)

    # 2. Remove non-printable and private-use symbols (frequent in PDF slide bullets)
    normalized = re.sub(r"[\uf000-\uffff\u2022\u2023\u25cf\u25cb\u25aa\u25ab]", " ", normalized)

    # 3. Repair line-break hyphenations: "infor-\nmation" -> "information"
    normalized = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", normalized)

    # 4. Expand contractions
    text_lower = normalized.lower()
    for contraction, expansion in CONTRACTIONS.items():
        text_lower = text_lower.replace(contraction, expansion)

    # 5. Collapse excessive horizontal whitespace, but PRESERVE line breaks.
    # Load-bearing: section/table heuristics (chunking strategies) and header
    # detection (detect_chunk_zone) split on "\n". Collapsing newlines to
    # spaces silently disables all of them — and token output is identical
    # either way since the lexer treats every whitespace run as a separator.
    cleaned = re.sub(r"[ \t\r\f\v]+", " ", text_lower)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


# ─── Porter Stemmer Implementation ────────────────────────────────────────────


class PorterStemmer:
    """
    Canonical rule-based Porter Stemmer for English (Martin Porter, 1980).

    Reduces inflected and derived words to their base morphological stem.
    Guarantees consistent, stateless stemming for both index and query representations.
    """

    def __init__(self) -> None:
        self.b = ""
        self.k = 0
        self.k0 = 0
        self.j = 0

    def _cons(self, i: int) -> bool:
        if self.b[i] in "aeiou":
            return False
        if self.b[i] == "y":
            if i == self.k0:
                return True
            return not self._cons(i - 1)
        return True

    def _m(self) -> int:
        n = 0
        i = self.k0
        while True:
            if i > self.j:
                return n
            if not self._cons(i):
                break
            i += 1
        i += 1
        while True:
            while True:
                if i > self.j:
                    return n
                if self._cons(i):
                    break
                i += 1
            i += 1
            n += 1
            while True:
                if i > self.j:
                    return n
                if not self._cons(i):
                    break
                i += 1
            i += 1

    def _vowelinstem(self) -> bool:
        return any(not self._cons(i) for i in range(self.k0, self.j + 1))

    def _doublec(self, i: int) -> bool:
        if i < self.k0 + 1:
            return False
        if self.b[i] != self.b[i - 1]:
            return False
        return self._cons(i)

    def _cvc(self, i: int) -> bool:
        if i < self.k0 + 2 or not self._cons(i) or self._cons(i - 1) or not self._cons(i - 2):
            return False
        ch = self.b[i]
        return ch not in "wxy"

    def _ends(self, s: str) -> bool:
        length = len(s)
        o = self.k - length + 1
        if o < self.k0:
            return False
        if self.b[o : self.k + 1] != s:
            return False
        self.j = self.k - length
        return True

    def _setto(self, s: str) -> None:
        length = len(s)
        o = self.j + 1
        self.b = self.b[:o] + s + self.b[o + length :]
        self.k = self.j + length

    def _r(self, s: str) -> None:
        if self._m() > 0:
            self._setto(s)

    def _step1ab(self) -> None:
        if self.b[self.k] == "s":
            if self._ends("sses"):
                self.k -= 2
            elif self._ends("ies"):
                self._setto("i")
            elif self.b[self.k - 1] != "s":
                self.k -= 1
        if self._ends("eed"):
            if self._m() > 0:
                self.k -= 1
        elif (self._ends("ed") or self._ends("ing")) and self._vowelinstem():
            self.k = self.j
            if self._ends("at"):
                self._setto("ate")
            elif self._ends("bl"):
                self._setto("ble")
            elif self._ends("iz"):
                self._setto("ize")
            elif self._doublec(self.k):
                self.k -= 1
                ch = self.b[self.k]
                if ch in "lsz":
                    self.k += 1
            elif self._m() == 1 and self._cvc(self.k):
                self._setto("e")

    def _step1c(self) -> None:
        if self._ends("y") and self._vowelinstem():
            self.b = self.b[: self.k] + "i" + self.b[self.k + 1 :]

    def _step2(self) -> None:
        if self.k <= self.k0:
            return
        c = self.b[self.k - 1]
        if c == "a":
            if self._ends("ational"):
                self._r("ate")
            elif self._ends("tional"):
                self._r("tion")
        elif c == "c":
            if self._ends("enci"):
                self._r("ence")
            elif self._ends("anci"):
                self._r("ance")
        elif c == "e":
            if self._ends("izer"):
                self._r("ize")
        elif c == "l":
            if self._ends("bli"):
                self._r("ble")
            elif self._ends("alli"):
                self._r("al")
            elif self._ends("entli"):
                self._r("ent")
            elif self._ends("eli"):
                self._r("e")
            elif self._ends("ousli"):
                self._r("ous")
        elif c == "o":
            if self._ends("ization"):
                self._r("ize")
            elif self._ends("ation") or self._ends("ator"):
                self._r("ate")
        elif c == "s":
            if self._ends("alism"):
                self._r("al")
            elif self._ends("iveness"):
                self._r("ive")
            elif self._ends("fulness"):
                self._r("ful")
            elif self._ends("ousness"):
                self._r("ous")
        elif c == "t":
            if self._ends("aliti"):
                self._r("al")
            elif self._ends("iviti"):
                self._r("ive")
            elif self._ends("biliti"):
                self._r("ble")
        elif c == "g" and self._ends("logi"):
            self._r("log")

    def _step3(self) -> None:
        if self.k <= self.k0:
            return
        c = self.b[self.k]
        if c == "e":
            if self._ends("icate"):
                self._r("ic")
            elif self._ends("ative"):
                self._r("")
            elif self._ends("alize"):
                self._r("al")
        elif c == "i":
            if self._ends("iciti"):
                self._r("ic")
        elif c == "l":
            if self._ends("ical"):
                self._r("ic")
            elif self._ends("ful"):
                self._r("")
        elif c == "s" and self._ends("ness"):
            self._r("")

    def _step4(self) -> None:
        if self.k <= self.k0:
            return
        c = self.b[self.k - 1]
        if c == "a":
            if not self._ends("al"):
                return
        elif c == "c":
            if not (self._ends("ance") or self._ends("ence")):
                return
        elif c == "e":
            if not self._ends("er"):
                return
        elif c == "i":
            if not self._ends("ic"):
                return
        elif c == "l":
            if not (self._ends("able") or self._ends("ible")):
                return
        elif c == "n":
            n_suffixes = ("ant", "ement", "ment", "ent")
            if not any(self._ends(s) for s in n_suffixes):
                return
        elif c == "o":
            if (self._ends("ion") and self.j >= self.k0 and self.b[self.j] in "st") or self._ends(
                "ou"
            ):
                pass
            else:
                return
        elif c == "s":
            if not self._ends("ism"):
                return
        elif c == "t":
            if not (self._ends("ate") or self._ends("iti")):
                return
        elif c == "u":
            if not self._ends("ous"):
                return
        elif c == "v":
            if not self._ends("ive"):
                return
        elif c == "z":
            if not self._ends("ize"):
                return
        else:
            return
        if self._m() > 1:
            self.k = self.j

    def _step5(self) -> None:
        self.j = self.k
        if self.b[self.k] == "e":
            a = self._m()
            if a > 1 or (a == 1 and not self._cvc(self.k - 1)):
                self.k -= 1
        if self.b[self.k] == "l" and self._doublec(self.k) and self._m() > 1:
            self.k -= 1

    def stem(self, word: str) -> str:
        """Stem a single word token."""
        word_clean = word.strip().lower()
        if len(word_clean) <= 2:
            return word_clean
        self.b = word_clean
        self.k = len(word_clean) - 1
        self.k0 = 0
        self._step1ab()
        self._step1c()
        self._step2()
        self._step3()
        self._step4()
        self._step5()
        return self.b[self.k0 : self.k + 1]


# Use threading.local() so each thread has its own PorterStemmer instance.
# The stemmer has mutable instance state (self.b, self.k, etc.) that is not
# safe to share across threads — concurrent calls corrupt stemmer output.
_local = threading.local()


def _get_stemmer() -> PorterStemmer:
    """Return the current thread's PorterStemmer, creating it on first use."""
    if not hasattr(_local, "stemmer"):
        _local.stemmer = PorterStemmer()
    return _local.stemmer


# Bound LRU to 8k to prevent idle RSS creep (was 32768 — English vocab is smaller)
@functools.lru_cache(maxsize=8192)
def stem_word(word: str) -> str:
    """Convenience helper to stem a single word using thread-local PorterStemmer with LRU cache."""
    return _get_stemmer().stem(word)


# ─── N-Grams (Bigrams) ────────────────────────────────────────────────────────


def extract_ngrams(tokens: list[str], n: int = 2) -> list[str]:
    """Generate n-gram compound phrases from a list of clean tokens."""
    if len(tokens) < n:
        return []
    return [f"{tokens[i]}_{tokens[i + 1]}" for i in range(len(tokens) - n + 1)]


# ─── Lexical Analysis & Tokenization ──────────────────────────────────────────


def lexical_analyze(
    text: str,
    stem: bool = True,
    is_query: bool = False,
    include_bigrams: bool = False,
) -> list[str]:
    """
    Complete lexical analysis pipeline:
      1. Text Normalization (cleaning, de-hyphenation, contraction expansion)
      2. Token extraction (alphanumeric words, preserving hyphenated terms like 'n-gram')
      3. Stopword filtering (core or query-noise)
      4. Porter stemming (if stem=True)
      5. Optional bigram compound extraction (e.g. 'invert_file', 'data_structur')
    """
    clean_text = normalize_text(text)
    if not clean_text:
        return []

    # Match words and compound terms: letters, digits, and optional interior hyphens
    tokens = re.findall(r"\b[a-z0-9]+(?:-[a-z0-9]+)*\b", clean_text)

    # Use query noise filter when analyzing search queries
    stopwords = get_stopwords(include_query_noise=is_query)

    # Filter stopwords and very short noise (single character unless numeric/meaningful)
    filtered = [t for t in tokens if t not in stopwords and (len(t) > 1 or t.isdigit())]

    stemmed = [_get_stemmer().stem(t) for t in filtered] if stem else filtered

    if not include_bigrams or len(stemmed) < 2:
        return stemmed

    # Combine unigrams with bigrams for enhanced compound matching
    bigrams = extract_ngrams(stemmed, n=2)
    return stemmed + bigrams
