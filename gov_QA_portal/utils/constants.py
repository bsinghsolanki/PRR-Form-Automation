# ─────────────────────────────────────────────────────
# FIELD_MAP
# keyword (normalized label fragment) → sheet column name
# ─────────────────────────────────────────────────────
FIELD_MAP = {
    # # Personal info
    # "first name"        : "Name",
    # "last name"         : "Name",
    # "full name"         : "Name",
    # "your name"         : "Name",
    # "name"              : "Name",
    # "phone"             : "Phone",
    # "telephone"         : "Phone",
    # "mobile"            : "Phone",
    # "fax"               : "Phone",
    # "company"           : "Company",
    # "organization"      : "Company",
    # "firm"              : "Company",

    # # Address
    # "street"            : "Street Address",
    # "address"           : "Street Address",
    # "city"              : "City",
    # "state"             : "State",
    # "zip"               : "Zip",
    # "postal"            : "Zip",

    # # Login / contact
    # "email"             : "Email",
    # "e-mail"            : "Email",
    # "username"          : "Email",

    # Request details
    "description"       : "Description",
    "describe"          : "Description",
    "request"           : "Description",
    "detail"            : "Description",
    "subject"           : "Description",
    "nature"            : "Description",
    "content"           : "Content Type",
    "type of record"    : "Content Type",
    "record type"       : "Content Type",

    # Purpose
    "purpose"           : "records_requested_for",
    "reason"            : "records_requested_for",
    "requested for"     : "records_requested_for",
    "use"               : "records_requested_for",

    # Department
    "department"        : "Department",
    "division"          : "Department",
    "office"            : "Department",
    "agency"            : "Department",
}

# ─────────────────────────────────────────────────────
# DEPARTMENT_PRIORITY
# Tried in order — first match wins
# ─────────────────────────────────────────────────────
DEPARTMENT_PRIORITY = [
    "admin",
    "city clerk",
    "clerk",
    "finance",
    "administration",
    "public records",
    "records",
]

# ─────────────────────────────────────────────────────
# DELIVERY_KEYWORDS
# Used to detect preferred method / delivery fields
# ─────────────────────────────────────────────────────
DELIVERY_KEYWORDS = [
    "preferred method",
    "receive record",
    "delivery method",
    "how would you like",
    "format",
    "method of delivery",
    "send record",
]

# ─────────────────────────────────────────────────────
# DATE_KEYWORDS
# ─────────────────────────────────────────────────────
DATE_FROM_KEYWORDS = [
    "date from", "start date", "from date",
    "begin date", "date begin", "date start",
    "record from", "period from",
]

DATE_TO_KEYWORDS = [
    "date to", "end date", "to date",
    "through date", "date through", "date end",
    "record to", "period to",
]

# ─────────────────────────────────────────────────────
# ACKNOWLEDGMENT_KEYWORDS
# ─────────────────────────────────────────────────────
ACKNOWLEDGMENT_KEYWORDS = [
    "acknowledge",
    "acknowledgment",
    "agree",
    "certify",
    "confirm",
    "accept",
    "i understand",
    "terms",
    "conditions",
    "consent",
    "i agree",
    "i certify",
    "hereby",
    "attest",
      ]
 
# ─────────────────────────────────────────────────────
# SIGNATURE_KEYWORDS
# ─────────────────────────────────────────────────────
SIGNATURE_KEYWORDS = [
    "signature", "sign here", "signed by",
    "applicant name", "requestor name",
    "print name", "printed name",
]

# ─────────────────────────────────────────────────────
# SKIP_KEYWORDS
# Fields to always skip
# ─────────────────────────────────────────────────────
SKIP_KEYWORDS = [
    "captcha", "recaptcha", "csrf",
    "token", "honeypot", "hidden",
]



REQUESTOR_TYPE_KEYWORDS = [
    "type of requestor",
    "requestor type",
    "type of requester",
    "requester type",
    "applicant type",
    "who are you",
    "i am a",
    "type of person",
    "requestor",
    "type of request",        # ← added
    "select requestor",       # ← added
]

AUTHORITY_TYPE_KEYWORDS = [
    "township",
    "police",
    "general authority",
    "type of request",
    "authority",
    "municipality",
    "borough",
    "is this a",
]

AUTHORITY_PRIORITY = [
    "township",            # second choice
    "town",
    "city",
    "general authority",   # most generic
    "general",
    "municipality",
    "county",
    "district",
              # last resort
]

# Hard fallback value matching exact portal text
REQUESTOR_TYPE_VALUE = "Commercial"