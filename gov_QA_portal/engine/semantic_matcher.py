from utils.normalizer import normalize
from utils.logger import get_logger

log = get_logger(__name__)

# Synonym groups — any word in a group matches any other
SYNONYMS = [
    {"name", "full name", "your name", "applicant", "requestor", "requester"},
    {"email", "e-mail", "mail", "electronic mail"},
    {"phone", "telephone", "mobile", "cell", "contact number"},
    {"address", "street", "location", "mailing"},
    {"city", "town", "municipality"},
    {"state", "province", "region"},
    {"zip", "postal", "zipcode", "postcode"},
    {"company", "organization", "organisation", "firm", "business", "employer"},
    {"description", "details", "explain", "describe", "request", "information"},
    {"department", "division", "office", "bureau", "unit", "agency"},
    {"purpose", "reason", "use", "intended use", "why"},
    {"date", "when", "period", "time", "from", "to"},
]


class SemanticMatcher:
    """
    Fuzzy fallback matcher.
    If FIELD_MAP has no keyword match, tries synonym groups
    against sheet column names to find the best column.

    Usage:
        matcher = SemanticMatcher(sheet_columns)
        col     = matcher.match("applicant full name")
        # → "Name"
    """

    def __init__(self, sheet_columns: list):
        self.columns = sheet_columns
        self._col_normalized = {
            normalize(c): c for c in sheet_columns
        }

    def match(self, label: str) -> str | None:
        """
        Try to match a field label to a sheet column.

        Args:
            label : Normalized field label from the form

        Returns:
            Sheet column name or None
        """
        l = normalize(label)

        # ── Direct normalized match ──────────────────────
        for col_norm, col_orig in self._col_normalized.items():
            if l == col_norm or l in col_norm or col_norm in l:
                log.info(f"🔗 Direct match: '{label}' → '{col_orig}'")
                return col_orig

        # ── Synonym group match ──────────────────────────
        for group in SYNONYMS:
            label_matches_group = any(syn in l for syn in group)
            if not label_matches_group:
                continue

            for col_norm, col_orig in self._col_normalized.items():
                col_matches_group = any(syn in col_norm for syn in group)
                if col_matches_group:
                    log.info(
                        f"🔗 Synonym match: '{label}' → '{col_orig}' "
                        f"(via group: {group})"
                    )
                    return col_orig

        # ── Word overlap fallback ────────────────────────
        label_words = set(l.split())
        best_score  = 0
        best_col    = None

        for col_norm, col_orig in self._col_normalized.items():
            col_words = set(col_norm.split())
            overlap   = len(label_words & col_words)
            if overlap > best_score:
                best_score = overlap
                best_col   = col_orig

        if best_col and best_score > 0:
            log.info(
                f"🔗 Word overlap match: '{label}' → '{best_col}' "
                f"(score: {best_score})"
            )
            return best_col

        log.debug(f"❌ No match found for: '{label}'")
        return None