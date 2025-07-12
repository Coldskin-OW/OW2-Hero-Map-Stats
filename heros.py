"""
Hero definitions and OCR correction mappings for Overwatch 2.
"""

# All current Overwatch 2 heroes categorized by role
OVERWATCH_HEROES = {
    'TANK': [
        "D.Va",
        "Doomfist",
        "Hazard",
        "Junker Queen",
        "Mauga",
        "Orisa",
        "Ramattra",
        "Reinhardt",
        "Roadhog",
        "Sigma",
        "Winston",
        "Wrecking Ball",
        "Zarya"
    ],
    'DAMAGE': [
        "Ashe",
        "Bastion",
        "Cassidy",
        "Echo",
        "Freja",
        "Genji",
        "Hanzo",
        "Junkrat",
        "Mei",
        "Pharah",
        "Reaper",
        "Sojourn",
        "Soldier: 76",
        "Sombra",
        "Symmetra",
        "Torbjörn",
        "Tracer",
        "Venture",
        "Widowmaker"
    ],
    'SUPPORT': [
        "Ana",
        "Baptiste",
        "Brigitte",
        "Illari",
        "Juno",
        "Kiriko",
        "Lifeweaver",
        "Lúcio",
        "Mercy",
        "Moira",
        "Zenyatta"
    ]
}

# OCR misread corrections (only fixes for misreads, not valid heroes)
HERO_CORRECTIONS: dict[str, str] = {
    # Wrecking Ball variations
    'WRECKING BRL': 'Wrecking Ball',
    'WRECKING BALI': 'Wrecking Ball',
    'WRECKINGBALL': 'Wrecking Ball',

    # Ramattra variations
    'RAMATIRA': 'Ramattra',
    'ARAMATIRA': 'Ramattra',

    # Doomfist variations
    'DOOMEST': 'Doomfist',

    # D.Va Variations
    'DVA': 'D.Va',
    'OVA': 'D.Va',
    'LVA': 'D.Va',

    # Mauga variations
    'MAUGR': 'Mauga',

    # Soldier: 76 variations
    'SOLDIER 76': 'Soldier: 76',
    'SOLDIER76': 'Soldier: 76',
    'SOLDIER': 'Soldier: 76',

    # Zarya variations
    'ZARYG': 'Zarya',

    #Juno variations
    'JUNG': 'Juno',
    'JUNG ': 'Juno',
    'JUNO': 'Juno',

    # Widowmaker variations
    'WIDOW': 'Widowmaker',
    'WIDOW MAKER': 'Widowmaker',

    # Mercy variations
    'MERECY': 'Mercy'
}


def get_hero_role(hero_name: str) -> str | None:
    """
    Get role for a specific hero, with OCR correction support.

    Args:
        hero_name (str): The hero name (possibly misread by OCR).

    Returns:
        str | None: The hero's role ('TANK', 'DAMAGE', 'SUPPORT'), or None if not found.
    """
    # Normalize input (uppercase for case-insensitive matching)
    normalized_input = hero_name.upper()

    # Check for corrections first
    corrected_name = HERO_CORRECTIONS.get(normalized_input, hero_name)

    # Find role
    for role, heroes in OVERWATCH_HEROES.items():
        if corrected_name in heroes:
            return role
    return None  # Not found