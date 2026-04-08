from utils.normalizer import normalize
from utils.constants import (
    DEPARTMENT_PRIORITY,
    DELIVERY_KEYWORDS,
    DATE_FROM_KEYWORDS,
    DATE_TO_KEYWORDS,
    ACKNOWLEDGMENT_KEYWORDS,
    SIGNATURE_KEYWORDS,
    SKIP_KEYWORDS,
    REQUESTOR_TYPE_KEYWORDS,
    REQUESTOR_TYPE_VALUE,
)
from utils.date_extractor import extract_mrpo_date, get_today
from utils.logger import get_logger

log = get_logger(__name__)


class DecisionEngine:

    def decide(
        self,
        label      : str,
        field_type : str,
        options    : list,
        description: str = "",
    ) -> str | None:

        l = normalize(label)

        # ── Always skip ──────────────────────────────────
        for kw in SKIP_KEYWORDS:
            if kw in l:
                log.debug(f"⏭️  Skipping: '{label}'")
                return "__SKIP__"

        # ── Date From → MRPO date ────────────────────────
        for kw in DATE_FROM_KEYWORDS:
            if kw in l:
                mrpo   = extract_mrpo_date(description) if description else None
                result = mrpo or get_today()
                log.info(f"📅 Date From → {result}")
                return result

        # ── Date To → today ──────────────────────────────
        for kw in DATE_TO_KEYWORDS:
            if kw in l:
                today = get_today()
                log.info(f"📅 Date To → {today}")
                return today

        # ── Generic date field ───────────────────────────
        if field_type == "date" or "date" in l:
            today = get_today()
            log.info(f"📅 Date field → {today}")
            return today

        # ── Signature ────────────────────────────────────
        for kw in SIGNATURE_KEYWORDS:
            if kw in l:
                return "__SIGN__"

        # ── Description / textarea ───────────────────────
        if field_type == "textarea":
            return "__DESCRIPTION__"

        # ── Type of Requestor → Commercial ───────────────
        for kw in REQUESTOR_TYPE_KEYWORDS:
            if kw in l:
                result = self._pick_requestor_type(options)
                log.info(f"👤 Type of Requestor → '{result}'")
                return result

        # ── Delivery / Preferred Method ──────────────────
        for kw in DELIVERY_KEYWORDS:
            if kw in l:
                result = self._pick_delivery(options)
                log.info(f"📬 Delivery → '{result}'")
                return result

        # ── Acknowledgment → always checkmark ────────────
        for kw in ACKNOWLEDGMENT_KEYWORDS:
            if kw in l:
                result = self._pick_acknowledgment(field_type, options)
                log.info(f"✅ Acknowledgment → '{result}'")
                return result

        # ── Department ───────────────────────────────────
        if any(kw in l for kw in ["department", "division", "office"]):
            best = self.pick_department(options)
            if best:
                return best

        # ── Purpose / Records requested for ─────────────
        if any(kw in l for kw in ["purpose", "requested for", "reason"]):
            return self._pick_purpose(options)

        # ── NJ OPRA ──────────────────────────────────────
        if "opra" in l:
            return "__NJ_OPRA_NEG__"

        return None

    # ─────────────────────────────────────────────────
    # PICKERS
    # ─────────────────────────────────────────────────

    def pick_department(self, options: list) -> str | None:
        if not options:
            return None
        options_lower = {o.lower(): o for o in options}
        for priority in DEPARTMENT_PRIORITY:
            for opt_lower, opt_original in options_lower.items():
                if priority in opt_lower:
                    log.info(f"🏢 Department → '{opt_original}'")
                    return opt_original
        return None

    def _pick_requestor_type(self, options: list) -> str:
        """
        Pick Commercial from available options.
        Falls back to REQUESTOR_TYPE_VALUE if no match.
        """
        targets = ["commercial", "business", "company", "corporate"]

        if options:
            options_lower = {o.lower(): o for o in options}
            for target in targets:
                for opt_lower, opt_original in options_lower.items():
                    if target in opt_lower:
                        log.info(f"👤 Requestor type matched: '{opt_original}'")
                        return opt_original

        log.info(f"👤 Requestor type fallback: '{REQUESTOR_TYPE_VALUE}'")
        return REQUESTOR_TYPE_VALUE

    def _pick_delivery(self, options: list) -> str:
        """Pick Electronic/Email delivery."""
        targets = ["electronic", "email", "e-mail", "digital", "online"]

        if options:
            options_lower = {o.lower(): o for o in options}
            for target in targets:
                for opt_lower, opt_original in options_lower.items():
                    if target in opt_lower:
                        return opt_original

        return "Electronic"

    def _pick_acknowledgment(self, field_type: str, options: list) -> str:
        """
        Always checkmark acknowledgment checkboxes.
        For dropdowns/radios pick yes/agree/accept.
        """
        # ── Checkbox → always check it ────────────────
        if field_type == "checkbox":
            log.info("☑️  Acknowledgment checkbox → __CHECK__")
            return "__CHECK__"

        # ── Radio → pick yes/agree option ─────────────
        yes_targets = [
            "yes", "agree", "accept",
            "i agree", "acknowledge",
            "confirm", "i certify",
        ]

        if options:
            options_lower = {o.lower(): o for o in options}
            for target in yes_targets:
                for opt_lower, opt_original in options_lower.items():
                    if target in opt_lower:
                        log.info(f"✅ Acknowledgment option → '{opt_original}'")
                        return opt_original

        # ── Dropdown → pick yes ────────────────────────
        return "Yes"

    def _pick_purpose(self, options: list) -> str:
        """Pick Commercial purpose."""
        targets = ["commercial", "business", "professional"]

        if options:
            options_lower = {o.lower(): o for o in options}
            for target in targets:
                for opt_lower, opt_original in options_lower.items():
                    if target in opt_lower:
                        return opt_original

        return "Commercial purpose"