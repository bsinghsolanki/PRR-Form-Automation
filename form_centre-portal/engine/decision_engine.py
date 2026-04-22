class DecisionEngine:
    """
    Determines the correct value/action for every known field pattern.

    Return values from decide():
      "__TODAY__"        → fill with today's date
      "__SIGN__"         → fill with requester full name (row["name"])
      "__DESCRIPTION__"  → fill with records description (row["description"])
      "0"                → fill fee threshold text fields with zero
      A string           → visible option text to select/click
      None               → no rule matched; fall through to sheet-data lookup
    """

    # ── Department priority (first match wins) ───────────────────────────
    DEPARTMENT_PRIORITY = [
        "purchasing",
        "city clerk",
        "public records",
        "public records act (pra) requests",
        "public records administration",
        "public records office",
        "public records office / other departments",
        "public records officer",
        "office of open records",
        "city treasurer",
        "cm/ca/city council",
        "city clerk department",
        "city clerk shared",
        "city clerk's department",
        "city clerk's office",
        "city clerk-all non-police related data",
        "city clerk/city manager's office",
        "city clerk/public records office",
        "secretary of the board",
        "recorder's office",
        "recorder-county clerk",
        "records management",
        "records manager",
        "accounting",
        "administration",
        "administration / city clerk",
        "administration department",
        "administrator's offfice",
        "assessor-recorder",
        "assessor-recorder-county clerk",
        "assessor/clerk-recorder",
        "assessor/recorder",
        "assessors",
        "borough clerk",
        "city council",
        "city council - clerk of council",
        "city manager",
        "city manager's department",
        "city manager's office",
        "city records",
        "city secretary",
        "clerk",
        "clerk of the board",
        "clerk recorder",
        "clerk treasurer's office",
        "clerk of commission",
        "county board",
        "county clerk",
        "department of finance",
        "deputy city clerk",
        "division of purchases",
        "finance",
        "finance & administrative services",
        "finance & records",
        "finance - treasury",
        "general",
        "records",
        "general city record requests",
        "general city records",
        "municipal clerk",
        "office of the county clerk",
        "other",
        "all other departments",
        "purchasing & contracting",
        "purchasing & fleet",
        "purchasing department",
        "purchasing office",
        "unknown",
    ]

    _DELIVERY_LABELS = [
        "delivery preference",
        "delivery notification",
        "delivery:",
        "preferred method of contact",
        "preferred method for access",
        "preferred method of delivery",
        "preferred delivery",
        "prefered delivery",
        "method of inspection",
        "receive my records",
        "receive the records",
        "receive the information",
        "receive the responsive data",
        "receive your records",
        "receive or view the records",
        "obtain the records",
        "request fulfilled",
        "prefer to receive",
        "prefer the requested record",
        "how would you like to receive",
        "how would you prefer to receive",
        "i would like to",
        "i am requesting an opportunity",   # NY FOIL "obtain copies" radio
        "i request to receive my records by",
        "i request to:",
        "i want to",
        "check one to indicate",
        "check one: i request",
        "select the method",
        "access to data in the following way",
        "contact preference",
        "requestor response preference",
        "select action below",
        "response method",
        "not readily available",
        "indicate the desired format",      # "Indicate the desired format for receiving..."
        "format for receiving",             # same field
        "desired format",                   # same field short form
        "indicate how you would like",      # similar fields on other forms
        "format of records",
        "please advise which you would like",
        "would you like to do",
    ]

    _EMAIL_OPTS = [
        "email the records",
        "scans via email",
        "copies via e-mail",
        "emailed copies",
        "electronic copy of record requested",
        "by email",
        "via email",
        "e-mail",
        "email",
        "electronic",
        "have copies of public records",
        "receive record copies",
        "obtain copies",
        "copies",
    ]

    _LEGAL_KEYWORDS = [
        "convicted", "offense",
        "legal proceeding", "n.j.s.a. 2c:28-3",
    ]

    _AGREEMENT_LABELS = [
        "do you agree?",
        "by checking the \"i agree\"",
        "by checking this box",
        "electronic signature agreement",
        "i agree to pay",
        "i have read and agree",
        "i understand the above",
        "i understand that obtaining",
        "i also understand that the town",
        "full name and contact information is true",
        "verification",
        "acknowledgement",
        "acknowledgment",           # US spelling (single e)
        "contact information requirements",
        "agree to pay up to",
        "request information statement",
        "please check one stating that you have or have not read",
        "have you accessed and read",
        "ada compliance",
        "site policy",
        "penalty",
        "i certify",
        "i acknowledge",                    # "I acknowledge that copying fees..."
        "i understand that a deposit",      # "I understand that a deposit may be required"
        "i understand that",                # generic understanding acknowledgement
        "nonlitigation",                    # "CERTIFICATION* Nonlitigation affiliation"
        "all boxes must be checked",        # instruction line on same form
        "in accordance with",               # Alaska AS 40.25.122 certification
    ]

    _SIGNATURE_LABELS = [
        "electronic signature",
        "digital signature",
        "signature of person",
        "signature of requester",
        "requestor's signature",
        "in lieu of a signature",
        "type your full name",
        "type your name",
        "initial here for signature",
        "esignature",
        "signature",
    ]

    _FEE_LABELS = [
        "fees will exceed",
        "fees will be more than",
        "fee will exceed",
        "fee will be more than",
        "duplication costs exceeding",
        "notify me before processing",
        "notify me of duplication",
        "maximum fee",
        "maximum authorization cost",
        "please let me know in advance",
        "let me know if the fees",
    ]

    _DESCRIPTION_LABELS = [
        "i hereby request, pursuant to",
        "pursuant to",
        "describe the records",
        "describe the data",
        "description of record",
        "description of request",
        "records requested",
        "record request",
        "documents requested",
        "information requested",
        "specific records requested",
        "complete description of the record",
        "provide detail",
        "detail of requested records",
        "record being requested",
        "records you are requesting",
        "records being requested",
        "type of record required",
        "clearly identify the documents",
        "please enter sufficient information",
        "please list each document",
        "identify the specific records",
        "subject or item requested",
        "request a public record",
        "i am requesting the following",
        "what right to know records",
        "please provide a written description",
        "please provide description",
        "brief description of record",
        "comments or description",
        "examine and/or copy the following",
        "description of document",
        "please list document",
        "please list the document",
        "list document",
        "project/subdivision",
        "project name",
        "subdivision",
    ]

    _DEPT_TEXT_LABELS = [
        "town department",
        "department (if known)",
        "department name",
        "which department",
        "name of department",
        "department holding",
        "this request pertains to",
    ]

    _REASON_LABELS = [
        "reason for requesting",
        "reason for the request",
        "reason for request",
        "purpose of request",
        "purpose of this request",
        "reason you are requesting",
        "state your reason",
        "provide your reason",
    ]

    # ────────────────────────────────────────────────────────────────────
    def __init__(self):
        pass

    # ── Department picker ────────────────────────────────────────────────

    def pick_department(self, available_options):
        available_lower = [o.strip().lower() for o in available_options]
        for preferred in self.DEPARTMENT_PRIORITY:
            pref_lower = preferred.lower()
            for i, opt_lower in enumerate(available_lower):
                if pref_lower in opt_lower or opt_lower in pref_lower:
                    print(f"🏢 Department matched: '{available_options[i]}' (priority: '{preferred}')")
                    return available_options[i]
        return None

    # ── Main decision method ─────────────────────────────────────────────

    def decide(self, label: str, field_type: str, options=None) -> str | None:
        l    = label.lower().strip()
        opts = list(options) if options else []
        ol   = [o.lower() for o in opts]

        # ── 1. Date fields ───────────────────────────────────────────────
        if field_type == "date":
            return "__TODAY__"
        if "date" in l and field_type in ("text", "textarea"):
            return "__TODAY__"

        # ── 2. Department text fields → write top priority dept as text ────
        # When a department field is a plain textbox (not radio/dropdown),
        # write "City Clerk" as the default — top of the priority list.
        if field_type in ("text", "textarea") and any(k in l for k in self._DEPT_TEXT_LABELS):
            return "__DEPT_TEXT__"

        # ── 3. Reason for requesting → fixed boilerplate ───────────────────
        if field_type in ("text", "textarea") and any(k in l for k in self._REASON_LABELS):
            return "__REASON__"

        # ── 3. Fee threshold → "0" ───────────────────────────────────────
        if field_type in ("text", "textarea") and any(k in l for k in self._FEE_LABELS):
            return "0"

        # ── 4. Description / records textarea ────────────────────────────
        if field_type in ("text", "textarea") and any(k in l for k in self._DESCRIPTION_LABELS):
            return "__DESCRIPTION__"

        # ── 5. NJ legal questions → negative option ──────────────────────
        if any(k in l for k in self._LEGAL_KEYWORDS):
            return (
                self._pick(ol, opts, ["have not", "will not", "am not", "not seeking"])
                or self._pick(ol, opts, ["no", "false"])
            )

        # ── 5. Commercial purpose → YES ─────────────────────────────────────
        # We are a commercial entity (Smartprocure), so answer YES
        if any(k in l for k in [
            "commercial purpose", "commercial / business purpose",
            "commercial solicitation", "commercial request",
            "is this a commercial request", "for commercial purpose",
            "a.r.s. section 39-121.03", "rcw 42.56.070",
        ]):
            return (
                self._pick(ol, opts, ["yes"])
                or self._pick(ol, opts, ["will "])   # "WILL /" in NJ OPRA
                or self._pick(ol, opts, ["commercial"])
            )

        # ── 6. Litigation → NO ──────────────────────────────────────────
        if any(k in l for k in [
            "legal proceeding", "litigation related",
            "pending or existing litigation", "seeking records in connection",
        ]):
            return self._pick(ol, opts, ["am not", "no"])

        # ── 7. Fee waiver → NO ──────────────────────────────────────────
        if "fee waiver" in l:
            return self._pick(ol, opts, ["no"])

        # ── 8. Delivery / receipt method → email option ──────────────────
        if any(k in l for k in self._DELIVERY_LABELS):
            return self._pick(ol, opts, self._EMAIL_OPTS) or "email"

        # ── 9a. Liability / legal obligation statements → SKIP (do not check) ──
        # These are statements that admit legal/financial liability.
        # We only check neutral deposit/process acknowledgements.
        _SKIP_CHECKBOX_LABELS = [
            "engaged in any litigation",            # "I certify that neither I nor the company...litigation"
            "legal disputes",                       # same field
            "nonlitigation affiliation",            # certification header
            "copying or scanning fees may apply",   # "I acknowledge that copying fees may apply"
            "personnel costs",                      # "I acknowledge responsibility for personnel costs"
            "staff retrieval time exceeds",         # same field
            "kib code",                             # Kodiak Island Borough code reference
        ]
        if field_type in ("checkbox", "radio") and any(k in l for k in _SKIP_CHECKBOX_LABELS):
            return "__SKIP__"

        # ── 9b. Neutral process acknowledgements → check ─────────────────
        # "I understand that a deposit may be required" — safe to check
        _SAFE_ACKNOWLEDGE = [
            "deposit may be required",
            "deposit may be",
        ]
        if field_type in ("checkbox",) and any(k in l for k in _SAFE_ACKNOWLEDGE):
            return opts[0] if opts else "yes"

        # ── 9. Agreement / acknowledgement ───────────────────────────────
        if any(k in l for k in self._AGREEMENT_LABELS):
            if field_type in ("radio", "checkbox", "dropdown"):
                return self._pick(ol, opts, [
                    "yes", "i agree", "i affirm", "i have read",
                    "have read", "i acknowledge", "i understand",
                    "click here", "true",
                ]) or (opts[0] if opts else "yes")
            return "__SIGN__"

        # ── 10. Signature fields ─────────────────────────────────────────
        if any(k in l for k in self._SIGNATURE_LABELS):
            if field_type in ("text", "textarea"):
                return "__SIGN__"
            if field_type == "checkbox" and opts:
                return opts[0]

        # ── 11. "Receive an email copy of this form" checkbox ────────────
        if "receive an email copy of this form" in l:
            return opts[0] if opts else "yes"

        # ── 12. Number of copies ─────────────────────────────────────────
        if any(k in l for k in [
            "number of copies", "copies you would like",
            "number of copies requested", "number of copies needed",
        ]):
            if field_type in ("text", "textarea"):
                return "1"
            return self._pick(ol, opts, ["1"]) or (opts[0] if opts else "1")

        # ── 2b. Copies in electronic format → YES ───────────────────────────
        if "copies in electronic format" in l or "electronic format" in l and "copies" in l:
            return self._pick(ol, opts, ["yes"])

        # ── 2c. Sheriff / specific agency office question → NO ───────────────
        # "Are you requesting documents from the [Agency] Sheriff's Office?" → No
        if "sheriff" in l and ("are you requesting" in l or "requesting documents from" in l):
            return self._pick(ol, opts, ["no"])

        # ── 2d. Requester willing to retrieve records → No ───────────────────
        if "willing to retrieve" in l or "requester willing" in l:
            return self._pick(ol, opts, ["no"])

        # ── 2e. Fee agreement → Yes ──────────────────────────────────────────
        if "fee agreement" in l:
            if field_type in ("radio", "checkbox", "dropdown"):
                return self._pick(ol, opts, ["yes", "i agree", "agree"])
            return "__SIGN__"

        # ── 2f. Request to / copy of records → Receive Copies / Yes ─────────
        if l.strip(":").strip() in ("request to", "copy of records"):
            return (
                self._pick(ol, opts, ["receive copies", "copies", "copy"])
                or self._pick(ol, opts, ["yes"])
            )

        # ── 2g. Purpose of request → Commercial (fallback Other) ────────────
        if "purpose of request" in l or "purpose of this request" in l:
            return (
                self._pick(ol, opts, ["commercial"])
                or self._pick(ol, opts, ["business"])
                or self._pick(ol, opts, ["other"])
            )

        # ── 2h. Media format → Electronic Copy ──────────────────────────────
        if "media format" in l:
            return (
                self._pick(ol, opts, ["electronic copy", "electronic", "e-copy"])
                or self._pick(ol, opts, ["email", "digital"])
            )

        # ── 12b. Type of Requestor → Commercial ─────────────────────────────
        if "type of requestor" in l or "requestor type" in l:
            return (
                self._pick(ol, opts, ["commercial"])
                or self._pick(ol, opts, ["business"])
                or (opts[1] if len(opts) > 1 else None)   # skip placeholder, take first real
            )

        # ── 13. Certified copies → NO ────────────────────────────────────
        # "Copies Need to be Certified as True and Correct" → No
        if "certified as true and correct" in l:
            return self._pick(ol, opts, ["no"])

        # ── 13a. "This request is made for" → Personal Use (not commercial) ──
        if "this request is made for" in l or "request is made for:" in l:
            return (
                self._pick(ol, opts, ["personal use", "personal"])
                or self._pick(ol, opts, ["non-commercial", "noncommercial"])
            )

        # ── 13b. "This request is for" → Copying (not Inspection) ───────────
        if l in ("this request is for:", "this request is for") or (
            "request is for" in l and field_type in ("radio", "checkbox")
        ):
            return (
                self._pick(ol, opts, ["copying", "copies", "copy"])
                or self._pick(ol, opts, ["electronic", "email"])
            )

        # ── OLD 13. Certified copies → NO (kept as fallback) ─────────────
        if "certified copies" in l:
            return self._pick(ol, opts, ["no"])

        # ── 14. Appointment to review → NO ───────────────────────────────
        if "appointment to review" in l:
            return self._pick(ol, opts, ["no"])

        # ── 15. Wish to have copies → YES ────────────────────────────────
        if "i wish to have hard copies" in l or ("i wish to have" in l and "hard cop" in l):
            return self._pick(ol, opts, ["no"])
        if "i wish to have" in l:
            return self._pick(ol, opts, ["yes"])

        # ── 16. Do you want copies? → YES electronic ─────────────────────
        if l.startswith("do you want copies"):
            return self._pick(ol, opts, ["yes, electronic", "yes, printed", "yes"])

        # ── 17. Inspection or copy → copy ────────────────────────────────
        if any(k in l for k in [
            "inspect the records or receive a copy",
            "inspection or copies",
            "record - inspection or copies",
        ]):
            return self._pick(ol, opts, ["copy", "duplicate"])

        # ── 18. Response via email? → YES ────────────────────────────────
        if "response method" in l and "email" in l:
            return self._pick(ol, opts, ["yes"])

        # ── 19. Residency → YES ──────────────────────────────────────────
        if "tennessee citizen" in l or "requestor a " in l:
            return self._pick(ol, opts, ["yes"])

        # ── 20. Police / agency booleans → NO ────────────────────────────
        if l == "incident" or "police records" in l or "government agency" in l:
            return self._pick(ol, opts, ["no"])

        # ── 21. Township / Police / General Authority → Township ─────────
        if "township" in l and "police" in l and "general authority" in l:
            return (
                self._pick(ol, opts, ["township"])
                or self._pick(ol, opts, ["general authority"])
                or self._pick(ol, opts, ["general"])
            )

        # ── 22. NJ split radio pairs ─────────────────────────────────────
        if l == "have/have not":
            return self._pick(ol, opts, ["have not"])
        if l == "will/will not":
            return self._pick(ol, opts, ["will not"])
        if l == "am/am not":
            return self._pick(ol, opts, ["am not"])

        return None

    # ── Helper ───────────────────────────────────────────────────────────

    def _pick(self, ol: list, opts: list, targets: list) -> str | None:
        """Return the first original-cased option whose lowercase contains any target."""
        for target in targets:
            for i, o in enumerate(ol):
                if target in o:
                    return opts[i]
        return None