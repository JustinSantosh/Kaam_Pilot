"""Indian states/UTs: customer text → 2-letter code for place of supply (D-006)."""

STATES: dict[str, str] = {
    "AN": "Andaman and Nicobar Islands",
    "AP": "Andhra Pradesh",
    "AR": "Arunachal Pradesh",
    "AS": "Assam",
    "BR": "Bihar",
    "CH": "Chandigarh",
    "CG": "Chhattisgarh",
    "DN": "Dadra and Nagar Haveli and Daman and Diu",
    "DL": "Delhi",
    "GA": "Goa",
    "GJ": "Gujarat",
    "HR": "Haryana",
    "HP": "Himachal Pradesh",
    "JK": "Jammu and Kashmir",
    "JH": "Jharkhand",
    "KA": "Karnataka",
    "KL": "Kerala",
    "LA": "Ladakh",
    "LD": "Lakshadweep",
    "MP": "Madhya Pradesh",
    "MH": "Maharashtra",
    "MN": "Manipur",
    "ML": "Meghalaya",
    "MZ": "Mizoram",
    "NL": "Nagaland",
    "OD": "Odisha",
    "PY": "Puducherry",
    "PB": "Punjab",
    "RJ": "Rajasthan",
    "SK": "Sikkim",
    "TN": "Tamil Nadu",
    "TS": "Telangana",
    "TR": "Tripura",
    "UP": "Uttar Pradesh",
    "UK": "Uttarakhand",
    "WB": "West Bengal",
}

ALIASES: dict[str, str] = {
    "chattisgarh": "CG",
    "orissa": "OD",
    "pondicherry": "PY",
    "uttaranchal": "UK",
    "new delhi": "DL",
    "nct of delhi": "DL",
    # Major cities customers name instead of the state. Names shared by cities in two states
    # (Bilaspur: CG and HP) are left out so they stay unknown and get flagged.
    "raipur": "CG",
    "bhilai": "CG",
    "durg": "CG",
    "mumbai": "MH",
    "bombay": "MH",
    "pune": "MH",
    "nagpur": "MH",
    "bengaluru": "KA",
    "bangalore": "KA",
    "chennai": "TN",
    "hyderabad": "TS",
    "kolkata": "WB",
    "ahmedabad": "GJ",
    "surat": "GJ",
    "jaipur": "RJ",
    "lucknow": "UP",
    "noida": "UP",
    "gurgaon": "HR",
    "gurugram": "HR",
    "bhopal": "MP",
    "indore": "MP",
    "patna": "BR",
    "ranchi": "JH",
    "bhubaneswar": "OD",
}

_BY_NAME = {name.lower(): code for code, name in STATES.items()}


def state_code(text: str | None) -> str | None:
    """'Maharashtra', 'mh', 'Mumbai' → 'MH'. Unknown → None (pricing then flags it)."""
    if not text:
        return None
    key = " ".join(text.strip().lower().replace(",", " ").split())
    if key.upper() in STATES:
        return key.upper()
    return _BY_NAME.get(key) or ALIASES.get(key)
