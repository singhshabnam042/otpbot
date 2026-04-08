"""
utils.py — Helper functions for the OTP Bot
"""

import re
from typing import Optional


def format_phone_number(raw_number: str) -> str:
    """
    Format a phone number string for clean display.
    5sim.net returns numbers like '79161234567' or '+79161234567'.
    We always add the '+' prefix.

    Examples:
      '79161234567'  → '+7 9161234567'
      '+79161234567' → '+7 9161234567'
      '447911123456' → '+44 7911123456'
    """
    # Strip any existing '+', spaces, or dashes
    digits = re.sub(r"[^\d]", "", raw_number)

    if not digits:
        return raw_number  # fallback – return as-is

    # Country codes can be 1-3 digits; try to split sensibly.
    # If the number starts with a known 2-or-3-digit CC prefix we keep it;
    # otherwise we just prepend '+' and return.
    # The cleanest approach: just show +<all digits> with a space after the CC.
    # We detect CC length by known prefixes in a simple lookup.
    cc_len = _detect_country_code_length(digits)
    if cc_len:
        cc = digits[:cc_len]
        subscriber = digits[cc_len:]
        return f"+{cc} {subscriber}"

    return f"+{digits}"


def _detect_country_code_length(digits: str) -> Optional[int]:
    """Return the length of the country code at the start of `digits`, or None."""
    # 3-digit country codes (common ones used by 5sim)
    THREE_DIGIT_CC = {
        "880",  # Bangladesh
        "381",  # Serbia
        "382",  # Montenegro
        "355",  # Albania
        "374",  # Armenia
        "994",  # Azerbaijan
        "375",  # Belarus
        "387",  # Bosnia
        "359",  # Bulgaria
        "385",  # Croatia
        "420",  # Czech Republic
        "372",  # Estonia
        "995",  # Georgia
        "996",  # Kyrgyzstan
        "371",  # Latvia
        "370",  # Lithuania
        "373",  # Moldova
        "389",  # North Macedonia
        "380",  # Ukraine
        "998",  # Uzbekistan
        "992",  # Tajikistan
        "993",  # Turkmenistan
        "977",  # Nepal
        "855",  # Cambodia
        "856",  # Laos
        "960",  # Maldives
        "850",  # North Korea
    }
    # 2-digit country codes (Russia=7, US/Canada=1, etc. are 1-digit; 2-digit are rare)
    TWO_DIGIT_CC = {
        "20",   # Egypt
        "27",   # South Africa
        "30",   # Greece
        "31",   # Netherlands
        "32",   # Belgium
        "33",   # France
        "34",   # Spain
        "36",   # Hungary
        "39",   # Italy
        "40",   # Romania
        "41",   # Switzerland
        "43",   # Austria
        "44",   # UK
        "45",   # Denmark
        "46",   # Sweden
        "47",   # Norway
        "48",   # Poland
        "49",   # Germany
        "51",   # Peru
        "52",   # Mexico
        "53",   # Cuba
        "54",   # Argentina
        "55",   # Brazil
        "56",   # Chile
        "57",   # Colombia
        "58",   # Venezuela
        "60",   # Malaysia
        "61",   # Australia
        "62",   # Indonesia
        "63",   # Philippines
        "64",   # New Zealand
        "65",   # Singapore
        "66",   # Thailand
        "81",   # Japan
        "82",   # South Korea
        "84",   # Vietnam
        "86",   # China
        "90",   # Turkey
        "91",   # India
        "92",   # Pakistan
        "93",   # Afghanistan
        "94",   # Sri Lanka
        "95",   # Myanmar
        "98",   # Iran
    }
    ONE_DIGIT_CC = {"1", "7"}

    # Check 3-digit first (most specific)
    if len(digits) > 3 and digits[:3] in THREE_DIGIT_CC:
        return 3
    if len(digits) > 2 and digits[:2] in TWO_DIGIT_CC:
        return 2
    if len(digits) > 1 and digits[:1] in ONE_DIGIT_CC:
        return 1
    return None


def extract_otp_code(sms_text: str) -> Optional[str]:
    """
    Try to extract a numeric OTP/verification code from an SMS body.
    Looks for 4-8 consecutive digits that look like a code.

    Returns the first match, or None if no code found.
    """
    if not sms_text:
        return None

    # Prefer patterns like "Your code is 123456" or "OTP: 654321"
    patterns = [
        r"(?:code|otp|verification|verifica[a-z]*|confirm[a-z]*)[^\d]*(\d{4,8})",
        r"(\d{6})",  # bare 6-digit code (most common Gmail OTP)
        r"(\d{4,8})",  # any 4-8 digit sequence
    ]
    for pattern in patterns:
        match = re.search(pattern, sms_text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def country_flag(country_code: str) -> str:
    """
    Convert a 2-letter ISO country code to its emoji flag.
    5sim uses full country names (like 'russia', 'india'), not ISO codes,
    so this is a best-effort lookup for common countries.
    """
    _MAP = {
        "russia": "🇷🇺", "india": "🇮🇳", "ukraine": "🇺🇦",
        "indonesia": "🇮🇩", "philippines": "🇵🇭", "vietnam": "🇻🇳",
        "myanmar": "🇲🇲", "cambodia": "🇰🇭", "malaysia": "🇲🇾",
        "thailand": "🇹🇭", "kenya": "🇰🇪", "ethiopia": "🇪🇹",
        "ghana": "🇬🇭", "nigeria": "🇳🇬", "egypt": "🇪🇬",
        "moldova": "🇲🇩", "kazakhstan": "🇰🇿", "uzbekistan": "🇺🇿",
        "bangladesh": "🇧🇩", "pakistan": "🇵🇰", "nepal": "🇳🇵",
        "china": "🇨🇳", "brazil": "🇧🇷", "colombia": "🇨🇴",
    }
    return _MAP.get(country_code.lower(), "🌍")


def humanize_country(country_code: str) -> str:
    """Convert 5sim country slug to a human-readable name."""
    _MAP = {
        "russia": "Russia", "india": "India", "ukraine": "Ukraine",
        "indonesia": "Indonesia", "philippines": "Philippines",
        "vietnam": "Vietnam", "myanmar": "Myanmar", "cambodia": "Cambodia",
        "malaysia": "Malaysia", "thailand": "Thailand", "kenya": "Kenya",
        "ethiopia": "Ethiopia", "ghana": "Ghana", "nigeria": "Nigeria",
        "egypt": "Egypt", "moldova": "Moldova", "kazakhstan": "Kazakhstan",
        "uzbekistan": "Uzbekistan", "bangladesh": "Bangladesh",
        "pakistan": "Pakistan", "nepal": "Nepal", "china": "China",
        "brazil": "Brazil", "colombia": "Colombia", "usa": "USA",
    }
    return _MAP.get(country_code.lower(), country_code.capitalize())
