"""
constants.py
============
FIELD_MAP: keyword (normalised label substring) → Google Sheet column name.

Rules applied in form_filler.py in order; first match wins.
All keys must be lowercase.
"""

FIELD_MAP: dict[str, str] = {

    # ── Company / Organisation ─────────────────────────────────────────
    "your business/organization name":   "Company",
    "name/ organization requesting":     "Company",   # ← also contains "name"
    "company name (if available)":       "Company",
    "company name":                      "Company",
    "company/organization":              "Company",
    "company (if applicable)":           "Company",
    "organization/business":             "Company",
    "company":                           "Company",

    # ── Name variants ──────────────────────────────────────────────────
    "first name of requestor":          "First Name",
    "requestor first name":             "First Name",
    "first and last name":              "Name",
    "first name":                       "First Name",
    "last name":                        "Last Name",
    "requestor last name":              "Last Name",
    "full name of requester":           "Name",
    "name of requester":                "Name",
    "name of requesting party":         "Name",
    "name of individual requesting":    "Name",
    "name of person requesting":        "Name",
    "request made by":                  "Name",
    "requestor name":                   "Name",
    "requester's name":                 "Name",
    "name (first, last)":               "Name",
    "name (last, first":                "Name",
    "your name":                        "Name",
    "contact/requestor":                "Name",
    "representing":                     "Name",
    "requestor's name":                 "Name",
    "name":                             "Name",
    "contact person":                   "Name",
    "contact name":                     "Name",
    "your name":                        "Name",

    # ── Email variants ─────────────────────────────────────────────────
    "requestor email":                  "Email",
    "email of requesting party":        "Email",
    "reply email":                      "Email",
    "your email":                       "Email",
    "e-mail address":                   "Email",
    "e-mail (optional)":                "Email",
    "e-mail":                           "Email",
    "email address":                    "Email",
    "email":                            "Email",
    "email the records (if applicable)":  "Email",

    # ── Phone variants ─────────────────────────────────────────────────
    "telephone number of requester":    "Phone",
    "telephone number":                 "Phone",
    "telephone":                        "Phone",
    "phone number of requesting party": "Phone",
    "requestor phone":                  "Phone",
    "contact phone":                    "Phone",
    "business hours telephone":         "Phone",
    "cell number":                      "Phone",
    "cell phone":                       "Phone",
    "home phone":                       "Phone",
    "fax number":                       "Fax",
    "fax":                              "Fax",
    "phone number":                     "Phone",
    "phone":                            "Phone",

    # ── Address variants ───────────────────────────────────────────────
    "address pertaining to this request":   "Street Address",
    "address associated with request":      "Street Address",
    "address/parcel no":                    "Street Address",
    "mailing address 1":                    "Street Address",
    "mailing address":                      "Street Address",
    "physical address":                     "Street Address",
    "requestor address":                    "Street Address",
    "street number and name":               "Street Address",
    "street address":                       "Street Address",
    "address line 1":                       "Street Address",
    "address line 2":                       "Street Address 2",
    "address 1":                            "Street Address",
    "address 2":                            "Street Address 2",
    "address1":                             "Street Address",
    "address2":                             "Street Address 2",
    "address (optional)":                   "Street Address",
    "address of requester":                 "Street Address",
    "address":                              "Street Address",

    # ── City / State / Zip ─────────────────────────────────────────────
    "city (optional)":                  "City",
    "city:":                            "City",
    "city":                             "City",
    "state (optional)":                 "State",
    "state / province / region":        "State",
    "state:":                           "State",
    "state":                            "State",
    "postal / zip code":                "Zip",
    "zip code (optional)":              "Zip",
    "zip code:":                        "Zip",
    "zip code":                         "Zip",
    "zip":                              "Zip",
    "postal code":                      "Zip",
    
    # ── Department ────────────────────────────────────────────────────
    "department holding the record":    "Department",
    "department of requested records":  "Department",
    "please select the department":     "Department",
    "what department":                  "Department",
    "department:":                      "Department",
    "departments":                      "Department",
    "department":                       "Department",
    "town department":                  "Department",
    "Department*":                      "Department",
    "Department":                       "Department",

    # ── Subject (contact forms) ────────────────────────────────────────
    "subject":                          "Description",
    "requested records":                "Description",
    "records":                          "Description",
    "record description":               "Description",
    "i hereby request, pursuant to Idaho Code 74-102, to examine and/or copy the following public records(including audio):": "Description",
}
