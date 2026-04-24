from harvest.language_normalizer import normalize_language_value

_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
)

_WORK_TYPE_MAP = {
    "article": "article",
    "book": "book",
    "book-chapter": "chapter",
    "chapter": "chapter",
    "dataset": "dataset",
    "preprint": "article",
    "review": "article",
    "editorial": "article",
    "letter": "article",
    "paratext": "article",
    "other": "other",
    "journal": "article",
}

_NAME_PARTICLES = frozenset({
    "da", "das", "de", "del", "della", "delle", "degli", "den", "der",
    "des", "di", "do", "dos", "du", "e",
    "el", "het", "la", "las", "le", "les", "lo", "los",
    "te", "ten", "ter",
    "al", "ben", "bin", "ibn",
    "van", "von",
})

_NAME_SUFFIXES = {
    "jr": "Jr.", "jr.": "Jr.", "junior": "Junior",
    "sr": "Sr.", "sr.": "Sr.", "senior": "Senior",
    "filho": "Filho", "filha": "Filha",
    "neto": "Neto", "neta": "Neta", "netto": "Netto",
    "sobrinho": "Sobrinho", "sobrinha": "Sobrinha",
    "ii": "II", "iii": "III", "iv": "IV", "v": "V",
}

def _deep_get(data, *keys, default=None):
    """Safely traverse nested dicts: ``_deep_get(d, "a", "b")`` → ``d["a"]["b"]``."""
    for key in keys:
        if not isinstance(data, dict):
            return default
        data = data.get(key)
        if data is None:
            return default
    return data

def _str_or_none(value):
    if value in (None, ""):
        return None
    return str(value).strip() or None


def _normalized_lang_pair(raw):
    """Return ``(normalized_lower, base_code)`` for matching ``*_with_lang`` entries."""
    if raw in (None, ""):
        return None, None
    s = str(raw).strip()
    norm = normalize_language_value(s)
    norm_lc = norm.strip().lower()
    base = norm_lc.split("-")[0].split("_")[0]
    return norm_lc, base


def _split_matches_by_lang(items, field_name, lang_code, *, value_key=None):
    """Split ``*_with_lang`` entries into exact-match vs base-language-match lists."""
    if not isinstance(items, list):
        return [], []
    requested, requested_base = _normalized_lang_pair(lang_code)

    if not requested:
        return [], []

    key = value_key or field_name
    exact, base = [], []

    for item in items:
        if not isinstance(item, dict):
            continue
        value = item.get(key)
        if value in (None, ""):
            continue

        item_norm, item_base = _normalized_lang_pair(str(item.get("language") or ""))
        if not item_norm:
            continue

        if item_norm == requested:
            exact.append(value)
        elif item_base == requested_base:
            base.append(value)

    return exact, base


def _pick_localized(source, field_name, lang_code, *, value_key=None):
    """Pick a localised scalar: try ``<field>_with_lang`` first, fall back to ``<field>``."""
    items = source.get(f"{field_name}_with_lang")
    exact, base = _split_matches_by_lang(items, field_name, lang_code, value_key=value_key)
    return _str_or_none(exact[0] if exact else base[0] if base else source.get(field_name))


def _tokenize_name(name):
    """Split a name string into tokens, isolating commas as separate tokens."""
    return name.replace(",", " , ").split()


def _extract_suffix(tokens):
    """Pop the last token if it is a known name suffix; return canonical form."""
    if tokens and tokens[-1].lower() in _NAME_SUFFIXES:
        return _NAME_SUFFIXES[tokens.pop().lower()]
    return None


def _strip_trailing_commas(tokens):
    """Remove trailing comma tokens left after suffix extraction."""
    while tokens and tokens[-1] == ",":
        tokens.pop()


def _split_leading_particles(tokens):
    """Pop leading particle words from *tokens*, keeping at least one word."""
    particles = []
    while len(tokens) > 1 and tokens[0].lower() in _NAME_PARTICLES:
        particles.append(tokens.pop(0))
    return " ".join(particles) if particles else None


def _split_trailing_particles(tokens):
    """Extract particle words between given names and the last token (family)."""
    particles = []
    i = len(tokens) - 2
    while i > 0 and tokens[i].lower() in _NAME_PARTICLES:
        particles.insert(0, tokens[i])
        i -= 1
    return " ".join(particles) if particles else None, i


def _classify_particle(particle):
    """Lowercase-initial → dropping-particle; uppercase → non-dropping-particle."""
    return "dropping-particle" if particle[0].islower() else "non-dropping-particle"


def _build_csl_name(*, family=None, given=None, particle=None, suffix=None):
    """Assemble a CSL-JSON name dict from already-parsed parts."""
    if not family and not given:
        return None
    result = {}
    if family:
        result["family"] = family
    if given:
        result["given"] = given
    if particle:
        result[_classify_particle(particle)] = particle
    if suffix:
        result["suffix"] = suffix
    return result


def _parse_comma_name(tokens):
    """Parse ``Family, Given`` format → *(family, given, particle)*.

    Leading particles in the family segment (e.g. "da Silva, João")
    are extracted automatically.
    """
    comma_idx = tokens.index(",")
    family_tokens = tokens[:comma_idx]
    given_tokens = [t for t in tokens[comma_idx + 1:] if t != ","]

    particle = _split_leading_particles(family_tokens)
    family = " ".join(family_tokens) if family_tokens else None
    given = " ".join(given_tokens) if given_tokens else None
    return family, given, particle


def _parse_natural_name(tokens):
    """Parse ``Given [particles] Family`` format → *(family, given, particle)*."""
    if len(tokens) == 1:
        return tokens[0], None, None

    family = tokens[-1]
    particle, boundary = _split_trailing_particles(tokens)
    given = " ".join(tokens[: boundary + 1])
    return family, given, particle


def _parse_name_parts(raw_name):
    """Best-effort split of a display name into CSL-JSON name-variable parts.

    Handles formats like::

      "João da Silva Jr."          → given / dropping-particle / family / suffix
      "da Silva, João"             → dropping-particle / family / given
      "Van Dyck, Peter"            → non-dropping-particle / family / given
      "Maria de los Santos Neto"   → given / dropping-particle / family / suffix
    """
    name = str(raw_name).strip()
    if not name:
        return None

    tokens = _tokenize_name(name)
    suffix = _extract_suffix(tokens)
    _strip_trailing_commas(tokens)

    if not tokens:
        return {"literal": name}

    if "," in tokens:
        family, given, particle = _parse_comma_name(tokens)
    else:
        family, given, particle = _parse_natural_name(tokens)

    return _build_csl_name(
        family=family or name,
        given=given,
        particle=particle,
        suffix=suffix,
    )


def _parse_author(authorship):
    if not isinstance(authorship, dict):
        return None
    name = _str_or_none(authorship.get("name"))
    if not name:
        return None
    return _parse_name_parts(name)


class CSLSourceExtractor:
    """Extract CSL-JSON fields from an indexed document ``_source`` dict.

    The instance is bound to a ``source`` dict and a ``language``; each public
    extractor method returns one CSL field resolved with respect to that
    language (when the field has ``*_with_lang`` translations).
    """

    def __init__(self, source, language=None):
        self.source = source if isinstance(source, dict) else {}
        self.language = language

    @property
    def currently_language(self):
        return self.language

    def title(self):
        return _pick_localized(self.source, "title", self.language) or "Untitled"

    def csl_type(self):
        return self.source.get("type")

    def publication_year(self):
        return self.source.get("publication_year")

    def issued(self):
        try:
            return {"date-parts": [[int(str(self.publication_year())[:4])]]}
        except (TypeError, ValueError):
            return None

    def authors(self):
        return [
            author
            for auth in (self.source.get("authorships") or [])
            if (author := _str_or_none(auth.get("name"))) is not None
        ]

    def authors_with_given_family(self):
        return [
            author
            for auth in (self.source.get("authorships") or [])
            if (author := _parse_author(auth)) is not None
        ]

    def doi(self):
        return self.normalize_doi(_deep_get(self.source, "ids", "doi"))

    def url(self, doi=None):
        if doi:
            return f"https://doi.org/{doi}"

        url = self.source.get("content_url")
        if isinstance(url, list) and url:
            url = url[0]
        return _str_or_none(url) or _str_or_none(_deep_get(self.source, "sources", "url"))

    def source_title(self):
        sources_list = self.source.get("sources")
        if isinstance(sources_list, list) and sources_list:
            title = _deep_get(sources_list[0], "title")
            if title:
                return str(title)
        return ""

    def volume(self):
        bib = self.source.get("biblio") or {}
        if not isinstance(bib, dict):
            return None
        return _str_or_none(bib.get("volume"))

    def issue(self):
        bib = self.source.get("biblio") or {}
        if not isinstance(bib, dict):
            return None
        return _str_or_none(bib.get("issue"))

    def pages(self):
        bib = self.source.get("biblio") or {}
        if not isinstance(bib, dict):
            return None

        if bib.get("pages"):
            return str(bib["pages"])

        first, last = _str_or_none(bib.get("first_page")), _str_or_none(bib.get("last_page"))
        if first and last:
            return f"{first}-{last}"
        return first or last

    def publisher(self):
        return _str_or_none(
            _deep_get(self.source, "primary_location", "source", "host_organization_name"),
        )

    def source_language(self):
        return _str_or_none(self.source.get("language"))

    @staticmethod
    def normalize_doi(doi):
        s = _str_or_none(doi)
        if not s:
            return None
        for prefix in _DOI_PREFIXES:
            if s.lower().startswith(prefix.lower()):
                return s[len(prefix):]
        return s
