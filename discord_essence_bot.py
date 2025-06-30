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
import numpy as np
from scipy import interpolate

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('discord')

# Bot configuration
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
WP_API_URL = os.getenv('WP_API_URL', 'https://stepan.chizhov.com')
WP_BOT_TOKEN = os.getenv('WP_BOT_TOKEN')

print(f"[STARTUP] Bot Token exists: {'Yes' if BOT_TOKEN else 'No'}")
print(f"[STARTUP] WP URL: {WP_API_URL}")
print(f"[STARTUP] WP Bot Token exists: {'Yes' if WP_BOT_TOKEN else 'No'}")
print(f"[STARTUP] WP Bot Token value: {WP_BOT_TOKEN[:10]}..." if WP_BOT_TOKEN else "[STARTUP] WP Bot Token is EMPTY!")

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

def interpolate_missing_data(labels, data, timestamps=None):
    """
    Interpolate missing data points to fill gaps in the time series
    Returns original data, interpolated data, and a mask indicating which points are interpolated
    """
    if not labels or not data or len(labels) != len(data):
        return labels, data, []
    
    # Convert labels to datetime objects if they aren't already
    if timestamps:
        # Use provided timestamps if available
        try:
            date_objects = [datetime.fromtimestamp(ts) if isinstance(ts, (int, float)) else datetime.strptime(str(ts), '%Y-%m-%d %H:%M:%S') for ts in timestamps]
        except:
            # Fallback to parsing labels
            date_objects = []
            for label in labels:
                try:
                    # Try different date formats
                    if isinstance(label, str):
                        if len(label.split()) == 2:  # "Jan 15" format
                            current_year = datetime.now().year
                            date_objects.append(datetime.strptime(f"{label} {current_year}", '%b %d %Y'))
                        else:
                            date_objects.append(datetime.strptime(label, '%Y-%m-%d'))
                    else:
                        date_objects.append(label)
                except:
                    # If parsing fails, create a sequential date
                    if date_objects:
                        last_date = date_objects[-1]
                        date_objects.append(last_date + timedelta(days=1))
                    else:
                        date_objects.append(datetime.now() - timedelta(days=len(labels)-len(date_objects)))
    else:
        # Parse from labels
        date_objects = []
        for label in labels:
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
                # If parsing fails, create a sequential date
                if date_objects:
                    last_date = date_objects[-1]
                    date_objects.append(last_date + timedelta(days=1))
                else:
                    date_objects.append(datetime.now() - timedelta(days=len(labels)-len(date_objects)))
    
    if len(date_objects) < 2:
        return labels, data, []
    
    # Sort by date to ensure proper interpolation
    combined = list(zip(date_objects, labels, data))
    combined.sort(key=lambda x: x[0])
    date_objects, labels, data = zip(*combined)
    date_objects, labels, data = list(date_objects), list(labels), list(data)
    
    # Find gaps larger than 2 days
    interpolated_mask = []
    new_dates = []
    new_labels = []
    new_data = []
    
    for i in range(len(date_objects)):
        new_dates.append(date_objects[i])
        new_labels.append(labels[i])
        new_data.append(data[i])
        interpolated_mask.append(False)  # Original data point
        
        # Check if there's a gap to the next point
        if i < len(date_objects) - 1:
            current_date = date_objects[i]
            next_date = date_objects[i + 1]
            gap_days = (next_date - current_date).days
            
            # If gap is more than 2 days, interpolate
            if gap_days > 2:
                current_value = data[i]
                next_value = data[i + 1]
                
                # Create interpolated points for each missing day
                for day in range(1, gap_days):
                    interpolated_date = current_date + timedelta(days=day)
                    
                    # Linear interpolation
                    ratio = day / gap_days
                    interpolated_value = current_value + (next_value - current_value) * ratio
                    
                    new_dates.append(interpolated_date)
                    new_labels.append(interpolated_date.strftime('%b %d'))
                    new_data.append(interpolated_value)
                    interpolated_mask.append(True)  # Interpolated data point
    
    return new_labels, new_data, interpolated_mask

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
        
        print(f"[CHART] Fetching chart data for book input: {book_input}")
        print(f"[CHART] Days parameter: {days_param}")
        print(f"[CHART] API request data: {data}")
        print(f"[CHART] Request URL: {url}")
        
        async with session.post(url, json=data, headers=headers) as response:
            if response.status == 200:
                result = await response.json()
                print(f"[CHART] Successfully fetched chart data")
                print(f"[CHART] Response keys: {list(result.keys())}")
                if 'data_info' in result:
                    print(f"[CHART] Total snapshots: {result['data_info'].get('total_snapshots', 'unknown')}")
                    print(f"[CHART] Filter applied: {result['data_info'].get('filter_applied', 'unknown')}")
                return result
            else:
                error_text = await response.text()
                print(f"[CHART] Failed to fetch chart data: {response.status} - {error_text}")
                return None
                
    except Exception as e:
        print(f"[CHART] Exception fetching chart data: {e}")
        return None

# Updated create_chart_image function with interpolation and better visualization
def create_chart_image(chart_data, chart_type, book_title, days_param):
    """Create a chart image using matplotlib with data interpolation for missing dates"""
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
            interpolated_color = '#B8E6E6'  # Lighter shade for interpolated data
        else:  # views
            data = chart_data.get('total_views', [])
            title = f'Views Over Time - {book_title}'
            ylabel = 'Total Views'
            color = '#FF6384'
            interpolated_color = '#FFB3C1'  # Lighter shade for interpolated data
        
        if not data or not labels:
            # Create a "no data" chart
            ax.text(0.5, 0.5, 'No data available for this time period', 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=16, color='gray')
            ax.set_title(title)
        else:
            # Interpolate missing data
            interpolated_labels, interpolated_data, interpolated_mask = interpolate_missing_data(
                labels, data, timestamps
            )
            
            if interpolated_labels and interpolated_data:
                x_indices = range(len(interpolated_labels))
                
                # Separate original and interpolated data for different styling
                original_x = []
                original_y = []
                interpolated_x = []
                interpolated_y = []
                
                for i, is_interpolated in enumerate(interpolated_mask):
                    if is_interpolated:
                        interpolated_x.append(i)
                        interpolated_y.append(interpolated_data[i])
                    else:
                        original_x.append(i)
                        original_y.append(interpolated_data[i])
                
                # Plot original data
                if original_x:
                    ax.plot(original_x, original_y, color=color, linewidth=2, marker='o', 
                           markersize=4, label='Actual Data', zorder=3)
                    ax.fill_between(original_x, original_y, alpha=0.3, color=color)
                
                # Plot interpolated data with different styling
                if interpolated_x:
                    ax.plot(interpolated_x, interpolated_y, color=interpolated_color, 
                           linewidth=1.5, linestyle='--', marker='s', markersize=3, 
                           label='Interpolated Data', alpha=0.8, zorder=2)
                    ax.fill_between(interpolated_x, interpolated_y, alpha=0.15, color=interpolated_color)
                
                # Connect all points with a subtle line
                ax.plot(x_indices, interpolated_data, color=color, linewidth=1, alpha=0.5, zorder=1)
                
                # Format axes
                ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
                ax.set_ylabel(ylabel, fontsize=12)
                ax.set_xlabel('Date', fontsize=12)
                
                # Format y-axis with commas
                ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
                
                # Set x-axis labels
                if len(interpolated_labels) > 15:
                    # Show every nth label to avoid crowding
                    step = len(interpolated_labels) // 10
                    ax.set_xticks(x_indices[::step])
                    ax.set_xticklabels(interpolated_labels[::step], rotation=45)
                else:
                    ax.set_xticks(x_indices)
                    ax.set_xticklabels(interpolated_labels, rotation=45)
                
                # Add legend if we have interpolated data
                if interpolated_x:
                    ax.legend(loc='upper left', framealpha=0.9)
            else:
                # Fallback to original data plotting
                x_indices = range(len(labels))
                ax.plot(x_indices, data, color=color, linewidth=2, marker='o', markersize=4)
                ax.fill_between(x_indices, data, alpha=0.3, color=color)
                
                # Format axes
                ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
                ax.set_ylabel(ylabel, fontsize=12)
                ax.set_xlabel('Date', fontsize=12)
                
                # Format y-axis with commas
                ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
                
                # Set x-axis labels
                if len(labels) > 15:
                    step = len(labels) // 10
                    ax.set_xticks(x_indices[::step])
                    ax.set_xticklabels(labels[::step], rotation=45)
                else:
                    ax.set_xticks(x_indices)
                    ax.set_xticklabels(labels, rotation=45)
        
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
        print(f"[CHART] Error creating chart image: {e}")
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
    global session
    session = await get_session()
    print(f'[READY] {bot.user} has connected to Discord!')
    print(f'[READY] Bot is in {len(bot.guilds)} guilds')
    
    # List all guilds
    for guild in bot.guilds:
        print(f'[READY] - Guild: {guild.name} (ID: {guild.id})')
    
    # Test WordPress connection immediately
    print('[TEST] Testing WordPress connection...')
    try:
        test_url = f"{WP_API_URL}/wp-json/rr-analytics/v1/health"
        headers = {
            'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)'
        }
        async with session.get(test_url, headers=headers) as response:
            print(f'[TEST] WordPress health check: Status {response.status}')
            if response.status == 200:
                print('[TEST] ✅ WordPress API is reachable!')
            else:
                response_text = await response.text()
                print(f'[TEST] ❌ WordPress API returned error status: {response_text[:200]}')
    except Exception as e:
        print(f'[TEST] ❌ Failed to reach WordPress: {e}')
    
    # Sync slash commands
    try:
        print('[SYNC] Starting command sync...')
        synced = await bot.tree.sync()
        print(f'[SYNC] Successfully synced {len(synced)} command(s)')
        for cmd in synced:
            print(f'[SYNC] - Command: {cmd.name}')
    except Exception as e:
        print(f'[ERROR] Failed to sync commands: {e}')
        import traceback
        traceback.print_exc()

@bot.event
async def on_disconnect():
    print('[DISCONNECT] Bot disconnected')
    # Don't close the session here - let it persist

@bot.event
async def on_error(event, *args, **kwargs):
    """Handle errors gracefully"""
    print(f'[ERROR] Error in {event}')
    import traceback
    traceback.print_exc()

# Close session only when bot is shutting down
async def cleanup():
    global session
    if session and not session.closed:
        await session.close()
        print('[CLEANUP] Session closed')

@bot.tree.command(name="essence", description="Combine two essence tags to discover rare book combinations")
@discord.app_commands.describe(
    tag1="First tag - choose from list or type your own",
    tag2="Second tag - choose from list or type your own"
)
@discord.app_commands.autocomplete(tag1=tag_autocomplete)
@discord.app_commands.autocomplete(tag2=tag_autocomplete)
async def essence(interaction: discord.Interaction, tag1: str, tag2: str):
    """Combine two essence tags - accepts both URL format and display names"""
    
    print(f"\n[COMMAND] Essence command called")
    print(f"[COMMAND] User: {interaction.user} (ID: {interaction.user.id})")
    print(f"[COMMAND] Guild: {interaction.guild.name if interaction.guild else 'DM'}")
    print(f"[COMMAND] Raw input: '{tag1}' + '{tag2}'")
    
    # Defer the response FIRST before any processing
    await interaction.response.defer()
    print("[COMMAND] Response deferred")
    
    try:
        # Get the session
        session = await get_session()
        
        # Normalize tags
        normalized_tag1 = normalize_tag(tag1)
        normalized_tag2 = normalize_tag(tag2)
        
        print(f"[COMMAND] Normalized: '{normalized_tag1}' + '{normalized_tag2}'")
        
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
        print(f"[API] URL: {url}")
        print(f"[API] Payload: {json.dumps(data)}")
        
        # Make API request
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        async with session.post(url, json=data, headers=headers) as response:
            response_text = await response.text()
            print(f"[API] Status: {response.status}")
            print(f"[API] Response: {response_text[:500]}...")  # First 500 chars
            
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
                print(f"[ERROR] API returned status {response.status}")
    
    except Exception as e:
        print(f"[ERROR] Exception in essence command: {type(e).__name__}: {e}")
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
    
    # Add promotional message every 2 commands
    if command_counter % 2 == 0:
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
        
        # Add promotional field with hyperlink
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━",
            value=f"{promo['text']}\n[**{promo['link_text']}**]({promo['url']})",
            inline=False
        )
    
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
    
    print(f"\n[RR-FOLLOWERS] Command called by {interaction.user}")
    print(f"[RR-FOLLOWERS] Book input: '{book_input}', Days: '{days}'")
    
    await interaction.response.defer()
    
    try:
        # Parse days parameter (supports date ranges) - NOW DEFAULTS TO 'all'
        days_param = parse_days_parameter(days)
        print(f"[RR-FOLLOWERS] Parsed days parameter: {days_param}")
        
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
        
        print(f"[RR-FOLLOWERS] API returned {data_info.get('total_snapshots', 'unknown')} snapshots")
        print(f"[RR-FOLLOWERS] Filter applied: {data_info.get('filter_applied', 'unknown')}")
        
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
        
        # Add data note about interpolation
        embed.add_field(
            name="📊 Chart Features",
            value="• Solid lines show actual data\n• Dashed lines show interpolated estimates for missing dates\n• Want to add your historical data? Visit [Stepan Chizhov's Discord](https://discord.gg/xvw9vbvrwj)",
            inline=False
        )
        
        # Add promotional message every 2 commands
        if command_counter % 2 == 0:
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
            
            # Add promotional field with hyperlink
            embed.add_field(
                name="━━━━━━━━━━━━━━━━━━━━━",
                value=f"{promo['text']}\n[**{promo['link_text']}**]({promo['url']})",
                inline=False
            )
        
        embed.set_footer(text="Data from Stepan Chizhov's Royal Road Analytics\n(starting with the 12th of June 2025)\nTo use the bot, start typing /rr-views or /rr-followers")
        
        await interaction.followup.send(embed=embed, file=file)
        print(f"[RR-FOLLOWERS] Successfully sent chart for book {book_id}")
        
    except Exception as e:
        print(f"[RR-FOLLOWERS] Error: {e}")
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
    
    print(f"\n[RR-VIEWS] Command called by {interaction.user}")
    print(f"[RR-VIEWS] Book input: '{book_input}', Days: '{days}'")
    
    await interaction.response.defer()
    
    try:
        # Parse days parameter (supports date ranges) - NOW DEFAULTS TO 'all'
        days_param = parse_days_parameter(days)
        print(f"[RR-VIEWS] Parsed days parameter: {days_param}")
        
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
        
        print(f"[RR-VIEWS] API returned {data_info.get('total_snapshots', 'unknown')} snapshots")
        print(f"[RR-VIEWS] Filter applied: {data_info.get('filter_applied', 'unknown')}")
        
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
        
        # Add data note about interpolation
        embed.add_field(
            name="📊 Chart Features",
            value="• Solid lines show actual data\n• Dashed lines show interpolated estimates for missing dates\n• Want to add your historical data? Visit [Stepan Chizhov's Discord](https://discord.gg/xvw9vbvrwj)",
            inline=False
        )
        
        # Add promotional message every 2 commands
        if command_counter % 2 == 0:
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
            
            # Add promotional field with hyperlink
            embed.add_field(
                name="━━━━━━━━━━━━━━━━━━━━━",
                value=f"{promo['text']}\n[**{promo['link_text']}**]({promo['url']})",
                inline=False
            )
        
        embed.set_footer(text="Data from Stepan Chizhov's Royal Road Analytics\n(starting with the 12th of June 2025)\nTo use the bot, start typing /rr-views or /rr-followers")
        
        await interaction.followup.send(embed=embed, file=file)
        print(f"[RR-VIEWS] Successfully sent chart for book {book_id}")
        
    except Exception as e:
        print(f"[RR-VIEWS] Error: {e}")
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
    print(f"[COMMAND] Ping command called by {interaction.user}")
    await interaction.response.send_message("Pong! The bot is online.", ephemeral=True)

# Test WordPress connection command
@bot.tree.command(name="test", description="Test WordPress API connection")
async def test(interaction: discord.Interaction):
    print(f"[COMMAND] Test command called by {interaction.user}")
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
            print(f"[TEST] Health check: {health_status}")
        
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
            print(f"[TEST] Essence endpoint: {essence_status}")
        
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
        print(f"[ERROR] Test command failed: {e}")
        await interaction.followup.send(
            f"❌ Test failed: {str(e)}",
            ephemeral=True
        )

# Process tags for the quick essence commands
async def process_quick_essence(interaction: discord.Interaction, tags: str):
    """Process quick essence command with two tags in one input"""
    
    print(f"\n[COMMAND] Quick essence command called")
    print(f"[COMMAND] User: {interaction.user}")
    print(f"[COMMAND] Input: '{tags}'")
    
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
            print(f"[COMMAND] Interpreted as: '{tag1_orig}' + '{tag2_orig}'")
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
        print(f"[ERROR] Exception in quick essence: {e}")
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

# Help command
@bot.tree.command(name="help", description="Learn how to use the Essence Bot")
async def help_command(interaction: discord.Interaction):
    """Show detailed help information"""
    
    embed = discord.Embed(
        title="📖 Essence Bot Help",
        description="Discover rare book combinations by combining Royal Road tags!",
        color=0x5468ff
    )
    
    # Commands section
    embed.add_field(
        name="🎮 Commands",
        value=(
            "**`/essence`** - Combine tags with autocomplete\n"
            "• Use Tab to navigate between fields\n"
            "• Type to see suggestions\n\n"
            "**`/e`** - Quick combination\n"
            "• Example: `/e Fantasy Magic`\n"
            "• Example: `/e female_lead litrpg`\n\n"
            "**`/combine`** - Another quick combination\n"
            "• Same as `/e`\n\n"
            "**`/tags`** - List all available tags\n"
            "**`/help`** - Show this help message\n"
            "**`/ping`** - Check if bot is online\n"
            "**`/rr-followers`** - Followers over time chart\n"
            "• Example: `/rr-followers 12345` (shows all time)\n"
            "• Example: `/rr-followers 12345 30` (last 30 days)\n"
            "• Example: `/rr-followers 12345 2025-01-01:2025-02-01`\n"
            "• Example: `/rr-followers https://royalroad.com/fiction/12345`\n\n"
            "**`/rr-views`** - Views over time chart\n"
            "• Example: `/rr-views 12345` (shows all time)\n"
            "• Same format as followers command\n\n"
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
            "4. Press Enter"
        ),
        inline=True
    )
    
    # Tag formats section
    embed.add_field(
        name="📝 Tag Formats",
        value=(
            "**Accepted formats:**\n"
            "• Display: `Fantasy`, `Female Lead`\n"
            "• URL: `fantasy`, `female_lead`\n"
            "• Mixed: `FANTASY`, `magic`\n"
            "**Multi-word tags:**\n"
            "• `/e Female Lead Magic` ✓\n"
            "• `/e portal fantasy litrpg` ✓"
        ),
        inline=True
    )
    
    # Chart features section
    embed.add_field(
        name="📊 Chart Features",
        value=(
            "**Default:** Shows all available data\n"
            "**Interpolation:** Missing dates filled with estimates\n"
            "• Solid lines = Actual data\n"
            "• Dashed lines = Interpolated data\n"
            "**Time ranges:** 30 days, date ranges, or 'all'"
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
    
    # Examples
    embed.add_field(
        name="📚 Example Combinations",
        value=(
            "`/e Fantasy Magic` - The Arcane Weave\n"
            "`/e LitRPG Progression` - The Ascending Interface\n"
            "`/e Female Lead Strong Lead` - The Valkyrie's Bond\n"
            "`/e Portal Fantasy Reincarnation` - The Eternal Gateway"
        ),
        inline=True
    )
    
    # Tips
    embed.add_field(
        name="💡 Pro Tips",
        value=(
            "• Try unusual combinations for rare discoveries!\n"
            "• Use `/tags` to see all 65+ available tags\n"
            "• Charts now default to showing all time data\n"
            "• Missing dates are filled with smart estimates\n"
            "• The rarer the combination, the more prestigious!"
        ),
        inline=False
    )
    
    embed.set_footer(text="Created by Stepan Chizhov • Powered by Royal Road Analytics")
    embed.timestamp = interaction.created_at
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Error handler
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    print(f"[ERROR] Command error: {type(error).__name__}: {error}")
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
