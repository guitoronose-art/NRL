"""Static game data and tuning constants."""

NRL_TEAMS = [
    ("Brisbane Broncos", "BRI"),
    ("Canberra Raiders", "CBR"),
    ("Canterbury Bulldogs", "CBY"),
    ("Cronulla Sharks", "CRO"),
    ("Dolphins", "DOL"),
    ("Gold Coast Titans", "GLD"),
    ("Manly Sea Eagles", "MAN"),
    ("Melbourne Storm", "MEL"),
    ("Newcastle Knights", "NEW"),
    ("New Zealand Warriors", "NZW"),
    ("North Queensland Cowboys", "NQL"),
    ("Parramatta Eels", "PAR"),
    ("Penrith Panthers", "PEN"),
    ("South Sydney Rabbitohs", "SOU"),
    ("St George Illawarra Dragons", "SGI"),
    ("Sydney Roosters", "SYD"),
    ("Wests Tigers", "WST"),
]

SEASON_ROUNDS = 27
MATCH_MINUTES = 80

# Ladder points
POINTS_WIN = 2
POINTS_DRAW = 1
POINTS_BYE = 2

# Player starting stats (0-100)
STARTING_STATS = {
    "speed": 40,
    "strength": 40,
    "passing": 40,
    "kicking": 40,
    "tackle": 40,
}
STARTING_ENERGY = 100
STARTING_CASH = 500

STARTING_RELATIONSHIPS = {
    "coach": 60,
    "teammates": 60,
    "fans": 50,
}

# If coach relationship falls below this, you're benched for the match.
BENCH_THRESHOLD = 25
# If teammates relationship falls below this, you get fewer passing moments.
COLD_SHOULDER_THRESHOLD = 35

# Player moments per match (min, max)
MOMENTS_PER_MATCH = (3, 5)

SHOP_ITEMS = [
    # (name, cost, description, effect_key, effect_value)
    ("Energy Drink", 50, "Restore 25% energy", "energy", 25),
    ("Sports Massage", 120, "Restore 60% energy", "energy", 60),
    ("Speed Boots", 400, "+3 Speed", "speed", 3),
    ("Gym Membership", 400, "+3 Strength", "strength", 3),
    ("Kicking Tee", 350, "+3 Kicking", "kicking", 3),
    ("Grip Gloves", 350, "+3 Passing", "passing", 3),
    ("Tackle Pads", 350, "+3 Tackle", "tackle", 3),
]
