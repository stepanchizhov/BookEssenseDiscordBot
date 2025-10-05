import discord
from discord.ext import commands
import aiohttp
import json
import logging
from typing import Optional, List, Dict, Any

# Set up logging
logger = logging.getLogger('discord')

class EssenceCommandsModule:
    def __init__(self, bot, session, wp_api_url, wp_bot_token, 
                 get_promotional_field_func=None, 
                 add_promotional_field_func=None,
                 tag_autocomplete_func=None):
        self.bot = bot
        self.session = session
        self.wp_api_url = wp_api_url
        self.wp_bot_token = wp_bot_token
        self.command_counter = 0
        
        # Store the shared functions
        self.get_promotional_field = get_promotional_field_func or (lambda f=False: None)
        self.add_promotional_field = add_promotional_field_func or (lambda e, f=False: e)
        self.tag_autocomplete = tag_autocomplete_func
        
        # Import tag data from shared_utils
        try:
            from shared_utils import TAG_MAPPING, UNIQUE_TAGS, normalize_tag
            self.TAG_MAPPING = TAG_MAPPING
            self.UNIQUE_TAGS = UNIQUE_TAGS
            self.normalize_tag = normalize_tag
        except ImportError:
            logger.error("[ESSENCE] Could not import shared_utils")
            self.TAG_MAPPING = {}
            self.UNIQUE_TAGS = []
            self.normalize_tag = lambda x: x
        
        # Register commands
        self.register_commands()
    
    def register_commands(self):
        """Register all essence-related commands with the bot"""
        
        # Main essence command with autocomplete
        @self.bot.tree.command(name="essence", description="Combine two essence tags to discover rare book combinations")
        @discord.app_commands.describe(
            tag1="First tag - choose from list or type your own",
            tag2="Second tag - choose from list or type your own"
        )
        @discord.app_commands.autocomplete(tag1=self.tag_autocomplete)
        @discord.app_commands.autocomplete(tag2=self.tag_autocomplete)
        async def essence(interaction: discord.Interaction, tag1: str, tag2: str):
            await self.essence_handler(interaction, tag1, tag2)
        
        # Quick essence command
        @self.bot.tree.command(name="e", description="Quick essence combination: /e Fantasy Magic")
        @discord.app_commands.describe(
            tags="Enter two tags separated by space (e.g., 'Fantasy Magic' or 'female_lead strong_lead')"
        )
        async def e_command(interaction: discord.Interaction, tags: str):
            await self.quick_essence_handler(interaction, tags)
        
        # Alias for quick essence
        @self.bot.tree.command(name="combine", description="Combine two essence tags: /combine Fantasy Magic")
        @discord.app_commands.describe(
            tags="Enter two tags separated by space"
        )
        async def combine_alias(interaction: discord.Interaction, tags: str):
            await self.quick_essence_handler(interaction, tags)
        
        # Tags command
        @self.bot.tree.command(name="tags", description="List all available essence tags")
        async def tags(interaction: discord.Interaction):
            await self.tags_handler(interaction)
        
        # Brag command
        @self.bot.tree.command(name="brag", description="Show essence combinations you discovered first!")
        async def brag_command(interaction: discord.Interaction):
            await self.brag_handler(interaction)
        
        # RR Stats command
        @self.bot.tree.command(name="rr-stats", description="Show Royal Road database statistics")
        async def rr_stats_command(interaction: discord.Interaction):
            await self.rr_stats_handler(interaction)
    
    async def essence_handler(self, interaction: discord.Interaction, tag1: str, tag2: str):
        """Handle the main essence command"""
        logger.info(f"\n[COMMAND] Essence command called")
        logger.info(f"[COMMAND] User: {interaction.user} (ID: {interaction.user.id})")
        logger.info(f"[COMMAND] Guild: {interaction.guild.name if interaction.guild else 'DM'}")
        logger.info(f"[COMMAND] Raw input: '{tag1}' + '{tag2}'")
        
        # Defer the response FIRST
        await interaction.response.defer()
        logger.info(f"[COMMAND] Response deferred")
        
        try:
            # Normalize tags
            normalized_tag1 = self.normalize_tag(tag1)
            normalized_tag2 = self.normalize_tag(tag2)
            
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
                'bot_token': self.wp_bot_token,
                'discord_user': {
                    'id': str(interaction.user.id),
                    'username': interaction.user.name,
                    'discriminator': interaction.user.discriminator,
                    'display_name': interaction.user.display_name
                }
            }
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/essence-combination"
            logger.info(f"[API] URL: {url}")
            
            # Make API request
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            async with self.session.post(url, json=data, headers=headers) as response:
                response_text = await response.text()
                logger.info(f"[API] Status: {response.status}")
                logger.info(f"[API] Response: {response_text[:500]}...")
                
                if response.status == 200:
                    result = json.loads(response_text)
                    
                    # Create embed using the normalized display names
                    embed = self.create_result_embed(result, normalized_tag1, normalized_tag2, interaction)
                    await interaction.followup.send(embed=embed)
                    logger.info(f"[COMMAND] Embed sent successfully")
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
                logger.info(f"[ERROR] Failed to send error message to user")
    
    async def quick_essence_handler(self, interaction: discord.Interaction, tags: str):
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
            possible_tags = []
            
            # Try different combinations
            for i in range(1, len(tag_list)):
                tag1_candidate = ' '.join(tag_list[:i])
                tag2_candidate = ' '.join(tag_list[i:])
                
                norm1 = self.normalize_tag(tag1_candidate)
                norm2 = self.normalize_tag(tag2_candidate)
                
                if norm1 and norm2:
                    possible_tags.append((norm1, norm2, tag1_candidate, tag2_candidate))
            
            if possible_tags:
                # Use the first valid combination
                tag1_norm, tag2_norm, tag1_orig, tag2_orig = possible_tags[0]
                logger.info(f"[COMMAND] Interpreted as: '{tag1_orig}' + '{tag2_orig}'")
            else:
                await interaction.response.send_message(
                    f"Could not interpret '{tags}' as two valid tags.\nTry: `/e Fantasy Magic` or `/e female_lead strong_lead`\nTriads, Tetrads, and Pentads will become available in the future!",
                    ephemeral=True
                )
                return
        else:
            tag1_orig, tag2_orig = tag_list[0], tag_list[1]
            tag1_norm = self.normalize_tag(tag1_orig)
            tag2_norm = self.normalize_tag(tag2_orig)
        
        # Now process as normal essence command
        try:
            await interaction.response.defer()
            
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
                'bot_token': self.wp_bot_token
            }
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/essence-combination"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            async with self.session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    result = json.loads(await response.text())
                    embed = self.create_result_embed(result, tag1_norm, tag2_norm, interaction)
                    await interaction.followup.send(embed=embed)
                    logger.info(f"[COMMAND] Quick essence completed successfully")
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
    
    async def tags_handler(self, interaction: discord.Interaction):
        """Show all available tags with examples"""
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
        all_tags = self.UNIQUE_TAGS
        
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
    
    async def brag_handler(self, interaction: discord.Interaction):
        """Show essence combinations the user discovered first"""
        self.command_counter += 1
        
        logger.info(f"\n[BRAG] Command called by {interaction.user}")
        logger.info(f"[BRAG] User ID: {interaction.user.id}, Username: {interaction.user.name}#{interaction.user.discriminator}")
        
        await interaction.response.defer()
        
        try:
            # Format Discord user string
            user_string = f"{interaction.user.name}#{interaction.user.discriminator}"
            
            # Make API request to get user's discoveries
            data = {
                'user_string': user_string,
                'bot_token': self.wp_bot_token
            }
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/user-discoveries"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            async with self.session.post(url, json=data, headers=headers) as response:
                response_text = await response.text()
                logger.info(f"[BRAG] API Status: {response.status}")
                logger.info(f"[BRAG] API Response: {response_text[:300]}...")
                
                if response.status == 200:
                    result = json.loads(response_text)
                    
                    if result['success'] and result['discoveries']:
                        embed = self.create_brag_embed(result, interaction.user)
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
                        
                    logger.info(f"[BRAG] Response sent successfully")
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
                logger.info(f"[ERROR] Failed to send error message to user")
    
    async def rr_stats_handler(self, interaction: discord.Interaction):
        """Show comprehensive Royal Road database statistics"""
        self.command_counter += 1
        
        logger.info(f"\n[RR-STATS] Command called by {interaction.user}")
        
        await interaction.response.defer()
        
        try:
            # Make API request to get database statistics
            data = {
                'bot_token': self.wp_bot_token
            }
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/database-stats"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            async with self.session.post(url, json=data, headers=headers) as response:
                response_text = await response.text()
                logger.info(f"[RR-STATS] API Status: {response.status}")
                logger.info(f"[RR-STATS] API Response: {response_text[:300]}...")
                
                if response.status == 200:
                    result = json.loads(response_text)
                    
                    if result['success']:
                        embed = self.create_stats_embed(result['stats'])
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send(
                            "❌ Failed to retrieve database statistics.",
                            ephemeral=True
                        )
                        
                    logger.info(f"[RR-STATS] Response sent successfully")
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
                logger.info(f"[ERROR] Failed to send error message to user")
    
    # Helper methods
    def calculate_relative_rarity(self, book_count: int, total_books: int) -> Dict[str, Any]:
        """Calculate rarity based on percentage of total books"""
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
        elif percentage <= 0.15:
            return {
                'rarity': '🌟 Mythic',
                'tier': 'mythic',
                'flavor': 'One of the rarest confluences in all the realms'
            }
        elif percentage <= 0.3:
            return {
                'rarity': '⭐ Legendary', 
                'tier': 'legendary',
                'flavor': 'A confluence of legend! Few have walked this path'
            }
        elif percentage <= 0.5:
            return {
                'rarity': '💜 Epic',
                'tier': 'epic', 
                'flavor': 'An epic combination explored by a true essence weaver'
            }
        elif percentage <= 1.0:
            return {
                'rarity': '💙 Rare',
                'tier': 'rare',
                'flavor': 'A rare find! This confluence holds secrets to explore'
            }
        elif percentage <= 5.0:
            return {
                'rarity': '💚 Uncommon',
                'tier': 'uncommon',
                'flavor': 'An uncommon path showing promise for discerning readers'
            }
        else:
            return {
                'rarity': '⚪ Common',
                'tier': 'common',
                'flavor': 'A well-established confluence, beloved by many'
            }
    
    def create_result_embed(self, result: Dict[str, Any], tag1: str, tag2: str, interaction: discord.Interaction) -> discord.Embed:
        """Create result embed for essence combination"""
        self.command_counter += 1
        
        # Get data from result
        book_count = result.get('book_count', 0)
        total_books = int(result.get('total_books', 0)) if result.get('total_books') else 0
        percentage = float(result.get('percentage', 0)) if result.get('percentage') else 0
        
        # Calculate rarity using relative system
        if total_books > 0:
            relative_rarity = self.calculate_relative_rarity(book_count, total_books)
            rarity_tier = relative_rarity['tier']
            rarity_display = relative_rarity['rarity']
            flavor_text = relative_rarity['flavor']
        else:
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
        
        embed.add_field(name="Essences Combined", value=essences_text, inline=True)
        embed.add_field(name="Creates", value=f"{result['combination_name']}", inline=True)
        embed.add_field(name="Rarity", value=rarity_display, inline=True)
        
        # Row 2: Three inline fields
        book_count_display = f"📚 **{book_count:,}**" if book_count is not None else "📚 **0**"
        embed.add_field(name="Books Found", value=book_count_display, inline=True)
        
        # Database Statistics
        if total_books and total_books > 0:
            stats_display = f"📊 {percentage}% of {total_books:,} Royal Road books\nanalyzed in Stepan Chizhov's database"
        else:
            stats_display = "📊 Database is being updated"
        embed.add_field(name="Database Statistics", value=stats_display, inline=True)
        
        # Lore
        embed.add_field(name="✦ Lore ✦", value=f"{flavor_text}", inline=True)
        
        # Row 3: Three inline fields
        # Most Popular Example
        if 'popular_book' in result and result['popular_book']:
            book = result['popular_book']
            book_value = f"**[{book['title']}]({book['url']})**\n"
            book_value += f"*by {book['author']}*\n"
            book_value += f"👥 {book['followers']:,} followers • ⭐ {book['rating']:.2f}/5.00 • 📄 {book['pages']:,} pages"
            embed.add_field(name="👑 Most Popular Example", value=book_value, inline=True)
        else:
            embed.add_field(name="👑 Most Popular Example", value="*No data available*", inline=True)
        
        # Random Discovery
        if 'random_book' in result and result['random_book']:
            book = result['random_book']
            book_value = f"**[{book['title']}]({book['url']})**\n"
            book_value += f"*by {book['author']}*\n"
            book_value += f"👥 {book['followers']:,} followers • ⭐ {book['rating']:.2f}/5.00 • 📄 {book['pages']:,} pages"
            embed.add_field(name="🎲 Random Discovery", value=book_value, inline=True)
        else:
            embed.add_field(name="🎲 Random Discovery", value="*No books with 20k+ words found*", inline=True)
        
        # Rising Stars Link
        rising_stars_url = self.build_rising_stars_url(tag1, tag2)
        if rising_stars_url:
            embed.add_field(
                name="⭐ Rising Stars",
                value=f"[**View on Rising Stars List**]({rising_stars_url})\nSee which books with these tags are trending upward!",
                inline=True
            )
        else:
            embed.add_field(name="⭐ Rising Stars", value="*Rising Stars link unavailable*", inline=True)
        
        # Inspiration message
        if ('popular_book' in result and result['popular_book']) or ('random_book' in result and result['random_book']):
            embed.add_field(
                name="💡 Get Inspired",
                value="Explore these examples to see how authors blend these essences!",
                inline=False
            )
        
        embed = self.add_promotional_field(embed)
        
        return embed
    
    def build_rising_stars_url(self, *tags) -> Optional[str]:
        """Build Rising Stars URL for any number of tags"""
        url_tags = []
        for tag in tags:
            url_tag = self.convert_display_to_url_format(tag)
            if url_tag:
                url_tags.append(url_tag)
        
        if url_tags and len(url_tags) == len(tags):
            tags_param = "%2C".join(url_tags)
            return f"https://stepan.chizhov.com/author-tools/all-rising-stars/?tags={tags_param}"
        
        return None
    
    def convert_display_to_url_format(self, display_name: str) -> Optional[str]:
        """Convert a display name back to URL format for Rising Stars links"""
        # Create reverse mapping
        reverse_mapping = {}
        for url_format, display_format in self.TAG_MAPPING.items():
            if display_format not in reverse_mapping:
                reverse_mapping[display_format] = url_format.lower()
        
        # Handle special cases
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
        
        if display_name in special_cases:
            return special_cases[display_name].lower()
        
        if display_name in reverse_mapping:
            return reverse_mapping[display_name]
        
        # If not found, try to convert display name to URL format
        url_format = display_name.lower().replace(' ', '_').replace('-', '_')
        return url_format
    
    def create_brag_embed(self, result: Dict[str, Any], user: discord.User) -> discord.Embed:
        """Create brag embed showing user's discoveries"""
        discoveries = result['discoveries']
        stats = result['stats']
        
        embed = discord.Embed(
            title="🏆 ESSENCE PIONEER ACHIEVEMENTS 🏆",
            description=f"**{user.display_name}** has discovered **{stats['total_discoveries']}** unique essence combinations out of total of **{stats['total_possible_combinations']}** tracked combinations!",
            color=0xFFD700
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
        
        # Show up to 5 rarest discoveries
        if discoveries:
            discovery_list = []
            has_zero_percentages = False
            
            for i, discovery in enumerate(discoveries[:5]):
                # Parse tags
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
                        tags = discovery['tags_key'].split(',') if isinstance(discovery['tags_key'], str) else []
                
                tags_display = " + ".join(tags)
                
                # Format date
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(discovery['created_at'], '%Y-%m-%d %H:%M:%S')
                    date_display = date_obj.strftime('%b %d, %Y')
                except:
                    date_display = discovery['created_at'][:10]
                
                # Use rarity_tier percentage
                rarity_tier_raw = discovery.get('rarity_tier', 0)
                if rarity_tier_raw is None or rarity_tier_raw == '':
                    rarity_percentage = 0.0
                    has_zero_percentages = True
                else:
                    rarity_percentage = float(rarity_tier_raw)
                    if rarity_percentage == 0.0:
                        has_zero_percentages = True
                
                # Add rarity emoji
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
            
            field_value = "\n".join(discovery_list)
            
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
        
        # Add achievement badges
        achievement_text = self.get_achievement_badges(stats['total_discoveries'])
        if achievement_text:
            embed.add_field(
                name="🎖️ Achievement Badges",
                value=achievement_text,
                inline=False
            )
        
        # Add promotional message
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━",
            value="🌟 **Share your discoveries!** Screenshot this and show off your pioneer status!\n[**Join our Discord Community**](https://discord.gg/xvw9vbvrwj)",
            inline=False
        )
        
        embed.set_footer(text="Keep exploring to discover more rare combinations! • Created by Stepan Chizhov")
        
        return embed
    
    def get_achievement_badges(self, discovery_count: int) -> Optional[str]:
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
    
    def create_stats_embed(self, stats: Dict[str, Any]) -> discord.Embed:
        """Create embed showing Royal Road database statistics"""
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
            name="✏️ Authors",
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
                    'stub': '🔒'
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
            facts.append(f"✏️ **Most Prolific:** {author['name']} ({int(author['book_count'] or 0)} books)")
        
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
        
        # Add promotional message
        embed = self.add_promotional_field(embed, force_show=True)
        
        embed.set_footer(text="Data collected by Stepan Chizhov's Royal Road Analytics • Updated continuously")
        
        return embed
