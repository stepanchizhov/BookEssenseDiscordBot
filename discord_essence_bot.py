import os
import json
import aiohttp
from typing import Optional

# We'll use discord.py's minimal components
import discord
from discord import app_commands

# Bot configuration
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
WP_API_URL = os.getenv('WP_API_URL', 'https://your-wordpress-site.com')
WP_BOT_TOKEN = os.getenv('WP_BOT_TOKEN')

# Create bot with minimal intents
intents = discord.Intents.default()
intents.message_content = True

class EssenceBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def setup_hook(self):
        # Create aiohttp session
        self.session = aiohttp.ClientSession()
        # Sync the command tree
        await self.tree.sync()
        print(f"Synced commands for {self.user}")
    
    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

# Create bot instance
bot = EssenceBot()

# Tag mapping (keep your existing mapping)
TAG_MAP = {
    'Fantasy': 'fantasy',
    'Magic': 'magic',
    'LitRPG': 'litrpg',
    'Progression': 'progression',
    'Portal Fantasy': 'summoned_hero',
    'Male Lead': 'male_lead',
    'Female Lead': 'female_lead',
    # ... add all your other tags
}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')

# Slash command for essence combination
@bot.tree.command(name="essence", description="Combine two essence tags to discover rare book combinations")
async def essence(interaction: discord.Interaction, tag1: str, tag2: str):
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
        async with bot.session.post(
            f"{WP_API_URL}/wp-json/rr-analytics/v1/essence-combination", 
            json=data
        ) as response:
            if response.status == 200:
                result = await response.json()
                
                # Create embed response
                embed = create_result_embed(result, tag1, tag2)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    "Error connecting to the essence database!",
                    ephemeral=True
                )
                
    except Exception as e:
        print(f"Error in essence command: {e}")
        await interaction.followup.send(
            "An error occurred while weaving essences!",
            ephemeral=True
        )

def create_result_embed(result, tag1, tag2):
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
        name="✦ Lore ✦",
        value=f"*{result['flavor_text']}*",
        inline=False
    )
    
    embed.set_footer(text=f"Discovered by {interaction.user.name}")
    embed.timestamp = interaction.created_at
    
    return embed

# Slash command for listing tags
@bot.tree.command(name="tags", description="List all available essence tags")
async def tags(interaction: discord.Interaction):
    """Show all available tags"""
    tag_list = "\n".join([f"• {tag}" for tag in sorted(TAG_MAP.keys())])
    
    embed = discord.Embed(
        title="📚 Available Essence Tags",
        description=tag_list[:4096],  # Discord limit
        color=0x5468ff
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Run the bot
if __name__ == "__main__":
    bot.run(BOT_TOKEN)
