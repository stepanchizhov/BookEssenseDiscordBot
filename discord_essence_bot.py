import discord
from discord.ext import commands
import aiohttp
import json
import os
from typing import Optional
import logging
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import io
import re
from urllib.parse import urlparse, parse_qs

from shoutout_module import ShoutoutModule


# Set up logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger('discord')

logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.getLogger('matplotlib.category').setLevel(logging.WARNING)

# Bot configuration
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
WP_API_URL = os.getenv('WP_API_URL', 'https://stepan.chizhov.com')
WP_BOT_TOKEN = os.getenv('WP_BOT_TOKEN')

logger.info(f"[STARTUP] Bot Token exists: {'Yes' if BOT_TOKEN else 'No'}")
logger.info(f"[STARTUP] WP URL: {WP_API_URL}")
logger.info(f"[STARTUP] WP Bot Token exists: {'Yes' if WP_BOT_TOKEN else 'No'}")
logger.info(f"[STARTUP] WP Bot Token value: {WP_BOT_TOKEN[:10]}..." if WP_BOT_TOKEN else "[STARTUP] WP Bot Token is EMPTY!")

# Initialize bot with command prefix (even though we'll use slash commands)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

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
    
    # CULTIVATION (bonus tag not in standard RR)
    # 'cultivation': 'Cultivation',
    # 'Cultivation': 'Cultivation',
    
    # TECHNOLOGICALLY ENGINEERED
    'technologically_engineered': 'Technologically Engineered',
    'Technologically Engineered': 'Technologically Engineered',
}

# Get unique display names for the choices
UNIQUE_TAGS = sorted(list(set(TAG_MAPPING.values())))

# Tag choices for the slash command (Discord limits to 25)
TAG_CHOICES = [
    discord.app_commands.Choice(name=tag, value=tag)
    for tag in UNIQUE_TAGS[:25]
]

# Track command usage for promotional messages
command_counter = 0

def get_promotional_field(force_show=False):
    """
    Get promotional field for embeds based on command counter
    
    Args:
        force_show (bool): Force showing a promotional message regardless of counter
    
    Returns:
        dict: Field data with name and value, or None if no promo should be shown
    """
    global command_counter
    
    # Only show promotional messages every 2 commands (or if forced)
    if not force_show and command_counter % 2 != 0:
        return None
    
    # Define all promotional messages
    promo_messages = [
        {
            "text": "📖 You can also read Stepan Chizhov's",
            "url": "https://www.royalroad.com/fiction/105229/",
            "link_text": "The Dark Lady's Guide to Villainy!"
        },
        {
            "text": "❤️ If you like this and other tools made by Stepan Chizhov:",
            "url": "https://www.patreon.com/stepanchizhov",
            "link_text": "Support his work on Patreon!"
        },
        {
            "text": "🔍 Find more analytical tools for Royal Road authors and readers!",
            "url": "https://stepan.chizhov.com",
            "link_text": "Visit stepan.chizhov.com"
        },
        {
            "text": "💬 Need help or have suggestions?",
            "url": "https://discord.gg/xvw9vbvrwj",
            "link_text": "Join our Support Discord"
        },
        {
            "text": "📚 Join discussions about Royal Road and analytics!",
            "url": "https://discord.gg/7Xrrf3Q5zp",
            "link_text": "Immersive Ink Community Discord"
        }
    ]
    
    # Rotate through promotional messages based on how many promos have been shown
    promo_index = (command_counter // 2 - 1) % len(promo_messages)
    promo = promo_messages[promo_index]
    
    return {
        "name": "━━━━━━━━━━━━━━━━━━━━━",
        "value": f"{promo['text']}\n[**{promo['link_text']}**]({promo['url']})",
        "inline": False
    }

def add_promotional_field(embed, force_show=False):
    """
    Add promotional field to an embed if conditions are met
    
    Args:
        embed (discord.Embed): The embed to add the field to
        force_show (bool): Force showing a promotional message regardless of counter
    
    Returns:
        discord.Embed: The embed with promotional field added (if applicable)
    """
    promo_field = get_promotional_field(force_show)
    
    if promo_field:
        embed.add_field(
            name=promo_field["name"],
            value=promo_field["value"],
            inline=promo_field["inline"]
        )
    
    return embed

def normalize_tag(tag: str) -> str:
    """Normalize any tag input to its canonical display name"""
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

def extract_book_id_from_url(url):
    """Extract book ID from Royal Road URL"""
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

# Updated parse_days_parameter function to handle date ranges - NOW DEFAULTS TO 'all'
def parse_days_parameter(days_str):
    """Parse the days parameter - supports numbers, 'all', or date ranges - DEFAULTS TO 'all'"""
    if days_str.lower() == 'all':
        return 'all'
    
    # Check if it's a date range (YYYY-MM-DD:YYYY-MM-DD)
    if ':' in days_str:
        try:
            start_date, end_date = days_str.split(':')
            # Validate date format
            datetime.strptime(start_date.strip(), '%Y-%m-%d')
            datetime.strptime(end_date.strip(), '%Y-%m-%d')
            return {
                'type': 'date_range',
                'start_date': start_date.strip(),
                'end_date': end_date.strip()
            }
        except ValueError:
            return 'all'  # Default to 'all' if date range is invalid
    
    # Check if it's a single date (from that date to now)
    if '-' in days_str and len(days_str) == 10:  # YYYY-MM-DD format
        try:
            datetime.strptime(days_str.strip(), '%Y-%m-%d')
            return {
                'type': 'from_date',
                'start_date': days_str.strip()
            }
        except ValueError:
            pass  # Fall through to number parsing
    
    # Try to parse as number of days
    try:
        days = int(days_str)
        if days <= 0:
            return 'all'  # Default to 'all' for invalid input
        return days
    except ValueError:
        return 'all'  # Default to 'all' for invalid input

def trim_leading_zeros(labels, data, timestamps=None):
    """
    Trim leading zeros from the data to start from first meaningful data point
    Returns trimmed labels, data, and timestamps
    """
    if not labels or not data or len(labels) != len(data):
        return labels, data, timestamps
    
    # Find the first non-zero data point to start from
    first_nonzero_index = 0
    for i, value in enumerate(data):
        if value > 0:
            first_nonzero_index = i
            break
    
    # Trim the data to start from first meaningful point
    if first_nonzero_index > 0:
        labels = labels[first_nonzero_index:]
        data = data[first_nonzero_index:]
        if timestamps:
            timestamps = timestamps[first_nonzero_index:]
    
    return labels, data, timestamps

def parse_dates_from_labels(labels, timestamps=None):
    """
    Convert labels to datetime objects for proper date scaling
    """
    date_objects = []
    
    if timestamps:
        # Use provided timestamps if available
        try:
            for ts in timestamps:
                if isinstance(ts, (int, float)):
                    date_objects.append(datetime.fromtimestamp(ts))
                else:
                    date_objects.append(datetime.strptime(str(ts), '%Y-%m-%d %H:%M:%S'))
            return date_objects
        except:
            pass  # Fall back to parsing labels
    
    # Parse from labels
    for i, label in enumerate(labels):
        try:
            if isinstance(label, str):
                if len(label.split()) == 2:  # "Jan 15" format
                    current_year = datetime.now().year
                    date_objects.append(datetime.strptime(f"{label} {current_year}", '%b %d %Y'))
                else:
                    date_objects.append(datetime.strptime(label, '%Y-%m-%d'))
            else:
                date_objects.append(label)
        except:
            # If parsing fails, create a sequential date based on previous dates
            if date_objects:
                last_date = date_objects[-1]
                date_objects.append(last_date + timedelta(days=1))
            else:
                # Start from a reasonable date if we have no context
                base_date = datetime.now() - timedelta(days=len(labels))
                date_objects.append(base_date + timedelta(days=i))
    
    return date_objects

async def get_book_chart_data(book_input, days_param, session):
    """Fetch chart data for a book from WordPress API with date filtering"""
    try:
        url = f"{WP_API_URL}/wp-json/rr-analytics/v1/book-chart-data"
        headers = {
            'User-Agent': 'RR-Analytics-Discord-Bot/1.0',
            'Content-Type': 'application/json'
        }
        
        # Base data
        data = {
            'book_input': str(book_input),
            'bot_token': WP_BOT_TOKEN
        }
        
        # Add date filtering parameters based on the parsed days_param
        if days_param == 'all':
            data['all_data'] = True
        elif isinstance(days_param, dict):
            if days_param['type'] == 'date_range':
                data['start_date'] = days_param['start_date']
                data['end_date'] = days_param['end_date']
            elif days_param['type'] == 'from_date':
                data['start_date'] = days_param['start_date']
        elif isinstance(days_param, int):
            data['days'] = days_param
        
        logger.info(f"[CHART] Fetching chart data for book input: {book_input}")
        logger.info(f"[CHART] Days parameter: {days_param}")
        logger.info(f"[CHART] API request data: {data}")
        logger.info(f"[CHART] Request URL: {url}")
        
        async with session.post(url, json=data, headers=headers) as response:
            if response.status == 200:
                result = await response.json()
                logger.info(f"[CHART] Successfully fetched chart data")
                logger.info(f"[CHART] Response keys: {list(result.keys())}")
                if 'data_info' in result:
                    logger.info(f"[CHART] Total snapshots: {result['data_info'].get('total_snapshots', 'unknown')}")
                    logger.info(f"[CHART] Filter applied: {result['data_info'].get('filter_applied', 'unknown')}")
                return result
            else:
                error_text = await response.text()
                logger.info(f"[CHART] Failed to fetch chart data: {response.status} - {error_text}")
                return None
                
    except Exception as e:
        logger.info(f"[CHART] Exception fetching chart data: {e}")
        return None

def filter_zero_data_points(labels, data, timestamps=None):
    """
    Filter out data points where the value is zero (except the first non-zero value)
    to avoid gaps in the chart while preserving meaningful trend information
    
    Returns filtered labels, data, and timestamps
    """
    if not labels or not data or len(labels) != len(data):
        return labels, data, timestamps
    
    filtered_labels = []
    filtered_data = []
    filtered_timestamps = []
    
    found_first_nonzero = False
    
    for i, value in enumerate(data):
        # Always include the first non-zero value to establish baseline
        if value > 0 and not found_first_nonzero:
            found_first_nonzero = True
            filtered_labels.append(labels[i])
            filtered_data.append(value)
            if timestamps:
                filtered_timestamps.append(timestamps[i])
        # After finding first non-zero, only include non-zero values
        elif found_first_nonzero and value > 0:
            filtered_labels.append(labels[i])
            filtered_data.append(value)
            if timestamps:
                filtered_timestamps.append(timestamps[i])
    
    # If we have timestamps, return all three; otherwise return what we have
    if timestamps:
        return filtered_labels, filtered_data, filtered_timestamps
    else:
        return filtered_labels, filtered_data, None

def trim_leading_zeros(labels, data, timestamps=None):
    """
    Trim leading zeros from the data to start from first meaningful data point
    Returns trimmed labels, data, and timestamps
    """
    if not labels or not data or len(labels) != len(data):
        return labels, data, timestamps
    
    # Find the first non-zero data point to start from
    first_nonzero_index = 0
    for i, value in enumerate(data):
        if value > 0:
            first_nonzero_index = i
            break
    
    # Trim the data to start from first meaningful point
    if first_nonzero_index > 0:
        labels = labels[first_nonzero_index:]
        data = data[first_nonzero_index:]
        if timestamps:
            timestamps = timestamps[first_nonzero_index:]
    
    return labels, data, timestamps

# Updated create_chart_image function with zero filtering
def create_chart_image(chart_data, chart_type, book_title, days_param):
    """Create a chart image using matplotlib with proper linear date scaling, leading zero trimming, and intermediate zero filtering"""
    try:
        # Set up the plot
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Prepare data - USE AS-IS from API (already filtered)
        labels = chart_data.get('labels', [])
        timestamps = chart_data.get('timestamps', [])  # If available from API
        
        if chart_type == 'followers':
            data = chart_data.get('followers', [])
            title = f'Followers Over Time - {book_title}'
            ylabel = 'Followers'
            color = '#4BC0C0'
        else:  # views
            data = chart_data.get('total_views', [])
            title = f'Views Over Time - {book_title}'
            ylabel = 'Total Views'
            color = '#FF6384'
        
        if not data or not labels:
            # Create a "no data" chart
            ax.text(0.5, 0.5, 'No data available for this time period', 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=16, color='gray')
            ax.set_title(title)
        else:
            # First, trim leading zeros to start from first meaningful data point
            trimmed_labels, trimmed_data, trimmed_timestamps = trim_leading_zeros(
                labels, data, timestamps
            )
            
            # Then, filter out intermediate zero data points
            if trimmed_labels and trimmed_data:
                filtered_labels, filtered_data, filtered_timestamps = filter_zero_data_points(
                    trimmed_labels, trimmed_data, trimmed_timestamps
                )
                
                if filtered_labels and filtered_data:
                    # Parse dates for proper linear scaling
                    date_objects = parse_dates_from_labels(filtered_labels, filtered_timestamps)
                    
                    # Plot the line connecting all non-zero data points using actual dates
                    ax.plot(date_objects, filtered_data, color=color, linewidth=2, marker='o', 
                           markersize=4, label='Data Points', zorder=3)
                    ax.fill_between(date_objects, filtered_data, alpha=0.3, color=color)
                    
                    # Format axes
                    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
                    ax.set_ylabel(ylabel, fontsize=12)
                    ax.set_xlabel('Date', fontsize=12)
                    
                    # Format y-axis with commas
                    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
                    
                    # Format x-axis with proper date formatting
                    if len(date_objects) > 1:
                        # Calculate span to determine appropriate date formatting
                        date_span = (date_objects[-1] - date_objects[0]).days
                        
                        if date_span > 365:  # More than a year, show months
                            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
                            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
                        elif date_span > 60:  # More than 2 months, show months
                            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
                            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
                        else:  # Less than 2 months, show days
                            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, date_span // 10)))
                        
                        # Rotate labels for better readability
                        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
                        
                        # Set reasonable limits with some padding
                        date_range = date_objects[-1] - date_objects[0]
                        padding = timedelta(days=max(1, date_range.days * 0.02))  # 2% padding
                        ax.set_xlim(date_objects[0] - padding, date_objects[-1] + padding)
                else:
                    # No meaningful data after filtering
                    ax.text(0.5, 0.5, 'No meaningful data to display after filtering', 
                           horizontalalignment='center', verticalalignment='center',
                           transform=ax.transAxes, fontsize=16, color='gray')
                    ax.set_title(title)
        
        # Add grid and styling
        ax.grid(True, alpha=0.3)
        ax.set_facecolor('#f8f9fa')
        
        # Add time period info with better formatting
        if isinstance(days_param, dict):
            if days_param['type'] == 'date_range':
                period_text = f"{days_param['start_date']} to {days_param['end_date']}"
            elif days_param['type'] == 'from_date':
                period_text = f"From {days_param['start_date']}"
        elif days_param == 'all':
            period_text = "All time"
        else:
            period_text = f"Last {days_param} days"
            
        ax.text(0.02, 0.98, period_text, transform=ax.transAxes, 
               fontsize=10, verticalalignment='top', 
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        
        # Save to bytes buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()  # Free memory
        
        return buffer
        
    except Exception as e:
        logger.info(f"[CHART] Error creating chart image: {e}")
        plt.close()  # Ensure we clean up even on error
        return None

async def tag_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[discord.app_commands.Choice[str]]:
    """Autocomplete function for tag selection that allows free input"""
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

async def get_session():
    """Get or create the aiohttp session"""
    global session
    if session is None or session.closed:
        session = aiohttp.ClientSession()
    return session

@bot.event
async def on_ready():
    global session, shoutout_module
    session = await get_session()
    logger.info(f'[READY] {bot.user} has connected to Discord!')
    logger.info(f'[READY] Bot is in {len(bot.guilds)} guilds')
    
    # List all guilds
    for guild in bot.guilds:
        logger.info(f'[READY] - Guild: {guild.name} (ID: {guild.id})')
        
    try:
        # Initialize shoutout module WITHOUT get_user_info_for_shoutout function
        # The module will handle user tier checks directly via the API
        shoutout_module = ShoutoutModule(bot, session, WP_API_URL, WP_BOT_TOKEN, tag_autocomplete)
        logger.info("Shoutout module initialized successfully")
        
        # Sync commands to Discord
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")   
    except Exception as e:
        logger.error(f"Error during bot startup: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Test WordPress connection immediately
    print('[TEST] Testing WordPress connection...')
    try:
        test_url = f"{WP_API_URL}/wp-json/rr-analytics/v1/health"
        headers = {
            'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)'
        }
        async with session.get(test_url, headers=headers) as response:
            logger.info(f'[TEST] WordPress health check: Status {response.status}')
            if response.status == 200:
                print('[TEST] ✅ WordPress API is reachable!')
            else:
                response_text = await response.text()
                logger.info(f'[TEST] ❌ WordPress API returned error status: {response_text[:200]}')
    except Exception as e:
        logger.info(f'[TEST] ❌ Failed to reach WordPress: {e}')
    
    # Sync slash commands
    try:
        print('[SYNC] Starting command sync...')
        synced = await bot.tree.sync()
        logger.info(f'[SYNC] Successfully synced {len(synced)} command(s)')
        for cmd in synced:
            logger.info(f'[SYNC] - Command: {cmd.name}')
    except Exception as e:
        logger.info(f'[ERROR] Failed to sync commands: {e}')
        import traceback
        traceback.print_exc()

@bot.event
async def on_disconnect():
    print('[DISCONNECT] Bot disconnected')
    # Don't close the session here - let it persist

@bot.event
async def on_error(event, *args, **kwargs):
    """Handle errors gracefully"""
    logger.info(f'[ERROR] Error in {event}')
    import traceback
    traceback.print_exc()

# Close session only when bot is shutting down
async def cleanup():
    global session
    if session and not session.closed:
        await session.close()
        print('[CLEANUP] Session closed')

@bot.tree.command(name="rr-others-also-liked-list", description="Show a list of all books that reference this book in 'Others Also Liked'")
@discord.app_commands.describe(
    book_input="Book ID or Royal Road URL"
)
async def rr_others_also_liked_list(interaction: discord.Interaction, book_input: str):
    """Show a comprehensive list of books that reference the given book in their 'Others Also Liked' section"""
    global command_counter
    command_counter += 1
    
    logger.info(f"\n[RR-OTHERS-ALSO-LIKED-LIST] Command called by {interaction.user}")
    logger.info(f"[RR-OTHERS-ALSO-LIKED-LIST] Book input: '{book_input}'")
    
    await interaction.response.defer()
    
    try:
        # Get the session
        global session
        
        # Make API request to get others also liked data
        data = {
            'book_input': book_input.strip(),
            'bot_token': WP_BOT_TOKEN,
            'discord_username': f"{interaction.user.name}#{interaction.user.discriminator}"  # Use username instead of ID
        }
        
        url = f"{WP_API_URL}/wp-json/rr-analytics/v1/others-also-liked"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        logger.info(f"[RR-OTHERS-ALSO-LIKED-LIST] Making API request to: {url}")
        
        # Set a longer timeout for this API call
        timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
        
        async with session.post(url, json=data, headers=headers, timeout=timeout) as response:
            response_text = await response.text()
            logger.info(f"[RR-OTHERS-ALSO-LIKED-LIST] API Status: {response.status}")
            
            if response.status == 200:
                result = json.loads(response_text)
                
                if result.get('success'):
                    embed = create_others_also_liked_list_embed(result, interaction.user)
                    await interaction.followup.send(embed=embed)
                    print("[RR-OTHERS-ALSO-LIKED-LIST] Successfully sent embed")
                else:
                    error_msg = result.get('message', 'Could not fetch data for the specified book.')
                    await interaction.followup.send(f"❌ {error_msg}", ephemeral=True)
            else:
                await interaction.followup.send(
                    f"❌ Error {response.status} from the database!",
                    ephemeral=True
                )
                logger.info(f"[ERROR] Others Also Liked List API returned status {response.status}")
                
    except asyncio.TimeoutError:
        logger.info(f"[ERROR] API timeout in rr-others-also-liked-list command")
        try:
            if interaction.response.is_done():
                await interaction.followup.send(
                    "⏰ Request timed out. The server might be busy. Please try again.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "⏰ Request timed out. The server might be busy. Please try again.",
                    ephemeral=True
                )
        except:
            print("[ERROR] Could not send timeout message")
    except Exception as e:
        logger.info(f"[ERROR] Exception in rr-others-also-liked-list command: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            await interaction.followup.send(
                "❌ An error occurred while fetching 'Others Also Liked' list data!",
                ephemeral=True
            )
        except:
            print("[ERROR] Failed to send error message to user")

@bot.tree.command(name="rr-others-also-liked", description="Show books that have this book in their 'Others Also Liked' section")
@discord.app_commands.describe(
    book_input="Book ID or Royal Road URL"
)
async def rr_others_also_liked(interaction: discord.Interaction, book_input: str):
    """Show books that reference the given book in their 'Others Also Liked' section"""
    global command_counter
    command_counter += 1
    
    logger.info(f"\n[RR-OTHERS-ALSO-LIKED] Command called by {interaction.user}")
    logger.info(f"[RR-OTHERS-ALSO-LIKED] Book input: '{book_input}'")
    
    await interaction.response.defer()
    
    try:
        # Get the session
        global session
        
        # Make API request to get others also liked data
        data = {
            'book_input': book_input.strip(),
            'bot_token': WP_BOT_TOKEN,
            'discord_username': f"{interaction.user.name}#{interaction.user.discriminator}"  # Use username instead of ID
        }
        
        url = f"{WP_API_URL}/wp-json/rr-analytics/v1/others-also-liked"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        logger.info(f"[RR-OTHERS-ALSO-LIKED] Making API request to: {url}")
        
        # Set a longer timeout for this API call
        timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
        
        async with session.post(url, json=data, headers=headers, timeout=timeout) as response:
            response_text = await response.text()
            logger.info(f"[RR-OTHERS-ALSO-LIKED] API Status: {response.status}")
            
            if response.status == 200:
                result = json.loads(response_text)
                
                if result.get('success'):
                    embed = create_others_also_liked_embed(result, interaction.user)
                    await interaction.followup.send(embed=embed)
                    print("[RR-OTHERS-ALSO-LIKED] Successfully sent embed")
                else:
                    error_msg = result.get('message', 'Could not fetch data for the specified book.')
                    await interaction.followup.send(f"❌ {error_msg}", ephemeral=True)
            else:
                await interaction.followup.send(
                    f"❌ Error {response.status} from the database!",
                    ephemeral=True
                )
                logger.info(f"[ERROR] Others Also Liked API returned status {response.status}")
                
    except asyncio.TimeoutError:
        logger.info(f"[ERROR] API timeout in rr-others-also-liked command")
        try:
            if interaction.response.is_done():
                await interaction.followup.send(
                    "⏰ Request timed out. The server might be busy. Please try again.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "⏰ Request timed out. The server might be busy. Please try again.",
                    ephemeral=True
                )
        except:
            print("[ERROR] Could not send timeout message")
    except Exception as e:
        logger.info(f"[ERROR] Exception in rr-others-also-liked command: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            await interaction.followup.send(
                "❌ An error occurred while fetching 'Others Also Liked' data!",
                ephemeral=True
            )
        except:
            print("[ERROR] Failed to send error message to user")

@bot.tree.command(name="rr-average-views", description="Show average views and chapters over time chart for a Royal Road book")
@discord.app_commands.describe(
    book_input="Book ID or Royal Road URL",
    days="Days to show: number (30), 'all', date (2024-01-01), or range (2024-01-01:2024-02-01). Default: 'all'"
)
async def rr_average_views(interaction: discord.Interaction, book_input: str, days: str = "all"):
    """Generate and send an average views over time chart with chapters for reference - DEFAULT TO 'all' TIME"""
    global command_counter
    command_counter += 1
    
    logger.info(f"\n[RR-AVERAGE-VIEWS] Command called by {interaction.user}")
    logger.info(f"[RR-AVERAGE-VIEWS] Book input: '{book_input}', Days: '{days}'")
    
    await interaction.response.defer()
    
    try:
        # Parse days parameter (supports date ranges) - NOW DEFAULTS TO 'all'
        days_param = parse_days_parameter(days)
        logger.info(f"[RR-AVERAGE-VIEWS] Parsed days parameter: {days_param}")
        
        # Fetch chart data - API handles ALL filtering
        global session
        chart_response = await get_book_chart_data(book_input.strip(), days_param, session)
        
        if not chart_response or not chart_response.get('success'):
            error_msg = "❌ Could not fetch data for the specified book."
            if chart_response and 'message' in chart_response:
                error_msg += f"\n{chart_response['message']}"
            else:
                error_msg += " The book might not exist or have no tracking data. If the book is new, you can add it by running this tool: https://stepan.chizhov.com/author-tools/rising-stars-checker/"
            
            await interaction.followup.send(error_msg, ephemeral=True)
            return
        
        chart_data = chart_response.get('chart_data', {})
        book_info = chart_response.get('book_info', {})
        data_info = chart_response.get('data_info', {})
        
        book_title = book_info.get('title', f'Book {book_info.get("id", "Unknown")}')
        book_id = book_info.get('id', 'Unknown')
        book_url = book_info.get('url', f'https://www.royalroad.com/fiction/{book_id}')
        
        logger.info(f"[RR-AVERAGE-VIEWS] API returned {data_info.get('total_snapshots', 'unknown')} snapshots")
        logger.info(f"[RR-AVERAGE-VIEWS] Filter applied: {data_info.get('filter_applied', 'unknown')}")
        
        # CRITICAL: Use data exactly as returned from API - NO FILTERING
        filtered_data = chart_data  # API already filtered everything
        
        # Create chart image with average views and chapters
        chart_buffer = create_average_views_chart_image(filtered_data, book_title, days_param)
        
        if not chart_buffer:
            await interaction.followup.send(
                "❌ Failed to generate chart image. Please try again later.",
                ephemeral=True
            )
            return
        
        # Create Discord file and embed
        file = discord.File(chart_buffer, filename=f"average_views_chart_{book_id}.png")
        
        embed = discord.Embed(
            title="📊 Average Views & Chapters Over Time",
            description=f"**[{book_title}]({book_url})**\nBook ID: {book_id}",
            color=0x9B59B6  # Purple color for average views
        )
        embed.set_image(url=f"attachment://average_views_chart_{book_id}.png")
        
        # Add stats if available
        if filtered_data.get('average_views'):
            latest_avg_views = filtered_data['average_views'][-1] if filtered_data['average_views'] else 0
            embed.add_field(name="Current Avg Views", value=f"{latest_avg_views:,}", inline=True)
            
            if len(filtered_data['average_views']) > 1:
                first_avg_views = filtered_data['average_views'][0]
                change = latest_avg_views - first_avg_views
                change_text = f"+{change:,}" if change >= 0 else f"{change:,}"
                embed.add_field(name="Change", value=change_text, inline=True)
        
        # Add chapters info
        if filtered_data.get('chapters'):
            latest_chapters = filtered_data['chapters'][-1] if filtered_data['chapters'] else 0
            embed.add_field(name="Current Chapters", value=f"{latest_chapters:,}", inline=True)
        
        # Use the filter description from the API
        period_text = data_info.get('filter_applied', 'Unknown period')
        embed.add_field(name="Period", value=period_text, inline=True)
        
        # Add data note about chart features
        embed.add_field(
            name="📊 Chart Features",
            value="• Purple line shows average views per chapter\n• Orange line shows total chapters for reference\n• Want to add your historical data? Visit [Stepan Chizhov's Discord](https://discord.gg/xvw9vbvrwj)",
            inline=False
        )
        
        embed = add_promotional_field(embed)
        
        embed.set_footer(text="Data from Stepan Chizhov's Royal Road Analytics\n(starting with the 12th of June 2025)\nTo use the bot, start typing /rr-average-views")
        
        await interaction.followup.send(embed=embed, file=file)
        logger.info(f"[RR-AVERAGE-VIEWS] Successfully sent chart for book {book_id}")
        
    except Exception as e:
        logger.info(f"[RR-AVERAGE-VIEWS] Error: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            await interaction.followup.send(
                "❌ An error occurred while generating the average views chart.",
                ephemeral=True
            )
        except:
            pass

@bot.tree.command(name="rr-ratings", description="Show rating metrics over time chart for a Royal Road book")
@discord.app_commands.describe(
    book_input="Book ID or Royal Road URL",
    days="Days to show: number (30), 'all', date (2024-01-01), or range (2024-01-01:2024-02-01). Default: 'all'"
)
async def rr_ratings(interaction: discord.Interaction, book_input: str, days: str = "all"):
    """Generate and send a rating metrics over time chart - matching admin dashboard - DEFAULT TO 'all' TIME"""
    global command_counter
    command_counter += 1
    
    logger.info(f"\n[RR-RATINGS] Command called by {interaction.user}")
    logger.info(f"[RR-RATINGS] Book input: '{book_input}', Days: '{days}'")
    
    await interaction.response.defer()
    
    try:
        # Parse days parameter (supports date ranges) - NOW DEFAULTS TO 'all'
        days_param = parse_days_parameter(days)
        logger.info(f"[RR-RATINGS] Parsed days parameter: {days_param}")
        
        # Fetch chart data - API handles ALL filtering
        global session
        chart_response = await get_book_chart_data(book_input.strip(), days_param, session)
        
        if not chart_response or not chart_response.get('success'):
            error_msg = "❌ Could not fetch data for the specified book."
            if chart_response and 'message' in chart_response:
                error_msg += f"\n{chart_response['message']}"
            else:
                error_msg += " The book might not exist or have no tracking data. If the book is new, you can add it by running this tool: https://stepan.chizhov.com/author-tools/rising-stars-checker/"
            
            await interaction.followup.send(error_msg, ephemeral=True)
            return
        
        chart_data = chart_response.get('chart_data', {})
        book_info = chart_response.get('book_info', {})
        data_info = chart_response.get('data_info', {})
        
        book_title = book_info.get('title', f'Book {book_info.get("id", "Unknown")}')
        book_id = book_info.get('id', 'Unknown')
        book_url = book_info.get('url', f'https://www.royalroad.com/fiction/{book_id}')
        
        logger.info(f"[RR-RATINGS] API returned {data_info.get('total_snapshots', 'unknown')} snapshots")
        logger.info(f"[RR-RATINGS] Filter applied: {data_info.get('filter_applied', 'unknown')}")
        
        # CRITICAL: Use data exactly as returned from API - NO FILTERING
        filtered_data = chart_data  # API already filtered everything
        
        # Create chart image with rating metrics (dual-axis)
        chart_buffer = create_ratings_chart_image(filtered_data, book_title, days_param)
        
        if not chart_buffer:
            await interaction.followup.send(
                "❌ Failed to generate chart image. Please try again later.",
                ephemeral=True
            )
            return
        
        # Create Discord file and embed
        file = discord.File(chart_buffer, filename=f"ratings_chart_{book_id}.png")
        
        embed = discord.Embed(
            title="⭐ Rating Metrics Over Time",
            description=f"**[{book_title}]({book_url})**\nBook ID: {book_id}",
            color=0x3498DB  # Blue color for ratings (matching admin dashboard)
        )
        embed.set_image(url=f"attachment://ratings_chart_{book_id}.png")
        
        # Add stats if available
        if filtered_data.get('overall_score'):
            latest_score = filtered_data['overall_score'][-1] if filtered_data['overall_score'] else 0
            embed.add_field(name="Current Rating", value=f"{latest_score:.2f}/5.00", inline=True)
        
        if filtered_data.get('ratings'):
            latest_ratings = filtered_data['ratings'][-1] if filtered_data['ratings'] else 0
            embed.add_field(name="Total Ratings", value=f"{latest_ratings:,}", inline=True)
            
            if len(filtered_data['ratings']) > 1:
                first_ratings = filtered_data['ratings'][0]
                change = latest_ratings - first_ratings
                change_text = f"+{change:,}" if change >= 0 else f"{change:,}"
                embed.add_field(name="Rating Change", value=change_text, inline=True)
        
        # Use the filter description from the API
        period_text = data_info.get('filter_applied', 'Unknown period')
        embed.add_field(name="Period", value=period_text, inline=True)
        
        # Add data note about chart features
        embed.add_field(
            name="📊 Chart Features",
            value="• Blue line shows overall rating score (0-5)\n• Yellow line shows number of ratings\n• Dual-axis chart matching admin dashboard\n• Want to add your historical data? Visit [Stepan Chizhov's Discord](https://discord.gg/xvw9vbvrwj)",
            inline=False
        )
        
        embed = add_promotional_field(embed)
        
        embed.set_footer(text="Data from Stepan Chizhov's Royal Road Analytics\n(starting with the 12th of June 2025)\nTo use the bot, start typing /rr-ratings")
        
        await interaction.followup.send(embed=embed, file=file)
        logger.info(f"[RR-RATINGS] Successfully sent chart for book {book_id}")
        
    except Exception as e:
        logger.info(f"[RR-RATINGS] Error: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            await interaction.followup.send(
                "❌ An error occurred while generating the ratings chart.",
                ephemeral=True
            )
        except:
            pass

@bot.tree.command(name="essence", description="Combine two essence tags to discover rare book combinations")
@discord.app_commands.describe(
    tag1="First tag - choose from list or type your own",
    tag2="Second tag - choose from list or type your own"
)
@discord.app_commands.autocomplete(tag1=tag_autocomplete)
@discord.app_commands.autocomplete(tag2=tag_autocomplete)
async def essence(interaction: discord.Interaction, tag1: str, tag2: str):
    """Combine two essence tags - accepts both URL format and display names"""
    
    logger.info(f"\n[COMMAND] Essence command called")
    logger.info(f"[COMMAND] User: {interaction.user} (ID: {interaction.user.id})")
    logger.info(f"[COMMAND] Guild: {interaction.guild.name if interaction.guild else 'DM'}")
    logger.info(f"[COMMAND] Raw input: '{tag1}' + '{tag2}'")
    
    # Defer the response FIRST before any processing
    await interaction.response.defer()
    print("[COMMAND] Response deferred")
    
    try:
        # Get the session
        session = await get_session()
        
        # Normalize tags
        normalized_tag1 = normalize_tag(tag1)
        normalized_tag2 = normalize_tag(tag2)
        
        logger.info(f"[COMMAND] Normalized: '{normalized_tag1}' + '{normalized_tag2}'")
        
        # Check if tags are valid
        if not normalized_tag1:
            await interaction.followup.send(
                f"Unknown tag: **{tag1}**\nUse `/tags` to see available tags, or try variations like 'female_lead' or 'Female Lead'", 
                ephemeral=True
            )
            return
            
        if not normalized_tag2:
            await interaction.followup.send(
                f"Unknown tag: **{tag2}**\nUse `/tags` to see available tags, or try variations like 'male_lead' or 'Male Lead'", 
                ephemeral=True
            )
            return
        
        if normalized_tag1 == normalized_tag2:
            await interaction.followup.send(
                "You cannot combine an essence with itself!", 
                ephemeral=True
            )
            return
        
        # Prepare API request with normalized tags
        data = {
            'tags': [normalized_tag1, normalized_tag2],
            'bot_token': WP_BOT_TOKEN,
            'discord_user': {
                'id': str(interaction.user.id),
                'username': interaction.user.name,
                'discriminator': interaction.user.discriminator,
                'display_name': interaction.user.display_name
            }
        }
        
        url = f"{WP_API_URL}/wp-json/rr-analytics/v1/essence-combination"
        logger.info(f"[API] URL: {url}")
        logger.info(f"[API] Payload: {json.dumps(data)}")
        
        # Make API request
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        async with session.post(url, json=data, headers=headers) as response:
            response_text = await response.text()
            logger.info(f"[API] Status: {response.status}")
            logger.info(f"[API] Response: {response_text[:500]}...")  # First 500 chars
            
            if response.status == 200:
                result = json.loads(response_text)
                
                # Create embed using the normalized display names
                embed = create_result_embed(result, normalized_tag1, normalized_tag2, interaction)
                await interaction.followup.send(embed=embed)
                print("[COMMAND] Embed sent successfully")
            else:
                await interaction.followup.send(
                    f"Error {response.status} from the essence database!",
                    ephemeral=True
                )
                logger.info(f"[ERROR] API returned status {response.status}")
    
    except Exception as e:
        logger.info(f"[ERROR] Exception in essence command: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            await interaction.followup.send(
                "An error occurred while weaving essences!",
                ephemeral=True
            )
        except:
            print("[ERROR] Failed to send error message to user")

def calculate_relative_rarity(book_count, total_books):
    """
    Calculate rarity based on percentage of total books (relative system)
    This replaces the old absolute thresholds with scalable percentages
    """
    if total_books == 0:
        return {
            'rarity': 'Unknown',
            'tier': 'unknown',
            'flavor': 'Database currently empty.'
        }
    
    percentage = (book_count / total_books) * 100
    
    if book_count == 0:
        return {
            'rarity': 'Undiscovered',
            'tier': 'undiscovered',
            'flavor': 'You are the first to seek this combination. A true pioneer!'
        }
    elif percentage <= 0.15:  # ≤ 0.15% (≤15 books out of 10k)
        return {
            'rarity': '🌟 Mythic',
            'tier': 'mythic',
            'flavor': 'One of the rarest confluences in all the realms'
        }
    elif percentage <= 0.3:   # ≤ 0.3% (≤30 books out of 10k)
        return {
            'rarity': '⭐ Legendary', 
            'tier': 'legendary',
            'flavor': 'A confluence of legend! Few have walked this path'
        }
    elif percentage <= 0.5:   # ≤ 0.5% (≤50 books out of 10k)
        return {
            'rarity': '💜 Epic',
            'tier': 'epic', 
            'flavor': 'An epic combination explored by a true essence weaver'
        }
    elif percentage <= 1.0:   # ≤ 1.0% (≤100 books out of 10k)
        return {
            'rarity': '💙 Rare',
            'tier': 'rare',
            'flavor': 'A rare find! This confluence holds secrets to explore'
        }
    elif percentage <= 5.0:   # ≤ 5.0% (≤500 books out of 10k) 
        return {
            'rarity': '💚 Uncommon',
            'tier': 'uncommon',
            'flavor': 'An uncommon path showing promise for discerning readers'
        }
    else:                     # > 5.0% (>500 books out of 10k)
        return {
            'rarity': '⚪ Common',
            'tier': 'common',
            'flavor': 'A well-established confluence, beloved by many'
        }

def create_others_also_liked_list_embed(result, user):
    """Create embed showing a simple list of books that reference the given book in 'Others Also Liked'"""
    global command_counter
    
    book_info = result.get('book_info', {})
    books = result.get('books', [])
    user_tier = result.get('user_tier', 'free')
    total_books = result.get('total_books', 0)
    
    # Create main embed
    embed = discord.Embed(
        title="📋 Others Also Liked - Complete List",
        description=f"Books that reference **[{book_info.get('title', 'Unknown')}]({book_info.get('url', '#')})** in their 'Others Also Liked' section",
        color=0x1E90FF  # Different blue color to distinguish from detailed version
    )
    
    # Add target book info (more compact)
    embed.add_field(
        name="📖 Target Book",
        value=f"**{book_info.get('author', 'Unknown')}** • {book_info.get('status', 'Unknown').title()} • ID: {book_info.get('id', 'Unknown')}",
        inline=False
    )
    
    # Add summary statistics
    stats_value = f"**{total_books:,}** books reference this title"
    if user_tier in ['administrator', 'admin', 'editor', 'patreon_premium', 'patreon_supporter', 'premium', 'pro', 'pro_free']:
        if len(books) <= total_books:
            stats_value += f"\n✅ **Premium Access** - Showing all {len(books)} books"
        else:
            stats_value += f"\n✅ **Premium Access** - Showing {len(books)} books"
    else:
        stats_value += f"\n🔒 **Free Tier** - Showing top book only"
        if total_books > 1:
            stats_value += f"\n[Upgrade for full access](https://patreon.com/stepanchizhov)"
    
    embed.add_field(
        name="📊 Summary",
        value=stats_value,
        inline=False
    )
    
    # Create book list - handle Discord message limits
    if books:
        book_links = []
        current_batch = []
        current_length = 0
        max_field_length = 1000  # Leave some buffer under Discord's 1024 limit
        
        for i, book in enumerate(books):
            # Create simple link format: "1. [Title](url) (followers)"
            followers_text = f"({book['followers']:,})" if book.get('followers', 0) > 0 else ""
            book_link = f"{i+1}. **[{book['title']}]({book['url']})** {followers_text}"
            
            # Check if adding this book would exceed the field limit
            if current_length + len(book_link) + 1 > max_field_length:  # +1 for newline
                # Save current batch and start new one
                if current_batch:
                    book_links.append('\n'.join(current_batch))
                current_batch = [book_link]
                current_length = len(book_link)
            else:
                current_batch.append(book_link)
                current_length += len(book_link) + 1  # +1 for newline
        
        # Add the last batch
        if current_batch:
            book_links.append('\n'.join(current_batch))
        
        # Add book list fields
        for i, book_batch in enumerate(book_links):
            field_name = "📚 Books" if i == 0 else f"📚 Books (continued {i+1})"
            embed.add_field(
                name=field_name,
                value=book_batch,
                inline=False
            )
        
        # Add note about sorting
        embed.add_field(
            name="ℹ️ List Info",
            value="📈 Sorted by followers (highest to lowest)\n📅 Use `/rr-others-also-liked` for detailed stats and timestamps",
            inline=False
        )
    else:
        embed.add_field(
            name="📚 No Books Found",
            value="This book is not referenced in any 'Others Also Liked' sections yet.",
            inline=False
        )
    
    # Add tier explanation for free users
    if user_tier not in ['administrator', 'admin', 'editor', 'patreon_premium', 'patreon_supporter', 'premium', 'pro', 'pro_free'] and total_books > 1:
        embed.add_field(
            name="🔓 Want to see all books?",
            value=(
                f"**{total_books - 1} more books** reference this title!\n"
                "[**Join any paid tier**](https://patreon.com/stepanchizhov) to see the complete list.\n"
                "Message [Stepan Chizhov](https://discord.gg/xvw9vbvrwj) to get access after subscribing."
            ),
            inline=False
        )
    
    # Add promotional field
    embed = add_promotional_field(embed)
    
    embed.set_footer(text="Data from Stepan Chizhov's Royal Road Analytics • Use /rr-others-also-liked for detailed view")
    
    return embed

def create_others_also_liked_embed(result, user):
    """Create embed showing books that reference the given book in 'Others Also Liked'"""
    global command_counter
    
    book_info = result.get('book_info', {})
    books = result.get('books', [])
    user_tier = result.get('user_tier', 'free')
    total_books = result.get('total_books', 0)
    
    # Create main embed
    embed = discord.Embed(
        title="📚 Others Also Liked This Book",
        description=f"Books that feature **[{book_info.get('title', 'Unknown')}]({book_info.get('url', '#')})** in their 'Others Also Liked' section",
        color=0x00A86B  # Green color
    )
    
    # Add book info field
    book_field = f"**Author:** {book_info.get('author', 'Unknown')}\n"
    book_field += f"**Status:** {book_info.get('status', 'Unknown').title()}\n"
    book_field += f"**Royal Road ID:** {book_info.get('id', 'Unknown')}"
    
    embed.add_field(
        name="📖 Target Book",
        value=book_field,
        inline=False
    )
    
    # Add statistics with enhanced information
    stats_value = f"**{total_books:,}** books reference this title"
    if user_tier in ['administrator', 'admin', 'editor', 'patreon_premium', 'patreon_supporter', 'premium', 'pro', 'pro_free']:
        if len(books) <= 9:
            stats_value += f"\n**Premium Access** - Showing all {len(books)} books"
        else:
            stats_value += f"\n**Premium Access** - Showing top 9 books"
    else:
        stats_value += f"\n**Free Tier** - Showing top book only"
        if total_books > 1:
            stats_value += f"\n[Upgrade for full access](https://patreon.com/stepanchizhov)"
    
    # Add information about the timestamp data
    # if books and any(book.get('timestamp') for book in books):
    #    stats_value += f"\n📅 *Showing when each book last referenced this title*"
    
    embed.add_field(
        name="📊 Statistics",
        value=stats_value,
        inline=False
    )
    
    # Add books with timestamp information
    if books:
        for i, book in enumerate(books[:9]):  # Limit to 9 for display
            book_value = f"**[{book['title']}]({book['url']})**\n"
            book_value += f"*by {book['author']}*\n"
            book_value += f"👥 {book['followers']:,} followers\n⭐ {book['rating']:.2f}/5.00"
            if book.get('status'):
                book_value += f"\nStatus: {book['status'].title()}"
            
            # Add timestamp information if available
            if book.get('timestamp'):
                try:
                    from datetime import datetime
                    # Parse the timestamp (assuming it's in MySQL datetime format)
                    timestamp_dt = datetime.strptime(book['timestamp'], '%Y-%m-%d %H:%M:%S')
                    # Format as date only
                    formatted_date = timestamp_dt.strftime('%b %d, %Y')
                    book_value += f"\nLast seen: {formatted_date}"
                except (ValueError, TypeError) as e:
                    # If timestamp parsing fails, show raw timestamp
                    book_value += f"\nLast seen: {book['timestamp'][:10]}"
            
            # Add position indicator - fixed logic
            position = ""
            if i == 0:
                position = "🥇 Most Popular - "
            elif i == 1:
                position = "🥈 Second - "
            elif i == 2:
                position = "🥉 Third - "
            else:
                position = f"#{i+1} - "
            
            embed.add_field(
                name=f"📚 {position}Book {i+1}",
                value=book_value,
                inline=True
            )
    else:
        embed.add_field(
            name="📚 No Books Found",
            value="This book is not referenced in any 'Others Also Liked' sections yet.",
            inline=False
        )
    
    # Add tier explanation
    if user_tier not in ['administrator', 'editor', 'premium', 'pro', 'pro_free'] and total_books > 1:
        embed.add_field(
            name="Want to see all books?",
            value=(
                f"**{total_books - 1} more books** reference this title!\n"
                "[**Join any paid tier**](https://patreon.com/stepanchizhov) to see the complete list.\n"
                "Message [Stepan Chizhov](https://discord.gg/xvw9vbvrwj) to get access after subscribing."
            ),
            inline=False
        )
    
    # Add promotional field
    embed = add_promotional_field(embed)
    
    embed.set_footer(text="Data from Stepan Chizhov's Royal Road Analytics")
    
    return embed

# NEW: Chart creation function for average views with chapters reference
def create_ratings_chart_image(chart_data, book_title, days_param):
    """Create a ratings metrics chart with dual axis (matching admin dashboard) using matplotlib"""
    try:
        logger.info(f"[CHART DEBUG] Starting ratings chart creation for {book_title}")
        
        # Set up the plot
        plt.style.use('default')
        fig, ax1 = plt.subplots(figsize=(12, 6))
        
        # Prepare data - USE AS-IS from API (already filtered)
        labels = chart_data.get('labels', [])
        timestamps = chart_data.get('timestamps', [])
        overall_score_data = chart_data.get('overall_score', [])
        ratings_data = chart_data.get('ratings', [])
        
        logger.info(f"[CHART DEBUG] Initial data lengths - labels:{len(labels)}, scores:{len(overall_score_data)}, ratings:{len(ratings_data)}")
        
        if not overall_score_data or not labels or not ratings_data or not timestamps:
            # Create a "no data" chart
            ax1.text(0.5, 0.5, 'No rating data available', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax1.transAxes, fontsize=16, color='red')
            ax1.set_title(f'Rating Metrics Over Time - {book_title}', fontsize=14, fontweight='bold', pad=20)
        else:
            # Convert timestamps to datetime objects for linear time axis
            date_objects = []
            filtered_scores = []
            filtered_ratings = []
            
            # Filter data: only include points where we have meaningful data
            for i in range(len(timestamps)):
                if timestamps[i] and ratings_data[i] > 0:  # Only include if we have actual ratings
                    date_obj = datetime.fromtimestamp(timestamps[i])
                    date_objects.append(date_obj)
                    
                    # Include scores only when we have ratings (ratings drive the chart)
                    filtered_scores.append(overall_score_data[i])
                    
                    # Include ratings (we already filtered for > 0)
                    filtered_ratings.append(ratings_data[i])
            
            logger.info(f"[CHART DEBUG] After filtering - dates:{len(date_objects)}, scores valid:{sum(1 for x in filtered_scores if x is not None)}, ratings valid:{sum(1 for x in filtered_ratings if x is not None)}")
            
            if not date_objects:
                raise ValueError("No valid data points with timestamps")
            
            # Create dual-axis chart (matching admin dashboard colors)
            color1_hex = '#36A2EB'  # Blue for rating score (from admin.js)
            color2_hex = '#FFCE56'  # Yellow for ratings count (from admin.js)
            
            logger.info(f"[CHART DEBUG] Plotting overall score data with linear time axis")
            # Plot overall score on primary axis (0-5 scale) - ADD FILL for better visibility
            ax1.set_xlabel('Date', fontsize=12)
            ax1.set_ylabel('Overall Rating Score', color=color1_hex, fontsize=12)
            ax1.set_ylim(0, 5)  # Rating scale is 0-5
            # REMOVED WHITE BORDER: Changed markeredgewidth from 2 to 0 and removed markeredgecolor
            line1 = ax1.plot(date_objects, filtered_scores, color=color1_hex, linewidth=2, 
                           marker='o', markersize=4, label='Overall Score', 
                           markerfacecolor=color1_hex, markeredgewidth=0)
            
            # Add fill under the rating score curve for better visibility (BLUE)
            ax1.fill_between(date_objects, filtered_scores, alpha=0.3, color='#36A2EB')  # Explicit blue color
            
            ax1.tick_params(axis='y', labelcolor=color1_hex)
            ax1.grid(True, alpha=0.3)
            
            logger.info(f"[CHART DEBUG] Plotting ratings count data")
            # Create secondary axis for ratings count - MATCH STYLING
            ax2 = ax1.twinx()
            ax2.set_ylabel('Number of Ratings', color=color2_hex, fontsize=12)
            # REMOVED WHITE BORDER: Changed markeredgewidth from 2 to 0 and removed markeredgecolor
            line2 = ax2.plot(date_objects, filtered_ratings, color=color2_hex, linewidth=2, 
                           marker='o', markersize=4, label='Ratings Count',
                           markerfacecolor=color2_hex, markeredgewidth=0)
            
            # SOLUTION: Use white fill with yellow edge to create yellow appearance without mixing
            # This creates a yellow-bordered area that doesn't blend with the blue underneath
            ax2.fill_between(date_objects, filtered_ratings, alpha=0.8, color='white', 
                           edgecolor='#FFCE56', linewidth=1)
            # Add a thin yellow fill on top for better yellow visibility
            ax2.fill_between(date_objects, filtered_ratings, alpha=0.3, color='#FFCE56')
            
            logger.info(f"[CHART DEBUG] Added white+yellow layered fill to avoid color mixing")
            
            ax2.tick_params(axis='y', labelcolor=color2_hex)
            
            # Scale ratings axis so it never goes above 5 (to stay below rating score visually)
            max_ratings = max(filtered_ratings) if filtered_ratings else 1
            # Calculate scale factor to keep ratings visually below scores
            # If max rating is > 100, use a larger scale; otherwise use a smaller one 
            if max_ratings > 100:
                scale_factor = max_ratings / 4.0  # Max ratings will display at 4.0 on visual scale
            elif max_ratings > 50:
                scale_factor = max_ratings / 3.5  # Max ratings will display at 3.5 on visual scale  
            else:
                scale_factor = max_ratings / 3.0  # Max ratings will display at 3.0 on visual scale
            
            ax2.set_ylim(0, scale_factor * 5)  # 0 to scale_factor*5 so max shows below rating line
            
            # Format ratings count with commas
            ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
            
            # Format x-axis for dates with exactly 12 date points
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
            from matplotlib.ticker import MaxNLocator
            ax1.xaxis.set_major_locator(MaxNLocator(nbins=12))  # Exactly 12 date points
            
            # Rotate date labels for better readability
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # Add title (matching admin dashboard)
            title = f'Rating Metrics Over Time - {book_title}'
            ax1.set_title(title, fontsize=14, fontweight='bold', pad=20)
            
            # Add legend (matching admin dashboard style)
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        # Adjust layout and save
        plt.tight_layout()
        
        # Save to BytesIO buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        
        logger.info(f"[CHART DEBUG] Chart created successfully, buffer size: {len(buffer.getvalue())} bytes")
        
        # Clean up
        plt.close()
        
        return buffer
       
    except Exception as e:
        logger.info(f"[CHART DEBUG] ERROR in chart creation: {e}")
        import traceback
        traceback.print_exc()
        plt.close()  # Ensure we clean up even on error
        return None


def create_average_views_chart_image(chart_data, book_title, days_param):
    """Create an average views chart with chapters reference using matplotlib"""
    try:
        logger.info(f"[CHART DEBUG] Starting chart creation for {book_title}")
        
        # Set up the plot
        plt.style.use('default')
        fig, ax1 = plt.subplots(figsize=(12, 6))
        
        # Prepare data - USE AS-IS from API (already filtered)
        labels = chart_data.get('labels', [])
        timestamps = chart_data.get('timestamps', [])
        average_views_data = chart_data.get('average_views', [])
        chapters_data = chart_data.get('chapters', [])
        
        logger.info(f"[CHART DEBUG] Initial data lengths - labels:{len(labels)}, avg_views:{len(average_views_data)}, chapters:{len(chapters_data)}")
        
        # Check if we have average_views data
        if not average_views_data or len(average_views_data) == 0:
            logger.info(f"[CHART DEBUG] No average_views data, trying to calculate from total_views/chapters")
            # Try to calculate average views from total_views and chapters if possible
            total_views_data = chart_data.get('total_views', [])
            if total_views_data and chapters_data and len(total_views_data) == len(chapters_data):
                average_views_data = []
                for i in range(len(total_views_data)):
                    if chapters_data[i] > 0:
                        avg_views = total_views_data[i] / chapters_data[i]
                        average_views_data.append(int(avg_views))
                    else:
                        average_views_data.append(0)
                logger.info(f"[CHART DEBUG] Calculated {len(average_views_data)} average_views values")
        
        if not average_views_data or not labels or not chapters_data or not timestamps:
            # Create a "no data" chart
            ax1.text(0.5, 0.5, 'No average views or chapters data available\n(Check logs for details)', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax1.transAxes, fontsize=14, color='red')
            ax1.set_title(f'Average Views & Chapters Over Time - {book_title}', fontsize=14, fontweight='bold', pad=20)
        else:
            # Convert timestamps to datetime objects for linear time axis
            date_objects = []
            filtered_avg_views = []
            filtered_chapters = []
            
            # IMPLEMENTATION OF REQUESTED FIXES:
            # 1. Start with the first non-zero point
            first_nonzero_index = -1
            for i, value in enumerate(average_views_data):
                if value > 0:
                    first_nonzero_index = i
                    break
            
            if first_nonzero_index == -1:
                # No non-zero values found
                ax1.text(0.5, 0.5, 'No meaningful average views data available', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=ax1.transAxes, fontsize=14, color='red')
                ax1.set_title(f'Average Views & Chapters Over Time - {book_title}', fontsize=14, fontweight='bold', pad=20)
            else:
                # Start from first non-zero point and handle intermediate zeros
                for i in range(first_nonzero_index, len(timestamps)):
                    if timestamps[i]:
                        date_obj = datetime.fromtimestamp(timestamps[i])
                        
                        # 2. If an intermediate average views datapoint is zero, skip it
                        # (only add non-zero values to create line between previous and next)
                        if average_views_data[i] > 0:
                            date_objects.append(date_obj)
                            filtered_avg_views.append(average_views_data[i])
                            filtered_chapters.append(chapters_data[i])
                
                logger.info(f"[CHART DEBUG] After filtering - dates:{len(date_objects)}, avg_views:{len(filtered_avg_views)}, chapters:{len(filtered_chapters)}")
                
                if not date_objects:
                    raise ValueError("No valid data points with timestamps after filtering")
                
                # Create dual-axis chart
                color1 = '#9B59B6'  # Purple for average views
                color2 = '#F39C12'  # Orange for chapters
                
                logger.info(f"[CHART DEBUG] Plotting average views data with linear time axis")
                # Plot average views on primary axis with linear time
                ax1.set_xlabel('Date', fontsize=12)
                ax1.set_ylabel('Average Views per Chapter', color=color1, fontsize=12)
                
                # Set y-axis from 0 to max for better scale visibility
                max_avg_views = max(filtered_avg_views) if filtered_avg_views else 1400
                ax1.set_ylim(0, max_avg_views * 1.1)  # 0 to max + 10% padding
                
                # Plot with datetime objects for linear time axis - FILL AREA for better visibility
                line1 = ax1.plot(date_objects, filtered_avg_views, color=color1, linewidth=2, 
                               marker='o', markersize=4, label='Average Views', 
                               markerfacecolor=color1, markeredgewidth=0)
                
                # Add fill under the curve for better visibility (like followers chart)
                ax1.fill_between(date_objects, filtered_avg_views, alpha=0.3, color=color1)
                
                ax1.tick_params(axis='y', labelcolor=color1)
                ax1.grid(True, alpha=0.3)
                
                logger.info(f"[CHART DEBUG] Plotting chapters data")
                # Create secondary axis for chapters
                ax2 = ax1.twinx()
                ax2.set_ylabel('Total Chapters', color=color2, fontsize=12)
                
                # 3. Circles without white borders for total chapters datapoints
                # 4. Filling under total chapters chart  
                # 5. Scale total chapters chart so that it is always below average view chart
                
                # Set chapters y-axis max to 125% of the highest chapter number
                # This makes the highest chapters value appear at ~80% of the y-axis height
                max_chapters = max(filtered_chapters) if filtered_chapters else 1
                chapters_axis_max = max_chapters * 1.25  # 125% of highest chapter number
                ax2.set_ylim(0, chapters_axis_max)  # Scale chapters axis properly
                
                line2 = ax2.plot(date_objects, filtered_chapters, color=color2, linewidth=2, 
                               marker='o', markersize=4, label='Chapters',
                               markerfacecolor=color2, markeredgewidth=0)
                
                # 4. Add fill under total chapters chart
                ax2.fill_between(date_objects, filtered_chapters, alpha=0.2, color=color2)
                
                ax2.tick_params(axis='y', labelcolor=color2)
                
                # Format x-axis for dates with exactly 12 date points
                ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
                from matplotlib.ticker import MaxNLocator
                ax1.xaxis.set_major_locator(MaxNLocator(nbins=12))  # Exactly 12 date points
                
                # Rotate date labels for better readability
                plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
                
                # Add title
                title = f'Average Views & Chapters Over Time - {book_title}'
                ax1.set_title(title, fontsize=14, fontweight='bold', pad=20)
                
                # Add legend
                lines1, labels1 = ax1.get_legend_handles_labels()
                lines2, labels2 = ax2.get_legend_handles_labels()
                ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        # Adjust layout and save
        plt.tight_layout()
        
        # Save to BytesIO buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        
        logger.info(f"[CHART DEBUG] Chart created successfully, buffer size: {len(buffer.getvalue())} bytes")
        
        # Clean up
        plt.close()
        
        return buffer
       
    except Exception as e:
        logger.info(f"[CHART DEBUG] ERROR in chart creation: {e}")
        import traceback
        traceback.print_exc()
        plt.close()  # Ensure we clean up even on error
        return None

def create_result_embed(result, tag1, tag2, interaction):
    """
    Create result embed - CURRENT VERSION (2 tags + interaction)
    
    This version works with current calling pattern:
    create_result_embed(result, tag1, tag2, interaction)
    """
    global command_counter
    command_counter += 1
    
    # For now, we work with exactly 2 tags as passed
    actual_tags = [tag1, tag2]
    
    # Get data from result
    book_count = result.get('book_count', 0)
    total_books = int(result.get('total_books', 0)) if result.get('total_books') else 0
    percentage = float(result.get('percentage', 0)) if result.get('percentage') else 0
    
    # Calculate rarity using relative system if total_books is available
    # This overrides whatever rarity the WordPress API returned
    if total_books > 0:
        relative_rarity = calculate_relative_rarity(book_count, total_books)
        
        # Override the API rarity with our relative calculation
        rarity_tier = relative_rarity['tier']
        rarity_display = relative_rarity['rarity']
        flavor_text = relative_rarity['flavor']
    else:
        # Fallback to API-provided rarity
        rarity_tier = result.get('rarity_tier', 'common')
        rarity_display = result.get('rarity', 'Common')
        flavor_text = result.get('flavor_text', 'A combination of essences.')
    
    # Color based on rarity
    colors = {
        'undiscovered': 0xFFFFFF,
        'mythic': 0xFF0000,
        'legendary': 0xFF8C00,
        'epic': 0x9400D3,
        'rare': 0x0000FF,
        'uncommon': 0x00FF00,
        'common': 0x808080,
        'unknown': 0x808080
    }
    
    embed = discord.Embed(
        title="🌟 ESSENCE COMBINATION DISCOVERED! 🌟",
        color=colors.get(rarity_tier, 0x808080)
    )
    
    # Row 1: Three inline fields
    essences_text = f"**{tag1}** + **{tag2}**"
    
    embed.add_field(
        name="Essences Combined",
        value=essences_text,
        inline=True
    )
    
    embed.add_field(
        name="Creates",
        value=f"{result['combination_name']}",
        inline=True
    )
    
    embed.add_field(
        name="Rarity",
        value=rarity_display,
        inline=True
    )
    
    # Row 2: Three inline fields
    # Books Found (just the count)
    embed.add_field(
        name="Books Found",
        value=f"📚 **{book_count:,}**",
        inline=True
    )
    
    # Database Statistics
    stats_display = f"📊 {percentage}% of {total_books:,} Royal Road books\nanalyzed in Stepan Chizhov's database"
    embed.add_field(
        name="Database Statistics",
        value=stats_display,
        inline=True
    )
    
    # Lore (using calculated flavor text)
    embed.add_field(
        name="✦ Lore ✦",
        value=f"{flavor_text}",
        inline=True
    )
    
    # Row 3: Three inline fields
    # Most Popular Example
    if 'popular_book' in result and result['popular_book']:
        book = result['popular_book']
        book_value = f"**[{book['title']}]({book['url']})**\n"
        book_value += f"*by {book['author']}*\n"
        book_value += f"👥 {book['followers']:,} followers • ⭐ {book['rating']:.2f}/5.00 • 📄 {book['pages']:,} pages"
        
        embed.add_field(
            name="👑 Most Popular Example",
            value=book_value,
            inline=True
        )
    else:
        embed.add_field(
            name="👑 Most Popular Example",
            value="*No data available*",
            inline=True
        )
    
    # Random Discovery
    if 'random_book' in result and result['random_book']:
        book = result['random_book']
        book_value = f"**[{book['title']}]({book['url']})**\n"
        book_value += f"*by {book['author']}*\n"
        book_value += f"👥 {book['followers']:,} followers • ⭐ {book['rating']:.2f}/5.00 • 📄 {book['pages']:,} pages"
        
        embed.add_field(
            name="🎲 Random Discovery",
            value=book_value,
            inline=True
        )
    else:
        embed.add_field(
            name="🎲 Random Discovery",
            value="*No books with 20k+ words found*",
            inline=True
        )
    
    # Rising Stars Link (NEW) - Works with 2 tags
    rising_stars_url = build_rising_stars_url(tag1, tag2)
    
    if rising_stars_url:
        embed.add_field(
            name="⭐ Rising Stars",
            value=f"[**View on Rising Stars List**]({rising_stars_url})\nSee which books with these tags are trending upward!",
            inline=True
        )
    else:
        embed.add_field(
            name="⭐ Rising Stars",
            value="*Rising Stars link unavailable*",
            inline=True
        )
    
    # Inspiration message (full width)
    if ('popular_book' in result and result['popular_book']) or ('random_book' in result and result['random_book']):
        embed.add_field(
            name="💡 Get Inspired",
            value="Explore these examples to see how authors blend these essences!",
            inline=False
        )
    
    embed = add_promotional_field(embed)
    
    return embed

# Helper function to build scalable Rising Stars URLs
def build_rising_stars_url(*tags):
    """Build Rising Stars URL for any number of tags"""
    url_tags = []
    for tag in tags:
        url_tag = convert_display_to_url_format(tag)
        if url_tag:
            url_tags.append(url_tag)
    
    if url_tags and len(url_tags) == len(tags):
        # Join tags with comma for URL
        tags_param = "%2C".join(url_tags)  # %2C is URL-encoded comma
        return f"https://stepan.chizhov.com/author-tools/all-rising-stars/?tags={tags_param}"
    
    return None

def convert_display_to_url_format(display_name):  # FIXED: Single colon
    """Convert a display name back to URL format for Rising Stars links"""
    # Create reverse mapping from display names to URL format
    reverse_mapping = {}
    for url_format, display_format in TAG_MAPPING.items():
        if display_format not in reverse_mapping:
            # Ensure URL format is lowercase
            reverse_mapping[display_format] = url_format.lower()
    
    # Handle special cases where multiple URL formats map to same display name
    # Prefer the most "standard" URL format (all lowercase)
    special_cases = {
        'Sci-fi': 'sci_fi',
        'Portal Fantasy / Isekai': 'portal_fantasy',
        'Multiple Lead Characters': 'multiple_lead',
        'Anti-Hero Lead': 'anti_hero_lead',
        'Artificial Intelligence': 'artificial_intelligence',
        'Attractive Lead': 'attractive_lead',
        'Female Lead': 'female_lead',
        'First Contact': 'first_contact',
        'Gender Bender': 'gender_bender',
        'Genetically Engineered': 'genetically_engineered',
        'Hard Sci-fi': 'hard_sci_fi',
        'High Fantasy': 'high_fantasy',
        'Low Fantasy': 'low_fantasy',
        'Male Lead': 'male_lead',
        'Martial Arts': 'martial_arts',
        'Non-Human Lead': 'non_human_lead',
        'Post Apocalyptic': 'post_apocalyptic',
        'Reader Interactive': 'reader_interactive',
        'Ruling Class': 'ruling_class',
        'School Life': 'school_life',
        'Secret Identity': 'secret_identity',
        'Slice of Life': 'slice_of_life',
        'Soft Sci-fi': 'soft_sci_fi',
        'Space Opera': 'space_opera',
        'Strong Lead': 'strong_lead',
        'Super Heroes': 'super_heroes',
        'Time Loop': 'time_loop',
        'Time Travel': 'time_travel',
        'Urban Fantasy': 'urban_fantasy',
        'Villainous Lead': 'villainous_lead',
        'Virtual Reality': 'virtual_reality',
        'War and Military': 'war_and_military',
        'Technologically Engineered': 'technologically_engineered',
        'Short Story': 'one_shot'
    }
    
    # Check special cases first
    if display_name in special_cases:
        return special_cases[display_name].lower()
    
    # Fall back to reverse mapping (already lowercase from above)
    if display_name in reverse_mapping:
        return reverse_mapping[display_name]
    
    # If not found, try to convert display name to URL format
    # Convert to lowercase and replace spaces with underscores
    url_format = display_name.lower().replace(' ', '_').replace('-', '_')
    return url_format

@bot.tree.command(name="tags", description="List all available essence tags")
async def tags(interaction: discord.Interaction):
    """Show all available tags with examples of accepted formats"""
    
    embed = discord.Embed(
        title="📚 Available Essence Tags",
        description=(
            "You can use any of these formats:\n"
            "• Display name: `Female Lead`\n"
            "• URL format: `female_lead`\n"
            "• Lowercase: `female lead`\n"
            "**Need help?** Use `/help` for detailed instructions!"
        ),
        color=0x5468ff
    )
    
    # Get unique tags
    all_tags = UNIQUE_TAGS
    
    # Split into chunks for better display
    chunk_size = 20
    for i in range(0, len(all_tags), chunk_size):
        chunk = all_tags[i:i + chunk_size]
        field_name = f"Tags {i+1}-{min(i+chunk_size, len(all_tags))}"
        field_value = "\n".join([f"• {tag}" for tag in chunk])
        
        # Discord has a 1024 character limit per field
        if len(field_value) > 1024:
            field_value = field_value[:1021] + "..."
        
        embed.add_field(
            name=field_name,
            value=field_value,
            inline=True
        )
    
    # Add quick start
    embed.add_field(
        name="🚀 Quick Start",
        value=(
            "**Try these commands:**\n"
            "`/e Fantasy Magic`\n"
            "`/e female_lead strong_lead`\n"
            "`/e LitRPG progression`\n"
            "`/e Portal Fantasy Reincarnation`\n\n"
            "Use `/help` for more examples!"
        ),
        inline=False
    )
    
    embed.set_footer(text="Tip: Use /e for quick combinations or /essence for autocomplete")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Updated chart commands with default 'all' parameter
@bot.tree.command(name="rr-followers", description="Show followers over time chart for a Royal Road book")
@discord.app_commands.describe(
    book_input="Book ID or Royal Road URL",
    days="Days to show: number (30), 'all', date (2024-01-01), or range (2024-01-01:2024-02-01). Default: 'all'"
)
async def rr_followers(interaction: discord.Interaction, book_input: str, days: str = "all"):
    """Generate and send a followers over time chart - DEFAULT TO 'all' TIME"""
    global command_counter
    command_counter += 1
    
    logger.info(f"\n[RR-FOLLOWERS] Command called by {interaction.user}")
    logger.info(f"[RR-FOLLOWERS] Book input: '{book_input}', Days: '{days}'")
    
    await interaction.response.defer()
    
    try:
        # Parse days parameter (supports date ranges) - NOW DEFAULTS TO 'all'
        days_param = parse_days_parameter(days)
        logger.info(f"[RR-FOLLOWERS] Parsed days parameter: {days_param}")
        
        # Fetch chart data - API handles ALL filtering
        global session
        chart_response = await get_book_chart_data(book_input.strip(), days_param, session)
        
        if not chart_response or not chart_response.get('success'):
            error_msg = "❌ Could not fetch data for the specified book."
            if chart_response and 'message' in chart_response:
                error_msg += f"\n{chart_response['message']}"
            else:
                error_msg += " The book might not exist or have no tracking data. If the book is new, you can add it by running this tool: https://stepan.chizhov.com/author-tools/rising-stars-checker/"
            
            await interaction.followup.send(error_msg, ephemeral=True)
            return
        
        chart_data = chart_response.get('chart_data', {})
        book_info = chart_response.get('book_info', {})
        data_info = chart_response.get('data_info', {})
        
        book_title = book_info.get('title', f'Book {book_info.get("id", "Unknown")}')
        book_id = book_info.get('id', 'Unknown')
        book_url = book_info.get('url', f'https://www.royalroad.com/fiction/{book_id}')
        
        logger.info(f"[RR-FOLLOWERS] API returned {data_info.get('total_snapshots', 'unknown')} snapshots")
        logger.info(f"[RR-FOLLOWERS] Filter applied: {data_info.get('filter_applied', 'unknown')}")
        
        # CRITICAL: Use data exactly as returned from API - NO FILTERING
        filtered_data = chart_data  # API already filtered everything
        
        # Create chart image with interpolation
        chart_buffer = create_chart_image(filtered_data, 'followers', book_title, days_param)
        
        if not chart_buffer:
            await interaction.followup.send(
                "❌ Failed to generate chart image. Please try again later.",
                ephemeral=True
            )
            return
        
        # Create Discord file and embed
        file = discord.File(chart_buffer, filename=f"followers_chart_{book_id}.png")
        
        embed = discord.Embed(
            title="📈 Followers Over Time",
            description=f"**[{book_title}]({book_url})**\nBook ID: {book_id}",
            color=0x4BC0C0
        )
        embed.set_image(url=f"attachment://followers_chart_{book_id}.png")
        
        # Add stats if available
        if filtered_data.get('followers'):
            latest_followers = filtered_data['followers'][-1] if filtered_data['followers'] else 0
            embed.add_field(name="Current Followers", value=f"{latest_followers:,}", inline=True)
            
            if len(filtered_data['followers']) > 1:
                first_followers = filtered_data['followers'][0]
                change = latest_followers - first_followers
                change_text = f"+{change:,}" if change >= 0 else f"{change:,}"
                embed.add_field(name="Change", value=change_text, inline=True)
        
        # Use the filter description from the API
        period_text = data_info.get('filter_applied', 'Unknown period')
        embed.add_field(name="Period", value=period_text, inline=True)
        
        # Add data note about chart features
        embed.add_field(
            name="📊 Chart Features",
            value="• Chart starts from the first meaningful data point\n• Points connected to show trends over time\n• Want to add your historical data? Visit [Stepan Chizhov's Discord](https://discord.gg/xvw9vbvrwj)",
            inline=False
        )
        
        embed = add_promotional_field(embed)
            
        embed.set_footer(text="Data from Stepan Chizhov's Royal Road Analytics\n(starting with the 12th of June 2025)\nTo use the bot, start typing /rr-views or /rr-followers")
        
        await interaction.followup.send(embed=embed, file=file)
        logger.info(f"[RR-FOLLOWERS] Successfully sent chart for book {book_id}")
        
    except Exception as e:
        logger.info(f"[RR-FOLLOWERS] Error: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            await interaction.followup.send(
                "❌ An error occurred while generating the followers chart.",
                ephemeral=True
            )
        except:
            pass

@bot.tree.command(name="rr-views", description="Show views over time chart for a Royal Road book")
@discord.app_commands.describe(
    book_input="Book ID or Royal Road URL",
    days="Days to show: number (30), 'all', date (2024-01-01), or range (2024-01-01:2024-02-01). Default: 'all'"
)
async def rr_views(interaction: discord.Interaction, book_input: str, days: str = "all"):
    """Generate and send a views over time chart - DEFAULT TO 'all' TIME"""
    global command_counter
    command_counter += 1
    
    logger.info(f"\n[RR-VIEWS] Command called by {interaction.user}")
    logger.info(f"[RR-VIEWS] Book input: '{book_input}', Days: '{days}'")
    
    await interaction.response.defer()
    
    try:
        # Parse days parameter (supports date ranges) - NOW DEFAULTS TO 'all'
        days_param = parse_days_parameter(days)
        logger.info(f"[RR-VIEWS] Parsed days parameter: {days_param}")
        
        # Fetch chart data - API handles ALL filtering
        global session
        chart_response = await get_book_chart_data(book_input.strip(), days_param, session)
        
        if not chart_response or not chart_response.get('success'):
            error_msg = "❌ Could not fetch data for the specified book."
            if chart_response and 'message' in chart_response:
                error_msg += f"\n{chart_response['message']}"
            else:
                error_msg += " The book might not exist or have no tracking data."
            
            await interaction.followup.send(error_msg, ephemeral=True)
            return
        
        chart_data = chart_response.get('chart_data', {})
        book_info = chart_response.get('book_info', {})
        data_info = chart_response.get('data_info', {})
        
        book_title = book_info.get('title', f'Book {book_info.get("id", "Unknown")}')
        book_id = book_info.get('id', 'Unknown')
        book_url = book_info.get('url', f'https://www.royalroad.com/fiction/{book_id}')
        
        logger.info(f"[RR-VIEWS] API returned {data_info.get('total_snapshots', 'unknown')} snapshots")
        logger.info(f"[RR-VIEWS] Filter applied: {data_info.get('filter_applied', 'unknown')}")
        
        # CRITICAL: Use data exactly as returned from API - NO FILTERING
        filtered_data = chart_data  # API already filtered everything
        
        # Create chart image with interpolation
        chart_buffer = create_chart_image(filtered_data, 'views', book_title, days_param)
        
        if not chart_buffer:
            await interaction.followup.send(
                "❌ Failed to generate chart image. Please try again later.",
                ephemeral=True
            )
            return
        
        # Create Discord file and embed
        file = discord.File(chart_buffer, filename=f"views_chart_{book_id}.png")
        
        embed = discord.Embed(
            title="📊 Views Over Time",
            description=f"**[{book_title}]({book_url})**\nBook ID: {book_id}",
            color=0xFF6384
        )
        embed.set_image(url=f"attachment://views_chart_{book_id}.png")
        
        # Add stats if available
        if filtered_data.get('total_views'):
            latest_views = filtered_data['total_views'][-1] if filtered_data['total_views'] else 0
            embed.add_field(name="Current Views", value=f"{latest_views:,}", inline=True)
            
            if len(filtered_data['total_views']) > 1:
                first_views = filtered_data['total_views'][0]
                change = latest_views - first_views
                change_text = f"+{change:,}" if change >= 0 else f"{change:,}"
                embed.add_field(name="Change", value=change_text, inline=True)
        
        # Use the filter description from the API
        period_text = data_info.get('filter_applied', 'Unknown period')
        embed.add_field(name="Period", value=period_text, inline=True)
        
        # Add data note about chart features
        embed.add_field(
            name="📊 Chart Features",
            value="• Chart starts from first meaningful data point\n• Points connected to show trends over time\n• Want to add your historical data? Visit [Stepan Chizhov's Discord](https://discord.gg/xvw9vbvrwj)",
            inline=False
        )
        
        embed = add_promotional_field(embed)
        
        embed.set_footer(text="Data from Stepan Chizhov's Royal Road Analytics\n(starting with the 12th of June 2025)\nTo use the bot, start typing /rr-views or /rr-followers")
        
        await interaction.followup.send(embed=embed, file=file)
        logger.info(f"[RR-VIEWS] Successfully sent chart for book {book_id}")
        
    except Exception as e:
        logger.info(f"[RR-VIEWS] Error: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            await interaction.followup.send(
                "❌ An error occurred while generating the views chart.",
                ephemeral=True
            )
        except:
            pass

# Test command to verify bot is responding
@bot.tree.command(name="ping", description="Test if the bot is responsive")
async def ping(interaction: discord.Interaction):
    logger.info(f"[COMMAND] Ping command called by {interaction.user}")
    await interaction.response.send_message("Pong! The bot is online.", ephemeral=True)

# Test WordPress connection command
@bot.tree.command(name="test", description="Test WordPress API connection")
async def test(interaction: discord.Interaction):
    logger.info(f"[COMMAND] Test command called by {interaction.user}")
    await interaction.response.defer(ephemeral=True)
    
    session = await get_session()
    
    try:
        # Test health endpoint
        health_url = f"{WP_API_URL}/wp-json/rr-analytics/v1/health"
        headers = {
            'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)'
        }
        async with session.get(health_url, headers=headers) as response:
            health_status = response.status
            health_text = await response.text()
            logger.info(f"[TEST] Health check: {health_status}")
        
        # Test essence endpoint
        test_data = {
            'tags': ['Fantasy', 'Magic'],
            'bot_token': WP_BOT_TOKEN
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        essence_url = f"{WP_API_URL}/wp-json/rr-analytics/v1/essence-combination"
        async with session.post(
            essence_url,
            json=test_data,
            headers=headers
        ) as response:
            essence_status = response.status
            essence_text = await response.text()
            logger.info(f"[TEST] Essence endpoint: {essence_status}")
        
        # Create response embed
        embed = discord.Embed(
            title="🔧 WordPress API Test Results",
            color=0x00ff00 if health_status == 200 and essence_status == 200 else 0xff0000
        )
        
        embed.add_field(
            name="Health Check",
            value=f"{'✅' if health_status == 200 else '❌'} Status: {health_status}",
            inline=False
        )
        
        embed.add_field(
            name="Essence Endpoint",
            value=f"{'✅' if essence_status == 200 else '❌'} Status: {essence_status}",
            inline=False
        )
        
        if essence_status == 200:
            try:
                result = json.loads(essence_text)
                embed.add_field(
                    name="Test Result",
                    value=f"Fantasy + Magic = {result.get('combination_name', 'Unknown')} ({result.get('book_count', 0)} books)",
                    inline=False
                )
            except:
                pass
        
        embed.add_field(
            name="API URL",
            value=f"`{WP_API_URL}`",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.info(f"[ERROR] Test command failed: {e}")
        await interaction.followup.send(
            f"❌ Test failed: {str(e)}",
            ephemeral=True
        )

# Process tags for the quick essence commands
async def process_quick_essence(interaction: discord.Interaction, tags: str):
    """Process quick essence command with two tags in one input"""
    
    logger.info(f"\n[COMMAND] Quick essence command called")
    logger.info(f"[COMMAND] User: {interaction.user}")
    logger.info(f"[COMMAND] Input: '{tags}'")
    
    # Split the input
    tag_list = tags.strip().split()
    
    if len(tag_list) < 2:
        await interaction.response.send_message(
            "Please provide two tags separated by space.\nExample: `/e Fantasy Magic`",
            ephemeral=True
        )
        return
    
    if len(tag_list) > 2:
        # If more than 2 words, try to intelligently combine them
        # e.g., "Female Lead Magic" -> ["Female Lead", "Magic"]
        possible_tags = []
        
        # Try different combinations
        for i in range(1, len(tag_list)):
            tag1_candidate = ' '.join(tag_list[:i])
            tag2_candidate = ' '.join(tag_list[i:])
            
            norm1 = normalize_tag(tag1_candidate)
            norm2 = normalize_tag(tag2_candidate)
            
            if norm1 and norm2:
                possible_tags.append((norm1, norm2, tag1_candidate, tag2_candidate))
        
        if possible_tags:
            # Use the first valid combination
            tag1_norm, tag2_norm, tag1_orig, tag2_orig = possible_tags[0]
            logger.info(f"[COMMAND] Interpreted as: '{tag1_orig}' + '{tag2_orig}'")
        else:
            await interaction.response.send_message(
                f"Could not interpret '{tags}' as two valid tags.\nTry: `/e Fantasy Magic` or `/e female_lead strong_lead`\nTriads, Tetrads, and Pentads (or Trios, Quartets, and Quintets, I don't know what you like more) will become available in the future!",
                ephemeral=True
            )
            return
    else:
        tag1_orig, tag2_orig = tag_list[0], tag_list[1]
        tag1_norm = normalize_tag(tag1_orig)
        tag2_norm = normalize_tag(tag2_orig)
    
    # Now process as normal essence command
    try:
        await interaction.response.defer()
        
        session = await get_session()
        
        if not tag1_norm:
            await interaction.followup.send(
                f"Unknown tag: **{tag1_orig}**\nUse `/tags` to see available tags.",
                ephemeral=True
            )
            return
            
        if not tag2_norm:
            await interaction.followup.send(
                f"Unknown tag: **{tag2_orig}**\nUse `/tags` to see available tags.",
                ephemeral=True
            )
            return
        
        if tag1_norm == tag2_norm:
            await interaction.followup.send(
                "You cannot combine an essence with itself!",
                ephemeral=True
            )
            return
        
        # Make API request
        data = {
            'tags': [tag1_norm, tag2_norm],
            'bot_token': WP_BOT_TOKEN
        }
        
        url = f"{WP_API_URL}/wp-json/rr-analytics/v1/essence-combination"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        async with session.post(url, json=data, headers=headers) as response:
            if response.status == 200:
                result = json.loads(await response.text())
                embed = create_result_embed(result, tag1_norm, tag2_norm, interaction)
                await interaction.followup.send(embed=embed)
                print("[COMMAND] Quick essence completed successfully")
            else:
                await interaction.followup.send(
                    f"Error {response.status} from the essence database!",
                    ephemeral=True
                )
                
    except Exception as e:
        logger.info(f"[ERROR] Exception in quick essence: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            await interaction.followup.send(
                "An error occurred while weaving essences!",
                ephemeral=True
            )
        except:
            pass

# Simple essence command that takes both tags as one input
@bot.tree.command(name="e", description="Quick essence combination: /e Fantasy Magic")
@discord.app_commands.describe(
    tags="Enter two tags separated by space (e.g., 'Fantasy Magic' or 'female_lead strong_lead')"
)
async def e_command(interaction: discord.Interaction, tags: str):
    """Quick essence command that accepts two tags in one input"""
    await process_quick_essence(interaction, tags)

# Add alias for convenience
@bot.tree.command(name="combine", description="Combine two essence tags: /combine Fantasy Magic")
@discord.app_commands.describe(
    tags="Enter two tags separated by space"
)
async def combine_alias(interaction: discord.Interaction, tags: str):
    """Alias for quick essence command"""
    await process_quick_essence(interaction, tags)

# NEW: Brag command to show user's essence discoveries
@bot.tree.command(name="brag", description="Show essence combinations you discovered first!")
async def brag_command(interaction: discord.Interaction):
    """Show essence combinations the user discovered first"""
    global command_counter
    command_counter += 1
    
    logger.info(f"\n[BRAG] Command called by {interaction.user}")
    logger.info(f"[BRAG] User ID: {interaction.user.id}, Username: {interaction.user.name}#{interaction.user.discriminator}")
    
    await interaction.response.defer()
    
    try:
        session = await get_session()
        
        # Format Discord user string (same format as stored in database)
        user_string = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        # Make API request to get user's discoveries
        data = {
            'user_string': user_string,
            'bot_token': WP_BOT_TOKEN
        }
        
        url = f"{WP_API_URL}/wp-json/rr-analytics/v1/user-discoveries"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        async with session.post(url, json=data, headers=headers) as response:
            response_text = await response.text()
            logger.info(f"[BRAG] API Status: {response.status}")
            logger.info(f"[BRAG] API Response: {response_text[:300]}...")
            
            if response.status == 200:
                result = json.loads(response_text)
                
                if result['success'] and result['discoveries']:
                    embed = create_brag_embed(result, interaction.user)
                    await interaction.followup.send(embed=embed)
                else:
                    # No discoveries found
                    embed = discord.Embed(
                        title="🔍 No Discoveries Yet",
                        description=f"**{interaction.user.display_name}**, you haven't made any first discoveries yet!\n\nTry combining some unusual essence tags to become the first discoverer of rare combinations!",
                        color=0x808080
                    )
                    embed.add_field(
                        name="💡 Tips for Discovery",
                        value=(
                            "• Try unusual combinations like `/e Mythos Time Loop`\n"
                            "• Combine niche tags like `/e Reader Interactive Genetically Engineered`\n"
                            "• Mix unexpected genres like `/e Sports Supernatural`\n"
                            "• Use `/tags` to see all available options!"
                        ),
                        inline=False
                    )
                    embed.set_footer(text="Keep exploring to become a legendary essence pioneer!")
                    await interaction.followup.send(embed=embed)
                    
                print("[BRAG] Response sent successfully")
            else:
                await interaction.followup.send(
                    f"❌ Error {response.status} from the discovery database!",
                    ephemeral=True
                )
                logger.info(f"[ERROR] Brag API returned status {response.status}")
    
    except Exception as e:
        logger.info(f"[ERROR] Exception in brag command: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            await interaction.followup.send(
                "❌ An error occurred while checking your discoveries!",
                ephemeral=True
            )
        except:
            print("[ERROR] Failed to send error message to user")

# Updated brag command function in discord_essence_bot.py

# Updated brag command function in discord_essence_bot.py

def create_brag_embed(result, user):
    """Create brag embed showing user's discoveries"""
    global command_counter
    
    discoveries = result['discoveries']
    stats = result['stats']
    
    embed = discord.Embed(
        title="🏆 ESSENCE PIONEER ACHIEVEMENTS 🏆",
        description=f"**{user.display_name}** has discovered **{stats['total_discoveries']}** unique essence combinations out of total of **{stats['total_possible_combinations']}** tracked combinations!",
        color=0xFFD700  # Gold color for achievements
    )
    
    # Set user avatar as thumbnail if available
    if user.avatar:
        embed.set_thumbnail(url=user.avatar.url)
    
    # Add discovery statistics
    embed.add_field(
        name="📊 Discovery Statistics",
        value=(
            f"🥇 **First Discoveries:** {stats['total_discoveries']}\n"
            f"🔮 **Times Rediscovered:** {stats['total_rediscoveries']}\n"
            f"📅 **First Discovery:** {stats['first_discovery_date']}\n"
            f"📅 **Latest Discovery:** {stats['latest_discovery_date']}"
        ),
        inline=False
    )
    
    # Show up to 5 rarest discoveries (sorted by rarity_tier ASC - lowest percentage first)
    if discoveries:
        discovery_list = []
        has_zero_percentages = False  # Track if we have any 0% entries
        
        for i, discovery in enumerate(discoveries[:5]):  # Limit to 5
            # Parse tags from JSON
            tags = []
            if 'tags' in discovery and discovery['tags']:
                try:
                    tags = json.loads(discovery['tags']) if isinstance(discovery['tags'], str) else discovery['tags']
                except json.JSONDecodeError:
                    tags = discovery['tags'].split(',') if isinstance(discovery['tags'], str) else []
            elif 'tags_key' in discovery and discovery['tags_key']:
                try:
                    tags = json.loads(discovery['tags_key']) if isinstance(discovery['tags_key'], str) else discovery['tags_key']
                except json.JSONDecodeError:
                    # tags_key might be comma-separated like "fantasy,magic"
                    tags = discovery['tags_key'].split(',') if isinstance(discovery['tags_key'], str) else []
                    
            tags_display = " + ".join(tags)
            
            # Format date nicely
            try:
                from datetime import datetime
                date_obj = datetime.strptime(discovery['created_at'], '%Y-%m-%d %H:%M:%S')
                date_display = date_obj.strftime('%b %d, %Y')
            except:
                date_display = discovery['created_at'][:10]  # Just the date part
            
            # FIXED: Use rarity_tier percentage instead of book count with null handling
            rarity_tier_raw = discovery.get('rarity_tier', 0)
            if rarity_tier_raw is None or rarity_tier_raw == '':
                rarity_percentage = 0.0
                has_zero_percentages = True  # Mark that we found a zero
            else:
                rarity_percentage = float(rarity_tier_raw)
                if rarity_percentage == 0.0:
                    has_zero_percentages = True  # Also mark if it's actually 0.0
            
            # Add rarity emoji based on percentage
            if rarity_percentage == 0:
                rarity_emoji = "✨"
            elif rarity_percentage <= 0.15:
                rarity_emoji = "🌟"
            elif rarity_percentage <= 0.3:
                rarity_emoji = "⭐"
            elif rarity_percentage <= 0.5:
                rarity_emoji = "💜"
            elif rarity_percentage <= 1.0:
                rarity_emoji = "💙"
            elif rarity_percentage <= 5.0:
                rarity_emoji = "💚"
            else:
                rarity_emoji = "⚪"
            
            discovery_list.append(
                f"{rarity_emoji} **{discovery['combination_name']}**\n"
                f"   └ *{tags_display}* • {date_display} • {rarity_percentage:.2f}%"
            )
        
        # Build the field value
        field_value = "\n".join(discovery_list)
        
        # Add notice about updating 0% entries if any exist
        if has_zero_percentages:
            field_value += "\n\n💡 *Some combinations show 0.00% - try running `/essence [tag1] [tag2]` again to update the percentage!*"
        
        embed.add_field(
            name=f"🔮 Rarest Discoveries (Top {len(discovery_list)} of {len(discoveries)})",
            value=field_value,
            inline=False
        )
        
        if len(discoveries) > 5:
            embed.add_field(
                name="📜 More Discoveries",
                value=f"*...and {len(discoveries) - 5} more! You're truly an essence pioneer!*",
                inline=False
            )
    
    # Add achievement badges based on discovery count
    achievement_text = get_achievement_badges(stats['total_discoveries'])
    if achievement_text:
        embed.add_field(
            name="🎖️ Achievement Badges",
            value=achievement_text,
            inline=False
        )
    
    # Add promotional message occasionally
    embed.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━",
        value="🌟 **Share your discoveries!** Screenshot this and show off your pioneer status!\n[**Join our Discord Community**](https://discord.gg/xvw9vbvrwj)",
        inline=False
    )
    
    embed.set_footer(text="Keep exploring to discover more rare combinations! • Created by Stepan Chizhov")
    
    return embed

def get_achievement_badges(discovery_count):
    """Get achievement badges based on number of discoveries"""
    badges = []
    
    if discovery_count >= 1:
        badges.append("🌱 **First Steps** - Made your first discovery!")
    if discovery_count >= 5:
        badges.append("🔍 **Explorer** - 5+ discoveries")
    if discovery_count >= 10:
        badges.append("⭐ **Pioneer** - 10+ discoveries")
    if discovery_count >= 25:
        badges.append("🏆 **Legend** - 25+ discoveries")
    if discovery_count >= 50:
        badges.append("👑 **Grandmaster** - 50+ discoveries")
    if discovery_count >= 100:
        badges.append("🌟 **Mythic Pioneer** - 100+ discoveries!")
    
    return "\n".join(badges) if badges else None

# NEW: RR Stats command to show Royal Road database statistics
@bot.tree.command(name="rr-stats", description="Show Royal Road database statistics")
async def rr_stats_command(interaction: discord.Interaction):
    """Show comprehensive Royal Road database statistics"""
    global command_counter
    command_counter += 1
    
    logger.info(f"\n[RR-STATS] Command called by {interaction.user}")
    
    await interaction.response.defer()
    
    try:
        session = await get_session()
        
        # Make API request to get database statistics
        data = {
            'bot_token': WP_BOT_TOKEN
        }
        
        url = f"{WP_API_URL}/wp-json/rr-analytics/v1/database-stats"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        async with session.post(url, json=data, headers=headers) as response:
            response_text = await response.text()
            logger.info(f"[RR-STATS] API Status: {response.status}")
            logger.info(f"[RR-STATS] API Response: {response_text[:300]}...")
            
            if response.status == 200:
                result = json.loads(response_text)
                
                if result['success']:
                    embed = create_stats_embed(result['stats'])
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(
                        "❌ Failed to retrieve database statistics.",
                        ephemeral=True
                    )
                    
                print("[RR-STATS] Response sent successfully")
            else:
                await interaction.followup.send(
                    f"❌ Error {response.status} from the statistics database!",
                    ephemeral=True
                )
                logger.info(f"[ERROR] RR-Stats API returned status {response.status}")
    
    except Exception as e:
        logger.info(f"[ERROR] Exception in rr-stats command: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            await interaction.followup.send(
                "❌ An error occurred while fetching Royal Road statistics!",
                ephemeral=True
            )
        except:
            print("[ERROR] Failed to send error message to user")

def create_stats_embed(stats):
    """Create embed showing Royal Road database statistics"""
    global command_counter
    
    embed = discord.Embed(
        title="📊 Royal Road Database Statistics",
        description="*Statistics from Stepan Chizhov's comprehensive Royal Road analytics database*",
        color=0x5468ff
    )
    
    # Total books section
    embed.add_field(
        name="📚 Total Books",
        value=f"**{stats['total_books']:,}** unique books tracked",
        inline=True
    )
    
    # Total authors section
    embed.add_field(
        name="✍️ Authors",
        value=f"**{stats['unique_authors']:,}** unique authors",
        inline=True
    )
    
    # Data collection period
    if stats.get('data_collection_period'):
        embed.add_field(
            name="📅 Data Period",
            value=f"**{stats['data_collection_period']}** days",
            inline=True
        )
    
    # Book status breakdown
    status_text = []
    if stats.get('status_breakdown'):
        for status, count in stats['status_breakdown'].items():
            percentage = (count / stats['total_books'] * 100) if stats['total_books'] > 0 else 0
            status_emoji = {
                'ongoing': '🟢',
                'completed': '✅', 
                'hiatus': '⏸️',
                'dropped': '❌',
                'stub': '📝'
            }.get(status.lower(), '📖')
            
            status_text.append(f"{status_emoji} **{status.title()}:** {count:,} ({percentage:.1f}%)")
    
    if status_text:
        embed.add_field(
            name="📈 Book Status Breakdown",
            value="\n".join(status_text),
            inline=False
        )
    
    # Interesting facts section
    facts = []
    if stats.get('oldest_ongoing_book'):
        book = stats['oldest_ongoing_book']
        facts.append(f"📜 **Oldest Ongoing:** [{book['title']}]({book['url']}) by {book['author']}")
    
    if stats.get('youngest_hiatus_book'):
        book = stats['youngest_hiatus_book']
        facts.append(f"⏸️ **Newest on Hiatus:** [{book['title']}]({book['url']}) by {book['author']}")
    
    if stats.get('most_popular_book'):
        book = stats['most_popular_book']
        facts.append(f"👑 **Most Popular:** [{book['title']}]({book['url']}) ({int(book['followers'] or 0):,} followers)")
    
    if stats.get('most_prolific_author'):
        author = stats['most_prolific_author']
        facts.append(f"✍️ **Most Prolific:** {author['name']} ({int(author['book_count'] or 0)} books)")
    
    if facts:
        embed.add_field(
            name="🎯 Notable Records",
            value="\n".join(facts),
            inline=False
        )
    
    # Snapshot statistics
    if stats.get('snapshot_stats'):
        snapshot_stats = stats['snapshot_stats']
        embed.add_field(
            name="📸 Snapshot Data",
            value=(
                f"**{snapshot_stats['total_snapshots']:,}** total snapshots\n"
                f"**{snapshot_stats['books_with_snapshots']:,}** books with tracking data\n"
                f"**{snapshot_stats['daily_snapshots']:,}** snapshots today"
            ),
            inline=True
        )
    
    # Database freshness
    if stats.get('last_update'):
        embed.add_field(
            name="🔄 Data Freshness",
            value=f"(for ONGOING books)\nLast updated: **{stats['last_update']}**",
            inline=True
        )
    
    # Fun fact
    if stats.get('total_words'):
        total_words = stats['total_words']
        # Convert to more readable format
        if total_words > 1_000_000_000:
            words_display = f"{total_words / 1_000_000_000:.1f}B words"
        elif total_words > 1_000_000:
            words_display = f"{total_words / 1_000_000:.1f}M words"
        else:
            words_display = f"{total_words:,} words"
        
        embed.add_field(
            name="📖 Total Content",
            value=f"**{words_display}** across all tracked books",
            inline=True
        )
    
    # Add promotional message occasionally
    embed = add_promotional_field(embed, force_show=True)
    
    embed.set_footer(text="Data collected by Stepan Chizhov's Royal Road Analytics • Updated continuously")
    
    return embed

# Help command
@bot.tree.command(name="help", description="Show detailed help information for all commands")
async def help_command(interaction: discord.Interaction):
    """Display comprehensive help information"""
    embed = discord.Embed(
        title="🤖 Discord Essence Bot Help",
        description=(
            "**Discover rare Royal Road book combinations & track analytics!**\n\n"
            "🎯 **Quick Start:** `/e Fantasy Magic` or `/rr-followers 105229`\n"
            "💡 **Tip:** Use autocomplete in `/essence` by pressing Tab after typing the command\n\n"
            "📊 **All chart commands show 'all time' data by default**"
        ),
        color=0x5468ff
    )
    
    # Commands section - UPDATED with new commands
    embed.add_field(
        name="🎮 Commands",
        value=(
            "**`/essence`** - Combine tags with autocomplete\n"
            "• Use Tab to navigate between fields\n"
            "• Type to see suggestions\n\n"
            "**`/tags`** - List all available tags\n"
            "**`/brag`** - Show your essence discoveries\n"
            "• Shows combinations you discovered first\n\n"
            "**`/ping`** - Check if bot is online\n\n"
            "**`/rr-followers`** - Followers over time chart\n"
            "• Example: `/rr-followers 12345 30` (last 30 days)\n"
            "• Example: `/rr-followers 12345 2025-01-01:2025-02-01`\n"
            "• Example: `/rr-followers https://royalroad.com/fiction/12345`\n\n"
            "**`/rr-views`** - Views over time chart\n"
            "**`/rr-average-views`** - Average views & chapters chart\n"
            "**`/rr-ratings`** - Rating metrics over time chart\n"
            "**`/rr-stats`** - Royal Road database statistics\n"
            "• Shows comprehensive database stats\n\n"
        ),
        inline=False
    )
    
    # How to use section
    embed.add_field(
        name="🎯 How to Use",
        value=(
            "**Method 1: Quick Command**\n"
            "Type `/e Fantasy Magic` and press Enter\n\n"
            "**Method 2: Autocomplete**\n"
            "1. Type `/essence`\n"
            "2. Press Tab or click the command\n"
            "3. Fill in both tag fields\n"
            "4. Press Enter\n\n"
            "**Chart Commands:**\n"
            "Use book ID or full Royal Road URL\n"
            "All charts default to showing all available data\n"
            "Add time parameters for specific periods"
        ),
        inline=False
    )
    
    # Chart features section
    embed.add_field(
        name="📊 Chart Features",
        value=(
            "🔷 **Followers Chart** - Track follower growth\n"
            "🔸 **Views Chart** - Monitor total view trends\n"
            "🟣 **Average Views Chart** - Views per chapter + chapter count\n"
            "🔵 **Ratings Chart** - Rating score & count over time\n\n"
            "**Time Formats:**\n"
            "• `30` - Last 30 days\n"
            "• `all` - All available data (default)\n"
            "• `2024-01-01` - From specific date\n"
            "• `2024-01-01:2024-02-01` - Date range"
        ),
        inline=False
    )
    
    # Rarity tiers
    embed.add_field(
        name="💎 Rarity Tiers",
        value=(
            "🌟 **Mythic** (0-5 books)\n"
            "⭐ **Legendary** (6-20 books)\n"
            "💜 **Epic** (21-50 books)\n"
            "💙 **Rare** (51-100 books)\n"
            "💚 **Uncommon** (101-500 books)\n"
            "⚪ **Common** (500+ books)"
        ),
        inline=True
    )
    
    # Examples section
    embed.add_field(
        name="💡 Examples",
        value=(
            "**Essence Discovery:**\n"
            "`/e Fantasy Magic` - Quick combo\n"
            "`/essence` then Tab → autocomplete\n\n"
            "**Chart Analysis:**\n"
            "`/rr-followers 105229` - All-time followers\n"
            "`/rr-views 105229 30` - Views last 30 days\n"
            "`/rr-average-views 105229` - Avg views + chapters\n"
            "`/rr-ratings 105229` - Rating trends\n\n"
            "**Advanced:**\n"
            "`/rr-followers https://royalroad.com/fiction/105229`\n"
            "`/rr-ratings 105229 2024-01-01:2024-06-01`"
        ),
        inline=False
    )
    
    # Links and support
    embed.add_field(
        name="🔗 Links & Support",
        value=(
            "📖 [Read \"The Dark Lady's Guide to Villainy\"](https://www.royalroad.com/fiction/105229)\n"
            "🔍 [More Tools](https://stepan.chizhov.com)\n"
            "💬 [Support Discord](https://discord.gg/xvw9vbvrwj)\n"
            "❤️ [Support on Patreon](https://patreon.com/stepanchizhov)\n"
            "📚 [Community Discord](https://discord.gg/7Xrrf3Q5zp)"
        ),
        inline=False
    )
    
    embed.set_footer(text="Tip: Start with '/e Fantasy Magic' or '/rr-followers 105229' to try it out!")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="rr-rs-chart", description="Show growth chart around a book's Main Rising Stars appearance")
@discord.app_commands.describe(
    book_input="Book ID or Royal Road URL",
    days_before="Days to show before RS appearance (default: 5)",
    days_after="Days to show after RS run ends (default: 5)"
)
async def rr_rs_chart(
    interaction: discord.Interaction, 
    book_input: str,
    days_before: int = 5,
    days_after: int = 5
):
    """Generate a chart showing growth around Main Rising Stars appearance"""
    global command_counter
    command_counter += 1
    
    print(f"\n[RR-RS-CHART] Command called by {interaction.user}")
    print(f"[RR-RS-CHART] Book input: '{book_input}', Days before: {days_before}, Days after: {days_after}")
    
    await interaction.response.defer()
    
    try:
        # Parse book input to get book ID
        book_id = None
        if book_input.isdigit():
            book_id = book_input
        else:
            # Extract book ID from URL
            import re
            match = re.search(r'/fiction/(\d+)', book_input)
            if match:
                book_id = match.group(1)
            else:
                await interaction.followup.send(
                    "❌ Invalid book input. Please provide a book ID or Royal Road URL.",
                    ephemeral=True
                )
                return
        
        # Call API to get Rising Stars chart data
        global session
        if session is None:
            session = aiohttp.ClientSession()
        
        # Prepare request data
        request_data = {
            'book_id': book_id,
            'days_before': days_before,
            'days_after': days_after,
            'bot_token': os.getenv('WP_BOT_TOKEN')
        }
        
        headers = {
            'User-Agent': 'RR-Discord-Bot/1.0',
            'X-WP-Nonce': 'discord-bot-request',
            'X-Forwarded-For': '127.0.0.1',
            'X-Real-IP': '127.0.0.1'
        }
        
        # Make API request
        async with session.post(
            f"{os.getenv('WP_API_URL')}/wp-json/rr-analytics/v1/rising-stars-chart",
            json=request_data,
            headers=headers,
            timeout=30
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                print(f"[RR-RS-CHART] API error: {response.status} - {error_text}")
                await interaction.followup.send(
                    f"❌ API error: {response.status}",
                    ephemeral=True
                )
                return
            
            data = await response.json()
        
        if not data.get('success'):
            error_msg = data.get('message', 'Unknown error occurred')
            await interaction.followup.send(f"❌ {error_msg}", ephemeral=True)
            return
        
        # Extract data
        book_info = data.get('book_info', {})
        chart_data = data.get('chart_data', {})
        rs_info = data.get('rs_info', {})
        growth_analysis = data.get('growth_analysis', {})
        
        book_title = book_info.get('title', f'Book {book_id}')
        book_url = book_info.get('url', f'https://www.royalroad.com/fiction/{book_id}')
        author = book_info.get('author_name', 'Unknown Author')
        
        # Create the chart
        chart_buffer = create_rs_impact_chart(chart_data, rs_info, book_title)
        
        if not chart_buffer:
            await interaction.followup.send(
                "❌ Failed to generate chart. Please try again later.",
                ephemeral=True
            )
            return
        
        # Create Discord file and embed
        file = discord.File(chart_buffer, filename=f"rs_chart_{book_id}.png")
        
        embed = discord.Embed(
            title="📈 Rising Stars Impact Analysis",
            description=f"**[{book_title}]({book_url})**\nby {author}\n\nBook ID: {book_id}",
            color=0x00A8FF
        )
        
        embed.set_image(url=f"attachment://rs_chart_{book_id}.png")
        
        # Add Rising Stars run information
        if rs_info:
            rs_lines = []
            if rs_info.get('first_appearance'):
                rs_lines.append(f"**First on Main RS:** {rs_info['first_appearance']}")
            if rs_info.get('last_appearance'):
                rs_lines.append(f"**Last on Main RS:** {rs_info['last_appearance']}")
            if rs_info.get('best_position'):
                rs_lines.append(f"**Best Position:** #{rs_info['best_position']}")
            if rs_info.get('days_on_list'):
                rs_lines.append(f"**Days on List:** {rs_info['days_on_list']}")
            
            if rs_lines:
                embed.add_field(
                    name="⭐ Main Rising Stars Run",
                    value="\n".join(rs_lines),
                    inline=True
                )
        
        # Add growth analysis - BEFORE Rising Stars
        if growth_analysis.get('before_rs'):
            before = growth_analysis['before_rs']
            before_lines = []
            
            if before.get('follower_growth_rate') is not None:
                rate = before['follower_growth_rate']
                before_lines.append(f"**Daily Growth:** {rate:.1f} followers/day")
            if before.get('total_follower_change') is not None:
                change = before['total_follower_change']
                before_lines.append(f"**Total Change:** {change:+,}")
            if before.get('view_growth_rate') is not None:
                rate = before['view_growth_rate']
                before_lines.append(f"**View Growth:** {rate:,.0f}/day")
            
            if before_lines:
                embed.add_field(
                    name="📊 Before Rising Stars",
                    value="\n".join(before_lines),
                    inline=True
                )
        
        # Add growth analysis - DURING Rising Stars
        if growth_analysis.get('during_rs'):
            during = growth_analysis['during_rs']
            during_lines = []
            
            if during.get('follower_growth_rate') is not None:
                rate = during['follower_growth_rate']
                during_lines.append(f"**Daily Growth:** {rate:.1f} followers/day")
                
                # Calculate percentage increase if we have before data
                if growth_analysis.get('before_rs', {}).get('follower_growth_rate'):
                    before_rate = growth_analysis['before_rs']['follower_growth_rate']
                    if before_rate > 0:
                        pct_increase = ((rate - before_rate) / before_rate) * 100
                        if pct_increase > 0:
                            during_lines.append(f"**Increase:** +{pct_increase:.0f}% vs before")
                        else:
                            during_lines.append(f"**Change:** {pct_increase:.0f}% vs before")
            
            if during.get('total_follower_change') is not None:
                change = during['total_follower_change']
                during_lines.append(f"**Total Gained:** {change:+,}")
            if during.get('view_growth_rate') is not None:
                rate = during['view_growth_rate']
                during_lines.append(f"**View Growth:** {rate:,.0f}/day")
            
            if during_lines:
                embed.add_field(
                    name="🚀 During Rising Stars",
                    value="\n".join(during_lines),
                    inline=True
                )
        
        # Add growth analysis - AFTER Rising Stars (if applicable)
        if growth_analysis.get('after_rs') and growth_analysis['after_rs'].get('has_data'):
            after = growth_analysis['after_rs']
            after_lines = []
            
            if after.get('follower_growth_rate') is not None:
                rate = after['follower_growth_rate']
                after_lines.append(f"**Daily Growth:** {rate:.1f} followers/day")
                
                # Compare to during RS period
                if growth_analysis.get('during_rs', {}).get('follower_growth_rate'):
                    during_rate = growth_analysis['during_rs']['follower_growth_rate']
                    if during_rate > 0:
                        pct_change = ((rate - during_rate) / during_rate) * 100
                        if pct_change < 0:
                            after_lines.append(f"**Drop:** {pct_change:.0f}% vs during RS")
                        else:
                            after_lines.append(f"**Change:** {pct_change:+.0f}% vs during RS")
            
            if after.get('total_follower_change') is not None:
                change = after['total_follower_change']
                after_lines.append(f"**Total Change:** {change:+,}")
            
            if after_lines:
                embed.add_field(
                    name="📉 After Rising Stars",
                    value="\n".join(after_lines),
                    inline=True
                )
        
        # Add summary impact
        if growth_analysis.get('impact_summary'):
            summary = growth_analysis['impact_summary']
            summary_lines = []
            
            if summary.get('follower_boost_percentage') is not None:
                boost = summary['follower_boost_percentage']
                if boost > 0:
                    summary_lines.append(f"**🎯 RS Follower Boost:** +{boost:.0f}%")
                else:
                    summary_lines.append(f"**🎯 RS Follower Impact:** {boost:.0f}%")
            
            if summary.get('total_followers_gained') is not None:
                total = summary['total_followers_gained']
                summary_lines.append(f"**Total Followers Gained:** {total:,}")
            
            if summary.get('retention_rate') is not None:
                retention = summary['retention_rate']
                summary_lines.append(f"**Growth Retention:** {retention:.0f}%")
            
            if summary_lines:
                embed.add_field(
                    name="💫 Impact Summary",
                    value="\n".join(summary_lines),
                    inline=False
                )
        
        # Add note about the chart
        embed.add_field(
            name="📊 Chart Details",
            value=(
                "• **Blue line:** Followers over time\n"
                "• **Orange line:** Views over time (right axis)\n"
                "• **Green shaded area:** Period on Main Rising Stars\n"
                "• **Vertical lines:** RS appearance start/end dates"
            ),
            inline=False
        )
        
        # Add promotional field
        embed = add_promotional_field(embed)
        
        embed.set_footer(text="Data from Stepan Chizhov's Royal Road Analytics\nTo use the bot, start typing /rr-rs-chart")
        
        await interaction.followup.send(embed=embed, file=file)
        print(f"[RR-RS-CHART] Successfully sent RS impact chart for book {book_id}")
        
    except Exception as e:
        print(f"[RR-RS-CHART] Error: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            await interaction.followup.send(
                "❌ An error occurred while generating the Rising Stars impact chart.",
                ephemeral=True
            )
        except:
            pass

def create_rs_impact_chart(chart_data, rs_info, book_title):
    """Create a chart showing follower/view growth around Rising Stars appearance"""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from datetime import datetime
        import numpy as np
        
        # Parse the data
        dates = [datetime.strptime(d, '%Y-%m-%d') for d in chart_data['dates']]
        followers = chart_data['followers']
        views = chart_data['total_views']
        
        # Create figure with two y-axes
        fig, ax1 = plt.subplots(figsize=(12, 6))
        
        # Set background color
        fig.patch.set_facecolor('#f0f0f0')
        ax1.set_facecolor('#ffffff')
        
        # Plot followers on primary axis
        color1 = '#1E88E5'
        ax1.set_xlabel('Date', fontsize=10)
        ax1.set_ylabel('Followers', color=color1, fontsize=10)
        line1 = ax1.plot(dates, followers, color=color1, linewidth=2, label='Followers', marker='o', markersize=3)
        ax1.tick_params(axis='y', labelcolor=color1)
        ax1.grid(True, alpha=0.3)
        
        # Create second y-axis for views
        ax2 = ax1.twinx()
        color2 = '#FF6B35'
        ax2.set_ylabel('Total Views', color=color2, fontsize=10)
        line2 = ax2.plot(dates, views, color=color2, linewidth=2, label='Views', linestyle='--', marker='s', markersize=3)
        ax2.tick_params(axis='y', labelcolor=color2)
        
        # Highlight Rising Stars period if available
        if rs_info and rs_info.get('first_appearance') and rs_info.get('last_appearance'):
            rs_start = datetime.strptime(rs_info['first_appearance'], '%Y-%m-%d')
            rs_end = datetime.strptime(rs_info['last_appearance'], '%Y-%m-%d')
            
            # Add shaded region for RS period
            ax1.axvspan(rs_start, rs_end, alpha=0.2, color='green', label='On Main Rising Stars')
            
            # Add vertical lines at start and end
            ax1.axvline(x=rs_start, color='green', linestyle=':', alpha=0.5, linewidth=1)
            ax1.axvline(x=rs_end, color='red', linestyle=':', alpha=0.5, linewidth=1)
            
            # Add text annotations
            y_pos = ax1.get_ylim()[1] * 0.95
            ax1.text(rs_start, y_pos, 'RS Start', rotation=90, verticalalignment='bottom', fontsize=8, color='green')
            ax1.text(rs_end, y_pos, 'RS End', rotation=90, verticalalignment='bottom', fontsize=8, color='red')
        
        # Format x-axis
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Add title
        ax1.set_title(f'Rising Stars Impact Analysis: {book_title}', fontsize=12, fontweight='bold', pad=20)
        
        # Combine legends
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        
        # Add RS period to legend if it exists
        if rs_info and rs_info.get('first_appearance'):
            ax1.legend(lines, labels, loc='upper left', fontsize=9)
        else:
            ax1.legend(lines, labels, loc='upper left', fontsize=9)
        
        # Add grid
        ax1.grid(True, which='major', alpha=0.3)
        ax1.grid(True, which='minor', alpha=0.1)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save to bytes buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
        buffer.seek(0)
        plt.close()
        
        return buffer
        
    except Exception as e:
        print(f"[RS-CHART] Error creating chart image: {e}")
        import traceback
        traceback.print_exc()
        plt.close()
        return None

@bot.tree.command(name="rr-rs-run", description="Show Rising Stars appearance history for a Royal Road book")
@discord.app_commands.describe(
    book_input="Book ID or Royal Road URL",
    tags="Comma-separated RS tags (e.g., 'main,fantasy,litrpg' or 'all'). Default: common tags"
)
async def rr_rs_run(
    interaction: discord.Interaction, 
    book_input: str,
    tags: str = ""
):
    """Show Rising Stars run information for a book"""
    global command_counter
    command_counter += 1
    
    print(f"\n[RR-RS-RUN] Command called by {interaction.user}")
    print(f"[RR-RS-RUN] Book input: '{book_input}', Tags: '{tags}'")
    
    await interaction.response.defer()
    
    try:
        # All possible RS tags from the database
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
            'virtual_reality', 'war_and_military', 'wuxia', 'xianxia'
        ]
        
        # Default tags to show if none specified
        DEFAULT_TAGS = ['main', 'fantasy', 'sci_fi', 'litrpg', 'romance', 
                       'action', 'adventure', 'comedy', 'drama', 'horror', 
                       'mystery', 'psychological']
        
        # Parse the tags parameter
        if tags:
            tags_lower = tags.lower().strip()
            
            if tags_lower == 'all':
                # Show all available tags
                requested_tags = ALL_RS_TAGS
            else:
                # Split by comma and clean up each tag
                input_tags = [tag.strip().lower().replace(' ', '_').replace('-', '_') 
                             for tag in tags.split(',')]
                
                # Validate tags against known RS tags
                requested_tags = []
                invalid_tags = []
                
                for tag in input_tags:
                    # Handle special cases and variations
                    tag_normalized = tag.replace('sci-fi', 'sci_fi').replace('scifi', 'sci_fi')
                    
                    if tag_normalized in ALL_RS_TAGS:
                        requested_tags.append(tag_normalized)
                    else:
                        invalid_tags.append(tag)
                
                if invalid_tags:
                    await interaction.followup.send(
                        f"⚠️ Unknown tags ignored: {', '.join(invalid_tags)}\n"
                        f"Use 'all' to include all tags, or choose from available RS tags.",
                        ephemeral=True
                    )
                    
                if not requested_tags:
                    requested_tags = DEFAULT_TAGS
        else:
            # Default to showing common tags
            requested_tags = DEFAULT_TAGS
        
        print(f"[RR-RS-RUN] Requested tags: {requested_tags[:10]}..." if len(requested_tags) > 10 else f"[RR-RS-RUN] Requested tags: {requested_tags}")
        
        # Parse book input to get book ID
        book_id = None
        if book_input.isdigit():
            book_id = book_input
        else:
            # Extract book ID from URL
            import re
            match = re.search(r'/fiction/(\d+)', book_input)
            if match:
                book_id = match.group(1)
            else:
                await interaction.followup.send(
                    "❌ Invalid book input. Please provide a book ID or Royal Road URL.",
                    ephemeral=True
                )
                return
        
        # Call API to get Rising Stars run data
        global session
        if session is None:
            session = aiohttp.ClientSession()
        
        # Prepare request data
        request_data = {
            'book_id': book_id,
            'tags': requested_tags,
            'bot_token': os.getenv('WP_BOT_TOKEN')
        }
        
        headers = {
            'User-Agent': 'RR-Discord-Bot/1.0',
            'X-WP-Nonce': 'discord-bot-request',
            'X-Forwarded-For': '127.0.0.1',
            'X-Real-IP': '127.0.0.1'
        }
        
        # Make API request
        async with session.post(
            f"{os.getenv('WP_API_URL')}/wp-json/rr-analytics/v1/rising-stars-run",
            json=request_data,
            headers=headers,
            timeout=30
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                print(f"[RR-RS-RUN] API error: {response.status} - {error_text}")
                await interaction.followup.send(
                    f"❌ API error: {response.status}",
                    ephemeral=True
                )
                return
            
            data = await response.json()
        
        if not data.get('success'):
            error_msg = data.get('message', 'Unknown error occurred')
            await interaction.followup.send(f"❌ {error_msg}", ephemeral=True)
            return
        
        # Extract book info and RS data
        book_info = data.get('book_info', {})
        rs_data = data.get('rising_stars_data', {})
        
        if not book_info:
            await interaction.followup.send(
                "❌ Book not found in database.",
                ephemeral=True
            )
            return
        
        # Create embed
        book_title = book_info.get('title', f'Book {book_id}')
        book_url = book_info.get('url', f'https://www.royalroad.com/fiction/{book_id}')
        author = book_info.get('author_name', 'Unknown Author')
        
        embed = discord.Embed(
            title="🌟 Rising Stars Run History",
            description=f"**[{book_title}]({book_url})**\nby {author}\n\nBook ID: {book_id}",
            color=0x00A8FF
        )
        
        # Track which tags have data
        tags_with_data = []
        
        # Add RS appearance data for each list
        if rs_data:
            # Sort tags to show Main first, then alphabetically
            sorted_tags = sorted(requested_tags, key=lambda x: (x != 'main', x))
            
            for tag_name in sorted_tags:
                tag_data = rs_data.get(tag_name, {})
                
                if tag_data and tag_data.get('appearances', 0) > 0:
                    tags_with_data.append(tag_name)
                    
                    # Build field value with RS statistics
                    field_lines = []
                    
                    # First appearance
                    if tag_data.get('first_seen'):
                        field_lines.append(f"📅 **First:** {tag_data['first_seen']}")
                    
                    # Current position
                    if tag_data.get('current_position'):
                        field_lines.append(f"📍 **Now:** #{tag_data['current_position']}")
                    else:
                        field_lines.append(f"📍 **Now:** Not on list")
                    
                    # Best position
                    if tag_data.get('best_position'):
                        field_lines.append(f"🏆 **Best:** #{tag_data['best_position']}")
                    
                    # Time on list
                    if tag_data.get('days_on_list'):
                        field_lines.append(f"⏱️ **Days:** {tag_data['days_on_list']}")
                    
                    # Total appearances
                    field_lines.append(f"📊 **Count:** {tag_data['appearances']}")
                    
                    # Trend indicator (compact)
                    if tag_data.get('trend'):
                        trend = tag_data['trend']
                        if trend == 'rising':
                            field_lines.append(f"📈 Rising")
                        elif trend == 'falling':
                            field_lines.append(f"📉 Falling")
                        elif trend == 'stable':
                            field_lines.append(f"➡️ Stable")
                    
                    # Format field name
                    display_name = tag_name.replace('_', ' ').title()
                    if tag_name == 'main':
                        display_name = "⭐ Main"
                    elif tag_name == 'sci_fi':
                        display_name = "Sci-Fi"
                    elif tag_name == 'litrpg':
                        display_name = "LitRPG"
                    elif tag_name == 'gamelit':
                        display_name = "GameLit"
                    elif tag_name == 'anti-hero_lead':
                        display_name = "Anti-Hero Lead"
                    elif tag_name == 'non-human_lead':
                        display_name = "Non-Human Lead"
                    
                    # Add field to embed (inline for compact display)
                    embed.add_field(
                        name=display_name,
                        value="\n".join(field_lines),
                        inline=True
                    )
                    
                    # Discord has a limit of 25 fields per embed
                    if len(embed.fields) >= 24:  # Leave room for summary
                        embed.add_field(
                            name="...",
                            value=f"*{len(sorted_tags) - len(embed.fields)} more tags hidden*",
                            inline=True
                        )
                        break
        
        # If no RS data found for any requested lists
        if not tags_with_data:
            embed.add_field(
                name="📊 No Rising Stars Data",
                value="This book has not appeared on any of the selected Rising Stars lists.",
                inline=False
            )
        else:
            # Add summary statistics
            total_appearances = sum(rs_data.get(tag, {}).get('appearances', 0) for tag in requested_tags)
            lists_appeared_on = len(tags_with_data)
            
            summary_lines = [
                f"**Total Appearances:** {total_appearances}",
                f"**Lists Appeared On:** {lists_appeared_on}"
            ]
            
            # Overall best position across all lists
            best_positions = [(tag, rs_data.get(tag, {}).get('best_position', 999)) 
                            for tag in requested_tags 
                            if rs_data.get(tag, {}).get('best_position')]
            if best_positions:
                best_tag, overall_best = min(best_positions, key=lambda x: x[1])
                display_name = best_tag.replace('_', ' ').title()
                if best_tag == 'main':
                    display_name = "Main"
                summary_lines.append(f"**Overall Best:** #{overall_best} ({display_name})")
            
            # Currently on how many lists
            current_lists = sum(1 for tag in requested_tags 
                              if rs_data.get(tag, {}).get('current_position'))
            if current_lists > 0:
                summary_lines.append(f"**Currently On:** {current_lists} list(s)")
            
            embed.add_field(
                name="📈 Summary",
                value="\n".join(summary_lines),
                inline=False
            )
        
        # Add note about query
        if len(requested_tags) == len(ALL_RS_TAGS):
            query_note = "Showing: All Rising Stars lists"
        elif requested_tags == DEFAULT_TAGS:
            query_note = "Showing: Common Rising Stars lists\n*Use `tags:'all'` to see all lists*"
        else:
            shown = min(5, len(requested_tags))
            tag_list = ', '.join(requested_tags[:shown])
            if len(requested_tags) > shown:
                tag_list += f" (+{len(requested_tags) - shown} more)"
            query_note = f"Showing: {tag_list}"
        
        embed.add_field(
            name="🔍 Query Info",
            value=query_note,
            inline=False
        )
        
        # Add promotional field
        embed = add_promotional_field(embed)
        
        embed.set_footer(text="Data from Stepan Chizhov's Royal Road Analytics\nTo use: /rr-rs-run [book] tags:'all' or tags:'fantasy,litrpg,romance'")
        
        await interaction.followup.send(embed=embed)
        print(f"[RR-RS-RUN] Successfully sent RS run data for book {book_id}")
        
    except Exception as e:
        print(f"[RR-RS-RUN] Error: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            await interaction.followup.send(
                "❌ An error occurred while fetching Rising Stars data.",
                ephemeral=True
            )
        except:
            pass

# Error handler
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    logger.info(f"[ERROR] Command error: {type(error).__name__}: {error}")
    import traceback
    traceback.print_exc()
    
    if interaction.response.is_done():
        await interaction.followup.send("An error occurred!", ephemeral=True)
    else:
        await interaction.response.send_message("An error occurred!", ephemeral=True)

# Add cleanup handler
import atexit
import signal

def cleanup_handler():
    """Cleanup handler for shutdown"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(cleanup())
        else:
            loop.run_until_complete(cleanup())
    except:
        pass

# Register cleanup handlers
atexit.register(cleanup_handler)
signal.signal(signal.SIGTERM, lambda s, f: cleanup_handler())
signal.signal(signal.SIGINT, lambda s, f: cleanup_handler())

# Global session variable
session = None

shoutout_module = None

# Run the bot
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("[ERROR] DISCORD_BOT_TOKEN environment variable not set!")
        exit(1)
    if not WP_BOT_TOKEN:
        print("[ERROR] WP_BOT_TOKEN environment variable not set!")
        exit(1)
    
    print("[STARTUP] Starting bot...")
    bot.run(BOT_TOKEN)




