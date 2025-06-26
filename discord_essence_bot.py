import discord
from discord.ext import commands
import aiohttp
import json
import os
from typing import Optional

# Bot configuration
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
WP_API_URL = os.getenv('WP_API_URL', 'https://stepan.chizhov.com')
WP_BOT_TOKEN = os.getenv('WP_BOT_TOKEN')

# Initialize bot with command prefix (even though we'll use slash commands)
intents = discord.Intents.default()
# intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Tag mapping
TAG_MAP = {
    # Genres
    'Fantasy': 'fantasy',
    'Action': 'action',
    'Adventure': 'adventure',
    'Comedy': 'comedy',
    'Drama': 'drama',
    'Horror': 'horror',
    'Mystery': 'mystery',
    'Psychological': 'psychological',
    'Romance': 'romance',
    'Satire': 'satire',
    'Sci-fi': 'sci_fi',
    'Short Story': 'one_shot',
    'Tragedy': 'tragedy',
    'Contemporary': 'contemporary',
    'Historical': 'historical',
    
    # Content Tags
    'Anti-Hero Lead': 'anti-hero_lead',
    'Artificial Intelligence': 'artificial_intelligence',
    'Attractive Lead': 'attractive_lead',
    'Cyberpunk': 'cyberpunk',
    'Dungeon': 'dungeon',
    'Dystopia': 'dystopia',
    'Female Lead': 'female_lead',
    'First Contact': 'first_contact',
    'GameLit': 'gamelit',
    'Gender Bender': 'gender_bender',
    'Genetically Engineered': 'genetically_engineered',
    'Grimdark': 'grimdark',
    'Hard Sci-fi': 'hard_sci-fi',
    'Harem': 'harem',
    'High Fantasy': 'high_fantasy',
    'LitRPG': 'litrpg',
    'Low Fantasy': 'low_fantasy',
    'Magic': 'magic',
    'Male Lead': 'male_lead',
    'Martial Arts': 'martial_arts',
    'Multiple Lead': 'multiple_lead',
    'Mythos': 'mythos',
    'Non-Human Lead': 'non-human_lead',
    'Portal Fantasy': 'summoned_hero',
    'Post Apocalyptic': 'post_apocalyptic',
    'Progression': 'progression',
    'Reader Interactive': 'reader_interactive',
    'Reincarnation': 'reincarnation',
    'Ruling Class': 'ruling_class',
    'School Life': 'school_life',
    'Secret Identity': 'secret_identity',
    'Slice of Life': 'slice_of_life',
    'Soft Sci-fi': 'soft_sci-fi',
    'Space Opera': 'space_opera',
    'Sports': 'sports',
    'Steampunk': 'steampunk',
    'Strategy': 'strategy',
    'Strong Lead': 'strong_lead',
    'Super Heroes': 'super_heroes',
    'Supernatural': 'supernatural',
    'Time Loop': 'loop',
    'Time Travel': 'time_travel',
    'Urban Fantasy': 'urban_fantasy',
    'Villainous Lead': 'villainous_lead',
    'Virtual Reality': 'virtual_reality',
    'War and Military': 'war_and_military',
    'Wuxia': 'wuxia',
    'Xianxia': 'xianxia',
    'Cultivation': 'cultivation'
}

# Global aiohttp session
session: Optional[aiohttp.ClientSession] = None

@bot.event
async def on_ready():
    global session
    session = aiohttp.ClientSession()
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_disconnect():
    global session
    if session:
        await session.close()

@bot.tree.command(name="essence", description="Combine two essence tags to discover rare book combinations")
async def essence(interaction: discord.Interaction, tag1: str, tag2: str):
    await interaction.response.defer()
    
    # Debug: Log the attempt
    print(f"[DEBUG] Essence command called with: {tag1}, {tag2}")
    print(f"[DEBUG] WP_API_URL: {WP_API_URL}")
    print(f"[DEBUG] WP_BOT_TOKEN exists: {'Yes' if WP_BOT_TOKEN else 'No'}")
    
    """Combine two essence tags"""
    
    # Convert display names to database slugs
    tag1_slug = TAG_MAP.get(tag1)
    tag2_slug = TAG_MAP.get(tag2)
    
    if not tag1_slug or not tag2_slug:
        await interaction.response.send_message(
            "Invalid tags! Use `/tags` to see available essences.", 
            ephemeral=True
        )
        return
        
    if tag1_slug == tag2_slug:
        await interaction.response.send_message(
            "You cannot combine an essence with itself!", 
            ephemeral=True
        )
        return
    
    # Show thinking message
    await interaction.response.defer()
    
    # Query WordPress API
    data = {
        'tags': sorted([tag1_slug, tag2_slug]),
        'bot_token': WP_BOT_TOKEN
    }
    
    try:
        async with session.post(
            f"{WP_API_URL}/wp-json/rr-analytics/v1/essence-combination", 
            json=data
        ) as response:
            if response.status == 200:
                result = await response.json()
                
                # Create embed response
                embed = create_result_embed(result, tag1, tag2, interaction)
                await interaction.followup.send(embed=embed)
            else:
                error_text = await response.text()
                print(f"API Error {response.status}: {error_text}")
                await interaction.followup.send(
                    "Error connecting to the essence database!",
                    ephemeral=True
                )
                
        result = await essence_combination_endpoint([tag1, tag2])
        
        if result:
            print(f"[DEBUG] Got result from API: {result}")
            # Create embed...
        else:
            print("[DEBUG] No result from API")
            await interaction.followup.send("Failed to get combination data")
    
    except Exception as e:
        print(f"Error in essence command: {e}")
        await interaction.followup.send(
            "An error occurred while weaving essences!",
            ephemeral=True
        )

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
    """Show all available tags"""
    tag_list = "\n".join([f"• {tag}" for tag in sorted(TAG_MAP.keys())])
    
    embed = discord.Embed(
        title="📚 Available Essence Tags",
        description=f"Use `/essence [tag1] [tag2]` to combine essences!\n\n{tag_list[:4000]}",  # Discord limit
        color=0x5468ff
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Run the bot
if __name__ == "__main__":
    bot.run(BOT_TOKEN)
