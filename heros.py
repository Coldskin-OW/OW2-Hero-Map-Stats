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
    # Ana
    'ANNA': 'Ana',
    
    # Ashe
    'ASHEE': 'Ashe',
    'ASH': 'Ashe',
    
    # Baptiste
    'BAPTIST': 'Baptiste',
    
    # Bastion
    'BAJTION': 'Bastion',
    
    # Brigitte
    'BRIGITE': 'Brigitte',
    
    # Cassidy
    'CASSID': 'Cassidy',
    'CASSADY': 'Cassidy',
    
    # D.Va
    'D.VA': 'D.Va',
    'DVA': 'D.Va',
    'LVA': 'D.Va',
    'OVA': 'D.Va',
    
    # Doomfist
    'DOOMEST': 'Doomfist',
    
    # Echo 
    'ECHD': 'Echo',
    
    # Freja
    'FREIA': 'Freja',
    
    # Genji
    'GENJU': 'Genji',
    'GENJ': 'Genji',
    'GENSU': 'Genji',
    
    # Hanzo
    'HANZA': 'Hanzo',
    'HANDZO': 'Hanzo',
    
    # Hazard
    'HAZARO': 'Hazard',

    # Illari
    'ILLAR': 'Illari',
    'FLLRRI': 'Illari',
    
    # Junker Queen
    'JUNKERQUEEN': 'Junker Queen',
    'SUNKERQUEEN': 'Junker Queen',
    
    # Junkrat
    'JUNKRATT': 'Junkrat',
    'SUNKRAT': 'Junkrat',
    
    # Juno
    'SUNG': 'Juno',
    'JUNG': 'Juno',
    'JUNG ': 'Juno',
    'JUNO': 'Juno',
    
    # Kiriko
    'KIRIKKO': 'Kiriko',
    
    # Lifeweaver
    'LIFEWEAVER': 'Lifeweaver',
    'LIFE WEAVER': 'Lifeweaver',
    'LIFEWEVER': 'Lifeweaver',
    'LIFFWEVER': 'Lifeweaver',
    
    # Lúcio
    'LUCIO': 'Lúcio',
    'LUE': 'Lúcio',
    
    # Mauga
    'MAUGR': 'Mauga',
    
    # Mei
    'ME': 'Mei',
    
    # Mercy
    'MERECY': 'Mercy',
    
    # Moira
    'MOIRHA': 'Moira',
    'MORIA': 'Moira',
    
    # Orisa
    'DRISA': 'Orisa',
    
    # Pharah
    'PHARA': 'Pharah',
    'FARAH': 'Pharah',
    
    # Ramattra
    'ARAMATIRA': 'Ramattra',
    'RAMATIRA': 'Ramattra',
    
    # Reaper
    'REAPAR': 'Reaper',
    
    # Reinhardt
    'REINHARD': 'Reinhardt',
    
    # Roadhog
    'RDADHOG': 'Roadhog',
    'ROADHDG': 'Roadhog',
    'RDADHDG': 'Roadhog',
    
    # Sigma
    'SIGMAA': 'Sigma',
    
    # Sojourn
    'SOJOUR': 'Sojourn',
    'SOSOURN': 'Sojourn',
    
    # Soldier: 76
    'SOLDIER': 'Soldier: 76',
    'SOLDIER 76': 'Soldier: 76',
    'SOLDIER76': 'Soldier: 76',
    
    # Sombra
    'SOMBRI': 'Sombra',
    
    # Symmetra
    'SYMETRA': 'Symmetra',
    
    # Torbjörn
    'TORBJORN': 'Torbjörn',
    'TORBSORN': 'Torbjörn',
    
    # Tracer
    'TRACAR': 'Tracer',
    
    # Venture
    'VENTUR': 'Venture',
    
    # Widowmaker
    'WIDOW': 'Widowmaker',
    'WIDOW MAKER': 'Widowmaker',
    
    # Winston
    'WINJTON': 'Winston',
    'WINITON': 'Winston',
    'WINSION': 'Winston',
    
    # Wrecking Ball
    'WRECKING BALI': 'Wrecking Ball',
    'WRECKING BRL': 'Wrecking Ball',
    'WRECKINGBALL': 'Wrecking Ball',
    
    # Zarya
    'ZARYG': 'Zarya',
    'ZARIYA': 'Zarya',
    
    # Zenyatta
    'ZENYATT': 'Zenyatta',
    'ZENYATA': 'Zenyatta',
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