import discord
from discord.ext import commands
import aiohttp
import json
import logging
import os
import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np
import io
from typing import Dict, Any, List, Optional

# Set up logging
logger = logging.getLogger('discord')

class RSAnalysisModule:
    def __init__(self, bot, session, wp_api_url, wp_bot_token, add_promotional_field_func=None):
        self.bot = bot
        self.session = session
        self.wp_api_url = wp_api_url
        self.wp_bot_token = wp_bot_token
        self.command_counter = 0
        
        # Store the promotional field function
        self.add_promotional_field = add_promotional_field_func or (lambda e, f=False: e)
        
        # All possible RS tags from the database
        self.ALL_RS_TAGS = [
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
            'virtual_reality', 'war_and_military', 'wuxia', 'xianxia',
            'sensitive', 'sexuality', 'ai_assisted', 'ai_generated', 'graphic_violence', 'profanity'
        ]
        
        # Default tags to show if none specified
        self.DEFAULT_TAGS = [
            'main', 'fantasy', 'sci_fi', 'litrpg', 'romance', 
            'action', 'adventure', 'comedy', 'drama', 'horror', 
            'mystery', 'psychological'
        ]
        
        # Register commands
        self.register_commands()
    
    def register_commands(self):
        """Register Rising Stars analysis commands with the bot"""
        
        @self.bot.tree.command(
            name="rr-rs-chart",
            description="Show growth chart around a book's Main Rising Stars appearance"
        )
        @discord.app_commands.describe(
            book_input="Book ID or Royal Road URL",
            days_before="Days to show before RS appearance (default: 7)",
            days_after="Days to show after RS run ends (default: 7)"
        )
        async def rr_rs_chart(
            interaction: discord.Interaction, 
            book_input: str,
            days_before: int = 7,
            days_after: int = 7
        ):
            await self.rs_chart_handler(interaction, book_input, days_before, days_after)
        
        @self.bot.tree.command(
            name="rr-rs-run",
            description="Show Rising Stars appearance history for a Royal Road book"
        )
        @discord.app_commands.describe(
            book_input="Book ID or Royal Road URL",
            tags="Comma-separated RS tags (e.g., 'main,fantasy,litrpg' or 'all'). Default: common tags"
        )
        async def rr_rs_run(
            interaction: discord.Interaction, 
            book_input: str,
            tags: str = ""
        ):
            await self.rs_run_handler(interaction, book_input, tags)
    
    async def rs_chart_handler(
        self,
        interaction: discord.Interaction,
        book_input: str,
        days_before: int,
        days_after: int
    ):
        """Generate a chart showing growth around Main Rising Stars appearance"""
        self.command_counter += 1
        
        # DEFER IMMEDIATELY - Critical for avoiding timeout
        await interaction.response.defer()
        
        logger.info(f"\n[RR-RS-CHART] Command called by {interaction.user}")
        logger.info(f"[RR-RS-CHART] Book input: '{book_input}', Days before: {days_before}, Days after: {days_after}")
        
        try:
            # Parse book input to get book ID
            book_id = self.extract_book_id(book_input)
            if not book_id:
                await interaction.followup.send(
                    "❌ Invalid book input. Please provide a book ID or Royal Road URL.",
                    ephemeral=True
                )
                return
            
            # Prepare request data
            request_data = {
                'book_id': book_id,
                'days_before': days_before,
                'days_after': days_after,
                'bot_token': self.wp_bot_token
            }
            
            headers = {
                'User-Agent': 'RR-Discord-Bot/1.0',
                'Content-Type': 'application/json',
                'X-WP-Nonce': 'discord-bot-request',
                'X-Forwarded-For': '127.0.0.1',
                'X-Real-IP': '127.0.0.1'
            }
            
            # Make API request
            async with self.session.post(
                f"{self.wp_api_url}/wp-json/rr-analytics/v1/rising-stars-chart",
                json=request_data,
                headers=headers,
                timeout=30
            ) as response:
                response_text = await response.text()
                logger.info(f"[RR-RS-CHART] API Response Status: {response.status}")
                
                if response.status == 403:
                    logger.info(f"[RR-RS-CHART] 403 Forbidden - Authentication failed")
                    await interaction.followup.send(
                        "❌ Authentication error. The bot token may be misconfigured.",
                        ephemeral=True
                    )
                    return
                elif response.status != 200:
                    logger.info(f"[RR-RS-CHART] API error response: {response_text[:500]}")
                    await interaction.followup.send(
                        f"❌ API error: {response.status}\nPlease contact support if this persists.",
                        ephemeral=True
                    )
                    return
                
                try:
                    data = json.loads(response_text)
                except json.JSONDecodeError as e:
                    logger.info(f"[RR-RS-CHART] Failed to parse JSON: {e}")
                    await interaction.followup.send(
                        "❌ Invalid response from server. Please try again later.",
                        ephemeral=True
                    )
                    return
            
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
            chart_buffer = self.create_rs_impact_chart(chart_data, rs_info, book_title)
            
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
                    
                    # Add info about peak days if available
                    if rs_info.get('best_position_dates'):
                        peak_days = len(rs_info['best_position_dates'])
                        if peak_days == 1:
                            rs_lines.append(f"**Peak Day:** {rs_info['best_position_dates'][0]}")
                        else:
                            rs_lines.append(f"**Days at Peak:** {peak_days}")
                
                if rs_info.get('days_on_list'):
                    rs_lines.append(f"**Total Days on the List:** {rs_info['days_on_list']}")
                
                if rs_lines:
                    embed.add_field(
                        name="⭐ Main Rising Stars Run",
                        value="\n".join(rs_lines),
                        inline=True
                    )
            
            # Add growth analysis sections
            self.add_growth_analysis_fields(embed, growth_analysis)
            
            # Add note about the chart
            embed.add_field(
                name="📊 Chart Details",
                value=(
                    "• **Blue line:** Followers over time (left axis)\n"
                    "• **Orange line:** Views over time (right axis)\n"
                    "• **Green shaded area:** Period on Main Rising Stars\n"
                    "• **Yellow shaded areas:** Days at peak RS position\n"
                    "• **Dotted lines:** RS start (green) and end (red) dates\n"
                    "• **Value boxes:** Exact counts at RS entry/exit points"
                ),
                inline=False
            )
            
            # Add promotional field
            embed = self.add_promotional_field(embed)
            
            embed.set_footer(text="Data from Stepan Chizhov's Royal Road Analytics\nTo use the bot, start typing /rr-rs-chart")
            
            await interaction.followup.send(embed=embed, file=file)
            logger.info(f"[RR-RS-CHART] Successfully sent RS impact chart for book {book_id}")
            
        except Exception as e:
            logger.info(f"[RR-RS-CHART] Error: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                await interaction.followup.send(
                    "❌ An error occurred while generating the Rising Stars impact chart.",
                    ephemeral=True
                )
            except:
                pass
    
    async def rs_run_handler(
        self,
        interaction: discord.Interaction,
        book_input: str,
        tags: str
    ):
        """Show Rising Stars run information for a book"""
        self.command_counter += 1
        
        logger.info(f"\n[RR-RS-RUN] Command called by {interaction.user}")
        logger.info(f"[RR-RS-RUN] Book input: '{book_input}', Tags: '{tags}'")
        
        await interaction.response.defer()
        
        try:
            # Parse the tags parameter
            requested_tags = self.parse_rs_tags(tags)
            
            logger.info(f"[RR-RS-RUN] Requested tags: {requested_tags[:10]}..." if len(requested_tags) > 10 else f"[RR-RS-RUN] Requested tags: {requested_tags}")
            
            # Parse book input to get book ID
            book_id = self.extract_book_id(book_input)
            if not book_id:
                await interaction.followup.send(
                    "❌ Invalid book input. Please provide a book ID or Royal Road URL.",
                    ephemeral=True
                )
                return
            
            # Prepare request data
            request_data = {
                'book_id': book_id,
                'tags': requested_tags,
                'bot_token': self.wp_bot_token
            }
            
            headers = {
                'User-Agent': 'RR-Discord-Bot/1.0',
                'Content-Type': 'application/json',
                'X-WP-Nonce': 'discord-bot-request',
                'X-Forwarded-For': '127.0.0.1',
                'X-Real-IP': '127.0.0.1'
            }
            
            # Make API request
            async with self.session.post(
                f"{self.wp_api_url}/wp-json/rr-analytics/v1/rising-stars-run",
                json=request_data,
                headers=headers,
                timeout=30
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.info(f"[RR-RS-RUN] API error: {response.status} - {error_text}")
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
            embed = self.create_rs_run_embed(book_info, rs_data, requested_tags, book_id)
            
            # Add promotional field
            embed = self.add_promotional_field(embed)
            
            await interaction.followup.send(embed=embed)
            logger.info(f"[RR-RS-RUN] Successfully sent RS run data for book {book_id}")
            
        except Exception as e:
            logger.info(f"[RR-RS-RUN] Error: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                await interaction.followup.send(
                    "❌ An error occurred while fetching Rising Stars data.",
                    ephemeral=True
                )
            except:
                pass
    
    # Helper methods
    def extract_book_id(self, book_input: str) -> Optional[str]:
        """Extract book ID from input string"""
        if book_input.isdigit():
            return book_input
        else:
            # Extract book ID from URL
            match = re.search(r'/fiction/(\d+)', book_input)
            if match:
                return match.group(1)
        return None
    
    def parse_rs_tags(self, tags_input: str) -> List[str]:
        """Parse the tags parameter and return list of requested tags"""
        if not tags_input:
            return self.DEFAULT_TAGS
        
        tags_lower = tags_input.lower().strip()
        
        if tags_lower == 'all':
            return self.ALL_RS_TAGS
        
        # Split by comma and clean up each tag
        input_tags = [tag.strip().lower().replace(' ', '_').replace('-', '_') 
                     for tag in tags_input.split(',')]
        
        # Validate tags against known RS tags
        requested_tags = []
        invalid_tags = []
        
        for tag in input_tags:
            # Handle special cases and variations
            tag_normalized = tag.replace('sci-fi', 'sci_fi').replace('scifi', 'sci_fi')
            
            if tag_normalized in self.ALL_RS_TAGS:
                requested_tags.append(tag_normalized)
            else:
                invalid_tags.append(tag)
        
        if not requested_tags:
            return self.DEFAULT_TAGS
        
        return requested_tags
    
    def create_rs_impact_chart(self, chart_data: Dict, rs_info: Dict, book_title: str) -> Optional[io.BytesIO]:
        """Create a chart showing follower/view growth around Rising Stars appearance"""
        try:
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
                y_pos = ax1.get_ylim()[1] * 0.8
                ax1.text(rs_start, y_pos, 'RS Start', rotation=90, verticalalignment='bottom', fontsize=8, color='green')
                ax1.text(rs_end, y_pos, 'RS End', rotation=90, verticalalignment='bottom', fontsize=8, color='red')
                
                # Add exact values at entry and exit points
                self.add_value_annotations(ax1, ax2, dates, followers, views, rs_start, rs_end, color1, color2)
                
                # Highlight best position periods
                self.highlight_best_positions(ax1, rs_info)
            
            # Format x-axis
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax1.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # Add title
            ax1.set_title(f'Rising Stars Impact Analysis: {book_title}', fontsize=12, fontweight='bold', pad=20)
            
            # Combine legends
            lines = line1 + line2
            labels = [l.get_label() for l in lines]
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
            logger.info(f"[RS-CHART] Error creating chart image: {e}")
            import traceback
            traceback.print_exc()
            plt.close()
            return None
    
    def add_value_annotations(self, ax1, ax2, dates, followers, views, rs_start, rs_end, color1, color2):
        """Add value annotations at RS entry and exit points"""
        # Find the indices for RS start and end
        rs_start_idx = None
        rs_end_idx = None
        
        for i, date in enumerate(dates):
            if date == rs_start:
                rs_start_idx = i
            if date == rs_end:
                rs_end_idx = i
        
        # If exact RS end date not found, find the closest date
        if rs_end_idx is None:
            for i in range(len(dates) - 1, -1, -1):
                if dates[i] <= rs_end:
                    rs_end_idx = i
                    break
        
        # If still no match, use the last available data point
        if rs_end_idx is None and len(dates) > 0:
            rs_end_idx = len(dates) - 1
        
        # Add annotations for entry values
        if rs_start_idx is not None:
            entry_followers = followers[rs_start_idx]
            entry_views = views[rs_start_idx]
            
            ax1.annotate(f'{entry_followers:,}', 
                       xy=(dates[rs_start_idx], entry_followers),
                       xytext=(-30, 5), textcoords='offset points',
                       fontsize=9, color=color1, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=color1, alpha=0.8))
            
            ax2.annotate(f'{entry_views:,}',
                       xy=(dates[rs_start_idx], entry_views),
                       xytext=(10, -15), textcoords='offset points',
                       fontsize=9, color=color2, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=color2, alpha=0.8))
        
        # Add annotations for exit values
        if rs_end_idx is not None:
            exit_followers = followers[rs_end_idx]
            exit_views = views[rs_end_idx]
            exit_date = dates[rs_end_idx]
            
            ax1.annotate(f'{exit_followers:,}',
                       xy=(exit_date, exit_followers),
                       xytext=(-35, 5), textcoords='offset points',
                       fontsize=9, color=color1, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                               edgecolor=color1, alpha=0.8))
            
            ax2.annotate(f'{exit_views:,}',
                       xy=(exit_date, exit_views),
                       xytext=(10, -15), textcoords='offset points',
                       fontsize=9, color=color2, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                               edgecolor=color2, alpha=0.8))
    
    def highlight_best_positions(self, ax, rs_info: Dict):
        """Highlight periods when book was at best position"""
        if rs_info.get('best_position_dates'):
            best_dates = rs_info['best_position_dates']
            best_pos = rs_info.get('best_position', 1)
            
            # Convert best position dates to datetime objects
            best_dates_dt = [datetime.strptime(d, '%Y-%m-%d') for d in best_dates]
            
            # Sort dates to find continuous periods
            best_dates_dt.sort()
            
            # Group consecutive dates into periods
            periods = []
            current_period_start = best_dates_dt[0]
            current_period_end = best_dates_dt[0]
            
            for i in range(1, len(best_dates_dt)):
                # Check if dates are consecutive (allowing 1 day gap)
                if (best_dates_dt[i] - current_period_end).days <= 1:
                    current_period_end = best_dates_dt[i]
                else:
                    # End current period and start new one
                    periods.append((current_period_start, current_period_end))
                    current_period_start = best_dates_dt[i]
                    current_period_end = best_dates_dt[i]
            
            # Add the last period
            periods.append((current_period_start, current_period_end))
            
            # Shade each period with yellow
            for period_start, period_end in periods:
                ax.axvspan(period_start, period_end, alpha=0.3, color='gold', 
                          label=f'At Peak #{best_pos}' if period_start == periods[0][0] else '')
            
            # Add a single annotation for peak position
            if periods:
                y_pos_best = ax.get_ylim()[1] * 0.85
                ax.text(periods[0][0], y_pos_best, f'Peak #{best_pos}', 
                        rotation=90, verticalalignment='bottom', 
                        fontsize=8, color='darkgoldenrod', fontweight='bold')
    
    def add_growth_analysis_fields(self, embed: discord.Embed, growth_analysis: Dict):
        """Add growth analysis fields to the embed"""
        # Before Rising Stars
        if growth_analysis.get('before_rs') and growth_analysis['before_rs'].get('has_data'):
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
            
            if before.get('prior_week_comparison'):
                comp = before['prior_week_comparison']
                if comp.get('growth_change_pct') is not None:
                    change_pct = comp['growth_change_pct']
                    if change_pct > 0:
                        before_lines.append(f"**vs Prior Week:** +{change_pct:.0f}%")
                    else:
                        before_lines.append(f"**vs Prior Week:** {change_pct:.0f}%")
            
            if before_lines:
                embed.add_field(
                    name="📊 Before Rising Stars",
                    value="\n".join(before_lines),
                    inline=True
                )
        elif growth_analysis.get('before_rs') and not growth_analysis['before_rs'].get('has_data'):
            embed.add_field(
                name="📊 Before Rising Stars",
                value="*No data available*\n(Book tracking may have started with RS)",
                inline=True
            )
        
        # During Rising Stars
        if growth_analysis.get('during_rs') and growth_analysis['during_rs']:
            during = growth_analysis['during_rs']
            during_lines = []
            
            if isinstance(during, dict) and during.get('follower_growth_rate') is not None:
                rate = during['follower_growth_rate']
                during_lines.append(f"**Daily Growth:** {rate:.1f} followers/day")
                
                # Calculate percentage increase in growth rate if we have before data
                before_rs = growth_analysis.get('before_rs')
                if isinstance(before_rs, dict) and before_rs.get('has_data') and before_rs.get('follower_growth_rate'):
                    before_rate = before_rs['follower_growth_rate']
                    if before_rate > 0:
                        pct_increase = ((rate - before_rate) / before_rate) * 100
                        if pct_increase > 0:
                            during_lines.append(f"**Growth Rate Increase:** +{pct_increase:.0f}%")
                        else:
                            during_lines.append(f"**Growth Rate Change:** {pct_increase:.0f}%")
            
            if isinstance(during, dict) and during.get('total_follower_change') is not None:
                change = during['total_follower_change']
                during_lines.append(f"**Total Gained:** +{change:,}")
                
                if during.get('start_followers') and during.get('end_followers'):
                    start = during['start_followers']
                    end = during['end_followers']
                    if start > 0:
                        total_pct = ((end - start) / start) * 100
                        during_lines.append(f"**Total Increase:** {total_pct:.0f}%")
            
            if isinstance(during, dict) and during.get('view_growth_rate') is not None:
                rate = during['view_growth_rate']
                during_lines.append(f"**View Growth:** {rate:,.0f}/day")
            
            if during_lines:
                embed.add_field(
                    name="🚀 During Rising Stars",
                    value="\n".join(during_lines),
                    inline=True
                )
        
        # After Rising Stars
        if growth_analysis.get('after_rs') and isinstance(growth_analysis['after_rs'], dict) and growth_analysis['after_rs'].get('has_data'):
            after = growth_analysis['after_rs']
            after_lines = []
            
            if after.get('follower_growth_rate') is not None:
                rate = after['follower_growth_rate']
                after_lines.append(f"**Daily Growth:** {rate:.1f} followers/day")
                
                # Compare to during RS period
                during_rs = growth_analysis.get('during_rs')
                if isinstance(during_rs, dict) and during_rs.get('follower_growth_rate'):
                    during_rate = during_rs['follower_growth_rate']
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
        
        # Impact summary
        if growth_analysis.get('impact_summary'):
            summary = growth_analysis['impact_summary']
            summary_lines = []
            
            if summary.get('total_increase_percentage') is not None:
                total_inc = summary['total_increase_percentage']
                summary_lines.append(f"**🎯 Total Follower Increase:** {total_inc:.0f}%")
            
            if summary.get('follower_boost_percentage') is not None:
                boost = summary['follower_boost_percentage']
                if boost > 0:
                    summary_lines.append(f"**Growth Rate Boost:** +{boost:.0f}%")
                else:
                    summary_lines.append(f"**📈 Growth Rate Change:** {boost:.0f}%")
            
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
    
    def create_rs_run_embed(self, book_info: Dict, rs_data: Dict, requested_tags: List[str], book_id: str) -> discord.Embed:
        """Create embed showing RS run history"""
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
                        field_lines.append(f"**First:** {tag_data['first_seen']}")
                    
                    # Current position
                    if tag_data.get('current_position'):
                        field_lines.append(f"**Now:** #{tag_data['current_position']}")
                    else:
                        field_lines.append(f"**Now:** Not on list")
                    
                    # Best position
                    if tag_data.get('best_position'):
                        field_lines.append(f"**Best:** #{tag_data['best_position']}")
                    
                    # Time on list
                    if tag_data.get('days_on_list'):
                        field_lines.append(f"**Days:** {tag_data['days_on_list']}")
                    
                    # Total appearances
                    field_lines.append(f"**Count:** {tag_data['appearances']}")
                    
                    # Trend indicator
                    if tag_data.get('trend'):
                        trend = tag_data['trend']
                        if trend == 'rising':
                            field_lines.append(f"📈 Rising")
                        elif trend == 'falling':
                            field_lines.append(f"📉 Declining")
                        elif trend == 'stable':
                            field_lines.append(f"➡️ Stable")
                    
                    # Format field name
                    display_name = self.format_tag_display_name(tag_name)
                    
                    # Add field to embed
                    embed.add_field(
                        name=display_name,
                        value="\n".join(field_lines),
                        inline=True
                    )
                    
                    # Discord has a limit of 25 fields per embed
                    if len(embed.fields) >= 24:
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
                display_name = self.format_tag_display_name(best_tag)
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
        if len(requested_tags) == len(self.ALL_RS_TAGS):
            query_note = "Showing: All Rising Stars lists"
        elif requested_tags == self.DEFAULT_TAGS:
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
        
        embed.set_footer(text="Data from Stepan Chizhov's Royal Road Analytics\nTo use: /rr-rs-run [book] tags:'all' or tags:'fantasy,litrpg,romance'")
        
        return embed
    
    def format_tag_display_name(self, tag_name: str) -> str:
        """Format tag name for display"""
        display_name = tag_name.replace('_', ' ').title()
        
        # Special cases
        special_names = {
            'main': '⭐ Main',
            'sci_fi': 'Sci-Fi',
            'litrpg': 'LitRPG',
            'gamelit': 'GameLit',
            'anti-hero_lead': 'Anti-Hero Lead',
            'non-human_lead': 'Non-Human Lead'
        }
        
        if tag_name in special_names:
            return special_names[tag_name]
        
        return display_name
