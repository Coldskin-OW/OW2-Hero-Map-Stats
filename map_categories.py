# map_categories.py

# All official Overwatch maps
OVERWATCH_MAPS = [
    "Blizzard World", "Eichenwalde", "Hollywood", "King's Row", "Midtown",
    "Numbani", "Paraíso", "Circuit Royal", "Dorado", "Havana", "Junkertown",
    "Rialto", "Route 66", "Shambali Monastery", "Watchpoint: Gibraltar",
    "Antarctic Peninsula", "Busan", "Ilios", "Lijiang Tower", "Nepal",
    "Oasis", "Samoa", "Colosseo", "Esperança", "New Queen Street",
    "New Junk City", "Suravasa", "Runasapi","Aatlis"
]

# Common OCR misread corrections
MAP_CORRECTIONS = {
    'ESPERANGA': 'Esperança',
    'PARAISO': 'Paraíso',
    'JUNKERTOWN': 'Junkertown',
    'NUMBAN1': 'Numbani',
    'NUMBAN)': 'Numbani',
    'KING ROW': "King's Row",
    'WATCHPOINT': 'Watchpoint: Gibraltar'
}

GAME_MODES = {
    'ASSAULT': [
        "Hanamura",
        "Temple of Anubis",
        "Volskaya Industries"
    ],
    'ESCORT': [
        "Dorado",
        "Route 66",
        "Watchpoint: Gibraltar",
        "Junkertown",
        "Circuit Royal",
        "Havana",
        "Rialto",
        "Shambali Monastery"
    ],
    'HYBRID': [
        "King's Row",
        "Blizzard World",
        "Eichenwalde",
        "Hollywood",
        "Midtown",
        "Numbani",
        "Paraíso"
    ],
    'CONTROL': [
        "Ilios",
        "Lijiang Tower",
        "Nepal",
        "Oasis",
        "Busan",
        "Antarctic Peninsula",
        "Samoa"
    ],
    'PUSH': [
        "Colosseo",
        "New Queen Street",
        "Esperança",
        "Runasapi"
    ],
    'FLASHPOINT': [
        "Aatlis",
        "New Junk City",
        "Suravasa"
    ]
}

def get_map_mode(map_name):
    """Get game mode for a specific map"""
    for mode, maps in GAME_MODES.items():
        if map_name in maps:
            return mode
    return None