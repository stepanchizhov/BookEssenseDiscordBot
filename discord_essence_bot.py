import discord
from discord.ext import commands
import aiohttp
import json
import os
from typing import Optional

# Bot configuration
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
WP_API_URL = os.getenv('WP_API_URL', 'https://your-wordpress-site.com')
WP_BOT_TOKEN = os.getenv('WP_BOT_TOKEN')

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True

class EssenceBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        
    async def setup_hook(self):
        await self.add_cog(EssenceGame(self))
        await self.tree.sync()
        print(f"Synced commands for {self.user}")

bot = EssenceBot()

# Tag mapping (65 tags total)
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
    'Cultivation': 'cultivation',
    'Academy': 'academy',
    'Technologically Engineered': 'technologically_engineered'
}

class EssenceGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def cog_load(self):
        self.session = aiohttp.ClientSession()
    
    async def cog_unload(self):
        if self.session:
            await self.session.close()
    
    async def tag_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = [
            discord.app_commands.Choice(name=tag, value=tag)
            for tag in TAG_MAP.keys()
            if current.lower() in tag.lower()
        ]
        return choices[:25]
    
    @discord.app_commands.command(name="essence", description="Combine two essence tags to discover rare book combinations")
    @discord.app_commands.autocomplete(tag1=tag_autocomplete, tag2=tag_autocomplete)
    async def essence(self, interaction: discord.Interaction, tag1: str, tag2: str):
        # Validate tags
        tag1_slug = TAG_MAP.get(tag1)
        tag2_slug = TAG_MAP.get(tag2)
        
        if not tag1_slug or not tag2_slug:
            await interaction.response.send_message("Invalid tags! Use `/tags` to see available essences.", ephemeral=True)
            return
            
        if tag1_slug == tag2_slug:
            await interaction.response.send_message("You cannot combine an essence with itself!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Query WordPress API
        data = {
            'tags': sorted([tag1_slug, tag2_slug]),
            'bot_token': WP_BOT_TOKEN
        }
        
        try:
            async with self.session.post(f"{WP_API_URL}/wp-json/rr-analytics/v1/essence-combination", json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    embed = self.create_result_embed(result, tag1, tag2, interaction)
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("Error connecting to the essence database!", ephemeral=True)
                    
        except Exception as e:
            print(f"Error: {e}")
            await interaction.followup.send("An error occurred while weaving essences!", ephemeral=True)
    
    def create_result_embed(self, result, tag1, tag2, interaction):
        colors = {
            'undiscovered': 0xFFFFFF,
            'mythic': 0xFF0000,
            'legendary': 0xFF8C00,
            'epic': 0x9400D3,
            'rare': 0x0000FF,
            'uncommon': 0x00FF00,
            'common': 0x808080
        }
        
        rarity_emojis = {
            'undiscovered': '✨',
            'mythic': '🌟',
            'legendary': '⭐',
            'epic': '💜',
            'rare': '💙',
            'uncommon': '💚',
            'common': '⚪'
        }
        
        rarity_tier = result.get('rarity_tier', 'common')
        rarity_emoji = rarity_emojis.get(rarity_tier, '⚪')
        
        embed = discord.Embed(
            title=f"{rarity_emoji} ESSENCE COMBINATION DISCOVERED! {rarity_emoji}",
            color=colors.get(rarity_tier, 0x808080)
        )
        
        embed.add_field(name="Essences Combined", value=f"**{tag1}** + **{tag2}**", inline=False)
        embed.add_field(name="Creates", value=f"***{result['combination_name']}***", inline=False)
        embed.add_field(name="Rarity", value=f"{rarity_emoji} {result['rarity']}", inline=True)
        embed.add_field(name="Books Found", value=f"📚 {result['book_count']}", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="✦ Lore ✦", value=f"*{result['flavor_text']}*", inline=False)
        embed.set_footer(text=f"Discovered by {interaction.user.name}")
        embed.timestamp = interaction.created_at
        
        return embed
    
    @discord.app_commands.command(name="tags", description="List all available essence tags")
    async def tags(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📚 Available Essence Tags",
            description="Use `/essence [tag1] [tag2]` to combine essences!\n\nTotal tags: " + str(len(TAG_MAP)),
            color=0x5468ff
        )
        
        # Split tags into chunks for Discord's field limits
        tag_list = sorted(TAG_MAP.keys())
        chunks = [tag_list[i:i+20] for i in range(0, len(tag_list), 20)]
        
        for i, chunk in enumerate(chunks):
            field_name = f"Tags ({i*20+1}-{min((i+1)*20, len(tag_list))})"
            field_value = "\n".join([f"• {tag}" for tag in chunk])
            embed.add_field(name=field_name, value=field_value[:1024], inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')

if __name__ == "__main__":
    bot.run(BOT_TOKEN)