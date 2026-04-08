"""
semantic_matcher.py
===================
Maps a raw form-field label to the correct Google Sheet column name.

Resolution order:
  1. Synonym lookup  (pre-built index, O(n) scan)
  2. Fuzzy matching  (rapidfuzz token_sort_ratio ≥ threshold)
"""

from rapidfuzz import fuzz, process


class SemanticMatcher:

    SYNONYMS: dict[str, list[str]] = {

        "Company": [
            "company", "organization", "business name", "company name",
            "company/organization", "your business/organization",
            "business / organization name", "company/ business/ organization",
            "organization (if any)", "organization/business",
            "name/ organization requesting",
        ],
        # ── Name ──────────────────────────────────────────────────────
        "First Name": [
            "first name", "given name", "forename", "first name of requestor",
            "requestor first name",
        ],
        "Last Name": [
            "last name", "surname", "family name", "requestor last name",
        ],
        "Name": [
            "full name", "your name", "requester name", "requestor name",
            "individual requesting", "name of requester", "name of requesting party",
            "name of individual", "name of person requesting", "request made by",
            "contact/requestor", "first and last name", "representing",
            "requestor's name", "name/ organization requesting", "name (first, last)",
            "name (last, first",
        ],

        # ── Email ──────────────────────────────────────────────────────
        "Email": [
            "email", "email address", "e-mail", "electronic mail",
            "contact email", "delivery email", "your email address",
            "reply email", "requestor email", "email of requesting party",
        ],

        # ── Phone ──────────────────────────────────────────────────────
        "Phone": [
            "phone", "telephone", "mobile", "contact number", "contact phone",
            "phone number of requesting party", "business hours telephone",
            "cell number", "cell phone", "home phone",
        ],
        "Fax": ["fax number", "fax"],

        # ── Address ────────────────────────────────────────────────────
        "Street Address": [
            "street address", "mailing address", "residential address",
            "address line 1", "physical address", "street number and name",
            "requestor address", "address pertaining to this request",
            "address associated with request", "mailing address 1", "address1",
            "address 1", "address of requester",
        ],
        "Street Address 2": [
            "address line 2", "address 2", "address2", "apt./suite",
        ],
        "City":  ["city", "city:", "town"],
        "State": ["state", "state:", "province", "state / province / region"],
        "Zip":   ["zip", "zipcode", "postal", "zip code", "postal / zip code"],

        # # ── Company / Org ──────────────────────────────────────────────
        # "Company": [
        #     "company", "organization", "business name", "company name",
        #     "company/organization", "your business/organization",
        #     "business / organization name", "company/ business/ organization",
        #     "organization (if any)", "organization/business",
        # ],

        # ── Department ─────────────────────────────────────────────────
        "Department": [
            "department", "agency", "department holding", "department of requested records",
            "town department", "please select the department", "what department",
        ],

        # ── Description ────────────────────────────────────────────────
        "Description": [
            "describe the records", "records you are requesting",
            "public records description", "description of request",
            "records requested", "documents requested", "information requested",
            "message", "question / comment", "subject",
        ],
    }

    def __init__(self, sheet_columns: list[str]):
        self._column_map: dict[str, str] = {
            self._norm(col): col for col in sheet_columns
        }
        self._normalized_columns = list(self._column_map.keys())

        # Pre-build: phrase → original column name
        self._synonym_index: dict[str, str] = {}
        for canonical, phrases in self.SYNONYMS.items():
            norm_c = self._norm(canonical)
            if norm_c in self._column_map:
                real_col = self._column_map[norm_c]
                for phrase in phrases:
                    self._synonym_index[phrase] = real_col

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────

    def match(self, label: str, threshold: int = 82) -> str | None:
        label = self._norm(label)

        # 1. Synonym lookup
        for phrase, col in self._synonym_index.items():
            if phrase in label:
                return col

        # 2. Fuzzy fallback
        if not self._normalized_columns:
            return None

        result = process.extractOne(
            label, self._normalized_columns, scorer=fuzz.token_sort_ratio
        )
        if result:
            match_key, score, _ = result
            if score >= threshold:
                return self._column_map[match_key]

        return None

    @staticmethod
    def _norm(text: str) -> str:
        if not text:
            return ""
        return text.lower().replace("*", "").replace(":", "").strip()
