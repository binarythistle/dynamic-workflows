# Made-up products for the demo. Not real funds, rates or fees.
PRODUCTS = [
    {
        "id": "cash-isa",
        "name": "Easy Access Cash ISA",
        "risk": "low",
        "min_years": 0,
        "easy_access": True,
        "isa": True,
        "allows_top_ups": True,
        "fees": "No fees",
        "description": "A savings account where the interest is tax-free. Your money is "
        "not invested, so it won't fall in value, but inflation can reduce what it "
        "buys over time. Withdraw any time.",
    },
    {
        "id": "fixed-saver",
        "name": "2-Year Fixed Saver",
        "risk": "low",
        "min_years": 2,
        "easy_access": False,
        "isa": False,
        "allows_top_ups": False,  # fixed term: one payment at the start
        "fees": "No fees",
        "description": "A savings account with a fixed interest rate for two years. "
        "Your money is locked in until the end of the term.",
    },
    {
        "id": "bond-fund",
        "name": "Bond Fund",
        "risk": "medium",
        "min_years": 3,
        "easy_access": True,
        "isa": False,
        "allows_top_ups": True,
        "fees": "0.20% a year",
        "description": "Lends money to governments and large companies. Usually steadier "
        "than shares, but it can still fall in value, especially when interest rates rise.",
    },
    {
        "id": "balanced-fund",
        "name": "Balanced Multi-Asset Fund",
        "risk": "medium",
        "min_years": 5,
        "easy_access": True,
        "isa": False,
        "allows_top_ups": True,
        "fees": "0.35% a year",
        "description": "Roughly 60% company shares and 40% bonds, spread worldwide. Aims "
        "for growth with smaller swings than an all-shares fund.",
    },
    {
        "id": "global-index",
        "name": "Global Shares Index Fund",
        "risk": "high",
        "min_years": 10,
        "easy_access": True,
        "isa": False,
        "allows_top_ups": True,
        "fees": "0.15% a year",
        "description": "Tracks thousands of company shares worldwide. The highest expected "
        "growth here over the long term, and the biggest falls along the way.",
    },
]
