import discord
from discord.ext import commands
import aiohttp
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

# Set up logging
logger = logging.getLogger('discord')

class OthersAlsoLikedModule:
    def __init__(self, bot, session, wp_api_url, wp_bot_token, add_promotional_field_func=None):
        self.bot = bot
        self.session = session
        self.wp_api_url = wp_api_url
        self.wp_bot_token = wp_bot_token
        self.command_counter = 0
        
        # Store the promotional field function
        self.add_promotional_field = add_promotional_field_func or (lambda e, f=False: e)
        
        # Register commands
        self.register_commands()
    
    def register_commands(self):
        """Register Others Also Liked commands with the bot"""
        
        @self.bot.tree.command(
            name="rr-others-also-liked", 
            description="Show books that have this book in their 'Others Also Liked' section"
        )
        @discord.app_commands.describe(
            book_input="Book ID or Royal Road URL"
        )
        async def rr_others_also_liked(interaction: discord.Interaction, book_input: str):
            await self.others_also_liked_handler(interaction, book_input)
        
        @self.bot.tree.command(
            name="rr-others-also-liked-list", 
            description="Show a list of all books that reference this book in 'Others Also Liked'"
        )
        @discord.app_commands.describe(
            book_input="Book ID or Royal Road URL"
        )
        async def rr_others_also_liked_list(interaction: discord.Interaction, book_input: str):
            await self.others_also_liked_list_handler(interaction, book_input)
    
    async def others_also_liked_handler(self, interaction: discord.Interaction, book_input: str):
        """Show books that reference the given book in their 'Others Also Liked' section - detailed view"""
        self.command_counter += 1
        
        logger.info(f"\n[RR-OTHERS-ALSO-LIKED] Command called by {interaction.user}")
        logger.info(f"[RR-OTHERS-ALSO-LIKED] Book input: '{book_input}'")
        
        await interaction.response.defer()
        
        try:
            # Make API request to get others also liked data
            data = {
                'book_input': book_input.strip(),
                'bot_token': self.wp_bot_token,
                'discord_username': f"{interaction.user.name}#{interaction.user.discriminator}"
            }
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/others-also-liked"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            logger.info(f"[RR-OTHERS-ALSO-LIKED] Making API request to: {url}")
            
            # Set a longer timeout for this API call
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with self.session.post(url, json=data, headers=headers, timeout=timeout) as response:
                response_text = await response.text()
                logger.info(f"[RR-OTHERS-ALSO-LIKED] API Status: {response.status}")
                
                if response.status == 200:
                    result = json.loads(response_text)
                    
                    if result.get('success'):
                        embed = self.create_others_also_liked_embed(result, interaction.user)
                        await interaction.followup.send(embed=embed)
                        logger.info(f"[RR-OTHERS-ALSO-LIKED] Successfully sent embed")
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
                await interaction.followup.send(
                    "⏰ Request timed out. The server might be busy. Please try again.",
                    ephemeral=True
                )
            except:
                logger.info(f"[ERROR] Could not send timeout message")
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
                logger.info(f"[ERROR] Failed to send error message to user")
    
    async def others_also_liked_list_handler(self, interaction: discord.Interaction, book_input: str):
        """Show a comprehensive list of all books that reference this book - list view"""
        self.command_counter += 1
        
        logger.info(f"\n[RR-OTHERS-ALSO-LIKED-LIST] Command called by {interaction.user}")
        logger.info(f"[RR-OTHERS-ALSO-LIKED-LIST] Book input: '{book_input}'")
        
        await interaction.response.defer()
        
        try:
            # Make API request to get others also liked data
            data = {
                'book_input': book_input.strip(),
                'bot_token': self.wp_bot_token,
                'discord_username': f"{interaction.user.name}#{interaction.user.discriminator}"
            }
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/others-also-liked"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            logger.info(f"[RR-OTHERS-ALSO-LIKED-LIST] Making API request to: {url}")
            
            # Set a longer timeout for this API call
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with self.session.post(url, json=data, headers=headers, timeout=timeout) as response:
                response_text = await response.text()
                logger.info(f"[RR-OTHERS-ALSO-LIKED-LIST] API Status: {response.status}")
                
                if response.status == 200:
                    result = json.loads(response_text)
                    
                    if result.get('success'):
                        embed = self.create_others_also_liked_list_embed(result, interaction.user)
                        await interaction.followup.send(embed=embed)
                        logger.info(f"[RR-OTHERS-ALSO-LIKED-LIST] Successfully sent embed")
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
                await interaction.followup.send(
                    "⏰ Request timed out. The server might be busy. Please try again.",
                    ephemeral=True
                )
            except:
                logger.info(f"[ERROR] Could not send timeout message")
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
                logger.info(f"[ERROR] Failed to send error message to user")
    
    def create_others_also_liked_embed(self, result: Dict[str, Any], user: discord.User) -> discord.Embed:
        """Create embed showing books that reference the given book in 'Others Also Liked' - detailed view"""
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
                        # Parse the timestamp
                        timestamp_dt = datetime.strptime(book['timestamp'], '%Y-%m-%d %H:%M:%S')
                        # Format as date only
                        formatted_date = timestamp_dt.strftime('%b %d, %Y')
                        book_value += f"\nLast seen: {formatted_date}"
                    except (ValueError, TypeError) as e:
                        # If timestamp parsing fails, show raw timestamp
                        book_value += f"\nLast seen: {book['timestamp'][:10]}"
                
                # Add position indicator
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
        
        # Add tier explanation for free users
        if user_tier not in ['administrator', 'editor', 'patreon_premium', 'patreon_supporter', 'premium', 'pro', 'pro_free'] and total_books > 1:
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
        embed = self.add_promotional_field(embed)
        
        embed.set_footer(text="Data from Stepan Chizhov's Royal Road Analytics")
        
        return embed
    
    def create_others_also_liked_list_embed(self, result: Dict[str, Any], user: discord.User) -> discord.Embed:
        """Create embed showing a simple list of books that reference the given book - list view"""
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
                
                # Discord has a limit of 25 fields per embed
                if len(embed.fields) >= 23:  # Leave room for other fields
                    remaining_books = len(books) - ((i + 1) * (max_field_length // 50))  # Approximate
                    if remaining_books > 0:
                        embed.add_field(
                            name="...",
                            value=f"*{remaining_books} more books not shown due to Discord limits*",
                            inline=False
                        )
                    break
            
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
        embed = self.add_promotional_field(embed)
        
        embed.set_footer(text="Data from Stepan Chizhov's Royal Road Analytics • Use /rr-others-also-liked for detailed view")
        
        return embed
