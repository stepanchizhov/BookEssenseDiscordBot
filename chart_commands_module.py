import discord
from discord.ext import commands
import aiohttp
import json
import logging
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import io

# Set up logging
logger = logging.getLogger('discord')

class ChartCommandsModule:
    def __init__(self, bot, session, wp_api_url, wp_bot_token, get_promotional_field_func=None, add_promotional_field_func=None):
        self.bot = bot
        self.session = session
        self.wp_api_url = wp_api_url
        self.wp_bot_token = wp_bot_token
        self.command_counter = 0
        
        # Store the promotional field functions
        self.get_promotional_field = get_promotional_field_func or (lambda f=False: None)
        self.add_promotional_field = add_promotional_field_func or (lambda e, f=False: e)
        
        # Register commands
        self.register_commands()
    
    def register_commands(self):
        """Register all chart commands with the bot"""
        
        @self.bot.tree.command(name="rr-followers", description="Show followers over time chart for a Royal Road book")
        @discord.app_commands.describe(
            book_input="Book ID or Royal Road URL",
            days="Days to show: number (30), 'all', date (2024-01-01), or range (2024-01-01:2024-02-01). Default: 'all'",
            rs_prediction="Show Rising Stars prediction analysis (optional, default: False)"
        )
        async def rr_followers(interaction: discord.Interaction, book_input: str, days: str = "all", rs_prediction: bool = False):
            await self.rr_followers_handler(interaction, book_input, days, rs_prediction)
        
        @self.bot.tree.command(name="rr-views", description="Show views over time chart for a Royal Road book")
        @discord.app_commands.describe(
            book_input="Book ID or Royal Road URL",
            days="Days to show: number (30), 'all', date (2024-01-01), or range (2024-01-01:2024-02-01). Default: 'all'"
        )
        async def rr_views(interaction: discord.Interaction, book_input: str, days: str = "all"):
            await self.rr_views_handler(interaction, book_input, days)
        
        @self.bot.tree.command(name="rr-average-views", description="Show average views and chapters over time chart for a Royal Road book")
        @discord.app_commands.describe(
            book_input="Book ID or Royal Road URL",
            days="Days to show: number (30), 'all', date (2024-01-01), or range (2024-01-01:2024-02-01). Default: 'all'"
        )
        async def rr_average_views(interaction: discord.Interaction, book_input: str, days: str = "all"):
            await self.rr_average_views_handler(interaction, book_input, days)
        
        @self.bot.tree.command(name="rr-ratings", description="Show rating metrics over time chart for a Royal Road book")
        @discord.app_commands.describe(
            book_input="Book ID or Royal Road URL",
            days="Days to show: number (30), 'all', date (2024-01-01), or range (2024-01-01:2024-02-01). Default: 'all'"
        )
        async def rr_ratings(interaction: discord.Interaction, book_input: str, days: str = "all"):
            await self.rr_ratings_handler(interaction, book_input, days)
    
    # Command handlers
    async def rr_followers_handler(self, interaction: discord.Interaction, book_input: str, days: str, rs_prediction: bool):
        """Generate and send a followers over time chart with optional RS prediction"""
        self.command_counter += 1
        
        logger.info(f"\n[RR-FOLLOWERS] Command called by {interaction.user}")
        logger.info(f"[RR-FOLLOWERS] Book input: '{book_input}', Days: '{days}', RS Prediction: {rs_prediction}")
        
        await interaction.response.defer()
        
        try:
            # Parse days parameter
            days_param = self.parse_days_parameter(days)
            logger.info(f"[RR-FOLLOWERS] Parsed days parameter: {days_param}")
            
            # Fetch chart data
            chart_response = await self.get_book_chart_data(book_input.strip(), days_param)
            
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
            
            # Use data exactly as returned from API
            filtered_data = chart_data
            
            # Check for Rising Stars potential
            rs_eligible = False
            rs_data = None
            
            if rs_prediction:
                # Full RS prediction requested
                discord_username = f"{interaction.user.name}#{interaction.user.discriminator}"
                logger.info(f"[RR-FOLLOWERS] Fetching RS prediction for user: {discord_username}")
                rs_data = await self.get_rs_prediction_data(book_input.strip(), discord_username)
                if rs_data:
                    logger.info(f"[RR-FOLLOWERS] RS prediction data received, eligible: {rs_data.get('eligible')}")
            else:
                # Quick eligibility check
                logger.info(f"[RR-FOLLOWERS] Checking RS eligibility for quick hint")
                rs_check = await self.check_rs_eligibility(book_input.strip())
                if rs_check and rs_check.get('eligible'):
                    rs_eligible = True
                    logger.info(f"[RR-FOLLOWERS] Book is RS eligible, will show hint")
            
            # Create chart image
            chart_buffer = self.create_chart_image(filtered_data, 'followers', book_title, days_param)
            
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
            
            # Add RS prediction or hint if applicable
            if rs_prediction and rs_data and rs_data.get('eligible'):
                logger.info(f"[RR-FOLLOWERS] Adding RS prediction to embed")
                embed = self.add_rs_prediction_to_embed(embed, rs_data, interaction.user)
            elif rs_eligible and not rs_prediction:
                logger.info(f"[RR-FOLLOWERS] Adding RS hint to embed")
                embed.add_field(
                    name="🌟 Rising Stars Potential Detected!",
                    value=(
                        "Your book shows potential for Rising Stars!\n"
                        "Run `/rr-followers` with `rs_prediction:True` for detailed analysis.\n"
                    ),
                    inline=False
                )
            
            # Add data note about chart features
            embed.add_field(
                name="📊 Chart Features",
                value=(
                    "• Chart starts from the first meaningful data point\n"
                    "• Points connected to show trends over time\n"
                    "• Want to add your historical data? Visit [Stepan Chizhov's Discord](https://discord.gg/xvw9vbvrwj)"
                ),
                inline=False
            )
            
            # Add promotional field
            embed = self.add_promotional_field(embed)
            
            # Set footer
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
    
    async def rr_views_handler(self, interaction: discord.Interaction, book_input: str, days: str):
        """Generate and send a views over time chart"""
        self.command_counter += 1
        
        logger.info(f"\n[RR-VIEWS] Command called by {interaction.user}")
        logger.info(f"[RR-VIEWS] Book input: '{book_input}', Days: '{days}'")
        
        await interaction.response.defer()
        
        try:
            # Parse days parameter
            days_param = self.parse_days_parameter(days)
            logger.info(f"[RR-VIEWS] Parsed days parameter: {days_param}")
            
            # Fetch chart data
            chart_response = await self.get_book_chart_data(book_input.strip(), days_param)
            
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
            
            # Use data exactly as returned from API
            filtered_data = chart_data
            
            # Create chart image
            chart_buffer = self.create_chart_image(filtered_data, 'views', book_title, days_param)
            
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
            
            embed = self.add_promotional_field(embed)
            
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
    
    async def rr_average_views_handler(self, interaction: discord.Interaction, book_input: str, days: str):
        """Generate and send an average views over time chart with chapters for reference"""
        self.command_counter += 1
        
        logger.info(f"\n[RR-AVERAGE-VIEWS] Command called by {interaction.user}")
        logger.info(f"[RR-AVERAGE-VIEWS] Book input: '{book_input}', Days: '{days}'")
        
        await interaction.response.defer()
        
        try:
            # Parse days parameter
            days_param = self.parse_days_parameter(days)
            logger.info(f"[RR-AVERAGE-VIEWS] Parsed days parameter: {days_param}")
            
            # Fetch chart data
            chart_response = await self.get_book_chart_data(book_input.strip(), days_param)
            
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
            
            # Use data exactly as returned from API
            filtered_data = chart_data
            
            # Create chart image with average views and chapters
            chart_buffer = self.create_average_views_chart_image(filtered_data, book_title, days_param)
            
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
            
            embed = self.add_promotional_field(embed)
            
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
    
    async def rr_ratings_handler(self, interaction: discord.Interaction, book_input: str, days: str):
        """Generate and send a rating metrics over time chart"""
        self.command_counter += 1
        
        logger.info(f"\n[RR-RATINGS] Command called by {interaction.user}")
        logger.info(f"[RR-RATINGS] Book input: '{book_input}', Days: '{days}'")
        
        await interaction.response.defer()
        
        try:
            # Parse days parameter
            days_param = self.parse_days_parameter(days)
            logger.info(f"[RR-RATINGS] Parsed days parameter: {days_param}")
            
            # Fetch chart data
            chart_response = await self.get_book_chart_data(book_input.strip(), days_param)
            
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
            
            # Use data exactly as returned from API
            filtered_data = chart_data
            
            # Create chart image with rating metrics
            chart_buffer = self.create_ratings_chart_image(filtered_data, book_title, days_param)
            
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
                color=0x3498DB  # Blue color for ratings
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
            
            embed = self.add_promotional_field(embed)
            
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
    
    # Helper methods
    async def get_book_chart_data(self, book_input, days_param):
        """Fetch chart data for a book from WordPress API with date filtering"""
        try:
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-chart-data"
            headers = {
                'User-Agent': 'RR-Analytics-Discord-Bot/1.0',
                'Content-Type': 'application/json'
            }
            
            # Base data
            data = {
                'book_input': str(book_input),
                'bot_token': self.wp_bot_token
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
            logger.info(f"[CHART] Request URL: {url}")
            
            async with self.session.post(url, json=data, headers=headers) as response:
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
    
    def parse_days_parameter(self, days_str):
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
    
    def trim_leading_zeros(self, labels, data, timestamps=None):
        """Trim leading zeros from the data to start from first meaningful data point"""
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
    
    def filter_zero_data_points(self, labels, data, timestamps=None):
        """Filter out data points where the value is zero (except the first non-zero value)"""
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
    
    def parse_dates_from_labels(self, labels, timestamps=None):
        """Convert labels to datetime objects for proper date scaling"""
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
    
    def create_chart_image(self, chart_data, chart_type, book_title, days_param):
        """Create a chart image using matplotlib with proper linear date scaling"""
        try:
            # Set up the plot
            plt.style.use('default')
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Prepare data - USE AS-IS from API (already filtered)
            labels = chart_data.get('labels', [])
            timestamps = chart_data.get('timestamps', [])
            
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
                trimmed_labels, trimmed_data, trimmed_timestamps = self.trim_leading_zeros(
                    labels, data, timestamps
                )
                
                # Then, filter out intermediate zero data points
                if trimmed_labels and trimmed_data:
                    filtered_labels, filtered_data, filtered_timestamps = self.filter_zero_data_points(
                        trimmed_labels, trimmed_data, trimmed_timestamps
                    )
                    
                    if filtered_labels and filtered_data:
                        # Parse dates for proper linear scaling
                        date_objects = self.parse_dates_from_labels(filtered_labels, filtered_timestamps)
                        
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
    
    def create_average_views_chart_image(self, chart_data, book_title, days_param):
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
                
                # Start with the first non-zero point
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
                            
                            # If an intermediate average views datapoint is zero, skip it
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
                    
                    # Plot with datetime objects for linear time axis
                    line1 = ax1.plot(date_objects, filtered_avg_views, color=color1, linewidth=2, 
                                   marker='o', markersize=4, label='Average Views', 
                                   markerfacecolor=color1, markeredgewidth=0)
                    
                    # Add fill under the curve for better visibility
                    ax1.fill_between(date_objects, filtered_avg_views, alpha=0.3, color=color1)
                    
                    ax1.tick_params(axis='y', labelcolor=color1)
                    ax1.grid(True, alpha=0.3)
                    
                    logger.info(f"[CHART DEBUG] Plotting chapters data")
                    # Create secondary axis for chapters
                    ax2 = ax1.twinx()
                    ax2.set_ylabel('Total Chapters', color=color2, fontsize=12)
                    
                    # Set chapters y-axis max to 125% of the highest chapter number
                    max_chapters = max(filtered_chapters) if filtered_chapters else 1
                    chapters_axis_max = max_chapters * 1.25
                    ax2.set_ylim(0, chapters_axis_max)
                    
                    line2 = ax2.plot(date_objects, filtered_chapters, color=color2, linewidth=2, 
                                   marker='o', markersize=4, label='Chapters',
                                   markerfacecolor=color2, markeredgewidth=0)
                    
                    # Add fill under total chapters chart
                    ax2.fill_between(date_objects, filtered_chapters, alpha=0.2, color=color2)
                    
                    ax2.tick_params(axis='y', labelcolor=color2)
                    
                    # Format x-axis for dates with exactly 12 date points
                    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
                    from matplotlib.ticker import MaxNLocator
                    ax1.xaxis.set_major_locator(MaxNLocator(nbins=12))
                    
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
    
    def create_ratings_chart_image(self, chart_data, book_title, days_param):
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
                        
                        # Include scores only when we have ratings
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
                # Plot overall score on primary axis (0-5 scale)
                ax1.set_xlabel('Date', fontsize=12)
                ax1.set_ylabel('Overall Rating Score', color=color1_hex, fontsize=12)
                ax1.set_ylim(0, 5)  # Rating scale is 0-5
                line1 = ax1.plot(date_objects, filtered_scores, color=color1_hex, linewidth=2, 
                               marker='o', markersize=4, label='Overall Score', 
                               markerfacecolor=color1_hex, markeredgewidth=0)
                
                # Add fill under the rating score curve for better visibility
                ax1.fill_between(date_objects, filtered_scores, alpha=0.3, color='#36A2EB')
                
                ax1.tick_params(axis='y', labelcolor=color1_hex)
                ax1.grid(True, alpha=0.3)
                
                logger.info(f"[CHART DEBUG] Plotting ratings count data")
                # Create secondary axis for ratings count
                ax2 = ax1.twinx()
                ax2.set_ylabel('Number of Ratings', color=color2_hex, fontsize=12)
                line2 = ax2.plot(date_objects, filtered_ratings, color=color2_hex, linewidth=2, 
                               marker='o', markersize=4, label='Ratings Count',
                               markerfacecolor=color2_hex, markeredgewidth=0)
                
                # Use white fill with yellow edge to create yellow appearance without mixing
                ax2.fill_between(date_objects, filtered_ratings, alpha=0.8, color='white', 
                               edgecolor='#FFCE56', linewidth=1)
                # Add a thin yellow fill on top for better yellow visibility
                ax2.fill_between(date_objects, filtered_ratings, alpha=0.3, color='#FFCE56')
                
                logger.info(f"[CHART DEBUG] Added white+yellow layered fill to avoid color mixing")
                
                ax2.tick_params(axis='y', labelcolor=color2_hex)
                
                # Scale ratings axis so it never goes above 5
                max_ratings = max(filtered_ratings) if filtered_ratings else 1
                # Calculate scale factor to keep ratings visually below scores
                if max_ratings > 100:
                    scale_factor = max_ratings / 4.0
                elif max_ratings > 50:
                    scale_factor = max_ratings / 3.5
                else:
                    scale_factor = max_ratings / 3.0
                
                ax2.set_ylim(0, scale_factor * 5)
                
                # Format ratings count with commas
                ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
                
                # Format x-axis for dates with exactly 12 date points
                ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
                from matplotlib.ticker import MaxNLocator
                ax1.xaxis.set_major_locator(MaxNLocator(nbins=12))
                
                # Rotate date labels for better readability
                plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
                
                # Add title
                title = f'Rating Metrics Over Time - {book_title}'
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
    
    # Rising Stars prediction methods
    async def get_rs_prediction_data(self, book_input, discord_username):
        """Get full RS prediction data with user tier check"""
        try:
            data = {
                'book_input': book_input,
                'discord_username': discord_username,
                'bot_token': self.wp_bot_token
            }
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/rising-stars-prediction"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'RR-Discord-Bot/1.0'
            }
            
            logger.info(f"[RS-PREDICTION] Fetching full RS data for book: {book_input}")
            
            async with self.session.post(url, json=data, headers=headers, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"[RS-PREDICTION] Data received, eligible: {result.get('eligible')}, premium: {result.get('is_premium')}")
                    return result
                else:
                    logger.error(f"[RS-PREDICTION] API error: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"[RS-PREDICTION] Exception: {e}")
            return None
    
    async def check_rs_eligibility(self, book_input):
        """Quick RS eligibility check - returns only eligibility status"""
        try:
            data = {
                'book_input': book_input,
                'bot_token': self.wp_bot_token
            }
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/rising-stars-prediction"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'RR-Discord-Bot/1.0'
            }
            
            logger.info(f"[RS-CHECK] Checking eligibility for book: {book_input}")
            
            async with self.session.post(url, json=data, headers=headers, timeout=10) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"[RS-CHECK] Eligibility result: {result.get('eligible')}")
                    return result
                else:
                    logger.error(f"[RS-CHECK] API error: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"[RS-CHECK] Exception: {e}")
            return None
    
    def add_rs_prediction_to_embed(self, embed, rs_data, user):
        """Add Rising Stars prediction information to embed while preserving all other fields"""
        
        if not rs_data.get('success') or not rs_data.get('eligible'):
            return embed
        
        is_premium = rs_data.get('is_premium', False)
        growth_metrics = rs_data.get('growth_metrics', {})
        
        # Add separator for RS section
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━",
            value="**🌟 RISING STARS ANALYSIS 🌟**",
            inline=False
        )
    
        # Current growth status
        week_growth = growth_metrics.get('week_growth', 0)
        recent_avg = growth_metrics.get('recent_avg_growth', 0)
        
        # Growth assessment
        if recent_avg >= 10:
            growth_status = "✅ **Strong growth detected!**"
            urgency = "Your book may reach Rising Stars soon."
        elif recent_avg >= 5:
            growth_status = "📈 **Moderate growth detected**"
            urgency = "With marketing boost, RS achievable in 1-2 weeks."
        else:
            growth_status = "🌱 **Building momentum**"
            urgency = "Need 10+ followers/day for RS potential."
        
        if not is_premium:
            # FREE USER - Basic disclaimer and tips
        
            embed.add_field(
                name="📊 Growth Status",
                value=f"**3-Day Daily Average:** {recent_avg:.1f} followers/day\n**7-Day Daily Average:** {(week_growth / 7):.1f} followers/day\n**Weekly Growth:** {week_growth} followers\n{growth_status}\n{urgency}",
                inline=False
            )
      
            embed.add_field(
                name="💡 Quick Tips",
                value=(
                    "• If you haven't started yet, arrange shoutouts now\n"
                    "• Consider scheduling ads on Royal Road (1-2 days approval)"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🔓 Want Detailed Predictions?",
                value=(
                    "Get personalized RS predictions including:\n"
                    "• Estimated peak positions\n"
                    "• Required followership growth for Top 3/7/25\n"
                    "• Marketing timeline\n"
                    "**[Support the RR Toolkit on Patreon to get access!](https://www.patreon.com/stepanchizhov)**\n\n"
                    "⚠️ *Ads are a financial risk with no guaranteed returns\nNot financial advice\nResults vary depending on CTR*\n"
                    "━━━━━━━━━━━━━━━━━━━━"
                ),
                inline=False
            )
        else:
            # PREMIUM USER - Detailed analysis
            predictions = rs_data.get('predictions', {})
            required_views = rs_data.get('required_views', {})
            marketing_recs = rs_data.get('marketing_recommendations', {})
            
            embed.add_field(
                name="📊 Current Growth Metrics",
                value=(
                    f"**3-Day Daily Average:** {recent_avg:.1f} followers/day\n"
                    f"**7-Day Daily Average:** {(week_growth / 7):.1f} followers/day\n"
                    f"**Weekly Growth:** {week_growth} followers"
                ),
                inline=True
            )
            
            # Position predictions
            if predictions:
                position_text = f"**Range:** #{predictions.get('estimated_position_range', 'Unknown')}\n\n"
                
                probs = predictions.get('position_probabilities', {})
                if probs:
                    position_text += "**Probabilities:**\n"
                    for pos, prob in probs.items():
                        if prob > 0:
                            # Determine probability label
                            if prob <= 5:
                                label = "Remote Chance"
                            elif prob <= 20:
                                label = "Highly Unlikely"
                            elif prob <= 35:
                                label = "Unlikely"
                            elif prob <= 50:
                                label = "Realistic Possibility"
                            elif prob <= 75:
                                label = "Likely"
                            elif prob <= 90:
                                label = "Highly Likely"
                            else:
                                label = "Almost Certain"
                            
                            position_text += f"• {pos}: {label}\n"
                
                embed.add_field(
                    name="🎯 Peak Position Prediction",
                    value=position_text,
                    inline=True
                )
            
            # Timeline estimate
            timeline = f"{urgency}\n\n⏰ Estimated Timeline\n" + rs_data.get('estimated_timeline', 'Unknown')
            embed.add_field(
                name=growth_status, 
                value=timeline,
                inline=True
            )
            
            # Marketing recommendations (condensed)
            if marketing_recs:
                # Find most relevant target
                achievable = []
                for target, rec in marketing_recs.items():
                    if rec.get('gap', 0) == 0:
                        achievable.append(target.replace('_', ' ').title())
                
                if achievable:
                    embed.add_field(
                        name="✅ Current Growth Status",
                        value=f"Current growth sufficient for: {', '.join(achievable)}",
                        inline=False
                    )
                else:
                    # Add each achievable target as a separate field
                    targets_added = 0
                    for target in ['top_25', 'top_10', 'top_7', 'top_3']:
                        if target in marketing_recs and marketing_recs[target].get('gap', 999) < 50:
                            rec = marketing_recs[target]
                            
                            # Create the target text for this specific target
                            target_text = (
                                f"Need at least:\n"
                                f"• {((rec['gap'] / 4) + recent_avg):.0f} new followers on day +1\n"
                                f"• {((rec['gap'] / 2) + recent_avg):.0f} new followers on day +2\n"
                                f"• At least {((rec['gap']) + recent_avg):.0f} new followers on Day 0 (main RS)\n"
                                f"• Continuous growth needed after\n"
                                f"**Ads:** {rec['ads_recommended']} recommended\n"
                                f"and/or\n"
                                f"**Shoutouts\\*:**\n"
                                f"Day 1: {rec['shoutouts_recommended']}, "
                                f"Day 2: {rec['shoutouts_recommended'] * 2}, "
                                f"Day 3: {rec['shoutouts_recommended'] * 3}, "
                                f"Day 4: {rec['shoutouts_recommended'] * 5}...\n\n"
                            )
                            
                            # Add as individual field with target name as title
                            embed.add_field(
                                name=f"🎯 Target: {target.replace('_', ' ').title()}",
                                value=target_text,
                                inline=False
                            )
                            targets_added += 1
                    
                    # If no targets were added, show the "no achievable targets" message
                    if targets_added == 0:
                        embed.add_field(
                            name="🎯 Recommendations",
                            value="No easily achievable targets (all gaps > 50 followers/day)",
                            inline=False
                        )
                    else:
                        # Add the footnote about shoutouts as a separate field
                        embed.add_field(
                            name="ℹ️ Note",
                            value="*Shoutouts recommendations are calculated for the baseline of ongoing books with 1,000+ followers/average views\nAdjust quantities based on your networking capabilities and preferences\nResults may very depending on the season, genre and other parameters",
                            inline=False
                        )
            
            # Shoutout search URL
            search_url = rs_data.get('shoutout_search_url')
            if search_url:
                embed.add_field(
                    name="🤝 Find Shoutout Partners",
                    value=f"[**Search for matching niche genre books**]({search_url})\nPlease be mindful:\nNot all authors want to do shoutouts\n\n⚠️ *Ads are a financial risk with no guaranteed returns\nNot financial advice\nResults vary depending on CTR*\n━━━━━━━━━━━━━━━━━━━━\n",
                    inline=False
                )
        
        return embed