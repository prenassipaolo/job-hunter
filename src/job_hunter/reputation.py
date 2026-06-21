"""Curated employer-reputation list.

the persona only wants roles at places with a strong reputation and real room to learn and
grow — top trading firms, big tech, serious fintech/scale-ups, and well-regarded
banks/research labs — not unknown small companies. This module tiers known employers
and lets the pipeline filter out everything it can't recognise as reputable.

Tiers (higher = more prestige / learning signal):
  3  elite quant/trading + frontier tech + tier-1 banks
  2  strong tech, fintech scale-ups, well-known banks & research-grade firms
  1  solid, reputable engineering employers worth working for

Add companies freely — matching is on normalised, word-ish substrings.
"""

from __future__ import annotations

import re

# --- Tier 3: elite -----------------------------------------------------------
TIER3 = {
    # Quant / proprietary trading
    "optiver", "imc", "imc trading", "flow traders", "jane street", "jump trading",
    "citadel", "citadel securities", "drw", "da vinci", "davinci", "maven securities",
    "qube research", "hudson river trading", "hrt", "five rings", "susquehanna", "sig",
    "xtx markets", "g-research", "gresearch", "marshall wace", "squarepoint", "quantlab",
    "akuna capital", "tower research", "virtu", "old mission", "jane street capital",
    "two sigma", "de shaw", "d. e. shaw", "point72", "millennium", "balyasny", "aqr",
    "man group", "bridgewater", "ahl", "qrt",
    # Frontier tech / AI
    "google", "deepmind", "google deepmind", "meta", "openai", "anthropic", "nvidia",
    "microsoft", "apple", "amazon", "netflix", "databricks",
    # Tier-1 investment banks
    "jp morgan", "j.p. morgan", "jpmorgan", "goldman sachs", "morgan stanley",
    "bank of america", "barclays", "deutsche bank", "ubs", "credit suisse",
    "bloomberg", "blackrock",
}

# --- Tier 2: strong ----------------------------------------------------------
TIER2 = {
    # Fintech / payments scale-ups
    "adyen", "stripe", "mollie", "bunq", "revolut", "wise", "monzo", "starling",
    "checkout.com", "n26", "klarna", "plaid", "bitvavo", "backbase", "mambu",
    "coinbase", "block", "square", "ramp", "robinhood", "trade republic", "scalable capital",
    # Tech scale-ups / product companies
    "booking.com", "booking", "spotify", "uber", "airbnb", "linkedin", "snowflake",
    "datadog", "palantir", "elastic", "gitlab", "miro", "messagebird", "picnic",
    "just eat takeaway", "takeaway", "zalando", "delivery hero", "hellofresh",
    "personio", "celonis", "graphcore", "wayve", "synthesia", "deepl", "mistral",
    # Banks / asset managers / insurers (well-regarded, strong learning)
    "ing", "abn amro", "rabobank", "nn group", "aegon", "achmea", "de volksbank",
    "hsbc", "lloyds", "natwest", "standard chartered", "nomura", "citi", "citigroup",
    "macquarie", "bnp paribas", "societe generale", "société générale", "santander",
    "julius baer", "pictet", "lombard odier", "vontobel", "swiss re", "zurich insurance",
    "partners group", "schroders", "fidelity", "pimco", "state street",
    # Research-grade / deep-tech / pharma DS
    "asml", "philips", "roche", "novartis", "shell", "elsevier", "cern", "tomtom",
    "qualcomm", "arm", "ibm", "sap", "siemens", "bosch",
}

# --- Tier 1: solid -----------------------------------------------------------
TIER1 = {
    "accenture", "capgemini", "deloitte", "kpmg", "pwc", "ey", "mckinsey", "bcg",
    "bain", "thoughtworks", "epam", "cognizant", "infosys", "tcs",
    "vodafone", "ericsson", "nokia", "klm", "klarna", "exact", "afterpay",
    "ahold delhaize", "albert heijn", "klm", "ns", "klm royal dutch",
    "data science", "datacamp", "dataiku", "ataccama",
}

TIER_POINTS = {3: 20, 2: 13, 1: 7, 0: 0}


def _normalise(company: str) -> str:
    c = company.lower()
    # Drop common legal suffixes / noise so "Optiver B.V." matches "optiver".
    c = re.sub(r"\b(b\.?v\.?|n\.?v\.?|ltd|limited|llc|inc|gmbh|ag|plc|sa|s\.a\.|group|holdings?)\b", " ", c)
    c = re.sub(r"[^a-z0-9.& ]+", " ", c)
    return re.sub(r"\s+", " ", c).strip()


def _matches(norm: str, name: str) -> bool:
    """True if a curated `name` appears as a word-ish chunk of the company string."""
    if name == norm:
        return True
    # token-boundary containment, e.g. "ing" must not match "trading"
    return re.search(rf"(^|[^a-z0-9]){re.escape(name)}([^a-z0-9]|$)", norm) is not None


def tier_for(company: str) -> int:
    """Return the reputation tier (3/2/1) for a company, or 0 if unrecognised."""
    norm = _normalise(company)
    if not norm:
        return 0
    for tier, names in ((3, TIER3), (2, TIER2), (1, TIER1)):
        for name in names:
            if _matches(norm, name):
                return tier
    return 0


def reputation_points(company: str) -> tuple[int, int]:
    """(tier, points) for the heuristic scorer."""
    tier = tier_for(company)
    return tier, TIER_POINTS[tier]


def is_reputable(company: str) -> bool:
    return tier_for(company) > 0
