import discord
from discord.ext import commands
import aiohttp
import json
import os
from typing import Optional
import logging

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
    'cultivation': 'Cultivation',
    'Cultivation': 'Cultivation',
    
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

# Global aiohttp session
session: Optional[aiohttp.ClientSession] = None

def normalize_tag(tag: str) -> str:
    """Normalize any tag input to its canonical display name"""
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

@bot.event
async def on_ready():
    global session
    session = aiohttp.ClientSession()
    print(f'[READY] {bot.user} has connected to Discord!')
    print(f'[READY] Bot is in {len(bot.guilds)} guilds')
    
    # List all guilds
    for guild in bot.guilds:
        print(f'[READY] - Guild: {guild.name} (ID: {guild.id})')
    
    # Test WordPress connection immediately
    print('[TEST] Testing WordPress connection...')
    try:
        test_url = f"{WP_API_URL}/wp-json/rr-analytics/v1/health"
        async with session.get(test_url) as response:
            print(f'[TEST] WordPress health check: Status {response.status}')
            if response.status == 200:
                print('[TEST] ✅ WordPress API is reachable!')
            else:
                print('[TEST] ❌ WordPress API returned error status')
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
    global session
    if session:
        await session.close()
        print('[DISCONNECT] Session closed')

@bot.tree.command(name="essence", description="Combine two essence tags to discover rare book combinations")
@discord.app_commands.describe(
    tag1="First tag (e.g., 'Fantasy', 'fantasy', 'female_lead', 'Female Lead')",
    tag2="Second tag (e.g., 'Magic', 'magic', 'litrpg', 'LitRPG')"
)
async def essence(interaction: discord.Interaction, tag1: str, tag2: str):
    """Combine two essence tags - accepts both URL format and display names"""
    
    print(f"\n[COMMAND] Essence command called")
    print(f"[COMMAND] User: {interaction.user} (ID: {interaction.user.id})")
    print(f"[COMMAND] Guild: {interaction.guild.name if interaction.guild else 'DM'}")
    print(f"[COMMAND] Raw input: '{tag1}' + '{tag2}'")
    
    try:
        # Defer the response first
        await interaction.response.defer()
        print("[COMMAND] Response deferred")
        
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
            'bot_token': WP_BOT_TOKEN
        }
        
        url = f"{WP_API_URL}/wp-json/rr-analytics/v1/essence-combination"
        print(f"[API] URL: {url}")
        print(f"[API] Payload: {json.dumps(data)}")
        
        # Make API request
        async with session.post(
            url,
            json=data,
            headers={'Content-Type': 'application/json'}
        ) as response:
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

def create_result_embed(result, tag1, tag2, interaction):
    # Color based on rarity
    colors = {
        'undiscovered': 0xFFFFFF,
        'mythic': 0xFF0000,
        'legendary': 0xFF8C00,
        'epic': 0x9400D3,
        'rare': 0x0000FF,
        'uncommon': 0x00FF00,
        'common': 0x808080
    }
    
    rarity_tier = result.get('rarity_tier', 'common')
    
    embed = discord.Embed(
        title="🌟 ESSENCE COMBINATION DISCOVERED! 🌟",
        color=colors.get(rarity_tier, 0x808080)
    )
    
    embed.add_field(
        name="Essences Combined",
        value=f"**{tag1}** + **{tag2}**",
        inline=False
    )
    
    embed.add_field(
        name="Creates",
        value=f"***{result['combination_name']}***",
        inline=False
    )
    
    embed.add_field(
        name="Rarity",
        value=f"{result['rarity']}",
        inline=True
    )
    
    embed.add_field(
        name="Books Found",
        value=f"📚 {result['book_count']}",
        inline=True
    )
    
    embed.add_field(
        name="\u200b",
        value="\u200b",
        inline=True
    )
    
    embed.add_field(
        name="✦ Lore ✦",
        value=f"*{result['flavor_text']}*",
        inline=False
    )
    
    embed.set_footer(text=f"Discovered by {interaction.user.name}")
    embed.timestamp = interaction.created_at
    
    return embed

@bot.tree.command(name="tags", description="List all available essence tags")
async def tags(interaction: discord.Interaction):
    """Show all available tags with examples of accepted formats"""
    
    embed = discord.Embed(
        title="📚 Available Essence Tags",
        description="You can use any of these formats:\n• Display name: `Female Lead`\n• URL format: `female_lead`\n• Lowercase: `female lead`\n• Shortcuts: `FL`, `ML`, `AI`, `VR`, `SOL`",
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
    
    # Add examples
    embed.add_field(
        name="Example Usage",
        value="`/essence fantasy magic`\n`/essence female_lead strong_lead`\n`/essence LitRPG progression`\n`/essence Portal Fantasy Reincarnation`",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

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
    
    try:
        # Test health endpoint
        health_url = f"{WP_API_URL}/wp-json/rr-analytics/v1/health"
        async with session.get(health_url) as response:
            health_status = response.status
            health_text = await response.text()
            print(f"[TEST] Health check: {health_status}")
        
        # Test essence endpoint
        test_data = {
            'tags': ['Fantasy', 'Magic'],
            'bot_token': WP_BOT_TOKEN
        }
        
        essence_url = f"{WP_API_URL}/wp-json/rr-analytics/v1/essence-combination"
        async with session.post(
            essence_url,
            json=test_data,
            headers={'Content-Type': 'application/json'}
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
