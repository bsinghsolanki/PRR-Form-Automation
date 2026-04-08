# legal_checks.py

class LegalDecisionEngine:
    def get_decision(self, label, options):
        l = label.lower()
        
        # ⚖️ LEGAL QUESTIONS
        if any(k in l for k in ["convicted", "offense", "commercial", "litigation"]):
            # If label has "NOT", we want to confirm (Yes/True)
            if any(n in l for n in ["not", "am not", "will not"]):
                return self._find(options, ["yes", "true", "agree"])
            # Otherwise, we want the negative (No/False)
            return self._find(options, ["no", "false", "i have not"])

        # 📦 ACCESS TYPE
        if any(k in l for k in ["access", "delivery", "copies"]):
            return self._find(options, ["email", "electronic", "copies", "scans"])

        return None

    def _find(self, options, targets):
        for t in targets:
            for opt in options:
                if t in opt.lower():
                    return opt
        return None