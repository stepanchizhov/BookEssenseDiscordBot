"""
Shared utilities for Discord Essence Bot
Contains tag mappings, normalization functions, and autocomplete helpers
"""

import discord
from typing import Optional, List
from urllib.parse import urlparse

# Comprehensive tag mapping - maps all variations to the canonical display name
TAG_MAPPING = {
    # FANTASY
    'fantasy': 'Fantasy',
    'Fantasy': 'Fantasy',
    
    # ACTION
    'action': 'Action',
    'Action': 'Action',
    
    # ADVENTURE
    'adventure': 'Adventure',
    'Adventure': 'Adventure',
    
    # COMEDY
    'comedy': 'Comedy',
    'Comedy': 'Comedy',
    
    # DRAMA
    'drama': 'Drama',
    'Drama': 'Drama',
    
    # HORROR
    'horror': 'Horror',
    'Horror': 'Horror',
    
    # MYSTERY
    'mystery': 'Mystery',
    'Mystery': 'Mystery',
    
    # PSYCHOLOGICAL
    'psychological': 'Psychological',
    'Psychological': 'Psychological',
    
    # ROMANCE
    'romance': 'Romance',
    'Romance': 'Romance',
    
    # SATIRE
    'satire': 'Satire',
    'Satire': 'Satire',
    
    # SCI-FI
    'sci_fi': 'Sci-fi',
    'sci-fi': 'Sci-fi',
    'scifi': 'Sci-fi',
    'Sci-fi': 'Sci-fi',
    'Sci Fi': 'Sci-fi',
    'Science Fiction': 'Sci-fi',
    
    # SHORT STORY
    'one_shot': 'Short Story',
    'oneshot': 'Short Story',
    'Short Story': 'Short Story',
    'One Shot': 'Short Story',
    
    # TRAGEDY
    'tragedy': 'Tragedy',
    'Tragedy': 'Tragedy',
    
    # CONTEMPORARY
    'contemporary': 'Contemporary',
    'Contemporary': 'Contemporary',
    
    # HISTORICAL
    'historical': 'Historical',
    'Historical': 'Historical',
    
    # ANTI-HERO LEAD
    'anti_hero_lead': 'Anti-Hero Lead',
    'anti-hero_lead': 'Anti-Hero Lead',
    'antihero': 'Anti-Hero Lead',
    'Anti-Hero Lead': 'Anti-Hero Lead',
    'Anti Hero Lead': 'Anti-Hero Lead',
    'Antihero': 'Anti-Hero Lead',
    
    # ARTIFICIAL INTELLIGENCE
    'artificial_intelligence': 'Artificial Intelligence',
    'ai': 'Artificial Intelligence',
    'AI': 'Artificial Intelligence',
    'Artificial Intelligence': 'Artificial Intelligence',
    
    # ATTRACTIVE LEAD
    'attractive_lead': 'Attractive Lead',
    'Attractive Lead': 'Attractive Lead',
    
    # CYBERPUNK
    'cyberpunk': 'Cyberpunk',
    'Cyberpunk': 'Cyberpunk',
    
    # DUNGEON
    'dungeon': 'Dungeon',
    'Dungeon': 'Dungeon',
    
    # DYSTOPIA
    'dystopia': 'Dystopia',
    'Dystopia': 'Dystopia',
    
    # FEMALE LEAD
    'female_lead': 'Female Lead',
    'Female Lead': 'Female Lead',
    'FL': 'Female Lead',
    'fl': 'Female Lead',
    
    # FIRST CONTACT
    'first_contact': 'First Contact',
    'First Contact': 'First Contact',
    
    # GAMELIT
    'gamelit': 'GameLit',
    'GameLit': 'GameLit',
    'Gamelit': 'GameLit',
    
    # GENDER BENDER
    'gender_bender': 'Gender Bender',
    'Gender Bender': 'Gender Bender',
    'genderbender': 'Gender Bender',
    
    # GENETICALLY ENGINEERED
    'genetically_engineered': 'Genetically Engineered',
    'Genetically Engineered': 'Genetically Engineered',
    
    # GRIMDARK
    'grimdark': 'Grimdark',
    'Grimdark': 'Grimdark',
    
    # HARD SCI-FI
    'hard_sci_fi': 'Hard Sci-fi',
    'hard_sci-fi': 'Hard Sci-fi',
    'Hard Sci-fi': 'Hard Sci-fi',
    'Hard SciFi': 'Hard Sci-fi',
    
    # HAREM
    'harem': 'Harem',
    'Harem': 'Harem',
    
    # HIGH FANTASY
    'high_fantasy': 'High Fantasy',
    'High Fantasy': 'High Fantasy',
    'highfantasy': 'High Fantasy',
    
    # LITRPG
    'litrpg': 'LitRPG',
    'LitRPG': 'LitRPG',
    'LITRPG': 'LitRPG',
    'Litrpg': 'LitRPG',
    
    # LOW FANTASY
    'low_fantasy': 'Low Fantasy',
    'Low Fantasy': 'Low Fantasy',
    'lowfantasy': 'Low Fantasy',
    
    # MAGIC
    'magic': 'Magic',
    'Magic': 'Magic',
    
    # MALE LEAD
    'male_lead': 'Male Lead',
    'Male Lead': 'Male Lead',
    'ML': 'Male Lead',
    'ml': 'Male Lead',
    
    # MARTIAL ARTS
    'martial_arts': 'Martial Arts',
    'Martial Arts': 'Martial Arts',
    'martialarts': 'Martial Arts',
    
    # MULTIPLE LEAD
    'multiple_lead': 'Multiple Lead Characters',
    'Multiple Lead': 'Multiple Lead Characters',
    'Multiple Lead Characters': 'Multiple Lead Characters',
    'Multiple Leads': 'Multiple Lead Characters',
    
    # MYTHOS
    'mythos': 'Mythos',
    'Mythos': 'Mythos',
    
    # NON-HUMAN LEAD
    'non_human_lead': 'Non-Human Lead',
    'non-human_lead': 'Non-Human Lead',
    'nonhuman': 'Non-Human Lead',
    'Non-Human Lead': 'Non-Human Lead',
    'Non Human Lead': 'Non-Human Lead',
    
    # PORTAL FANTASY / ISEKAI
    'summoned_hero': 'Portal Fantasy / Isekai',
    'portal_fantasy': 'Portal Fantasy / Isekai',
    'isekai': 'Portal Fantasy / Isekai',
    'Portal Fantasy': 'Portal Fantasy / Isekai',
    'Portal Fantasy / Isekai': 'Portal Fantasy / Isekai',
    'Isekai': 'Portal Fantasy / Isekai',
    'Summoned Hero': 'Portal Fantasy / Isekai',
    
    # POST APOCALYPTIC
    'post_apocalyptic': 'Post Apocalyptic',
    'Post Apocalyptic': 'Post Apocalyptic',
    'postapocalyptic': 'Post Apocalyptic',
    'Post-Apocalyptic': 'Post Apocalyptic',
    
    # PROGRESSION
    'progression': 'Progression',
    'Progression': 'Progression',
    
    # READER INTERACTIVE
    'reader_interactive': 'Reader Interactive',
    'Reader Interactive': 'Reader Interactive',
    
    # REINCARNATION
    'reincarnation': 'Reincarnation',
    'Reincarnation': 'Reincarnation',
    
    # RULING CLASS
    'ruling_class': 'Ruling Class',
    'Ruling Class': 'Ruling Class',
    
    # SCHOOL LIFE
    'school_life': 'School Life',
    'School Life': 'School Life',
    'schoollife': 'School Life',
    
    # SECRET IDENTITY
    'secret_identity': 'Secret Identity',
    'Secret Identity': 'Secret Identity',
    
    # SLICE OF LIFE
    'slice_of_life': 'Slice of Life',
    'Slice of Life': 'Slice of Life',
    'sliceoflife': 'Slice of Life',
    'SOL': 'Slice of Life',
    'sol': 'Slice of Life',
    
    # SOFT SCI-FI
    'soft_sci_fi': 'Soft Sci-fi',
    'soft_sci-fi': 'Soft Sci-fi',
    'Soft Sci-fi': 'Soft Sci-fi',
    'Soft SciFi': 'Soft Sci-fi',
    
    # SPACE OPERA
    'space_opera': 'Space Opera',
    'Space Opera': 'Space Opera',
    'spaceopera': 'Space Opera',
    
    # SPORTS
    'sports': 'Sports',
    'Sports': 'Sports',
    
    # STEAMPUNK
    'steampunk': 'Steampunk',
    'Steampunk': 'Steampunk',
    
    # STRATEGY
    'strategy': 'Strategy',
    'Strategy': 'Strategy',
    
    # STRONG LEAD
    'strong_lead': 'Strong Lead',
    'Strong Lead': 'Strong Lead',
    
    # SUPER HEROES
    'super_heroes': 'Super Heroes',
    'Super Heroes': 'Super Heroes',
    'superheroes': 'Super Heroes',
    'Superheroes': 'Super Heroes',
    
    # SUPERNATURAL
    'supernatural': 'Supernatural',
    'Supernatural': 'Supernatural',
    
    # TIME LOOP
    'time_loop': 'Time Loop',
    'loop': 'Time Loop',
    'Time Loop': 'Time Loop',
    'timeloop': 'Time Loop',
    
    # TIME TRAVEL
    'time_travel': 'Time Travel',
    'Time Travel': 'Time Travel',
    'timetravel': 'Time Travel',
    
    # URBAN FANTASY
    'urban_fantasy': 'Urban Fantasy',
    'Urban Fantasy': 'Urban Fantasy',
    'urbanfantasy': 'Urban Fantasy',
    
    # VILLAINOUS LEAD
    'villainous_lead': 'Villainous Lead',
    'Villainous Lead': 'Villainous Lead',
    'villain': 'Villainous Lead',
    'Villain': 'Villainous Lead',
    
    # VIRTUAL REALITY
    'virtual_reality': 'Virtual Reality',
    'Virtual Reality': 'Virtual Reality',
    'VR': 'Virtual Reality',
    'vr': 'Virtual Reality',
    
    # WAR AND MILITARY
    'war_and_military': 'War and Military',
    'War and Military': 'War and Military',
    'military': 'War and Military',
    'Military': 'War and Military',
    
    # WUXIA
    'wuxia': 'Wuxia',
    'Wuxia': 'Wuxia',
    
    # XIANXIA
    'xianxia': 'Xianxia',
    'Xianxia': 'Xianxia',
    'cultivation': 'Xianxia',
    'Cultivation': 'Xianxia',    
    
    # TECHNOLOGICALLY ENGINEERED
    'technologically_engineered': 'Technologically Engineered',
    'Technologically Engineered': 'Technologically Engineered',

    # ADDITIONAL TAGS
    # CRAFTING
    'crafting': 'Crafting',
    'Crafting': 'Crafting',
    
    # KINGDOM BUILDING
    'kingdom_building': 'Kingdom Building',
    'kingdom-building': 'Kingdom Building',
    'Kingdom Building': 'Kingdom Building',
    'kingdombuilding': 'Kingdom Building',
    
    # MONSTER TAMING
    'monster_taming': 'Monster Taming',
    'monster-taming': 'Monster Taming',
    'Monster Taming': 'Monster Taming',
    'monstertaming': 'Monster Taming', 

    'necromancy': 'Necromancy', 
    'Necromancy': 'Necromancy', 

    'no_harem': 'No Harem', 
    'no-harem': 'No Harem', 
    'noharem': 'No Harem', 
    'No Harem': 'No Harem', 

    'no_romance': 'No Romance', 
    'no-romance': 'No Romance', 
    'No Romance': 'No Romance', 
    'noromance': 'No Romance', 

    'pirates': 'Pirates', 
    'Pirates': 'Pirates', 

    'political_intrigue': 'Political Intrigue', 
    'political-intrigue': 'Political Intrigue', 
    'Political Intrigue': 'Political Intrigue', 
    'politicalintrigue': 'Political Intrigue', 

    'space_exploration': 'Space Exploration', 
    'space-exploration': 'Space Exploration', 
    'Space Exploration': 'Space Exploration', 
    'spaceexploration': 'Space Exploration', 

    'vampires': 'Vampires',    
    'Vampires': 'Vampires',    

    # Technical Tags
    'ai_assisted': 'AI-Assisted Content',
    'aiassisted': 'AI-Assisted Content',
    'ai-assisted': 'AI-Assisted Content',
    'AI Assisted': 'AI-Assisted Content',
    'AI-Assisted': 'AI-Assisted Content',
    'ai_assisted_content': 'AI-Assisted Content',
    'aiassistedcontent': 'AI-Assisted Content',
    'ai-assisted-content': 'AI-Assisted Content',
    'AI Assisted Content': 'AI-Assisted Content',
    'AI-Assisted Content': 'AI-Assisted Content',

    'ai_generated': 'AI-Generated Content',
    'aigenerated': 'AI-Generated Content',
    'ai-generated': 'AI-Generated Content',
    'AI Generated': 'AI-Generated Content',
    'AI-Generated': 'AI-Generated Content',
    'ai_generated_content': 'AI-Generated Content',
    'aigeneratedcontent': 'AI-Generated Content',
    'ai-generated-content': 'AI-Generated Content',
    'AI Generated Content': 'AI-Generated Content',
    'AI-Generated Content': 'AI-Generated Content',

    'graphic_violence': 'Graphic Violence',
    'graphic-violence': 'Graphic Violence',
    'graphicviolence': 'Graphic Violence',
    'Graphic Violence': 'Graphic Violence',

    'profanity': 'Profanity',
    'Profanity': 'Profanity',

    'sensitive': 'Sensitive Content',
    'sensitive_content': 'Sensitive Content',
    'sensitive-content': 'Sensitive Content',
    'sensitivecontent': 'Sensitive Content',
    'Sensitive Content': 'Sensitive Content',

    'sexuality': 'Sexual Content', 
    'sexual_content': 'Sexual Content',
    'sexual-content': 'Sexual Content',
    'sexualcontent': 'Sexual Content',
    'Sexual Content': 'Sexual Content',
}

# Get unique display names for the choices
UNIQUE_TAGS = sorted(list(set(TAG_MAPPING.values())))

# Tag choices for slash commands (Discord limits to 25)
TAG_CHOICES = [
    discord.app_commands.Choice(name=tag, value=tag)
    for tag in UNIQUE_TAGS[:25]
]


def normalize_tag(tag: str) -> Optional[str]:
    """
    Normalize any tag input to its canonical display name
    
    Args:
        tag: The tag to normalize (can be in various formats)
        
    Returns:
        The canonical display name or None if not recognized
    """
    # Handle None or empty input
    if not tag:
        return None
        
    # First try exact match
    if tag in TAG_MAPPING:
        return TAG_MAPPING[tag]
    
    # Try case-insensitive match
    tag_lower = tag.lower()
    for key, value in TAG_MAPPING.items():
        if key.lower() == tag_lower:
            return value
    
    # Try removing spaces/underscores/hyphens
    tag_normalized = tag.replace(' ', '').replace('_', '').replace('-', '').lower()
    for key, value in TAG_MAPPING.items():
        key_normalized = key.replace(' ', '').replace('_', '').replace('-', '').lower()
        if key_normalized == tag_normalized:
            return value
    
    # If no match found, return None
    return None


async def tag_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[discord.app_commands.Choice[str]]:
    """
    Autocomplete function for tag selection that allows free input
    
    Args:
        interaction: The Discord interaction
        current: The current text being typed
        
    Returns:
        List of autocomplete choices (up to 25)
    """
    # Handle None input
    if current is None:
        current = ""
    
    # Get all unique tags
    all_tags = UNIQUE_TAGS
    
    # If user hasn't typed anything, show popular tags
    if not current:
        popular_tags = [
            'Fantasy', 'Magic', 'LitRPG', 'Progression', 'Action', 
            'Adventure', 'Romance', 'Female Lead', 'Male Lead', 'Dungeon',
            'High Fantasy', 'Urban Fantasy', 'Sci-fi', 'Horror', 'Comedy'
        ]
        return [
            discord.app_commands.Choice(name=tag, value=tag)
            for tag in popular_tags[:25]  # Discord limits to 25
        ]
    
    # Filter tags based on what user typed
    current_lower = current.lower()
    matching_tags = []
    
    # First, add exact matches and starts-with matches
    for tag in all_tags:
        if tag.lower().startswith(current_lower):
            matching_tags.append(tag)
    
    # Then add contains matches
    for tag in all_tags:
        if current_lower in tag.lower() and tag not in matching_tags:
            matching_tags.append(tag)
    
    # Also check against URL format
    for key, value in TAG_MAPPING.items():
        if current_lower in key.lower() and value not in matching_tags:
            matching_tags.append(value)
    
    # If user typed something that doesn't match any known tags,
    # still show it as an option (free-form input)
    normalized = normalize_tag(current)
    if not normalized and current not in matching_tags:
        matching_tags.insert(0, current)  # User's input at the top
    
    # Return up to 25 choices
    return [
        discord.app_commands.Choice(name=tag, value=tag)
        for tag in matching_tags[:25]
    ]


def extract_book_id_from_url(url: str) -> Optional[int]:
    """
    Extract book ID from Royal Road URL
    
    Args:
        url: The URL or book ID to parse
        
    Returns:
        The book ID as an integer or None if invalid
    """
    try:
        # Handle various URL formats:
        # https://www.royalroad.com/fiction/12345/book-title
        # https://royalroad.com/fiction/12345
        # 12345 (just the ID)
        
        if url.isdigit():
            return int(url)
            
        parsed = urlparse(url)
        if 'royalroad.com' in parsed.netloc:
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2 and path_parts[0] == 'fiction':
                return int(path_parts[1])
                
        return None
    except (ValueError, IndexError):
        return None


# All possible Rising Stars tags (for RS-specific commands)
ALL_RS_TAGS = [
    'main', 'action', 'adventure', 'anti-hero_lead', 'artificial_intelligence',
    'attractive_lead', 'comedy', 'contemporary', 'cyberpunk', 'drama', 'dungeon',
    'dystopia', 'fantasy', 'female_lead', 'first_contact', 'gamelit',
    'gender_bender', 'genetically_engineered', 'grimdark', 'hard_sci-fi',
    'harem', 'high_fantasy', 'historical', 'horror', 'litrpg', 'loop',
    'low_fantasy', 'magic', 'male_lead', 'martial_arts', 'multiple_lead',
    'mystery', 'mythos', 'non-human_lead', 'one_shot', 'post_apocalyptic',
    'progression', 'psychological', 'reader_interactive', 'reincarnation',
    'romance', 'ruling_class', 'satire', 'school_life', 'sci_fi',
    'secret_identity', 'slice_of_life', 'soft_sci-fi', 'space_opera',
    'sports', 'steampunk', 'strategy', 'strong_lead', 'summoned_hero',
    'super_heroes', 'supernatural', 'technologically_engineered',
    'time_travel', 'tragedy', 'urban_fantasy', 'villainous_lead',
    'virtual_reality', 'war_and_military', 'wuxia', 'xianxia',
    'sensitive', 'sexuality', 'ai_assisted', 'ai_generated', 'graphic_violence', 'profanity'
]

# Default tags for Rising Stars commands
DEFAULT_RS_TAGS = [
    'main', 'fantasy', 'sci_fi', 'litrpg', 'romance', 
    'action', 'adventure', 'comedy', 'drama', 'horror', 
    'mystery', 'psychological'
]
