# -*- coding: utf-8 -*-
"""Duelist profiles for NT Goat Studio.

theme : the duelist's signature cards (taken from Konami's own decks for that
        character), in PRIORITY order. A tier deck = tier staples + theme cards
        from the top until the deck has 40 cards. "@2" / "@3" = only from that
        tier upwards (keeps early decks fair).
boost : +1 for boss characters (one tier stronger, and Goat Max in the final
        stretch of the story).
max   : post-game "Goat Max" decks (best Goat Format deck close to the profile).
        Either {"deck": <archetype>} or {"base": <archetype>, "swap": "-n card / +n card"}.
"""

# ── generic support packages per tier ────────────────────────────────────────
TIER_NAMES = {1: "Rookie", 2: "Duelist", 3: "Expert", 4: "Goat Max"}

STAPLES = {
    1: """
2 Trap Hole
1 Fissure
1 Dust Tornado
1 Rush Recklessly
1 Waboku
1 Negate Attack
1 Shadow Spell
1 Spellbinding Circle
1 Raigeki Break
1 Reinforcements
1 Mystical Space Typhoon
""",
    2: """
1 Pot of Greed
1 Mystical Space Typhoon
1 Heavy Storm
1 Book of Moon
1 Nobleman of Crossout
1 Swords of Revealing Light
1 Premature Burial
1 Enemy Controller
1 Trap Hole
1 Dust Tornado
1 Sakuretsu Armor
1 Mirror Force
1 Call of the Haunted
1 Magic Cylinder
1 Waboku
1 Sangan
""",
    3: """
1 Pot of Greed
1 Graceful Charity
1 Delinquent Duo
1 Snatch Steal
1 Heavy Storm
1 Mystical Space Typhoon
1 Premature Burial
1 Swords of Revealing Light
2 Nobleman of Crossout
2 Book of Moon
2 Sakuretsu Armor
1 Mirror Force
1 Ring of Destruction
1 Torrential Tribute
1 Call of the Haunted
1 Bottomless Trap Hole
1 Sangan
1 Sinister Serpent
1 Magician of Faith
""",
}
FILLER = """
3 Trap Hole
2 Waboku
2 Negate Attack
2 Dust Tornado
2 Reinforcements
2 Rush Recklessly
2 Shadow Spell
2 Spellbinding Circle
2 Raigeki Break
1 Fissure
2 Magic Jammer
"""

# ── new Goat archetypes used by the profiles (added to the deck catalogue) ──
EXTRA_ARCHETYPES = {
    "Harpie Control": dict(name="Harpie Control", note="Wind Goat: Birdface, Hunting Ground, Elegant Egotist", main="""
2 Birdface
1 Harpie Lady 1
1 Harpie Lady 2
1 Harpie Lady 3
1 Cyber Harpie Lady
1 Harpie Lady Sisters
1 Harpie's Pet Dragon
1 Twin-Headed Behemoth
1 Injection Fairy Lily
1 Sangan
1 Sinister Serpent
2 Magician of Faith
1 D.D. Warrior Lady
1 Breaker the Magical Warrior
1 Spirit Reaper
2 Harpies' Hunting Ground
2 Elegant Egotist
1 Pot of Greed
1 Graceful Charity
1 Delinquent Duo
1 Snatch Steal
1 Heavy Storm
1 Mystical Space Typhoon
1 Premature Burial
1 Swords of Revealing Light
1 Nobleman of Crossout
2 Book of Moon
1 Scapegoat
2 Sakuretsu Armor
1 Mirror Force
1 Ring of Destruction
1 Torrential Tribute
1 Call of the Haunted
1 Ceasefire
""", extra=""),

    "Water Goat": dict(name="Water Goat", note="A Legendary Ocean, Mother Grizzly recruiters, Abyss Soldier", main="""
3 Mother Grizzly
2 Abyss Soldier
2 Penguin Soldier
1 The Legendary Fisherman
1 Amphibian Beast
1 Sangan
1 Sinister Serpent
2 Magician of Faith
1 Tribe-Infecting Virus
1 D.D. Warrior Lady
1 Breaker the Magical Warrior
1 Exiled Force
1 Spirit Reaper
2 A Legendary Ocean
1 Pot of Greed
1 Graceful Charity
1 Delinquent Duo
1 Snatch Steal
1 Heavy Storm
1 Mystical Space Typhoon
1 Premature Burial
1 Swords of Revealing Light
2 Nobleman of Crossout
2 Book of Moon
2 Sakuretsu Armor
1 Mirror Force
1 Ring of Destruction
1 Torrential Tribute
1 Call of the Haunted
1 Ceasefire
1 Bottomless Trap Hole
""", extra=""),

    "Insect Lock": dict(name="Insect Lock", note="Weevil's Insect Barrier + DNA Surgery lock with flip control", main="""
2 Man-Eater Bug
2 Needle Worm
2 Pinch Hopper
1 Insect Queen
1 Skull-Mark Ladybug
1 Parasite Paracide
1 Sangan
1 Sinister Serpent
2 Magician of Faith
1 Tribe-Infecting Virus
1 Morphing Jar
1 Cyber Jar
1 Tsukuyomi
1 D.D. Warrior Lady
3 Book of Moon
1 Book of Taiyou
1 Pot of Greed
1 Graceful Charity
1 Delinquent Duo
1 Snatch Steal
1 Heavy Storm
1 Mystical Space Typhoon
1 Premature Burial
1 Swords of Revealing Light
1 Nobleman of Crossout
1 Insect Barrier
1 DNA Surgery
2 Sakuretsu Armor
1 Mirror Force
1 Ring of Destruction
1 Torrential Tribute
1 Call of the Haunted
1 Ceasefire
""", extra=""),

    "Blue-Eyes Gate": dict(name="Blue-Eyes Gate", note="Kaiba: Reasoning / Monster Gate into Blue-Eyes, Cyber-Stein into Ultimate", main="""
3 Blue-Eyes White Dragon
2 Vorse Raider
1 La Jinn the Mystical Genie of the Lamp
1 Lord of D.
1 Cyber-Stein
1 Jinzo
1 Black Luster Soldier - Envoy of the Beginning
3 Reasoning
3 Monster Gate
1 The Flute of Summoning Dragon
2 Enemy Controller
1 Pot of Greed
1 Graceful Charity
1 Card Destruction
2 Upstart Goblin
1 Heavy Storm
1 Premature Burial
2 Scapegoat
1 Snatch Steal
1 Delinquent Duo
1 Swords of Revealing Light
1 Mystical Space Typhoon
1 Nobleman of Crossout
1 Book of Moon
1 Dimension Fusion
1 Mirror Force
1 Ring of Destruction
1 Torrential Tribute
1 Call of the Haunted
1 Ceasefire
""", extra="""
1 Blue-Eyes Ultimate Dragon
1 XYZ-Dragon Cannon
1 Master of Oz
"""),

    "Fiend Burn Control": dict(name="Lava Control", note="Marik: Lava Golem + Fiend control (Helpoemer, Vampire Lord)", main="""
2 Lava Golem
1 Helpoemer
1 Vampire Lord
1 Newdoria
1 Mystic Tomato
1 Tribe-Infecting Virus
1 Sangan
1 Sinister Serpent
2 Magician of Faith
1 Twin-Headed Behemoth
1 Breaker the Magical Warrior
1 D.D. Warrior Lady
1 Spirit Reaper
1 Tsukuyomi
1 Black Luster Soldier - Envoy of the Beginning
1 Exiled Force
2 Scapegoat
1 Pot of Greed
1 Graceful Charity
1 Delinquent Duo
1 Snatch Steal
1 Heavy Storm
1 Mystical Space Typhoon
1 Premature Burial
1 Swords of Revealing Light
2 Nobleman of Crossout
2 Book of Moon
1 Creature Swap
2 Sakuretsu Armor
1 Mirror Force
1 Ring of Destruction
1 Torrential Tribute
1 Call of the Haunted
1 Ceasefire
""", extra=""),

    "Gate Guardian Gate": dict(name="Gate Guardian Gate", note="Para: Reasoning/Monster Gate into Sanga, Kazejin, Suijin", main="""
1 Sanga of the Thunder
1 Kazejin
1 Suijin
1 Jinzo
1 Dark Magician of Chaos
1 Black Luster Soldier - Envoy of the Beginning
2 Thunder Dragon
2 Cannon Soldier
3 Reasoning
3 Monster Gate
1 Dimension Fusion
1 Pot of Greed
1 Graceful Charity
1 Card Destruction
2 Upstart Goblin
1 Heavy Storm
1 Giant Trunade
1 Premature Burial
3 Scapegoat
1 Snatch Steal
1 Delinquent Duo
1 Swords of Revealing Light
1 Mystical Space Typhoon
1 Brain Control
1 Nobleman of Crossout
1 Book of Moon
1 Mirror Force
1 Ring of Destruction
1 Torrential Tribute
1 Call of the Haunted
1 Ceasefire
""", extra=""),
}

# ── profiles ─────────────────────────────────────────────────────────────────
GOATX = "Goat Control A"
P = {}

P["01"] = dict(name="Yami Yugi", boost=1, theme="""
1 Dark Magician
1 Dark Magician Girl
2 Skilled Dark Magician
1 Dark Magician of Chaos @2
1 Dark Magic Curtain
1 Buster Blader
1 Breaker the Magical Warrior @2
1 Black Luster Soldier - Envoy of the Beginning @3
2 Obnoxious Celtic Guard
2 Big Shield Gardna
2 Kycoo the Ghost Destroyer
1 Magical Hats
1 Summoned Skull
1 Skull Archfiend of Lightning
2 Zombyra the Dark
1 Kuriboh
1 Celtic Guardian
1 Mystical Elf
2 Giant Soldier of Stone
1 Dark Magic Attack
1 Mystic Box
1 Magic-Arm Shield
2 Spellbinding Circle
1 Rope of Spirit
""", max=[dict(deck="Chaos Control"), dict(deck="Goat Control A"), dict(deck="Reasoning Gate A"),
          dict(deck="Chaos Return A"), dict(deck="Goat Control B")])

P["02"] = dict(name="Yugi Muto", boost=0, theme="""
1 Dark Magician
1 Gaia The Fierce Knight
2 Valkyrion the Magna Warrior
1 Alpha The Magnet Warrior
2 Beta The Magnet Warrior
2 Gamma The Magnet Warrior
1 Buster Blader
1 Summoned Skull
1 Dark Magician of Chaos @3
2 Skilled Dark Magician
2 Mystical Elf
2 Obnoxious Celtic Guard
2 Giant Rat
1 Curse of Dragon
2 Celtic Guardian
2 Winged Dragon,Guardian of the Fortress #1
1 Zombyra the Dark
1 Magical Hats
1 Mystic Box
2 Rock Bombardment
1 Dark Magic Attack
2 Lightforce Sword
""", max=[dict(deck="Goat Control B"), dict(deck="Chaos Control"), dict(deck="Reasoning Gate A"),
          dict(deck="Chaos Return A")])

P["03"] = dict(name="Seto Kaiba", boost=1, theme="""
3 Blue-Eyes White Dragon
3 Vorse Raider
2 La Jinn the Mystical Genie of the Lamp
2 Enemy Controller
1 Lord of D.
1 The Flute of Summoning Dragon
3 X-Head Cannon
3 Y-Dragon Head
3 Z-Metal Tank
2 Battle Ox
2 Cyber-Tech Alligator
2 Gilasaurus
1 Kycoo the Ghost Destroyer
1 Ryu-Kishin Powered
2 Ancient Lamp
1 Swordstalker
2 Cost Down
1 Fusion Gate
1 Negate Attack
""", max=[dict(deck="Blue-Eyes Gate"), dict(deck="Chaos Control", swap="-1 Card Destruction\n+1 Enemy Controller"),
          dict(deck="Machine Gate")])

P["04"] = dict(name="Joey Wheeler", boost=0, theme="""
1 Red-Eyes B. Dragon
2 Axe Raider
2 Gearfried the Iron Knight
2 Panther Warrior
2 Goblin Attack Force
2 Marauding Captain
1 Jinzo @2
2 Rocket Warrior
2 Zombyra the Dark
2 Time Wizard
1 Gilford the Lightning
2 Alligator's Sword
2 Baby Dragon
1 Little-Winguard
2 Graceful Dice
1 Skull Dice
1 Reinforcement of the Army
2 Tiger Axe
1 Kunai with Chain
1 Fairy Box
""", max=[dict(deck="Warrior Toolbox", swap="-1 Command Knight\n+1 Jinzo"), dict(deck="Warrior Beat"),
          dict(deck="Goat Control B")])

P["05"] = dict(name="Mai Valentine", boost=0, theme="""
2 Harpie Lady Sisters
1 Harpie Lady 1
1 Harpie Lady 2
1 Harpie Lady 3
1 Cyber Harpie Lady
1 Harpie's Pet Dragon
2 Birdface
2 Elegant Egotist
2 Harpies' Hunting Ground
2 Amazon Archer
2 Flying Kamakiri #1
1 Injection Fairy Lily @2
2 Cyber Shield
2 Triangle Ecstasy Spark
2 Mirror Wall
1 Reload
1 Malevolent Nuzzler
""", max=[dict(deck="Harpie Control"), dict(deck="Goat Control B")])

P["06"] = dict(name="Yami Bakura", boost=1, theme="""
3 Dark Necrofear
3 Headless Knight
2 Night Assailant
1 The Earl of Demise
2 Wall of Illusion
2 Kycoo the Ghost Destroyer
2 Kryuel
1 Destiny Board
1 Spirit Message "I"
1 Spirit Message "N"
1 Spirit Message "A"
1 Spirit Message "L"
1 Mask of Darkness
1 The Portrait's Secret
2 Slate Warrior
2 Giant Germ
1 Dimension Fusion
1 Return from the Different Dimension
1 Magic Jammer
2 Bark of Dark Ruler
""", max=[dict(deck="Chaos Return B"), dict(deck="Zombies A"), dict(deck="Goat Control A")])

P["07"] = dict(name="Yami Marik", boost=1, theme="""
2 Lava Golem
1 Helpoemer
1 Vampire Lord
1 Newdoria
1 Viser Des
1 Dark Jeroid
1 Gil Garth
1 Revival Jam
1 Twin-Headed Behemoth
2 Nightmare Wheel
""", max=[dict(deck="Goat Control A"), dict(deck="Fiend Burn Control")])

P["08"] = dict(name="Marik Ishtar", boost=1, theme="""
2 Lava Golem
2 Helpoemer
1 Vampire Lord
1 Viser Des
1 Dark Jeroid
2 Gil Garth
2 Newdoria
1 Revival Jam
1 Twin-Headed Behemoth
2 Nightmare Wheel
""", max=[dict(deck="Fiend Burn Control"), dict(deck="Goat Control A"), dict(deck="Zombies B")])

P["09"] = dict(name="Odion", boost=0, theme="""
3 Mystical Beast Serket
3 Embodiment of Apophis
3 Nimble Momonga
2 Night Assailant
2 Mask of Darkness
3 Judgment of Anubis
3 Jar of Greed
2 Cathedral of Nobles
1 Magic Jammer
2 Spirit Reaper
1 Morphing Jar @2
""", max=[dict(deck="Flip Control"), dict(deck="Goat Control B")])

P["10"] = dict(name="Ishizu Ishtar", boost=1, theme="""
3 Thunder Dragon
2 Zolga
2 Agido
3 Morphing Jar #2
3 Needle Worm
1 Mask of Darkness
1 Cyber Jar @2
1 Morphing Jar @2
2 Reasoning
2 A Cat of Ill Omen
1 Book of Taiyou
3 Jar of Greed
3 Hiro's Shadow Scout
2 Cathedral of Nobles
2 Reload
""", max=[dict(deck="Goat Control A"), dict(deck="Flip Control")])

P["11"] = dict(name="Pegasus", boost=1, theme="""
3 Toon World
2 Toon Table of Contents
1 Relinquished
1 Thousand-Eyes Idol
1 Black Illusion Ritual
2 Toon Gemini Elf
2 Toon Masked Sorcerer
2 Toon Cannon Soldier
1 Toon Summoned Skull
1 Toon Dark Magician Girl
1 Blue-Eyes Toon Dragon
2 Toon Mermaid
2 Toon Goblin Attack Force
1 Toon Alligator
1 Toon Defense
1 Royal Decree
1 Magic Jammer
""", extra="3 Thousand-Eyes Restrict",
    max=[dict(deck="Goat Control A", swap="-1 Morphing Jar\n+1 Relinquished"), dict(deck="Reasoning Gate A"),
         dict(deck="Chaos Return B")])

P["12"] = dict(name="Bandit Keith", boost=0, theme="""
2 Barrel Dragon
3 Robotic Knight
3 Mechanicalchaser
3 Gradius
3 Blast Sphere
1 Slot Machine
1 Launcher Spider
2 Limiter Removal
2 Machine Conversion Factory
2 Metalmorph
1 Cannon Soldier
2 Time Machine
1 Pendulum Machine
""", max=[dict(deck="Machine Gate")])

P["13"] = dict(name="Strings", boost=0, theme="""
3 Revival Jam
3 Humanoid Slime
2 Worm Drake
2 Abyss Soldier
2 Mother Grizzly
1 Penguin Soldier
2 Jam Breeding Machine
2 Jam Defender
1 A Legendary Ocean
1 Suijin
1 Granadora
2 Ameba
1 Creature Swap
""", extra="2 Humanoid Worm Drake",
    max=[dict(deck="Water Goat", swap="-1 Amphibian Beast\n-1 The Legendary Fisherman\n+2 Revival Jam")])

P["14"] = dict(name="Arkana", boost=0, theme="""
3 Dark Magician
3 Dark Elf
2 Rogue Doll
2 Aqua Madoor
2 Skilled Dark Magician
3 Nimble Momonga
2 Dark Magic Curtain
2 Ectoplasmer
1 Thousand Knives
1 Dark Magic Attack
2 Silent Fiend
""", max=[dict(deck="Chaos Return B", swap="-1 Jinzo\n+1 Dark Magician")])

P["15"] = dict(name="Rare Hunter", boost=0, theme="""
1 Exodia the Forbidden One
1 Left Arm of the Forbidden One
1 Left Leg of the Forbidden One
1 Right Arm of the Forbidden One
1 Right Leg of the Forbidden One
3 Royal Magical Library
3 Thunder Dragon
3 Toon Table of Contents
2 Jar of Greed
2 Stone Statue of the Aztecs
1 Toon Cannon Soldier
2 Last Will
""", max=[dict(deck="Exodia Library")])

P["17"] = dict(name="Solomon", boost=0, theme="""
1 Exodia the Forbidden One
1 Left Arm of the Forbidden One
1 Left Leg of the Forbidden One
1 Right Arm of the Forbidden One
1 Right Leg of the Forbidden One
3 Pyramid Turtle
2 Guardian Sphinx
3 Horn Imp
3 The Snake Hair
2 Call of the Mummy
2 Swarm of Scarabs
1 Mask of Darkness
2 Poison of the Old Man
1 Firewing Pegasus
2 Dark Coffin
1 Emergency Provisions
""", max=[dict(deck="Exodia Library"), dict(deck="Zombies A")])

P["19"] = dict(name="Tea Gardner", boost=0, theme="""
2 Dark Magician Girl
3 Red Archery Girl
3 Skelengel
2 Dancing Fairy
3 Mokey Mokey
2 Petit Moth
2 Oscillo Hero #2
2 Penguin Knight
2 Gift of The Mystical Elf
2 Rain of Mercy
2 Breath of Light
1 Elf's Light
2 Solemn Wishes
1 Book of Taiyou
""", max=[dict(deck="Goat Control A", name="Fairy Goat",
               swap="-1 Morphing Jar\n-1 Spirit Reaper\n-1 Exiled Force\n-1 Jinzo\n+1 Dark Magician Girl\n+2 Shining Angel\n+1 Injection Fairy Lily")])

P["20"] = dict(name="Serenity", boost=0, theme="""
2 Gyakutenno Megami
3 Red Archery Girl
2 Marie the Fallen One
3 Amazon Archer
2 Goddess of Whim
2 Princess of Tsurugi
3 Witch's Apprentice
1 Goddess with the Third Eye
2 Chorus of Sanctuary
2 Horn of Light
3 Numinous Healer
2 Rain of Mercy
""", max=[dict(deck="Chaos Recruiter", name="Angel Chaos", swap="-1 Night Assailant\n+1 Marie the Fallen One")])

P["21"] = dict(name="Rex Raptor", boost=0, theme="""
3 Two-Headed King Rex
3 Gilasaurus
2 Megazowler
2 Sword Arm of Dragon
3 Uraby
3 Crawling Dragon #2
2 Giant Rat
2 Mad Sword Beast
1 Red-Eyes B. Dragon
2 Wasteland
3 Raise Body Heat
1 Jar of Greed
""", max=[dict(deck="Zoo", name="Dino Zoo",
               swap="-1 Berserk Gorilla\n-1 King Tiger Wanghu\n-1 Chiron the Mage\n+2 Gilasaurus\n+1 Two-Headed King Rex")])

P["22"] = dict(name="Espa Roba", boost=0, theme="""
1 Jinzo @2
2 Jinzo #7
3 Cyber Raider
2 The Fiend Megacyber
3 The Illusory Gentleman
3 Hiro's Shadow Scout
2 Big Eye
3 Oscillo Hero #2
1 Reflect Bounder
3 Mind Control
2 Senri Eye
2 Mind Wipe
3 The Eye of Truth
""", max=[dict(deck="Reasoning Gate B"), dict(deck="Reasoning Gate A")])

P["23"] = dict(name="Weevil", boost=0, theme="""
3 Insect Queen
3 Pinch Hopper
2 Man-Eater Bug
2 Skull-Mark Ladybug
2 Parasite Paracide
1 Insect Barrier
2 DNA Surgery
3 Cocoon of Evolution
1 Great Moth
2 Giant Flea
2 Jirai Gumo
1 Big Insect
1 Swarm of Locusts
2 Multiplication of Ants
1 Forest
""", max=[dict(deck="Insect Lock")])

P["24"] = dict(name="Mako", boost=0, theme="""
3 Great White
2 The Legendary Fisherman
2 Amphibian Beast
3 Mother Grizzly
2 A Legendary Ocean
1 Abyss Soldier @2
3 Jellyfish
1 Fortress Whale
1 Kairyu-Shin
2 Giant Red Seasnake
3 Fiend Kraken
2 Catapult Turtle
2 Tornado Wall
""", max=[dict(deck="Water Goat")])

P["25"] = dict(name="Mokuba", boost=0, theme="""
3 Des Koala
1 Big Koala
3 Torike
3 Griffore
2 Dark Rabbit
1 Ryu-Ran
1 Rude Kaiser
2 Penguin Soldier
2 Toon Alligator
2 Krokodilus
2 Forest
2 The Big March of Animals
2 Beast Fangs
2 Stray Lambs
""", max=[dict(deck="Zoo", name="Koala Zoo",
               swap="-1 Chiron the Mage\n-1 King Tiger Wanghu\n+1 Des Koala\n+1 Big Koala")])

P["26"] = dict(name="Gozaburo", boost=1, theme="""
2 Exodia Necross
2 Contract with Exodia
1 Exodia the Forbidden One
1 Left Arm of the Forbidden One
1 Left Leg of the Forbidden One
1 Right Arm of the Forbidden One
1 Right Leg of the Forbidden One
3 Kycoo the Ghost Destroyer
2 Slate Warrior
3 Foolish Burial
""", max=[dict(deck="Exodia Library")])

P["27"] = dict(name="Noah", boost=1, theme="""
3 Shinato, King of a Higher Plane
2 Shinato's Ark
2 Airknight Parshath
2 Tsukuyomi
3 Dunames Dark Witch
2 Dancing Fairy
3 Manju of the Ten Thousand Hands
2 The Forgiving Maiden
2 The Sanctuary in the Sky
1 Swords of Concealing Light
""", max=[dict(deck="Goat Control A")])

P["28"] = dict(name="Rebecca", boost=0, theme="""
3 Fire Princess
3 Cannon Soldier
3 Dancing Fairy
2 Skull-Mark Ladybug
1 Marie the Fallen One
1 Injection Fairy Lily @2
2 Servant of Catabolism
2 Level Limit - Area B
2 Gravity Bind
1 Poison of the Old Man
2 Solemn Wishes
""", max=[dict(deck="Burn", swap="-1 Des Koala\n-1 Lava Golem\n+2 Fire Princess")])

P["29"] = dict(name="Lumis", boost=0, theme="""
2 Airknight Parshath @2
2 Melchid the Four-Face Beast
2 Grand Tiki Elder
2 Dunames Dark Witch
2 Shining Angel
2 Maha Vailo
2 Banisher of the Light
1 Moisture Creature
3 Mask of Brutality
2 Mask of the Accursed
1 Mask of Restrict
1 Mask of Dispel
1 Compulsory Evacuation Device
""", max=[dict(deck="Goat Control B")])

P["30"] = dict(name="Umbra", boost=0, theme="""
3 Shining Abyss
2 Vampire Lord
2 The Masked Beast
1 Curse of the Masked Beast
1 Nuvia the Wicked
2 Night Assailant
2 Wall of Illusion
2 Zombyra the Dark
2 Mask of Brutality
2 Mask of the Accursed
2 Mystic Plasma Zone
""", max=[dict(deck="Zombies A")])

P["31"] = dict(name="PaniK", boost=0, theme="""
3 Castle of Dark Illusions
2 King of Yamimakai
2 Dark Chimera
2 Sorcerer of the Doomed
1 Reaper of the Cards
1 Metal Guardian
2 Pyramid Turtle
2 Dragon Zombie
2 The Snake Hair
2 Dark Artist
2 Yami
3 Shadow Spell
2 Swords of Concealing Light
2 Dark Mirror Force
""", max=[dict(deck="Zombies B")])

P["32"] = dict(name="Para", boost=0, theme="""
1 Gate Guardian
1 Sanga of the Thunder
1 Kazejin
1 Suijin
3 Jirai Gumo
2 Sorcerer of the Doomed
2 Cannon Soldier
2 Gilasaurus
3 Giant Germ
2 Tribute Doll
2 Judgment of Anubis
2 Second Coin Toss
""", max=[dict(deck="Gate Guardian Gate")])

P["33"] = dict(name="Dox", boost=0, theme="""
2 Labyrinth Wall
1 Wall Shadow
1 Dungeon Worm
1 Shadow Ghoul
1 Monster Tamer
3 Jirai Gumo
2 Cannon Soldier
3 Giant Rat
2 The Statue of Easter Island
2 Magical Labyrinth
2 Shield & Sword
2 Judgment of Anubis
""", max=[dict(deck="Burn")])

P["34"] = dict(name="Bonz", boost=0, theme="""
2 Pumpking the King of Ghosts
3 Armored Zombie
3 Clown Zombie
2 Dragon Zombie
2 Zanki
2 Crawling Dragon
3 The Snake Hair
2 Castle of Dark Illusions
2 Vengeful Bog Spirit
2 Skull Lair
2 Skull Invitation
2 Curse of Fiend
""", max=[dict(deck="Zombies A")])

P["35"] = dict(name="Gansley (Big 1)", boost=0, theme="""
3 Mother Grizzly
2 Abyss Soldier
2 Giant Red Seasnake
2 Amphibian Beast
2 Suijin
2 Revival Jam
1 Penguin Soldier
1 The Legendary Fisherman
1 Melchid the Four-Face Beast
2 Wall of Illusion
3 A Legendary Ocean
2 Tornado Wall
""", max=[dict(deck="Water Goat")])

P["36"] = dict(name="Crump (Big 2)", boost=0, theme="""
3 Penguin Soldier
3 Mother Grizzly
3 Giant Red Seasnake
2 Catapult Turtle
2 Abyss Soldier
1 Penguin Knight
2 Granadora
3 A Legendary Ocean
2 Level Limit - Area B
2 Gravity Bind
""", max=[dict(deck="Flip Control")])

P["37"] = dict(name="Johnson (Big 3)", boost=0, theme="""
3 Thunder Dragon
3 Royal Magical Library
3 Judge Man
3 Banisher of the Light
2 Skelengel
3 Slate Warrior
1 Berserk Gorilla
2 Return from the Different Dimension
2 Non Aggression Area
""", extra="2 Twin-Headed Thunder Dragon", max=[dict(deck="Reasoning Gate A")])

P["38"] = dict(name="Nesbitt (Big 4)", boost=0, theme="""
1 Barrel Dragon
2 Machine King
3 Gradius
3 Gear Golem the Moving Fortress
3 Mechanicalchaser
2 Blast Sphere
1 Robotic Knight
1 Cannon Soldier
1 Reflect Bounder @2
2 Gradius' Option
2 Limiter Removal
2 7 Completed
""", max=[dict(deck="Machine Gate")])

P["39"] = dict(name="Leichter (Big 5)", boost=0, theme="""
3 Satellite Cannon
2 Airknight Parshath
3 Shining Angel
1 Jinzo @2
2 Royal Magical Library
1 Maha Vailo
1 Marie the Fallen One
1 Injection Fairy Lily @2
2 Luminous Spark
2 Royal Decree
1 Wave-Motion Cannon
""", max=[dict(deck="Chaos Control")])

P["40"] = dict(name="Bakura", boost=0, theme="""
3 Dragon Zombie
3 Armored Zombie
3 Headless Knight
3 Clown Zombie
3 Pyramid Turtle
2 Patrician of Darkness
2 The Gross Ghost of Fled Dreams
1 The Portrait's Secret
2 Skull Servant
2 Book of Life
1 Call of the Mummy
2 Ectoplasmer
2 Violet Crystal
""", max=[dict(deck="Zombies B")])

PROFILES = P

# Special / tournament decks (Beginner's Cup "bc", Expert Cup "ec", wild "yasei")
SPECIAL = {
    "bc1.ydc": ("04", 1), "bc2.ydc": ("03", 1),
    "ec1.ydc": ("01", 3), "ec2.ydc": ("40", 3),
    "yasei.ydc": ("25", 2),
}

# Developer decks found unused in the ROM (selectable in the Studio)
DEV_DECKS = {
    "ojama.ydc": "Ojama Lock (unused developer deck)",
    "countdown.ydc": "Final Countdown stall (unused developer deck)",
    "ganseki.ydc": "Stone / Rock wall (unused developer deck)",
    "e3_013.ydc": "E3 2005 demo - Yami Yugi",
    "e3_033.ydc": "E3 2005 demo - Kaiba XYZ",
    "e3_043.ydc": "E3 2005 demo - Joey",
    "e3_player.ydc": "E3 2005 demo - player deck",
    "default_test.ydc": "Developer test deck",
}
