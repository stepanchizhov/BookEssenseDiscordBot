import discord
from discord.ext import commands
import aiohttp
import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger('discord')

class PopularThisWeekModule:
    def __init__(self, bot, session, wp_api_url, wp_bot_token, add_promotional_field_func=None):
        self.bot = bot
        self.session = session
        self.wp_api_url = wp_api_url
        self.wp_bot_token = wp_bot_token
        self.command_counter = 0
        
        # Store the promotional field function
        self.add_promotional_field = add_promotional_field_func or (lambda e, f=False: e)
        
        # Import tag data from shared_utils if available
        try:
            from shared_utils import ALL_RS_TAGS
            self.ALL_PTW_TAGS = ALL_RS_TAGS  # PTW uses same tags as RS
        except ImportError:
            # Fallback if shared_utils not available
            self.ALL_PTW_TAGS = [
                'main', 'action', 'adventure', 'comedy', 'drama', 'fantasy',
                'horror', 'mystery', 'psychological', 'romance', 'sci_fi', 'tragedy'
            ]
        
        # Register commands
        self.register_commands()
    
    def register_commands(self):
        """Register Popular This Week commands with the bot"""
        
        @self.bot.tree.command(
            name="rr-ptw",
            description="Show Popular This Week list with view counts from last 7 days"
        )
        @discord.app_commands.describe(
            count="Number of books to show (1-20, default: 20)",
            book_input="Book ID or URL to show context (books above/below)",
            tag="PTW tag to display (default: 'main')"
        )
        async def rr_ptw(
            interaction: discord.Interaction,
            count: int = 20,
            book_input: str = None,
            tag: str = "main"
        ):
            await self.ptw_list_handler(interaction, count, book_input, tag)
        
        @self.bot.tree.command(
            name="rr-ptw-check",
            description="Check when a book appeared on Popular This Week"
        )
        @discord.app_commands.describe(
            book_input="Book ID or Royal Road URL",
            tags="Comma-separated PTW tags (e.g., 'main,fantasy,litrpg' or 'all'). Default: 'main'"
        )
        async def rr_ptw_check(
            interaction: discord.Interaction,
            book_input: str,
            tags: str = "main"
        ):
            await self.ptw_check_handler(interaction, book_input, tags)
    
    async def ptw_list_handler(
        self,
        interaction: discord.Interaction,
        count: int,
        book_input: Optional[str],
        tag: str
    ):
        """Handle the PTW list display command"""
        self.command_counter += 1
        
        logger.info(f"\n[RR-PTW] Command called by {interaction.user}")
        logger.info(f"[RR-PTW] Count: {count}, Book input: '{book_input}', Tag: '{tag}'")
        
        await interaction.response.defer()
        
        try:
            # Validate count
            if count < 1 or count > 20:
                await interaction.followup.send(
                    "❌ Count must be between 1 and 20.",
                    ephemeral=True
                )
                return
            
            # Normalize tag
            tag = tag.lower().replace(' ', '_').replace('-', '_')
            if tag not in self.ALL_PTW_TAGS:
                await interaction.followup.send(
                    f"❌ Unknown tag: '{tag}'. Use 'main' or other valid tags.",
                    ephemeral=True
                )
                return
            
            # Parse book input if provided
            context_book_id = None
            if book_input:
                context_book_id = self.extract_book_id(book_input)
                if not context_book_id:
                    await interaction.followup.send(
                        "❌ Invalid book input. Please provide a book ID or Royal Road URL.",
                        ephemeral=True
                    )
                    return
            
            # Prepare API request
            request_data = {
                'action': 'get_ptw_list',
                'tag': tag,
                'count': count,
                'context_book_id': context_book_id,
                'bot_token': self.wp_bot_token
            }
            
            headers = {
                'User-Agent': 'RR-Discord-Bot/1.0',
                'Content-Type': 'application/json'
            }
            
            # Make API request
            async with self.session.post(
                f"{self.wp_api_url}/wp-json/rr-analytics/v1/popular-this-week",
                json=request_data,
                headers=headers,
                timeout=30
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"[RR-PTW] API error: {response.status} - {error_text}")
                    await interaction.followup.send(
                        f"❌ API error: {response.status}",
                        ephemeral=True
                    )
                    return
                
                data = await response.json()
            
            if not data.get('success'):
                error_msg = data.get('message', 'Failed to fetch PTW data')
                await interaction.followup.send(f"❌ {error_msg}", ephemeral=True)
                return
            
            # Create embed
            embed = self.create_ptw_list_embed(data, count, context_book_id, tag)
            
            # Add promotional field
            embed = self.add_promotional_field(embed)
            
            await interaction.followup.send(embed=embed)
            logger.info(f"[RR-PTW] Successfully sent PTW list")
            
        except Exception as e:
            logger.error(f"[RR-PTW] Error: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                await interaction.followup.send(
                    "❌ An error occurred while fetching Popular This Week data.",
                    ephemeral=True
                )
            except:
                pass
    
    async def ptw_check_handler(
        self,
        interaction: discord.Interaction,
        book_input: str,
        tags: str
    ):
        """Handle checking when a book appeared on PTW"""
        self.command_counter += 1
        
        logger.info(f"\n[RR-PTW-CHECK] Command called by {interaction.user}")
        logger.info(f"[RR-PTW-CHECK] Book input: '{book_input}', Tags: '{tags}'")
        
        await interaction.response.defer()
        
        try:
            # Parse book input
            book_id = self.extract_book_id(book_input)
            if not book_id:
                await interaction.followup.send(
                    "❌ Invalid book input. Please provide a book ID or Royal Road URL.",
                    ephemeral=True
                )
                return
            
            # Parse tags
            requested_tags = self.parse_ptw_tags(tags)
            
            # Prepare API request
            request_data = {
                'action': 'check_book_ptw',
                'book_id': book_id,
                'tags': requested_tags,
                'bot_token': self.wp_bot_token
            }
            
            headers = {
                'User-Agent': 'RR-Discord-Bot/1.0',
                'Content-Type': 'application/json'
            }
            
            # Make API request
            async with self.session.post(
                f"{self.wp_api_url}/wp-json/rr-analytics/v1/popular-this-week",
                json=request_data,
                headers=headers,
                timeout=30
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"[RR-PTW-CHECK] API error: {response.status} - {error_text}")
                    await interaction.followup.send(
                        f"❌ API error: {response.status}",
                        ephemeral=True
                    )
                    return
                
                data = await response.json()
            
            if not data.get('success'):
                error_msg = data.get('message', 'Failed to check PTW appearances')
                await interaction.followup.send(f"❌ {error_msg}", ephemeral=True)
                return
            
            # Create embed
            embed = self.create_ptw_check_embed(data, book_id, requested_tags)
            
            # Add promotional field
            embed = self.add_promotional_field(embed)
            
            await interaction.followup.send(embed=embed)
            logger.info(f"[RR-PTW-CHECK] Successfully sent PTW check data")
            
        except Exception as e:
            logger.error(f"[RR-PTW-CHECK] Error: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                await interaction.followup.send(
                    "❌ An error occurred while checking Popular This Week data.",
                    ephemeral=True
                )
            except:
                pass
    
    def create_ptw_list_embed(
            self,
            data: Dict[str, Any],
            count: int,
            context_book_id: Optional[str],
            tag: str
        ) -> discord.Embed:
            """Create embed for PTW list display"""
            books = data.get('books', [])
            context_info = data.get('context_info', {})
            timestamp = data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            # Format tag display
            tag_display = self.format_tag_display(tag)
            
            # Create embed
            embed = discord.Embed(
                title=f"🔥 Popular This Week - {tag_display}",
                description=f"Top {min(count, len(books))} books by views in the last 7 days",
                color=0xFF6B35  # Orange color for popularity
            )
            
            # Add timestamp info
            try:
                timestamp_dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                formatted_time = timestamp_dt.strftime('%b %d, %Y at %I:%M %p UTC')
                embed.add_field(
                    name="📅 Last Updated",
                    value=formatted_time,
                    inline=False
                )
            except:
                pass
            
            # If context book was requested, add its detailed comparison info
            if context_book_id and context_info:
                context_lines = []
                
                if context_info.get('title'):
                    book_url = f"https://www.royalroad.com/fiction/{context_book_id}"
                    context_lines.append(f"**Book:** [{context_info['title']}]({book_url})")
                
                if context_info.get('position'):
                    context_lines.append(f"**Current Position:** #{context_info['position']}")
                else:
                    context_lines.append("**Current Position:** Not on this PTW list")
                
                if context_info.get('weekly_views'):
                    context_lines.append(f"**Weekly Views:** {context_info['weekly_views']:,}")
                
                # Add comparison with books above and below
                if context_info.get('book_above'):
                    above = context_info['book_above']
                    diff = above['view_difference']
                    if diff > 0:
                        context_lines.append(f"\n📈 **To reach #{above['position']}:** Need +{abs(diff):,} more views")
                        context_lines.append(f"   _{above['title']}: {above['weekly_views']:,} views_")
                    else:
                        context_lines.append(f"\n📈 **Gap to #{above['position']}:** Already ahead by {abs(diff):,} views!")
                        context_lines.append(f"   _{above['title']}: {above['weekly_views']:,} views_")
                
                if context_info.get('book_below'):
                    below = context_info['book_below']
                    diff = below['view_difference']
                    if diff > 0:
                        context_lines.append(f"\n📉 **Lead over #{below['position']}:** +{diff:,} views ahead")
                        context_lines.append(f"   _{below['title']}: {below['weekly_views']:,} views_")
                    else:
                        context_lines.append(f"\n📉 **Behind #{below['position']}:** -{abs(diff):,} views behind")
                        context_lines.append(f"   _{below['title']}: {below['weekly_views']:,} views_")
                
                embed.add_field(
                    name="📖 Your Book Analysis",
                    value="\n".join(context_lines),
                    inline=False
                )
            
            # Add books list
            if books:
                # Split into multiple fields if necessary (Discord limit is 1024 chars per field)
                book_entries = []
                for i, book in enumerate(books[:count], 1):
                    # Format position with medals for top 3
                    if i == 1:
                        position = "🥇"
                    elif i == 2:
                        position = "🥈"
                    elif i == 3:
                        position = "🥉"
                    else:
                        position = f"**#{i}**"
                    
                    # Create book entry with link and ID
                    book_id = book.get('book_id', 'Unknown')
                    book_title = book.get('title', 'Unknown Title')
                    book_url = f"https://www.royalroad.com/fiction/{book_id}"
                    weekly_views = book.get('weekly_views', 0)
                    
                    # Highlight context book if it's in the list
                    if context_book_id and str(book_id) == str(context_book_id):
                        entry = f"{position} **→** [{book_title}]({book_url})\n   **{weekly_views:,} views** ← Your book"
                    else:
                        entry = f"{position} [{book_title}]({book_url})\n   **{weekly_views:,} views**"
                    
                    book_entries.append(entry)
                
                # Add books in batches to respect Discord's field limits
                current_batch = []
                current_length = 0
                field_count = 1
                
                for entry in book_entries:
                    if current_length + len(entry) + 2 > 1024:  # +2 for newlines
                        # Send current batch
                        field_name = "📚 Books" if field_count == 1 else f"📚 Books (continued)"
                        embed.add_field(
                            name=field_name,
                            value="\n\n".join(current_batch),
                            inline=False
                        )
                        current_batch = [entry]
                        current_length = len(entry)
                        field_count += 1
                    else:
                        current_batch.append(entry)
                        current_length += len(entry) + 2
                
                # Add remaining batch
                if current_batch:
                    field_name = "📚 Books" if field_count == 1 else f"📚 Books (continued)"
                    embed.add_field(
                        name=field_name,
                        value="\n\n".join(current_batch),
                        inline=False
                    )
            else:
                embed.add_field(
                    name="📚 No Data",
                    value="No books found for this PTW list.",
                    inline=False
                )
            
            # Add note about the list
            embed.add_field(
                name="ℹ️ About Popular This Week",
                value=(
                    "• Updates multiple times daily\n"
                    "• Based on total views in the last 7 days\n"
                    "• Maximum 20 books per tag list\n"
                    "• Use `/rr-ptw-check [book]` to see appearance history"
                ),
                inline=False
            )
            
            embed.set_footer(text="Data from Stepan Chizhov's Royal Road Analytics • Popular This Week tracker")
            
            return embed
    
    def create_ptw_check_embed(
        self,
        data: Dict[str, Any],
        book_id: str,
        requested_tags: List[str]
    ) -> discord.Embed:
        """Create embed for PTW check results"""
        book_info = data.get('book_info', {})
        ptw_appearances = data.get('ptw_appearances', {})
        
        book_title = book_info.get('title', f'Book {book_id}')
        book_url = f"https://www.royalroad.com/fiction/{book_id}"
        author = book_info.get('author', 'Unknown Author')
        
        # Create embed
        embed = discord.Embed(
            title="📊 Popular This Week History",
            description=f"**[{book_title}]({book_url})**\nby {author}\n\nBook ID: {book_id}",
            color=0xFF6B35
        )
        
        # Track tags with appearances
        tags_with_data = []
        
        # Process each requested tag
        for tag in requested_tags:
            tag_data = ptw_appearances.get(tag, {})
            
            if tag_data and (tag_data.get('appearances', 0) > 0 or tag_data.get('current_position')):
                tags_with_data.append(tag)
                
                field_lines = []
                
                # Current position
                if tag_data.get('current_position'):
                    field_lines.append(f"**Current:** #{tag_data['current_position']}")
                    if tag_data.get('current_views'):
                        field_lines.append(f"**Weekly Views:** {tag_data['current_views']:,}")
                else:
                    field_lines.append("**Current:** Not on list")
                
                # Best position
                if tag_data.get('best_position'):
                    field_lines.append(f"**Best:** #{tag_data['best_position']}")
                    if tag_data.get('best_position_date'):
                        field_lines.append(f"**Best Date:** {tag_data['best_position_date']}")
                
                # First and last seen
                if tag_data.get('first_seen'):
                    field_lines.append(f"**First Seen:** {tag_data['first_seen']}")
                if tag_data.get('last_seen'):
                    field_lines.append(f"**Last Seen:** {tag_data['last_seen']}")
                
                # Total appearances
                if tag_data.get('appearances'):
                    field_lines.append(f"**Total Appearances:** {tag_data['appearances']}")
                
                # Days on list
                if tag_data.get('days_on_list'):
                    field_lines.append(f"**Days on List:** {tag_data['days_on_list']}")
                
                # Recent trend
                if tag_data.get('trend'):
                    trend = tag_data['trend']
                    if trend == 'rising':
                        field_lines.append("📈 **Trend:** Rising")
                    elif trend == 'falling':
                        field_lines.append("📉 **Trend:** Falling")
                    elif trend == 'stable':
                        field_lines.append("➡️ **Trend:** Stable")
                    elif trend == 'new':
                        field_lines.append("🆕 **Trend:** New Entry")
                
                # Format tag display
                tag_display = self.format_tag_display(tag)
                
                embed.add_field(
                    name=f"🔥 {tag_display}",
                    value="\n".join(field_lines),
                    inline=True
                )
                
                # Discord limit check
                if len(embed.fields) >= 24:
                    break
        
        # No appearances found
        if not tags_with_data:
            embed.add_field(
                name="📊 No PTW Appearances",
                value="This book has not appeared on any of the requested Popular This Week lists.",
                inline=False
            )
        else:
            # Add summary
            total_appearances = sum(
                ptw_appearances.get(tag, {}).get('appearances', 0)
                for tag in requested_tags
            )
            
            summary_lines = [
                f"**Total Appearances:** {total_appearances}",
                f"**Lists Appeared On:** {len(tags_with_data)}"
            ]
            
            # Find overall best position
            best_positions = []
            for tag in requested_tags:
                if ptw_appearances.get(tag, {}).get('best_position'):
                    best_positions.append(
                        (tag, ptw_appearances[tag]['best_position'])
                    )
            
            if best_positions:
                best_tag, best_pos = min(best_positions, key=lambda x: x[1])
                tag_display = self.format_tag_display(best_tag)
                summary_lines.append(f"**Overall Best:** #{best_pos} ({tag_display})")
            
            # Currently on how many lists
            current_count = sum(
                1 for tag in requested_tags
                if ptw_appearances.get(tag, {}).get('current_position')
            )
            if current_count > 0:
                summary_lines.append(f"**Currently On:** {current_count} list(s)")
            
            embed.add_field(
                name="📈 Summary",
                value="\n".join(summary_lines),
                inline=False
            )
        
        # Add query info
        if len(requested_tags) == 1 and requested_tags[0] == 'main':
            query_note = "Showing: Main PTW list only\n*Add `tags:'all'` to see all lists*"
        elif 'all' in requested_tags or len(requested_tags) == len(self.ALL_PTW_TAGS):
            query_note = "Showing: All PTW lists"
        else:
            shown_tags = ', '.join(requested_tags[:5])
            if len(requested_tags) > 5:
                shown_tags += f" (+{len(requested_tags) - 5} more)"
            query_note = f"Showing: {shown_tags}"
        
        embed.add_field(
            name="🔍 Query Info",
            value=query_note,
            inline=False
        )
        
        embed.set_footer(
            text="Data from Stepan Chizhov's Royal Road Analytics\n"
                 "Use: /rr-ptw-check [book] tags:'all' or tags:'fantasy,litrpg'"
        )
        
        return embed
    
    def extract_book_id(self, book_input: str) -> Optional[str]:
        """Extract book ID from input string"""
        if not book_input:
            return None
            
        # Check if it's already a number
        if book_input.isdigit():
            return book_input
        
        # Try to extract from URL
        match = re.search(r'/fiction/(\d+)', book_input)
        if match:
            return match.group(1)
        
        return None
    
    def parse_ptw_tags(self, tags_input: str) -> List[str]:
        """Parse tags parameter for PTW check"""
        if not tags_input or tags_input.lower() == 'main':
            return ['main']
        
        if tags_input.lower() == 'all':
            return self.ALL_PTW_TAGS
        
        # Split by comma and clean
        input_tags = [
            tag.strip().lower().replace(' ', '_').replace('-', '_')
            for tag in tags_input.split(',')
        ]
        
        # Validate against known tags
        valid_tags = []
        for tag in input_tags:
            # Handle special cases
            tag_normalized = tag.replace('sci-fi', 'sci_fi').replace('scifi', 'sci_fi')
            
            if tag_normalized in self.ALL_PTW_TAGS:
                valid_tags.append(tag_normalized)
        
        return valid_tags if valid_tags else ['main']
    
    def format_tag_display(self, tag: str) -> str:
        """Format tag for display"""
        special_names = {
            'main': '📍 Main',
            'sci_fi': 'Sci-Fi',
            'litrpg': 'LitRPG',
            'gamelit': 'GameLit',
            'anti_hero_lead': 'Anti-Hero Lead',
            'non_human_lead': 'Non-Human Lead'
        }
        
        if tag in special_names:
            return special_names[tag]
        
        return tag.replace('_', ' ').title()
