"""
Discord Bot Shoutout Swap System Module - Complete Unified Version
Modular extension for the existing Discord Essence Bot
Includes all original functionality plus announcement features with no duplication
"""

import discord
from discord.ext import commands
import aiohttp
import json
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import logging
from collections import defaultdict

# Set up logging for this module
logger = logging.getLogger('discord')

class ShoutoutModule:
    """
    Modular shoutout swap system for Discord bot
    Handles campaign creation, browsing, application management, and user campaigns
    """
    
    def __init__(self, bot: commands.Bot, session: aiohttp.ClientSession, wp_api_url: str, wp_bot_token: str, tag_autocomplete_func=None):
        self.bot = bot
        self.session = session
        self.wp_api_url = wp_api_url
        self.wp_bot_token = wp_bot_token
        self.tag_autocomplete = tag_autocomplete_func

        logger.info(f"[SHOUTOUT_MODULE] Initializing enhanced module...")
        logger.info(f"[SHOUTOUT_MODULE] bot: {bot}")
        logger.info(f"[SHOUTOUT_MODULE] wp_api_url: {wp_api_url}")
        logger.info(f"[SHOUTOUT_MODULE] wp_bot_token: {'[SET]' if wp_bot_token else '[NOT SET]'}")

        # Rate limiting for DMs
        self.dm_cooldowns = defaultdict(lambda: datetime.min)
        self.dm_rate_limit = timedelta(seconds=5)  # 5 seconds between DMs to same user
        
        # Register commands immediately
        self.register_commands()
        logger.info(f"[SHOUTOUT_MODULE] All commands registered")
    
    def register_commands(self):
        """Register all shoutout-related commands with the bot"""
        
        # Create campaign command - works everywhere
        @self.bot.tree.command(name="shoutout-campaign-create", description="Create a new shoutout campaign")
        async def shoutout_campaign_create(interaction: discord.Interaction):
            """Create a new shoutout campaign - works anywhere"""
            await self.handle_campaign_create(interaction)

        @self.bot.tree.command(name="shoutout-view-details", description="View detailed information about a shoutout campaign")
        @discord.app_commands.describe(
            campaign_id="The ID of the campaign to view"
        )
        async def shoutout_view_details(
            interaction: discord.Interaction,
            campaign_id: int
        ):
            await self.handle_view_campaign_details(interaction, campaign_id)

        # Browse campaigns command - with genre filter enabled
        @self.bot.tree.command(name="shoutout-browse", description="Browse available shoutout campaigns")
        @discord.app_commands.describe(
            genre="Filter by genre/tag",
            show_mine="Include your own campaigns in the list (default: False)"
            # platform="Filter by platform (Royal Road, Scribble Hub, Kindle, Audible, etc.)",
            # min_followers="Minimum follower count",
            # max_followers="Maximum follower count",
            # server_only="Show only campaigns from this server"
        )
        async def shoutout_browse(
            interaction: discord.Interaction,
            genre: Optional[str] = None,
            show_mine: Optional[bool] = False
            # platform: Optional[str] = None,
            # min_followers: Optional[int] = None,
            # max_followers: Optional[int] = None,
            # server_only: Optional[bool] = False
        ):
            await self.handle_browse_campaigns(
                interaction=interaction,
                genre=genre,
                platform=None,
                min_followers=None,
                max_followers=None,
                server_only=False,
                show_mine=show_mine
            )
        
        # Add autocomplete for genre if tag_autocomplete function is available
        if self.tag_autocomplete:
            shoutout_browse.autocomplete('genre')(self.tag_autocomplete)
        
        # My campaigns command - works everywhere (no DM restriction)
        @self.bot.tree.command(name="shoutout-my-campaigns", description="Manage your shoutout campaigns")
        @discord.app_commands.describe(
            filter_status="Filter by campaign status (active, paused, completed, all)"
        )
        @discord.app_commands.choices(filter_status=[
            discord.app_commands.Choice(name="Active", value="active"),
            discord.app_commands.Choice(name="Paused", value="paused"),
            discord.app_commands.Choice(name="Completed", value="completed"),
            discord.app_commands.Choice(name="All", value="all")
        ])
        async def shoutout_my_campaigns(
            interaction: discord.Interaction,
            filter_status: Optional[str] = "active"
        ):
            await self.handle_my_campaigns(interaction, filter_status)
        
        # Apply to the campaign command
        @self.bot.tree.command(name="shoutout-apply", description="Apply to a specific shoutout campaign")
        @discord.app_commands.describe(
            campaign_id="The ID of the campaign to apply to"
        )
        async def shoutout_apply(
            interaction: discord.Interaction,
            campaign_id: int
        ):
            await self.handle_apply_to_campaign(interaction, campaign_id)

        # My applications command - Track applications to other campaigns
        @self.bot.tree.command(name="shoutout-my-applications", description="View your applications to shoutout campaigns")
        @discord.app_commands.describe(
            filter_status="Filter by application status"
        )
        @discord.app_commands.choices(filter_status=[
            discord.app_commands.Choice(name="All", value="all"),
            discord.app_commands.Choice(name="Pending", value="pending"),
            discord.app_commands.Choice(name="Approved", value="approved"),
            discord.app_commands.Choice(name="Declined", value="declined"),
            discord.app_commands.Choice(name="Completed", value="completed")
        ])
        async def shoutout_my_applications(
            interaction: discord.Interaction,
            filter_status: Optional[str] = "all"
        ):
            await self.handle_my_applications(interaction, filter_status)
    
    async def handle_campaign_create(self, interaction: discord.Interaction):
        """Handle campaign creation workflow - works in servers and DMs"""
        try:
            await interaction.response.defer(ephemeral=True)
            deferred = True
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Failed to defer: {e}")
            deferred = False
            return
    
        logger.info(f"[SHOUTOUT_MODULE] ========== CAMPAIGN CREATE START ==========")
        logger.info(f"[SHOUTOUT_MODULE] User: {interaction.user.id} ({interaction.user.name})")
        
        # Log server info
        if interaction.guild:
            logger.info(f"[SHOUTOUT_MODULE] Guild: {interaction.guild.id} ({interaction.guild.name})")
            server_id = str(interaction.guild.id)
            server_name = interaction.guild.name
        else:
            logger.info(f"[SHOUTOUT_MODULE] Guild: DM (no server)")
            server_id = None
            server_name = None
        
        try:
            # Build the request data
            discord_username = f"{interaction.user.name}#{interaction.user.discriminator}"
            
            data = {
                'bot_token': self.wp_bot_token,
                'discord_user_id': str(interaction.user.id),
                'discord_username': discord_username,
                'server_id': server_id,
                'server_name': server_name,
                'check_tier_only': True  # Just checking tier first
            }
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns"
            
            logger.info(f"[SHOUTOUT_MODULE] API URL: {url}")
            logger.info(f"[SHOUTOUT_MODULE] Request data: {json.dumps({k: v if k != 'bot_token' else '[hidden]' for k, v in data.items()})}")
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            logger.info(f"[SHOUTOUT_MODULE] Making POST request to WordPress API...")
            
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with self.session.post(url, json=data, headers=headers, timeout=timeout) as response:
                logger.info(f"[SHOUTOUT_MODULE] Response status: {response.status}")
                
                response_text = await response.text()
                logger.info(f"[SHOUTOUT_MODULE] Response body (first 500 chars): {response_text[:500]}")
                
                try:
                    result = json.loads(response_text)
                    logger.info(f"[SHOUTOUT_MODULE] Parsed response: {json.dumps(result, indent=2)}")
                except json.JSONDecodeError as e:
                    logger.error(f"[SHOUTOUT_MODULE] JSON decode error: {e}")
                    
                    if deferred:
                        await interaction.followup.send(
                            "❌ Server returned invalid response. The API endpoint may not be properly configured.",
                            ephemeral=True
                        )
                    return
                
                # Handle the response based on status and content
                if response.status == 200 and result.get('has_access'):
                    logger.info(f"[SHOUTOUT_MODULE] User has access! Tier: {result.get('user_tier', 'unknown')}")
                    
                    # Show success message
                    embed = discord.Embed(
                        title="📝 Create Shoutout Campaign",
                        description=f"Welcome! Your tier: **{result.get('user_tier', 'unknown').upper()}**\n\nLet's set up your shoutout campaign.",
                        color=0x00A86B
                    )
                    
                    embed.add_field(
                        name="Step 1: Book Details",
                        value="Click the button below to enter your book information",
                        inline=False
                    )
                    
                    # Create view with buttons
                    view = CampaignCreationView(self, interaction.user.id, result.get('user_tier', 'unknown'))
                    
                    if deferred:
                        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                    else:
                        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                        
                else:
                    logger.info(f"[SHOUTOUT_MODULE] User doesn't have access. Response: {result}")
                    
                    embed = discord.Embed(
                        title="🔒 Shoutout Campaigns - Development Access",
                        description="Shoutout campaigns are currently in development and only available to supporters.",
                        color=0xff6b6b
                    )
                    embed.add_field(
                        name="Get Access",
                        value="Support the project on [Patreon](https://www.patreon.com/stepanchizhov) to get early access!",
                        inline=False
                    )
                    embed.add_field(
                        name="Debug Info",
                        value=f"Your tier: **{result.get('user_tier', 'unknown')}**\nHas access: **{result.get('has_access', False)}**",
                        inline=False
                    )
                    
                    if deferred:
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        
        except asyncio.TimeoutError:
            logger.error(f"[SHOUTOUT_MODULE] Request timeout")
            if deferred:
                await interaction.followup.send("❌ Request timed out. Please try again.", ephemeral=True)
                    
        except aiohttp.ClientError as e:
            logger.error(f"[SHOUTOUT_MODULE] Client error: {type(e).__name__}: {e}")
            if deferred:
                await interaction.followup.send("❌ Network error occurred. Please try again.", ephemeral=True)
                    
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Unexpected error: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[SHOUTOUT_MODULE] Traceback: {traceback.format_exc()}")
            
            if deferred:
                await interaction.followup.send("❌ An unexpected error occurred. Please try again later.", ephemeral=True)
        
        finally:
            logger.info(f"[SHOUTOUT_MODULE] ========== CAMPAIGN CREATE END ==========")

    async def handle_view_campaign_details(self, interaction: discord.Interaction, campaign_id: int):
        """Handle viewing detailed campaign information"""
        try:
            await interaction.response.defer(ephemeral=True)
            logger.info(f"[SHOUTOUT_MODULE] View details request for campaign {campaign_id} by {interaction.user.id}")
            
            # Fetch campaign details from API
            params = {
                'bot_token': self.wp_bot_token,
                'discord_user_id': str(interaction.user.id)
            }
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns/{campaign_id}/details"
            headers = {
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with self.session.get(url, params=params, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    campaign = await response.json()
                    
                    # Check if campaign exists and is active
                    if not campaign or campaign.get('campaign_status') != 'active':
                        await interaction.followup.send(
                            f"❌ Campaign #{campaign_id} not found or is not active",
                            ephemeral=True
                        )
                        return
                    
                    # Create the public announcement embed (reuse the existing method)
                    embed = self.create_public_campaign_details_embed(campaign)
                    
                    # Create view with Apply button if user isn't the campaign creator
                    view = None
                    campaign_creator_id = campaign.get('discord_user_id')
                    if campaign_creator_id and str(interaction.user.id) != str(campaign_creator_id):
                        # User is not the creator, show Apply button
                        view = PublicCampaignView(self, campaign)
                    
                    await interaction.followup.send(
                        embed=embed,
                        view=view,
                        ephemeral=True
                    )
                    
                elif response.status == 404:
                    await interaction.followup.send(
                        f"❌ Campaign #{campaign_id} not found",
                        ephemeral=True
                    )
                else:
                    logger.error(f"[SHOUTOUT_MODULE] Failed to fetch campaign details: {response.status}")
                    await interaction.followup.send(
                        "❌ Failed to fetch campaign details. Please try again later",
                        ephemeral=True
                    )
                    
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ Request timed out. Please try again.", ephemeral=True)
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error viewing campaign details: {e}")
            import traceback
            logger.error(f"[SHOUTOUT_MODULE] Traceback: {traceback.format_exc()}")
            await interaction.followup.send("❌ An error occurred.", ephemeral=True)
    
    async def handle_browse_campaigns(
        self,
        interaction: discord.Interaction,
        genre: Optional[str] = None,
        platform: Optional[str] = None,
        min_followers: Optional[int] = None,
        max_followers: Optional[int] = None,
        server_only: Optional[bool] = False,
        show_mine: Optional[bool] = False
    ):  
        """Handle browsing campaigns with filters"""
        # Defer IMMEDIATELY - this must happen within 3 seconds
        try:
            await interaction.response.defer()
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Failed to defer browse response: {e}")
            return
        
        # Now we can do logging and other operations
        logger.info(f"[SHOUTOUT_MODULE] Browse campaigns - deferred response")
        logger.info(f"[SHOUTOUT_MODULE] Browse campaigns called by {interaction.user.id}")
        logger.info(f"[SHOUTOUT_MODULE] Parameters: genre={genre}, show_mine={show_mine}, server_only={server_only}")    
        
        try:
            # Build API request
            params = {
                'bot_token': self.wp_bot_token,
                'discord_user_id': str(interaction.user.id),
                'discord_username': f"{interaction.user.name}#{interaction.user.discriminator}"
            }
            
            # Add server_id if in a guild (important for filtering)
            if interaction.guild:
                params['server_id'] = str(interaction.guild.id)
                logger.info(f"[SHOUTOUT_MODULE] Browsing from server: {interaction.guild.id}")
            else:
                logger.info(f"[SHOUTOUT_MODULE] Browsing from DMs")
            
            # Add filters
            if genre:
                params['genre'] = genre
            if platform:
                params['platform'] = platform
            if min_followers is not None:
                params['min_followers'] = min_followers
            if max_followers is not None:
                params['max_followers'] = max_followers
            if server_only:
                params['server_only'] = 'true'
            # Always pass show_mine parameter (even if False) so the API knows what to do
            params['show_mine'] = 'true' if show_mine else 'false'
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns"
            headers = {
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            logger.info(f"[SHOUTOUT_MODULE] Fetching campaigns from: {url}")
            # logger.info(f"[SHOUTOUT_MODULE] Request params: {params}")
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with self.session.get(url, params=params, headers=headers, timeout=timeout) as response:
                logger.info(f"[SHOUTOUT_MODULE] Browse response status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    campaigns = result.get('campaigns', [])
                    
                    logger.info(f"[SHOUTOUT_MODULE] Found {len(campaigns)} campaigns")
                    
                    if campaigns:
                        embed = self.create_campaign_list_embed(campaigns)
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send(
                            "No campaigns found matching your criteria. Try adjusting your filters or check back later!",
                            ephemeral=True
                        )
                else:
                    logger.error(f"[SHOUTOUT_MODULE] Failed to fetch campaigns: {response.status}")
                    await interaction.followup.send(
                        "❌ Failed to fetch campaigns. Please try again later.",
                        ephemeral=True
                    )
                    
        except asyncio.TimeoutError:
            logger.error(f"[SHOUTOUT_MODULE] Browse request timeout")
            await interaction.followup.send(
                "❌ Request timed out. Please try again.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error browsing campaigns: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[SHOUTOUT_MODULE] Traceback:\n{traceback.format_exc()}")
            
            await interaction.followup.send(
                "❌ An error occurred while fetching campaigns.",
                ephemeral=True
            )
    
    def create_campaign_list_embed(self, campaigns: List[Dict]) -> discord.Embed:
        """Create embed showing list of campaigns"""
        embed = discord.Embed(
            title="📚 Available Shoutout Campaigns",
            description=f"Found {len(campaigns)} campaign(s)",
            color=0x00A86B
        )
        
        for i, campaign in enumerate(campaigns[:10]):  # Show max 10
            campaign_id = campaign.get('id', 'Unknown')
            book_url = campaign.get('book_url', '#')
            book_title = campaign.get('book_title', 'Unknown Book')
            
            # Handle available_dates - show first one if it's a list
            available_dates_str = ""
            available_dates = campaign.get('available_dates')
            if available_dates:
                try:
                    # Try to parse as JSON if it's a string
                    if isinstance(available_dates, str):
                        import json
                        dates_list = json.loads(available_dates)
                    else:
                        dates_list = available_dates
                    
                    if isinstance(dates_list, list) and dates_list:
                        if len(dates_list) > 1:
                            available_dates_str = f"**Dates available:** {dates_list[0]} (+{len(dates_list)-1} more)"
                        else:
                            available_dates_str = f"**Dates available:** {dates_list[0]}"
                    elif isinstance(dates_list, str):
                        available_dates_str = f"**Dates available:** {dates_list}"
                except:
                    # If parsing fails, just use as string
                    if available_dates:
                        available_dates_str = f"**Dates available:** {available_dates}"
            
            # Build field value with book link at the top
            field_value_parts = []
            
            # Add book link if available
            if book_url and book_url != '#':
                field_value_parts.append(f"[View Book]({book_url})")
            
            field_value_parts.extend([
                f"**Campaign ID:** #{campaign_id}",
                f"**Author:** {campaign.get('author_name', 'Unknown')}",
                # f"**Platform:** {campaign.get('platform', 'Unknown')}",  # Future functionality
                f"**Slots Available:** {campaign.get('available_slots', 0)}"
            ])
            
            # Add available dates if present
            if available_dates_str:
                field_value_parts.append(available_dates_str)
            
            field_value = "\n".join(field_value_parts)
            
            # Use plain text for field name (no markdown)
            embed.add_field(
                name=f"{i+1}. {book_title}",  # Plain text title
                value=field_value,
                inline=False
            )
        
        if len(campaigns) > 10:
            embed.add_field(
                name="More campaigns available",
                value=f"Showing 10 of {len(campaigns)} campaigns. Use filters to narrow results",
                inline=False
            )
        
        embed.set_footer(text="💡 Apply to any campaign using: /shoutout-apply [campaign_id]\n❓ Check any campaign's info using: /shoutout-view-details [campaign_id]")
        
        return embed
        
    async def fetch_book_stats(self, book_url: str, campaign_rr_book_id: int = None) -> Optional[Dict]:
        """Fetch book statistics from WordPress API"""
        try:
            # Extract RR book ID from URL if it's a Royal Road book
            rr_book_id = None
            if 'royalroad.com' in book_url:
                import re
                match = re.search(r'/fiction/(\d+)', book_url)
                if match:
                    rr_book_id = match.group(1)
            
            if not rr_book_id:
                return None
            
            # Make API call to get book stats
            params = {
                'bot_token': self.wp_bot_token,
                'rr_book_id': rr_book_id,
                'campaign_rr_book_id': campaign_rr_book_id
            }
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/shoutout/book-stats"
            headers = {
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            timeout = aiohttp.ClientTimeout(total=5)
            async with self.session.get(url, params=params, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    return await response.json()
            
            return None
            
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error fetching book stats: {e}")
            return None
    
    async def handle_my_campaigns(self, interaction: discord.Interaction, filter_status: str = "active"):
        """Handle viewing and managing user's own campaigns - works everywhere"""
        try:
            await interaction.response.defer(ephemeral=True)
            logger.info(f"[SHOUTOUT_MODULE] My campaigns request from {interaction.user.id}")
            
            # Build API request
            params = {
                'bot_token': self.wp_bot_token,
                'discord_user_id': str(interaction.user.id),
                'discord_username': f"{interaction.user.name}#{interaction.user.discriminator}",
                'filter_status': filter_status
            }
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/shoutout/my-campaigns/{interaction.user.id}"
            headers = {
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with self.session.get(url, params=params, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    result = await response.json()
                    campaigns = result.get('campaigns', [])
                    
                    if not campaigns:
                        await interaction.followup.send(
                            f"You don't have any {filter_status} campaigns. Use `/shoutout-campaign-create` to create one!",
                            ephemeral=True
                        )
                        return
                    
                    # Create paginated view
                    view = MyCampaignsView(self, campaigns, interaction.user.id)
                    embed = self.create_my_campaigns_embed(campaigns[0], 0, len(campaigns))
                    
                    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                    
                else:
                    logger.error(f"[SHOUTOUT_MODULE] Failed to fetch user campaigns: {response.status}")
                    await interaction.followup.send(
                        "❌ Failed to fetch your campaigns. Please try again later.",
                        ephemeral=True
                    )
                    
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ Request timed out. Please try again.", ephemeral=True)
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error in my_campaigns: {e}")
            await interaction.followup.send("❌ An error occurred.", ephemeral=True)
    
    async def handle_apply_to_campaign(self, interaction: discord.Interaction, campaign_id: int):
        """Handle application to a specific campaign"""
        try:
            await interaction.response.defer(ephemeral=True)
            logger.info(f"[SHOUTOUT_MODULE] Apply request from {interaction.user.id} for campaign {campaign_id}")
            
            # First, get campaign details
            params = {
                'bot_token': self.wp_bot_token,
                'discord_user_id': str(interaction.user.id)
            }
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns/{campaign_id}/details"
            headers = {
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with self.session.get(url, params=params, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    campaign = await response.json()
                    
                    # Show campaign details and confirm application
                    embed = discord.Embed(
                        title=f"Apply to: {campaign.get('book_title', 'Unknown')}",
                        description=f"By {campaign.get('author_name', 'Unknown')}",
                        color=0x00A86B
                    )
                    embed.add_field(
                        name="Platform",
                        value=campaign.get('platform', 'Unknown'),
                        inline=True
                    )
                    embed.add_field(
                        name="Available Slots",
                        value=f"{campaign.get('available_slots', 0)} remaining",
                        inline=True
                    )
                    embed.add_field(
                        name="Book URL",
                        value=f"[View Book]({campaign.get('book_url', '#')})",
                        inline=False
                    )
                    
                    # Use unified application view
                    view = ApplicationConfirmView(self, campaign_id, campaign)
                    
                    await interaction.followup.send(
                        embed=embed,
                        view=view,
                        ephemeral=True
                    )
                    
                elif response.status == 404:
                    await interaction.followup.send(
                        f"❌ Campaign #{campaign_id} not found or is no longer active.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "❌ Failed to fetch campaign details.",
                        ephemeral=True
                    )
                    
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error applying to campaign: {e}")
            await interaction.followup.send("❌ An error occurred.", ephemeral=True)

    async def handle_my_applications(self, interaction: discord.Interaction, filter_status: str = "all"):
        """Handle viewing user's applications to other campaigns"""
        try:
            await interaction.response.defer(ephemeral=True)
            logger.info(f"[SHOUTOUT_MODULE] My applications request from {interaction.user.id}, filter: {filter_status}")
            
            # Build API request
            params = {
                'bot_token': self.wp_bot_token,
                'discord_user_id': str(interaction.user.id),
                'discord_username': f"{interaction.user.name}#{interaction.user.discriminator}"
            }
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/shoutout/my-applications/{interaction.user.id}"
            headers = {
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with self.session.get(url, params=params, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    result = await response.json()
                    applications = result.get('applications', [])
                    
                    # Filter applications if requested
                    if filter_status != 'all':
                        applications = [app for app in applications if app.get('status') == filter_status]
                    
                    if not applications:
                        status_text = f"{filter_status} " if filter_status != 'all' else ""
                        await interaction.followup.send(
                            f"You don't have any {status_text}applications. Use `/shoutout-browse` to find campaigns!",
                            ephemeral=True
                        )
                        return
                    
                    # Create paginated view
                    view = MyApplicationsView(self, applications, interaction.user.id, filter_status)
                    embed = view.create_application_embed(0)
                    
                    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                    
                else:
                    logger.error(f"[SHOUTOUT_MODULE] Failed to fetch user applications: {response.status}")
                    await interaction.followup.send(
                        "❌ Failed to fetch your applications. Please try again later.",
                        ephemeral=True
                    )
                    
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ Request timed out. Please try again.", ephemeral=True)
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error in my_applications: {e}")
            await interaction.followup.send("❌ An error occurred.", ephemeral=True)

    def create_public_campaign_details_embed(self, campaign: Dict) -> discord.Embed:
        """Create embed for public campaign details view (similar to announcement)"""
        embed = discord.Embed(
            title=f"📖 {campaign.get('book_title', 'Unknown')}",
            description=f"by **{creator_mention}**",  # Now clickable Discord mention
            color=0x00A86B
        )
        
        #embed = discord.Embed(
        #    title=f"📖 {campaign.get('book_title', 'Unknown')}",
        #    description=f"by **{campaign.get('author_name', 'Unknown')}**",
        #    color=0x00A86B
        #)
        
        # Add book URL if available
        book_url = campaign.get('book_url')
        if book_url:
            embed.add_field(
                name="📚 Book Link",
                value=f"[Read on {campaign.get('platform', 'Platform')}]({book_url})",
                inline=False
            )
        
        # Campaign details
        embed.add_field(
            name="Platform",
            value=campaign.get('platform', 'Unknown'),
            inline=True
        )
        
        available_slots = campaign.get('available_slots', 0)
        total_slots = campaign.get('total_slots', 0)
        embed.add_field(
            name="Available Slots",
            value=f"{available_slots}/{total_slots}",
            inline=True
        )
        
        embed.add_field(
            name="Campaign ID",
            value=f"#{campaign.get('id', 'Unknown')}",
            inline=True
        )
        
        # Add available dates
        available_dates = campaign.get('available_dates')
        if available_dates:
            try:
                # Try to parse as JSON if it's a string
                if isinstance(available_dates, str):
                    import json
                    dates_list = json.loads(available_dates)
                else:
                    dates_list = available_dates
                
                if isinstance(dates_list, list) and dates_list:
                    if len(dates_list) > 1:
                        dates_str = f"{dates_list[0]} (+{len(dates_list)-1} more dates)"
                    else:
                        dates_str = dates_list[0]
                    embed.add_field(
                        name="📅 Shoutout Dates Available",
                        value=dates_str,
                        inline=False
                    )
                elif isinstance(dates_list, str):
                    embed.add_field(
                        name="📅 Shoutout Dates Available",
                        value=dates_list,
                        inline=False
                    )
            except:
                # If parsing fails, just use as string
                if available_dates:
                    embed.add_field(
                        name="📅 Shoutout Dates Available",
                        value=available_dates,
                        inline=False
                    )
        
        # Add blurb if available
        blurb = campaign.get('blurb')
        if blurb:
            embed.add_field(
                name="About the Book",
                value=blurb[:500] if len(blurb) > 500 else blurb,
                inline=False
            )
        
        # Add campaign creator info
        # creator_id = campaign.get('discord_user_id')
        #if creator_id:
        #    embed.add_field(
        #        name="Campaign Creator",
        #        value=f"<@{creator_id}>",
        #        inline=True
        #    )
        
        # Add status
        status = campaign.get('campaign_status', 'unknown')
        if status != 'active':
            embed.add_field(
                name="Status",
                value=status.title(),
                inline=True
            )
        
        # Check if user already applied
        if campaign.get('applied_books'):
            # User has applied with some books
            applied_count = len(campaign['applied_books'])
            if applied_count == 1:
                embed.add_field(
                    name="📚 Your Applications",
                    value="You've applied to this campaign with 1 book. You can apply with different books!",
                    inline=False
                )
            else:
                embed.add_field(
                    name="📚 Your Applications",
                    value=f"You've applied to this campaign with {applied_count} different books.",
                    inline=False
                )
        elif campaign.get('is_full'):
            embed.add_field(
                name="⚠️ Note", 
                value="This campaign is currently full",
                inline=False
            )
        else:
            embed.add_field(
                name="How to Apply",
                value="Click the **Apply** button below to submit your application!",
                inline=False
            )

        embed.set_footer(text=f"Campaign #{campaign.get('id')} • Buttons expire after 15 minutes")
        
        return embed    

    async def send_dm_with_ratelimit(self, user_id: int, embed: discord.Embed) -> bool:
        """Send DM with rate limit protection"""
        try:
            # Check cooldown
            now = datetime.now()
            last_dm = self.dm_cooldowns[user_id]
            
            if now - last_dm < self.dm_rate_limit:
                wait_time = (self.dm_rate_limit - (now - last_dm)).total_seconds()
                logger.info(f"[SHOUTOUT_MODULE] Rate limit: waiting {wait_time:.1f}s before DMing user {user_id}")
                await asyncio.sleep(wait_time)
            
            # Try to get the user
            try:
                user = await self.bot.fetch_user(user_id)
            except discord.NotFound:
                logger.error(f"[SHOUTOUT_MODULE] User {user_id} not found")
                return False
            except discord.HTTPException as e:
                if e.status == 429:  # Rate limited
                    logger.warning(f"[SHOUTOUT_MODULE] Rate limited when fetching user {user_id}")
                    await asyncio.sleep(5)  # Wait 5 seconds and skip
                    return False
                raise
            
            # Send DM with error handling
            try:
                await user.send(embed=embed)
                self.dm_cooldowns[user_id] = datetime.now()
                logger.info(f"[SHOUTOUT_MODULE] DM sent successfully to {user_id}")
                return True
            except discord.Forbidden:
                logger.info(f"[SHOUTOUT_MODULE] Cannot DM user {user_id} - DMs disabled")
                return False
            except discord.HTTPException as e:
                if e.status == 429:  # Rate limited
                    retry_after = e.retry_after if hasattr(e, 'retry_after') else 60
                    logger.warning(f"[SHOUTOUT_MODULE] Rate limited sending DM. Retry after: {retry_after}s")
                    # Don't retry, just log it
                    return False
                raise
                
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error sending DM to {user_id}: {e}")
            return False
    
    def create_my_campaigns_embed(self, campaign: Dict, index: int, total: int) -> discord.Embed:
        """Create embed for a single campaign in my campaigns view"""
        embed = discord.Embed(
            title=f"Campaign {index + 1}/{total}: {campaign.get('book_title', 'Unknown')}",
            color=0x00A86B if campaign.get('campaign_status') == 'active' else 0xFFA500
        )
        
        embed.add_field(
            name="Status",
            value=campaign.get('campaign_status', 'unknown').title(),
            inline=True
        )
        embed.add_field(
            name="Available Slots",
            value=f"{campaign.get('available_slots', 0)}/{campaign.get('total_slots', 0)}",
            inline=True
        )
        embed.add_field(
            name="Campaign ID",
            value=f"#{campaign.get('id', 'Unknown')}",
            inline=True
        )
        
        # Applications summary
        applications = campaign.get('applications', [])
        pending = len([a for a in applications if a.get('status') == 'pending'])
        approved = len([a for a in applications if a.get('status') == 'approved'])
        
        embed.add_field(
            name="Applications",
            value=f"**Pending:** {pending}\n**Approved:** {approved}",
            inline=False
        )
        
        # List pending applications (first 5) with clickable Discord mentions
        if pending > 0:
            pending_apps = [a for a in applications if a.get('status') == 'pending'][:5]
            app_list = []
            for app in pending_apps:
                discord_id = app.get('discord_user_id')
                if discord_id:
                    app_list.append(f"• <@{discord_id}> - {app.get('book_title', 'Unknown')}")
                else:
                    app_list.append(f"• {app.get('discord_username', 'Unknown')} - {app.get('book_title', 'Unknown')}")
            
            embed.add_field(
                name="Recent Pending Applications",
                value="\n".join(app_list),
                inline=False
            )
            
            if pending > 5:
                embed.set_footer(text=f"And {pending - 5} more pending applications...")
        
        return embed


class CampaignCreationView(discord.ui.View):
    """View for campaign creation workflow"""
    
    def __init__(self, module: ShoutoutModule, user_id: int, user_tier: str):
        super().__init__(timeout=300)
        self.module = module
        self.user_id = user_id
        self.user_tier = user_tier
    
    @discord.ui.button(label="Enter Book Details", style=discord.ButtonStyle.primary)
    async def book_details_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show modal for book details"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This campaign creation is for another user.", ephemeral=True)
            return
        
        modal = EnhancedBookDetailsModal(self.module)
        await interaction.response.send_modal(modal)
        logger.info(f"[SHOUTOUT_MODULE] Enhanced book details modal sent to user {interaction.user.id}")


class EnhancedBookDetailsModal(discord.ui.Modal, title="Campaign Details"):
    """Enhanced modal for campaign creation with shoutout code"""
    
    book_title = discord.ui.TextInput(
        label="Book Title",
        placeholder="Enter your book's title",
        required=True,
        max_length=200
    )
    
    author_name = discord.ui.TextInput(
        label="Author Name",
        placeholder="Your pen name or author name",
        required=True,
        max_length=100
    )
    
    book_url = discord.ui.TextInput(
        label="Book URL",
        placeholder="https://www.royalroad.com/fiction/...",
        required=True,
        max_length=500
    )
    
    platform = discord.ui.TextInput(
        label="Platform",
        placeholder="Royal Road, Scribble Hub, Kindle, Audible, etc.",
        required=True,
        max_length=50
    )
    
    available_slots = discord.ui.TextInput(
        label="Number of Shoutout Slots",
        placeholder="How many shoutouts can you offer? (minimum 1)",
        required=True,
        max_length=5
    )
    
    def __init__(self, module):
        super().__init__()
        self.module = module
        logger.info(f"[SHOUTOUT_MODULE] EnhancedBookDetailsModal initialized")
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission with enhanced data"""
        logger.info(f"[SHOUTOUT_MODULE] ========== ENHANCED MODAL SUBMIT START ==========")
        logger.info(f"[SHOUTOUT_MODULE] Modal submitted by {interaction.user.id}")
        
        try:
            await interaction.response.defer(ephemeral=True)
            logger.info(f"[SHOUTOUT_MODULE] Modal response deferred")
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Failed to defer modal response: {e}")
            return
        
        try:
            logger.info(f"[SHOUTOUT_MODULE] Book Title: {self.book_title.value}")
            logger.info(f"[SHOUTOUT_MODULE] Book URL: {self.book_url.value}")
            logger.info(f"[SHOUTOUT_MODULE] Platform: {self.platform.value}")
            logger.info(f"[SHOUTOUT_MODULE] Author: {self.author_name.value}")
            logger.info(f"[SHOUTOUT_MODULE] Slots value: {self.available_slots.value}")
            
            # Validate slots number
            try:
                slots = int(self.available_slots.value)
                logger.info(f"[SHOUTOUT_MODULE] Slots parsed as: {slots}")
            except ValueError as e:
                logger.error(f"[SHOUTOUT_MODULE] Invalid slots value: {e}")
                await interaction.followup.send(
                    "❌ Please enter a valid number for slots",
                    ephemeral=True
                )
                return
                
            if slots < 1:
                logger.error(f"[SHOUTOUT_MODULE] Slots less than 1: {slots}")
                await interaction.followup.send(
                    "❌ You must offer at least 1 shoutout slot",
                    ephemeral=True
                )
                return
            
            # Validate book URL
            book_url = self.book_url.value.strip()
            if book_url:
                # Basic URL validation
                if not (book_url.startswith('http://') or book_url.startswith('https://')):
                    await interaction.followup.send(
                        "❌ Book URL must start with http:// or https://",
                        ephemeral=True
                    )
                    return
                
                # Optional: Check for valid domain structure
                import re
                url_pattern = re.compile(
                    r'^https?://'  # http:// or https://
                    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                    r'localhost|'  # localhost...
                    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                    r'(?::\d+)?'  # optional port
                    r'(?:/?|[/?]\S+)$', re.IGNORECASE)
                
                if not url_pattern.match(book_url):
                    await interaction.followup.send(
                        "❌ Please enter a valid URL for your book",
                        ephemeral=True
                    )
                    return
            
            # Get server ID and name if in a guild
            if interaction.guild:
                server_id = str(interaction.guild.id)
                server_name = interaction.guild.name
                logger.info(f"[SHOUTOUT_MODULE] Server ID: {server_id}")
                logger.info(f"[SHOUTOUT_MODULE] Server Name: {server_name}")
            else:
                server_id = None
                server_name = None
                logger.info(f"[SHOUTOUT_MODULE] No server (DM)")
            
            discord_username = f"{interaction.user.name}#{interaction.user.discriminator}"
            logger.info(f"[SHOUTOUT_MODULE] Discord username: {discord_username}")
            
            # Create campaign via API with ALL book data
            data = {
                'bot_token': self.module.wp_bot_token,
                'discord_user_id': str(interaction.user.id),
                'discord_username': discord_username,
                'book_title': self.book_title.value,
                'book_url': book_url,
                'platform': self.platform.value,
                'author_name': self.author_name.value,
                'available_slots': slots,
                'server_id': server_id,
                'server_name': server_name,
                'campaign_settings': {
                    'auto_approve': False,
                    'require_mutual_server': False
                }
            }
            
            logger.info(f"[SHOUTOUT_MODULE] Preparing to send campaign data")
            for key, value in data.items():
                if key == 'bot_token':
                    logger.info(f"[SHOUTOUT_MODULE]   {key}: [hidden]")
                else:
                    logger.info(f"[SHOUTOUT_MODULE]   {key}: {value}")
            
            url = f"{self.module.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.module.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            logger.info(f"[SHOUTOUT_MODULE] Making POST request to: {url}")
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with self.module.session.post(url, json=data, headers=headers, timeout=timeout) as response:
                logger.info(f"[SHOUTOUT_MODULE] Response status: {response.status}")
                response_text = await response.text()
                logger.info(f"[SHOUTOUT_MODULE] Response text (first 500): {response_text[:500]}")
                
                try:
                    result = json.loads(response_text)
                    logger.info(f"[SHOUTOUT_MODULE] Parsed response: {json.dumps(result, indent=2)}")
                except json.JSONDecodeError as e:
                    logger.error(f"[SHOUTOUT_MODULE] Failed to parse JSON response: {e}")
                    await interaction.followup.send(
                        "❌ Server returned invalid response. Please try again",
                        ephemeral=True
                    )
                    return
                
                if response.status == 200 and result.get('success'):
                    logger.info(f"[SHOUTOUT_MODULE] Campaign created successfully! ID: {result.get('campaign_id')}")
                    
                    embed = discord.Embed(
                        title="✅ Campaign Created Successfully!",
                        description=f"Your shoutout campaign for **{self.book_title.value}** has been created.",
                        color=0x00A86B
                    )
                    embed.add_field(
                        name="Campaign ID",
                        value=result.get('campaign_id', 'Unknown'),
                        inline=True
                    )
                    embed.add_field(
                        name="Available Slots",
                        value=str(slots),
                        inline=True
                    )
                    embed.add_field(
                        name="Platform",
                        value=self.platform.value.title(),
                        inline=True
                    )
                    embed.add_field(
                        name="Book URL",
                        value=f"[View Book]({book_url})",
                        inline=False
                    )
                    embed.add_field(
                        name="Next Steps",
                        value=(
                            "• Your campaign is now live\n"
                            "• Use `/shoutout-my-campaigns` to manage applications\n"
                            "• Click 'Announce' to share your campaign publicly"
                        ),
                        inline=False
                    )
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    logger.info(f"[SHOUTOUT_MODULE] Success message sent to user")
                else:
                    error_msg = result.get('message', 'Unknown error occurred')
                    logger.error(f"[SHOUTOUT_MODULE] Campaign creation failed: {error_msg}")
                    await interaction.followup.send(
                        f"❌ Failed to create campaign: {error_msg}",
                        ephemeral=True
                    )
        
        except aiohttp.ClientError as e:
            logger.error(f"[SHOUTOUT_MODULE] Network error: {type(e).__name__}: {e}")
            await interaction.followup.send(
                "❌ Network error occurred. Please try again.",
                ephemeral=True
            )
        except asyncio.TimeoutError:
            logger.error(f"[SHOUTOUT_MODULE] Request timeout")
            await interaction.followup.send(
                "❌ Request timed out. Please try again.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Unexpected error in on_submit: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[SHOUTOUT_MODULE] Traceback:\n{traceback.format_exc()}")
            
            try:
                await interaction.followup.send(
                    "❌ An error occurred while creating your campaign. Please try again.",
                    ephemeral=True
                )
            except:
                logger.error(f"[SHOUTOUT_MODULE] Failed to send error message to user")
        
        finally:
            logger.info(f"[SHOUTOUT_MODULE] ========== ENHANCED MODAL SUBMIT END ==========")


class MyCampaignsView(discord.ui.View):
    """View for navigating through user's campaigns"""
    
    def __init__(self, module: ShoutoutModule, campaigns: List[Dict], user_id: int):
        super().__init__(timeout=600)
        self.module = module
        self.campaigns = campaigns
        self.user_id = user_id
        self.current_index = 0
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current index"""
        self.previous_button.disabled = self.current_index == 0
        self.next_button.disabled = self.current_index >= len(self.campaigns) - 1
        
        if self.campaigns:
            current_campaign = self.campaigns[self.current_index]
            self.manage_button.label = f"Manage #{current_campaign.get('id', '?')}"
            self.edit_button.label = f"Edit #{current_campaign.get('id', '?')}"
            self.announce_button.label = f"Announce #{current_campaign.get('id', '?')}"
    
    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary, custom_id="prev", row=0)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous campaign"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your campaign list.", ephemeral=True)
            return
        
        self.current_index = max(0, self.current_index - 1)
        self.update_buttons()
        
        embed = self.module.create_my_campaigns_embed(
            self.campaigns[self.current_index],
            self.current_index,
            len(self.campaigns)
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Manage", style=discord.ButtonStyle.primary, custom_id="manage", row=1)
    async def manage_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open management view for current campaign"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your campaign.", ephemeral=True)
            return
        
        current_campaign = self.campaigns[self.current_index]
        
        # Create comprehensive management view
        view = CampaignManagementView(self.module, current_campaign, interaction.user.id)
        embed = view.create_management_embed()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Edit", style=discord.ButtonStyle.secondary, custom_id="edit", row=1)
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open edit view for current campaign"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your campaign.", ephemeral=True)
            return
        
        current_campaign = self.campaigns[self.current_index]
        
        # Create edit menu view
        view = CampaignEditMenuView(self.module, current_campaign, interaction.user.id)
        embed = view.create_edit_menu_embed()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="📢 Announce", style=discord.ButtonStyle.success, custom_id="announce", row=1)
    async def announce_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Create public announcement for current campaign"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your campaign.", ephemeral=True)
            return
        
        current_campaign = self.campaigns[self.current_index]
        
        # Check if campaign is active
        if current_campaign.get('campaign_status') != 'active':
            await interaction.response.send_message(
                "⚠️ Only active campaigns can be announced. Please resume your campaign first.",
                ephemeral=True
            )
            return
        
        # Check if there are available slots
        if current_campaign.get('available_slots', 0) <= 0:
            await interaction.response.send_message(
                "⚠️ This campaign has no available slots. Consider increasing slots before announcing.",
                ephemeral=True
            )
            return
        
        # Create public announcement embed
        embed = self.create_public_announcement_embed(current_campaign)
        
        # Create view with Apply button for the public announcement
        view = PublicCampaignView(self.module, current_campaign)
        
        # Send as a new public message (not ephemeral)
        await interaction.response.send_message(
            content="📢 **New Shoutout Campaign Available!**",
            embed=embed,
            view=view,
            ephemeral=False  # Make it public
        )
    
    def create_public_announcement_embed(self, campaign: Dict) -> discord.Embed:
        """Create embed for public campaign announcement"""
        # Get creator Discord ID for mention
        creator_id = campaign.get('discord_user_id')
        creator_mention = f"<@{creator_id}>" if creator_id else campaign.get('author_name', 'Unknown')
        
        embed = discord.Embed(
            title=f"📖 {campaign.get('book_title', 'Unknown')}",
            description=f"by **{creator_mention}**",  # Now clickable Discord mention
            color=0x00A86B
        )
        
        # Add book URL if available
        book_url = campaign.get('book_url')
        if book_url:
            embed.add_field(
                name="📚 Book Link",
                value=f"[Read on {campaign.get('platform', 'Platform')}]({book_url})",
                inline=False
            )
        
        # Campaign details
        embed.add_field(
            name="Platform",
            value=campaign.get('platform', 'Unknown'),
            inline=True
        )
        
        available_slots = campaign.get('available_slots', 0)
        total_slots = campaign.get('total_slots', 0)
        embed.add_field(
            name="Available Slots",
            value=f"{available_slots}/{total_slots}",
            inline=True
        )
        
        embed.add_field(
            name="Campaign ID",
            value=f"#{campaign.get('id', 'Unknown')}",
            inline=True
        )
        
        # Add available dates
        available_dates = campaign.get('available_dates')
        if available_dates:
            try:
                # Try to parse as JSON if it's a string
                if isinstance(available_dates, str):
                    import json
                    dates_list = json.loads(available_dates)
                else:
                    dates_list = available_dates
                
                if isinstance(dates_list, list) and dates_list:
                    if len(dates_list) > 1:
                        dates_str = f"{dates_list[0]} (+{len(dates_list)-1} more dates)"
                    else:
                        dates_str = dates_list[0]
                    embed.add_field(
                        name="📅 Shoutout Dates Available",
                        value=dates_str,
                        inline=False
                    )
                elif isinstance(dates_list, str):
                    embed.add_field(
                        name="📅 Shoutout Dates Available",
                        value=dates_list,
                        inline=False
                    )
            except:
                # If parsing fails, just use as string
                if available_dates:
                    embed.add_field(
                        name="📅 Shoutout Dates Available",
                        value=available_dates,
                        inline=False
                    )
        
        # Add blurb if available
        blurb = campaign.get('blurb')
        if blurb:
            embed.add_field(
                name="About the Book",
                value=blurb[:500] if len(blurb) > 500 else blurb,
                inline=False
            )
        
        embed.add_field(
            name="How to Apply",
            value="Click the **Apply** button below to submit your application!",
            inline=False
        )
        
        return embed
    
    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary, custom_id="next", row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next campaign"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your campaign list.", ephemeral=True)
            return
        
        self.current_index = min(len(self.campaigns) - 1, self.current_index + 1)
        self.update_buttons()
        
        embed = self.module.create_my_campaigns_embed(
            self.campaigns[self.current_index],
            self.current_index,
            len(self.campaigns)
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    #@discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.secondary, custom_id="refresh", row=2)
    #async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
    #    """Refresh campaign data"""
    #    if interaction.user.id != self.user_id:
    #        await interaction.response.send_message("This is not your campaign list.", ephemeral=True)
    #        return
    #    
    #    await interaction.response.send_message("♻️ Refreshing campaigns...", ephemeral=True)


class CampaignManagementView(discord.ui.View):
    """View for managing a specific campaign (without announce button - moved to main view)"""
    
    def __init__(self, module: ShoutoutModule, campaign: Dict, user_id: int):
        super().__init__(timeout=600)
        self.module = module
        self.campaign = campaign
        self.user_id = user_id
    
    def create_management_embed(self) -> discord.Embed:
        """Create embed for campaign management options"""
        embed = discord.Embed(
            title=f"📚 Manage Campaign: {self.campaign.get('book_title', 'Unknown')}",
            description=f"Campaign ID: #{self.campaign.get('id', 'Unknown')}",
            color=0x3498db
        )
        
        # Campaign status
        status = self.campaign.get('campaign_status', 'unknown')
        embed.add_field(
            name="Status",
            value=f"**{status.title()}**",
            inline=True
        )
        
        # Slot management
        total_slots = self.campaign.get('total_slots', 0)
        available_slots = self.campaign.get('available_slots', 0)
        embed.add_field(
            name="Slots",
            value=f"{available_slots}/{total_slots} available",
            inline=True
        )
        
        # Application counts
        applications = self.campaign.get('applications', [])
        pending = len([a for a in applications if a.get('status') == 'pending'])
        approved = len([a for a in applications if a.get('status') == 'approved'])
        completed = len([a for a in applications if a.get('status') == 'completed'])
        
        embed.add_field(
            name="Applications",
            value=f"Pending: {pending}\nApproved: {approved}\nCompleted: {completed}",
            inline=False
        )
        
        # Management options
        embed.add_field(
            name="📋 Management Options",
            value=(
                "• **Review Applications** - Review pending applications\n"
                "• **Pause/Resume** - Temporarily pause or resume campaign\n"
                "• **View Approved** - See approved participants\n"
                "• **Complete Campaign** - Mark campaign as completed"
            ),
            inline=False
        )
        
        return embed
    
    @discord.ui.button(label="📋 Review Pending", style=discord.ButtonStyle.primary, row=0)
    async def review_pending_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Review pending applications"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot manage this campaign.", ephemeral=True)
            return
        
        pending_apps = [
            app for app in self.campaign.get('applications', [])
            if app.get('status') == 'pending'
        ]
        
        if not pending_apps:
            await interaction.response.send_message(
                "No pending applications to review.",
                ephemeral=True
            )
            return
        
        view = ApplicationReviewView(self.module, self.campaign, pending_apps, self.user_id)
        embed = view.create_application_embed(0)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="⏸️ Pause Campaign", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_status_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle campaign status between active and paused"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot manage this campaign.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Call API to toggle status
            data = {
                'bot_token': self.module.wp_bot_token,
                'discord_user_id': str(self.user_id)
            }
            
            url = f"{self.module.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns/{self.campaign['id']}/toggle-status"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.module.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with self.module.session.put(url, json=data, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    result = await response.json()
                    new_status = result.get('new_status', 'unknown')
                    
                    # Update button label
                    if new_status == 'paused':
                        button.label = "▶️ Resume Campaign"
                    else:
                        button.label = "⏸️ Pause Campaign"
                    
                    # Update campaign status locally
                    self.campaign['campaign_status'] = new_status
                    
                    # Update embed
                    embed = self.create_management_embed()
                    await interaction.followup.edit_message(
                        message_id=interaction.message.id,
                        embed=embed,
                        view=self
                    )
                    
                    await interaction.followup.send(
                        f"✅ Campaign {new_status}!",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "❌ Failed to update campaign status.",
                        ephemeral=True
                    )
                    
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error toggling campaign status: {e}")
            await interaction.followup.send(
                "❌ An error occurred while updating the campaign.",
                ephemeral=True
            )
    
    @discord.ui.button(label="✅ View Approved", style=discord.ButtonStyle.secondary, row=1)
    async def view_approved_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View approved applications"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot manage this campaign.", ephemeral=True)
            return
        
        approved_apps = [
            app for app in self.campaign.get('applications', [])
            if app.get('status') == 'approved'
        ]
        
        if not approved_apps:
            await interaction.response.send_message(
                "No approved applications yet.",
                ephemeral=True
            )
            return
        
        # Create embed showing approved participants
        embed = discord.Embed(
            title=f"✅ Approved Participants",
            description=f"Campaign: {self.campaign.get('book_title', 'Unknown')}",
            color=0x00A86B
        )
        
        for i, app in enumerate(approved_apps[:10], 1):
            discord_id = app.get('discord_user_id')
            user_display = f"<@{discord_id}>" if discord_id else app.get('discord_username', 'Unknown')
            book_data = app.get('participant_book_data', {})
            
            field_value = (
                f"**User:** {user_display}\n"
                f"**Book:** {book_data.get('book_title', 'Unknown')}\n"
            )
            
            if app.get('assigned_shout_date'):
                field_value += f"**Date:** {app['assigned_shout_date']}\n"
            if app.get('assigned_chapter'):
                field_value += f"**Chapter:** {app['assigned_chapter']}\n"
            
            embed.add_field(
                name=f"{i}. {book_data.get('book_title', 'Unknown')}",
                value=field_value,
                inline=False
            )
        
        if len(approved_apps) > 10:
            embed.set_footer(text=f"Showing 10 of {len(approved_apps)} approved participants")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🏁 Complete Campaign", style=discord.ButtonStyle.danger, row=1)
    async def complete_campaign_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Mark campaign as completed"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot manage this campaign.", ephemeral=True)
            return
        
        # Show confirmation
        embed = discord.Embed(
            title="⚠️ Complete Campaign?",
            description=(
                "This will mark your campaign as **completed** and:\n"
                "• Remove it from active listings\n"
                "• Prevent new applications\n"
                "• Keep existing participant data\n\n"
                "Are you sure you want to complete this campaign?"
            ),
            color=0xFFA500
        )
        
        # Create confirmation view
        view = CampaignCompleteConfirmView(self.module, self.campaign, self.user_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class CampaignEditMenuView(discord.ui.View):
    """Menu view for selecting what to edit in a campaign"""
    
    def __init__(self, module: ShoutoutModule, campaign: Dict, user_id: int):
        super().__init__(timeout=300)
        self.module = module
        self.campaign = campaign
        self.user_id = user_id
        logger.info(f"[SHOUTOUT_MODULE] CampaignEditMenuView initialized for campaign {campaign.get('id')} by user {user_id}")
    
    def create_edit_menu_embed(self) -> discord.Embed:
        """Create embed showing edit options"""
        embed = discord.Embed(
            title=f"📝 Edit Campaign: {self.campaign.get('book_title', 'Unknown')}",
            description=f"Campaign ID: #{self.campaign.get('id', 'Unknown')}\nSelect what you want to edit:",
            color=0x3498db
        )
        
        embed.add_field(
            name="📖 Book Details",
            value="Title, Author, URL, Platform, Blurb",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Campaign Settings",
            value="Available slots, auto-approve, mutual server requirement",
            inline=False
        )
        
        embed.add_field(
            name="✨ Shoutout Info",
            value="Shoutout code/URL, narrator, dates",
            inline=False
        )
        
        #embed.add_field(
        #    name="🌐 Server Visibility",
        #    value="Which servers can see this campaign",
        #    inline=False
        #)
        
        return embed
    
    @discord.ui.button(label="📖 Edit Book Details", style=discord.ButtonStyle.primary, row=0)
    async def edit_book_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open modal to edit book details"""
        logger.info(f"[SHOUTOUT_MODULE] Edit Book Details clicked by {interaction.user.id} for campaign {self.campaign.get('id')}")
        
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot edit this campaign.", ephemeral=True)
            return
        
        modal = EditBookDetailsModal(self.module, self.campaign)
        await interaction.response.send_modal(modal)
        logger.info(f"[SHOUTOUT_MODULE] Book details modal shown")
    
    @discord.ui.button(label="⚙️ Edit Settings", style=discord.ButtonStyle.primary, row=1)
    async def edit_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open modal to edit campaign settings"""
        logger.info(f"[SHOUTOUT_MODULE] Edit Settings clicked by {interaction.user.id} for campaign {self.campaign.get('id')}")
        
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot edit this campaign.", ephemeral=True)
            return
        
        modal = EditCampaignSettingsModal(self.module, self.campaign)
        await interaction.response.send_modal(modal)
        logger.info(f"[SHOUTOUT_MODULE] Settings modal shown")
    
    @discord.ui.button(label="✨ Edit Shoutout Info", style=discord.ButtonStyle.primary, row=2)
    async def edit_shoutout_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open modal to edit shoutout details"""
        logger.info(f"[SHOUTOUT_MODULE] Edit Shoutout Info clicked by {interaction.user.id} for campaign {self.campaign.get('id')}")
        
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot edit this campaign.", ephemeral=True)
            return
        
        modal = EditShoutoutDetailsModal(self.module, self.campaign)
        await interaction.response.send_modal(modal)
        logger.info(f"[SHOUTOUT_MODULE] Shoutout details modal shown")
    
# @discord.ui.button(label="🌐 Edit Server Visibility", style=discord.ButtonStyle.primary, row=3)
    # async def edit_servers_button(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     """Show server selection view instead of modal"""
    #     logger.info(f"[SHOUTOUT_MODULE] ========== EDIT SERVER VISIBILITY START ==========")
    #     logger.info(f"[SHOUTOUT_MODULE] Clicked by user {interaction.user.id} ({interaction.user.name}) for campaign {self.campaign.get('id')}")
    #     
    #     if interaction.user.id != self.user_id:
    #         logger.warning(f"[SHOUTOUT_MODULE] User {interaction.user.id} tried to edit campaign owned by {self.user_id}")
    #         await interaction.response.send_message("You cannot edit this campaign.", ephemeral=True)
    #         return
    #     
    #     # Get mutual servers (servers where both bot and user are members)
    #     try:
    #         # Log bot information
    #         logger.info(f"[SHOUTOUT_MODULE] Bot user: {self.module.bot.user.name} (ID: {self.module.bot.user.id})")
    #         logger.info(f"[SHOUTOUT_MODULE] Total guilds bot is in: {len(self.module.bot.guilds)}")
    #         
    #         # Log first 5 guilds the bot is in
    #         for i, guild in enumerate(self.module.bot.guilds[:5]):
    #             logger.info(f"[SHOUTOUT_MODULE] Bot guild {i+1}: {guild.name} (ID: {guild.id}, Members: {guild.member_count})")
    #         
    #         if len(self.module.bot.guilds) > 5:
    #             logger.info(f"[SHOUTOUT_MODULE] ... and {len(self.module.bot.guilds) - 5} more guilds")
    #         
    #         # Check if bot.guilds is properly populated
    #         if not self.module.bot.guilds:
    #             logger.error(f"[SHOUTOUT_MODULE] Bot.guilds is empty! Bot may not be fully initialized.")
    #             logger.info(f"[SHOUTOUT_MODULE] Bot ready state: {self.module.bot.is_ready()}")
    #             logger.info(f"[SHOUTOUT_MODULE] Bot closed state: {self.module.bot.is_closed()}")
    #         
    #         mutual_servers = []
    #         user_found_in_guilds = []
    #         user_not_found_in_guilds = []
    #         
    #         logger.info(f"[SHOUTOUT_MODULE] Starting mutual server search for user {interaction.user.id}")
    #         
    #         for guild in self.module.bot.guilds:
    #             try:
    #                 # Try multiple methods to find the member
    #                 member = None
    #                 
    #                 # Method 1: Direct get_member
    #                 member = guild.get_member(interaction.user.id)
    #                 
    #                 if member:
    #                     logger.info(f"[SHOUTOUT_MODULE] ✅ User FOUND in guild: {guild.name} (ID: {guild.id}) via get_member")
    #                     user_found_in_guilds.append(guild.name)
    #                     mutual_servers.append({
    #                         'id': str(guild.id),
    #                         'name': guild.name,
    #                         'member_count': guild.member_count
    #                     })
    #                 else:
    #                     # Method 2: Check if we need to fetch member
    #                     logger.debug(f"[SHOUTOUT_MODULE] User not found via get_member in {guild.name}, checking cache...")
    #                     
    #                     # Log cache status
    #                     if hasattr(guild, '_members'):
    #                         logger.debug(f"[SHOUTOUT_MODULE] Guild {guild.name} has {len(guild._members)} members in cache")
    #                     
    #                     # Try to check if user ID is in guild's member cache
    #                     if interaction.user.id in [m.id for m in guild.members]:
    #                         member = guild.get_member(interaction.user.id)
    #                         if member:
    #                             logger.info(f"[SHOUTOUT_MODULE] ✅ User FOUND in guild: {guild.name} (ID: {guild.id}) via members list")
    #                             user_found_in_guilds.append(guild.name)
    #                             mutual_servers.append({
    #                                 'id': str(guild.id),
    #                                 'name': guild.name,
    #                                 'member_count': guild.member_count
    #                             })
    #                     else:
    #                         logger.debug(f"[SHOUTOUT_MODULE] ❌ User NOT in guild: {guild.name} (ID: {guild.id})")
    #                         user_not_found_in_guilds.append(guild.name)
    #                 
    #             except Exception as e:
    #                 logger.error(f"[SHOUTOUT_MODULE] Error checking guild {guild.name}: {type(e).__name__}: {e}")
    #         
    #         # Log summary
    #         logger.info(f"[SHOUTOUT_MODULE] ========== MUTUAL SERVER SEARCH COMPLETE ==========")
    #         logger.info(f"[SHOUTOUT_MODULE] User found in {len(user_found_in_guilds)} guilds:")
    #         for guild_name in user_found_in_guilds[:10]:  # Log first 10
    #             logger.info(f"[SHOUTOUT_MODULE]   - {guild_name}")
    #         if len(user_found_in_guilds) > 10:
    #             logger.info(f"[SHOUTOUT_MODULE]   ... and {len(user_found_in_guilds) - 10} more")
    #         
    #         logger.info(f"[SHOUTOUT_MODULE] User NOT found in {len(user_not_found_in_guilds)} guilds")
    #         if len(user_not_found_in_guilds) <= 5:
    #             for guild_name in user_not_found_in_guilds:
    #                 logger.info(f"[SHOUTOUT_MODULE]   - {guild_name}")
    #         
    #         logger.info(f"[SHOUTOUT_MODULE] Total mutual servers found: {len(mutual_servers)}")
    #         
    #         if not mutual_servers:
    #             logger.warning(f"[SHOUTOUT_MODULE] No mutual servers found for user {interaction.user.id}")
    #             
    #             # Additional debugging info
    #             logger.info(f"[SHOUTOUT_MODULE] Debug info:")
    #             logger.info(f"[SHOUTOUT_MODULE] - Bot intents: {self.module.bot.intents}")
    #             logger.info(f"[SHOUTOUT_MODULE] - Members intent enabled: {self.module.bot.intents.members}")
    #             logger.info(f"[SHOUTOUT_MODULE] - Guilds intent enabled: {self.module.bot.intents.guilds}")
    #             logger.info(f"[SHOUTOUT_MODULE] - Presences intent enabled: {self.module.bot.intents.presences}")
    #             
    #             await interaction.response.send_message(
    #                 "❌ No mutual servers found. Make sure you're in servers where this bot is present.",
    #                 ephemeral=True
    #             )
    #             return
    #         
    #         # Create server selection view
    #         logger.info(f"[SHOUTOUT_MODULE] Creating ServerSelectionView with {len(mutual_servers)} servers")
    #         view = ServerSelectionView(self.module, self.campaign, mutual_servers, interaction.user.id)
    #         embed = view.create_server_selection_embed()
    #         await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    #         logger.info(f"[SHOUTOUT_MODULE] Server selection view shown successfully")
    #         
    #     except Exception as e:
    #         logger.error(f"[SHOUTOUT_MODULE] Unexpected error getting mutual servers: {type(e).__name__}: {e}")
    #         import traceback
    #         logger.error(f"[SHOUTOUT_MODULE] Traceback:\n{traceback.format_exc()}")
    #         
    #         await interaction.response.send_message(
    #             "❌ An error occurred while fetching server list.",
    #             ephemeral=True
    #         )
    #     finally:
    #         logger.info(f"[SHOUTOUT_MODULE] ========== EDIT SERVER VISIBILITY END ==========")
    
#    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary, row=4)
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary, row=3)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel editing"""
        logger.info(f"[SHOUTOUT_MODULE] Edit cancelled by {interaction.user.id} for campaign {self.campaign.get('id')}")
        await interaction.response.edit_message(
            content="Edit cancelled.",
            embed=None,
            view=None
        )
        
class EditBookDetailsModal(discord.ui.Modal, title="Edit Book Details"):
    """Modal for editing book details"""
    
    def __init__(self, module: ShoutoutModule, campaign: Dict):
        super().__init__()
        self.module = module
        self.campaign = campaign
        
        # Pre-fill with existing values
        self.book_title.default = campaign.get('book_title', '')
        self.author_name.default = campaign.get('author_name', '')
        self.book_url.default = campaign.get('book_url', '')
        self.platform.default = campaign.get('platform', '')
        self.blurb.default = campaign.get('blurb', '')
        
        logger.info(f"[SHOUTOUT_MODULE] EditBookDetailsModal initialized with campaign {campaign.get('id')}")
    
    book_title = discord.ui.TextInput(
        label="Book Title",
        placeholder="Enter your book's title",
        required=False,
        max_length=200
    )
    
    author_name = discord.ui.TextInput(
        label="Author Name",
        placeholder="Your pen name or author name",
        required=False,
        max_length=100
    )
    
    book_url = discord.ui.TextInput(
        label="Book URL",
        placeholder="https://www.royalroad.com/fiction/...",
        required=False,
        max_length=500
    )
    
    platform = discord.ui.TextInput(
        label="Platform",
        placeholder="Royal Road, Scribble Hub, Kindle, etc.",
        required=False,
        max_length=50
    )
    
    blurb = discord.ui.TextInput(
        label="Book Description/Blurb",
        placeholder="A brief description of your book",
        required=False,
        max_length=1000,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle book details update"""
        logger.info(f"[SHOUTOUT_MODULE] Book details form submitted for campaign {self.campaign.get('id')}")
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Validate book URL if provided
            if self.book_url.value:
                book_url = self.book_url.value.strip()
                if not (book_url.startswith('http://') or book_url.startswith('https://')):
                    await interaction.followup.send(
                        "❌ Book URL must start with http:// or https://",
                        ephemeral=True
                    )
                    return
                
                # Optional: Check for valid domain structure
                import re
                url_pattern = re.compile(
                    r'^https?://'  # http:// or https://
                    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                    r'localhost|'  # localhost...
                    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                    r'(?::\d+)?'  # optional port
                    r'(?:/?|[/?]\S+)$', re.IGNORECASE)
                
                if not url_pattern.match(book_url):
                    await interaction.followup.send(
                        "❌ Please enter a valid URL for your book",
                        ephemeral=True
                    )
                    return
            
            # Build update data (only include changed fields)
            update_data = {
                'bot_token': self.module.wp_bot_token
            }
            
            if self.book_title.value:
                update_data['book_title'] = self.book_title.value
                logger.info(f"[SHOUTOUT_MODULE] Updating book_title: {self.book_title.value}")
            if self.author_name.value:
                update_data['author_name'] = self.author_name.value
                logger.info(f"[SHOUTOUT_MODULE] Updating author_name: {self.author_name.value}")
            if self.book_url.value:
                update_data['book_url'] = self.book_url.value
                logger.info(f"[SHOUTOUT_MODULE] Updating book_url: {self.book_url.value}")
            if self.platform.value:
                update_data['platform'] = self.platform.value
                logger.info(f"[SHOUTOUT_MODULE] Updating platform: {self.platform.value}")
            if self.blurb.value:
                update_data['blurb'] = self.blurb.value
                logger.info(f"[SHOUTOUT_MODULE] Updating blurb (length: {len(self.blurb.value)})")
            
            # Only proceed if there's something to update
            if len(update_data) > 1:  # More than just bot_token
                url = f"{self.module.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns/{self.campaign['id']}/edit-book"
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.module.wp_bot_token}',
                    'User-Agent': 'Essence-Discord-Bot/1.0'
                }
                
                logger.info(f"[SHOUTOUT_MODULE] Sending PUT request to {url}")
                logger.info(f"[SHOUTOUT_MODULE] Update data fields: {list(update_data.keys())}")
                
                timeout = aiohttp.ClientTimeout(total=10)
                async with self.module.session.put(url, json=update_data, headers=headers, timeout=timeout) as response:
                    logger.info(f"[SHOUTOUT_MODULE] Response status: {response.status}")
                    
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"[SHOUTOUT_MODULE] Book details updated successfully: {result}")
                        await interaction.followup.send(
                            "✅ Book details updated successfully!",
                            ephemeral=True
                        )
                    else:
                        error_text = await response.text()
                        logger.error(f"[SHOUTOUT_MODULE] Failed to update book details. Status: {response.status}, Error: {error_text}")
                        await interaction.followup.send(
                            "❌ Failed to update book details",
                            ephemeral=True
                        )
            else:
                logger.info(f"[SHOUTOUT_MODULE] No changes made - all fields empty")
                await interaction.followup.send(
                    "ℹ️ No changes made.",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error updating book details: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[SHOUTOUT_MODULE] Traceback: {traceback.format_exc()}")
            await interaction.followup.send(
                "❌ An error occurred while updating book details",
                ephemeral=True
            )

class EditCampaignSettingsModal(discord.ui.Modal, title="Edit Campaign Settings"):
    """Modal for editing campaign settings including preferences"""
    
    def __init__(self, module: ShoutoutModule, campaign: Dict):
        super().__init__()
        self.module = module
        self.campaign = campaign
        
        # Pre-fill with existing values
        self.available_slots.default = str(campaign.get('total_slots', 1))
        
        # Parse campaign settings for auto_approve and require_mutual_server
        settings = campaign.get('campaign_settings', {})
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except:
                settings = {}
        
        self.auto_approve.default = "yes" if settings.get('auto_approve', False) else "no"
        self.require_mutual_server.default = "yes" if settings.get('require_mutual_server', False) else "no"
        
        logger.info(f"[SHOUTOUT_MODULE] EditCampaignSettingsModal initialized with campaign {campaign.get('id')}")
        logger.info(f"[SHOUTOUT_MODULE] Current settings: slots={self.available_slots.default}, auto_approve={self.auto_approve.default}, mutual_server={self.require_mutual_server.default}")
    
    available_slots = discord.ui.TextInput(
        label="Total Shoutout Slots",
        placeholder="How many shoutouts can you offer?",
        required=True,
        max_length=5
    )
    
    auto_approve = discord.ui.TextInput(
        label="Auto-Approve Applications",
        placeholder="Type 'yes' or 'no'",
        required=True,
        max_length=3
    )
    
    require_mutual_server = discord.ui.TextInput(
        label="Require Mutual Server",
        placeholder="Type 'yes' or 'no' - Require applicants to share a server with you?",
        required=True,
        max_length=3
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle settings update"""
        logger.info(f"[SHOUTOUT_MODULE] Settings form submitted for campaign {self.campaign.get('id')}")
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Validate slots
            try:
                slots = int(self.available_slots.value)
                if slots < 1:
                    logger.warning(f"[SHOUTOUT_MODULE] Invalid slots value: {slots}")
                    await interaction.followup.send(
                        "❌ You must offer at least 1 shoutout slot.",
                        ephemeral=True
                    )
                    return
                logger.info(f"[SHOUTOUT_MODULE] Slots validated: {slots}")
            except ValueError:
                logger.error(f"[SHOUTOUT_MODULE] Invalid slots value: {self.available_slots.value}")
                await interaction.followup.send(
                    "❌ Please enter a valid number for slots.",
                    ephemeral=True
                )
                return
            
            # Validate yes/no fields
            auto_approve_value = self.auto_approve.value.lower().strip()
            mutual_server_value = self.require_mutual_server.value.lower().strip()
            
            if auto_approve_value not in ['yes', 'no']:
                logger.warning(f"[SHOUTOUT_MODULE] Invalid auto_approve value: {auto_approve_value}")
                await interaction.followup.send(
                    "❌ Auto-approve must be 'yes' or 'no'",
                    ephemeral=True
                )
                return
            
            if mutual_server_value not in ['yes', 'no']:
                logger.warning(f"[SHOUTOUT_MODULE] Invalid require_mutual_server value: {mutual_server_value}")
                await interaction.followup.send(
                    "❌ Require mutual server must be 'yes' or 'no'",
                    ephemeral=True
                )
                return
            
            # Convert to boolean
            auto_approve_bool = auto_approve_value == 'yes'
            mutual_server_bool = mutual_server_value == 'yes'
            
            logger.info(f"[SHOUTOUT_MODULE] Settings parsed: auto_approve={auto_approve_bool}, mutual_server={mutual_server_bool}")
            
            # Update settings
            data = {
                'bot_token': self.module.wp_bot_token,
                'available_slots': slots,
                'campaign_settings': {
                    'auto_approve': auto_approve_bool,
                    'require_mutual_server': mutual_server_bool
                }
            }
            
            url = f"{self.module.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns/{self.campaign['id']}/edit-settings"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.module.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            logger.info(f"[SHOUTOUT_MODULE] Sending PUT request to {url}")
            logger.info(f"[SHOUTOUT_MODULE] Update data: {json.dumps(data, indent=2)}")
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with self.module.session.put(url, json=data, headers=headers, timeout=timeout) as response:
                logger.info(f"[SHOUTOUT_MODULE] Response status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"[SHOUTOUT_MODULE] Settings updated successfully: {result}")
                    
                    await interaction.followup.send(
                        f"✅ Campaign settings updated!\n"
                        f"• Total slots: {slots}\n"
                        f"• Auto-approve: {'Enabled' if auto_approve_bool else 'Disabled'}\n"
                        f"• Require mutual server: {'Yes' if mutual_server_bool else 'No'}",
                        ephemeral=True
                    )
                else:
                    error_text = await response.text()
                    logger.error(f"[SHOUTOUT_MODULE] Failed to update settings. Status: {response.status}, Error: {error_text}")
                    await interaction.followup.send(
                        "❌ Failed to update campaign settings.",
                        ephemeral=True
                    )
                    
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error updating settings: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[SHOUTOUT_MODULE] Traceback: {traceback.format_exc()}")
            await interaction.followup.send(
                "❌ An error occurred while updating settings.",
                ephemeral=True
            )

class EditShoutoutDetailsModal(discord.ui.Modal, title="Edit Shoutout Details"):
    """Modal for editing shoutout-specific details"""
    
    def __init__(self, module: ShoutoutModule, campaign: Dict):
        super().__init__()
        self.module = module
        self.campaign = campaign
        
        # Pre-fill with existing values if available
        self.shoutout_code.default = campaign.get('shoutout_code', '')
        self.narrator.default = campaign.get('narrator', '')
        self.publication_date.default = campaign.get('publication_date', '')
        self.available_dates.default = campaign.get('available_dates', '')
        
        logger.info(f"[SHOUTOUT_MODULE] EditShoutoutDetailsModal initialized with campaign {campaign.get('id')}")
    
    shoutout_code = discord.ui.TextInput(
        label="Your Shoutout Code's URL",
        placeholder="https://docs.google.com/... (Get code: finitevoid.dev/shoutout)",
        required=False,
        max_length=500
    )
    
    narrator = discord.ui.TextInput(
        label="Narrator (for Audiobooks)",
        placeholder="Narrator name if applicable",
        required=False,
        max_length=200
    )
    
    publication_date = discord.ui.TextInput(
        label="Publication Date",
        placeholder="YYYY-MM-DD",
        required=False,
        max_length=10
    )
    
    available_dates = discord.ui.TextInput(
        label="Available Shoutout Dates",
        placeholder="When can you post shoutouts? (e.g., Mondays, after Ch 50)",
        required=False,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle shoutout details update"""
        logger.info(f"[SHOUTOUT_MODULE] Shoutout details form submitted for campaign {self.campaign.get('id')}")
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Validate shoutout code URL if provided
            if self.shoutout_code.value:
                shoutout_url = self.shoutout_code.value.strip()
                if not (shoutout_url.startswith('http://') or shoutout_url.startswith('https://')):
                    await interaction.followup.send(
                        "❌ Shoutout code URL must start with http:// or https://",
                        ephemeral=True
                    )
                    return
                
                # Optional: Check for valid domain structure
                import re
                url_pattern = re.compile(
                    r'^https?://'  # http:// or https://
                    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                    r'localhost|'  # localhost...
                    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                    r'(?::\d+)?'  # optional port
                    r'(?:/?|[/?]\S+)$', re.IGNORECASE)
                
                if not url_pattern.match(shoutout_url):
                    await interaction.followup.send(
                        "❌ Please enter a valid URL for your shoutout code",
                        ephemeral=True
                    )
                    return
            
            # Build update data
            update_data = {
                'bot_token': self.module.wp_bot_token
            }
            
            if self.shoutout_code.value:
                update_data['shoutout_code'] = self.shoutout_code.value
                logger.info(f"[SHOUTOUT_MODULE] Updating shoutout_code: {self.shoutout_code.value}")
            if self.narrator.value:
                update_data['narrator'] = self.narrator.value
                logger.info(f"[SHOUTOUT_MODULE] Updating narrator: {self.narrator.value}")
            if self.publication_date.value:
                # Validate date format
                import re
                if not re.match(r'^\d{4}-\d{2}-\d{2}$', self.publication_date.value):
                    logger.warning(f"[SHOUTOUT_MODULE] Invalid date format: {self.publication_date.value}")
                    await interaction.followup.send(
                        "❌ Invalid date format. Please use YYYY-MM-DD",
                        ephemeral=True
                    )
                    return
                update_data['publication_date'] = self.publication_date.value
                logger.info(f"[SHOUTOUT_MODULE] Updating publication_date: {self.publication_date.value}")
            if self.available_dates.value:
                update_data['available_dates'] = self.available_dates.value
                logger.info(f"[SHOUTOUT_MODULE] Updating available_dates: {self.available_dates.value}")
            
            if len(update_data) > 1:  # More than just bot_token
                url = f"{self.module.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns/{self.campaign['id']}/edit-shoutout"
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.module.wp_bot_token}',
                    'User-Agent': 'Essence-Discord-Bot/1.0'
                }
                
                logger.info(f"[SHOUTOUT_MODULE] Sending PUT request to {url}")
                logger.info(f"[SHOUTOUT_MODULE] Update data fields: {list(update_data.keys())}")
                
                timeout = aiohttp.ClientTimeout(total=10)
                async with self.module.session.put(url, json=update_data, headers=headers, timeout=timeout) as response:
                    logger.info(f"[SHOUTOUT_MODULE] Response status: {response.status}")
                    
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"[SHOUTOUT_MODULE] Shoutout details updated successfully: {result}")
                        await interaction.followup.send(
                            "✅ Shoutout details updated successfully!",
                            ephemeral=True
                        )
                    else:
                        error_text = await response.text()
                        logger.error(f"[SHOUTOUT_MODULE] Failed to update shoutout details. Status: {response.status}, Error: {error_text}")
                        await interaction.followup.send(
                            "❌ Failed to update shoutout details",
                            ephemeral=True
                        )
            else:
                logger.info(f"[SHOUTOUT_MODULE] No changes made - all fields empty")
                await interaction.followup.send(
                    "ℹ️ No changes made.",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error updating shoutout details: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[SHOUTOUT_MODULE] Traceback: {traceback.format_exc()}")
            await interaction.followup.send(
                "❌ An error occurred while updating shoutout details",
                ephemeral=True
            )

class ServerSelectionView(discord.ui.View):
    """View for selecting which servers can see the campaign"""
    
    def __init__(self, module: ShoutoutModule, campaign: Dict, mutual_servers: List[Dict], user_id: int):
        super().__init__(timeout=300)
        self.module = module
        self.campaign = campaign
        self.mutual_servers = mutual_servers
        self.user_id = user_id
        
        # Parse current allowed servers
        allowed_servers = campaign.get('allowed_servers')
        if allowed_servers:
            try:
                if isinstance(allowed_servers, str):
                    self.selected_servers = set(json.loads(allowed_servers))
                else:
                    self.selected_servers = set(allowed_servers)
            except:
                self.selected_servers = set()
        else:
            self.selected_servers = set()
        
        logger.info(f"[SHOUTOUT_MODULE] ServerSelectionView initialized with {len(mutual_servers)} servers")
        logger.info(f"[SHOUTOUT_MODULE] Currently selected servers: {self.selected_servers}")
        
        # Create dropdown
        self.add_item(ServerSelectDropdown(self.mutual_servers, self.selected_servers))
    
    def create_server_selection_embed(self) -> discord.Embed:
        """Create embed for server selection"""
        embed = discord.Embed(
            title="🌐 Edit Server Visibility",
            description=(
                "Select which servers can see your campaign.\n"
                "• **No selection** = Campaign visible in all servers\n"
                "• **Select servers** = Campaign only visible in selected servers\n\n"
                f"Found **{len(self.mutual_servers)}** mutual servers."
            ),
            color=0x3498db
        )
        
        if self.selected_servers:
            selected_names = []
            for server_id in self.selected_servers:
                server = next((s for s in self.mutual_servers if s['id'] == server_id), None)
                if server:
                    selected_names.append(server['name'])
            
            if selected_names:
                embed.add_field(
                    name="Currently Selected",
                    value="\n".join(f"• {name}" for name in selected_names[:10]),
                    inline=False
                )
                if len(selected_names) > 10:
                    embed.set_footer(text=f"And {len(selected_names) - 10} more...")
        else:
            embed.add_field(
                name="Currently Selected",
                value="None (visible in all servers)",
                inline=False
            )
        
        return embed
    
    @discord.ui.button(label="💾 Save Changes", style=discord.ButtonStyle.success, row=4)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Save selected servers"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot edit this campaign.", ephemeral=True)
            return
        
        logger.info(f"[SHOUTOUT_MODULE] Saving server visibility for campaign {self.campaign.get('id')}")
        logger.info(f"[SHOUTOUT_MODULE] Selected servers: {self.selected_servers}")
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Prepare data
            if self.selected_servers:
                allowed_servers = json.dumps(list(self.selected_servers))
            else:
                allowed_servers = None
            
            data = {
                'bot_token': self.module.wp_bot_token,
                'allowed_servers': allowed_servers
            }
            
            url = f"{self.module.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns/{self.campaign['id']}/edit-servers"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.module.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            logger.info(f"[SHOUTOUT_MODULE] Sending PUT request to {url}")
            logger.info(f"[SHOUTOUT_MODULE] Allowed servers data: {allowed_servers}")
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with self.module.session.put(url, json=data, headers=headers, timeout=timeout) as response:
                logger.info(f"[SHOUTOUT_MODULE] Response status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"[SHOUTOUT_MODULE] Server visibility updated successfully: {result}")
                    
                    if self.selected_servers:
                        await interaction.followup.send(
                            f"✅ Server visibility updated! Campaign visible to {len(self.selected_servers)} server(s).",
                            ephemeral=True
                        )
                    else:
                        await interaction.followup.send(
                            "✅ Server visibility updated! Campaign visible to all servers.",
                            ephemeral=True
                        )
                else:
                    error_text = await response.text()
                    logger.error(f"[SHOUTOUT_MODULE] Failed to update server visibility. Status: {response.status}, Error: {error_text}")
                    await interaction.followup.send(
                        "❌ Failed to update server visibility.",
                        ephemeral=True
                    )
                    
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error updating server visibility: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[SHOUTOUT_MODULE] Traceback: {traceback.format_exc()}")
            await interaction.followup.send(
                "❌ An error occurred while updating server visibility.",
                ephemeral=True
            )
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary, row=4)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel server selection"""
        logger.info(f"[SHOUTOUT_MODULE] Server selection cancelled for campaign {self.campaign.get('id')}")
        await interaction.response.edit_message(
            content="Server selection cancelled.",
            embed=None,
            view=None
        )


class ServerSelectDropdown(discord.ui.Select):
    """Dropdown for selecting servers"""
    
    def __init__(self, mutual_servers: List[Dict], selected_servers: set):
        self.mutual_servers = mutual_servers
        self.parent_view = None  # Will be set when added to view
        
        # Create options (max 25 for Discord)
        options = []
        for server in mutual_servers[:24]:  # Leave room for "Clear All" option
            options.append(
                discord.SelectOption(
                    label=server['name'][:100],  # Discord max label length
                    value=server['id'],
                    description=f"{server['member_count']} members",
                    default=server['id'] in selected_servers
                )
            )
        
        # Add clear all option
        options.append(
            discord.SelectOption(
                label="🗑️ Clear All Selections",
                value="CLEAR_ALL",
                description="Make campaign visible in all servers",
                emoji="🗑️"
            )
        )
        
        super().__init__(
            placeholder=f"Select servers ({len(selected_servers)} selected)",
            min_values=0,
            max_values=len(options),
            options=options
        )
        
        logger.info(f"[SHOUTOUT_MODULE] ServerSelectDropdown created with {len(options)} options")
    
    async def callback(self, interaction: discord.Interaction):
        """Handle server selection"""
        if not self.view:
            await interaction.response.send_message("Error: View not properly initialized", ephemeral=True)
            return
        
        if interaction.user.id != self.view.user_id:
            await interaction.response.send_message("You cannot edit this selection.", ephemeral=True)
            return
        
        logger.info(f"[SHOUTOUT_MODULE] Server selection changed. Selected values: {self.values}")
        
        # Check if clear all was selected
        if "CLEAR_ALL" in self.values:
            self.view.selected_servers.clear()
            logger.info(f"[SHOUTOUT_MODULE] Cleared all server selections")
        else:
            self.view.selected_servers = set(self.values)
            logger.info(f"[SHOUTOUT_MODULE] Updated selected servers: {self.view.selected_servers}")
        
        # Update the embed
        embed = self.view.create_server_selection_embed()
        await interaction.response.edit_message(embed=embed, view=self.view)
        
class EditServerVisibilityModal(discord.ui.Modal, title="Edit Server Visibility"):
    """Modal for editing which servers can see the campaign"""
    
    def __init__(self, module: ShoutoutModule, campaign: Dict):
        super().__init__()
        self.module = module
        self.campaign = campaign
        
        # Pre-fill with existing values
        allowed_servers = campaign.get('allowed_servers')
        if allowed_servers:
            try:
                servers_list = json.loads(allowed_servers) if isinstance(allowed_servers, str) else allowed_servers
                self.server_ids.default = ', '.join(servers_list) if isinstance(servers_list, list) else ''
            except:
                self.server_ids.default = ''
    
    server_ids = discord.ui.TextInput(
        label="Allowed Server IDs",
        placeholder="Leave empty for all servers, or enter comma-separated server IDs",
        required=False,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle server visibility update"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Parse server IDs
            if self.server_ids.value:
                # Split by comma and clean up
                server_list = [s.strip() for s in self.server_ids.value.split(',') if s.strip()]
                # Validate they look like Discord IDs (numeric strings)
                for server_id in server_list:
                    if not server_id.isdigit():
                        await interaction.followup.send(
                            f"❌ Invalid server ID: {server_id}. Server IDs should be numeric.",
                            ephemeral=True
                        )
                        return
                
                allowed_servers = json.dumps(server_list)
            else:
                # Empty means visible to all
                allowed_servers = None
            
            data = {
                'bot_token': self.module.wp_bot_token,
                'allowed_servers': allowed_servers
            }
            
            url = f"{self.module.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns/{self.campaign['id']}/edit-servers"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.module.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with self.module.session.put(url, json=data, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    if allowed_servers:
                        await interaction.followup.send(
                            f"✅ Server visibility updated! Campaign visible to {len(server_list)} server(s).",
                            ephemeral=True
                        )
                    else:
                        await interaction.followup.send(
                            "✅ Server visibility updated! Campaign visible to all servers.",
                            ephemeral=True
                        )
                else:
                    await interaction.followup.send(
                        "❌ Failed to update server visibility.",
                        ephemeral=True
                    )
                    
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error updating server visibility: {e}")
            await interaction.followup.send(
                "❌ An error occurred while updating server visibility.",
                ephemeral=True
            )

class PublicCampaignView(discord.ui.View):
    def __init__(self, module: ShoutoutModule, campaign: Dict):
        super().__init__(timeout=900)  # 15 minutes
        self.module = module
        self.campaign = campaign
        self.campaign_id = campaign.get('id')
        
        # Add a "refresh" button alongside Apply
        refresh_button = discord.ui.Button(
            label="🔄 Refresh",
            style=discord.ButtonStyle.secondary,
            custom_id="refresh_campaign"
        )
        refresh_button.callback = self.refresh_button_callback
        self.add_item(refresh_button)
    
    async def refresh_button_callback(self, interaction: discord.Interaction):
        """Provide fresh buttons"""
        await interaction.response.send_message(
            f"To get a fresh application button, use:\n"
            f"`/shoutout-view-details {self.campaign_id}`\n\n"
            f"Or apply directly with:\n"
            f"`/shoutout-apply {self.campaign_id}`",
            ephemeral=True
        )
    
    @discord.ui.button(label="📝 Apply to the Campaign", style=discord.ButtonStyle.primary, custom_id="apply_public")
    async def apply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show application modal when Apply is clicked"""
        # Check if user is trying to apply to their own campaign
        campaign_creator_id = self.campaign.get('discord_user_id')
        if campaign_creator_id and str(interaction.user.id) == str(campaign_creator_id):
            await interaction.response.send_message(
                "❌ You cannot apply to your own campaign!",
                ephemeral=True
            )
            return
        
        # Check if campaign is still active and has slots
        if self.campaign.get('available_slots', 0) <= 0:
            await interaction.response.send_message(
                "❌ This campaign has no available slots.",
                ephemeral=True
            )
            return
        
        # Use the unified application modal
        modal = ApplicationModal(self.module, self.campaign_id, self.campaign)
        await interaction.response.send_modal(modal)
    
    #@discord.ui.button(label="📊 View Details", style=discord.ButtonStyle.secondary, custom_id="view_details")
    #async def details_button(self, interaction: discord.Interaction, button: discord.ui.Button):
    #    """Show detailed campaign information"""
    #    embed = discord.Embed(
    #        title=f"Campaign Details: {self.campaign.get('book_title', 'Unknown')}",
    #        color=0x3498db
    #    )
    #    
    #    # Add all campaign details
    #    embed.add_field(
    #        name="Campaign Creator",
    #        value=f"<@{self.campaign.get('discord_user_id')}>" if self.campaign.get('discord_user_id') else self.campaign.get('discord_username', 'Unknown'),
    #        inline=True
    #    )
    #    
    #    embed.add_field(
    #        name="Campaign ID",
    #        value=f"#{self.campaign_id}",
    #        inline=True
    #    )
    #    
    #    embed.add_field(
    #        name="Status",
    #        value=self.campaign.get('campaign_status', 'active').title(),
    #        inline=True
    #    )
    #    
    #    # Add instructions
    #    embed.add_field(
    #        name="How Shoutout Swaps Work",
    #        value=(
    #            "1. Apply with your book details\n"
    #            "2. If approved, exchange shoutouts with the campaign creator\n"
    #            "3. Both authors promote each other's books\n"
    #            "4. Track progress with `/shoutout-my-applications`"
    #        ),
    #        inline=False
    #    )
    #    
    #    await interaction.response.send_message(embed=embed, ephemeral=True)


class CampaignCompleteConfirmView(discord.ui.View):
    """Confirmation view for completing a campaign"""
    
    def __init__(self, module: ShoutoutModule, campaign: Dict, user_id: int):
        super().__init__(timeout=60)
        self.module = module
        self.campaign = campaign
        self.user_id = user_id
    
    @discord.ui.button(label="✅ Yes, Complete", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm campaign completion"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot complete this campaign.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Update campaign status to completed
            data = {
                'bot_token': self.module.wp_bot_token,
                'discord_user_id': str(self.user_id)
            }
            
            # First, change status to completed
            self.campaign['campaign_status'] = 'completed'
            
            url = f"{self.module.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns/{self.campaign['id']}/toggle-status"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.module.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                content="✅ Campaign marked as completed!",
                embed=None,
                view=None
            )
            
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error completing campaign: {e}")
            await interaction.followup.send(
                "❌ Failed to complete campaign.",
                ephemeral=True
            )
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel completion"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your action.", ephemeral=True)
            return
        
        await interaction.response.edit_message(
            content="Campaign completion cancelled.",
            embed=None,
            view=None
        )


class ApplicationReviewView(discord.ui.View):
    """View for reviewing and managing applications"""
    
    def __init__(self, module: ShoutoutModule, campaign: Dict, applications: List[Dict], user_id: int):
        super().__init__(timeout=600)
        self.module = module
        self.campaign = campaign
        self.applications = applications
        self.user_id = user_id
        self.current_index = 0
        self.update_buttons()
    
    def create_application_embed(self, index: int) -> discord.Embed:
        """Create embed for a single application with book stats and shoutout code"""
        app = self.applications[index]
        book_data = app.get('participant_book_data', {})
        
        embed = discord.Embed(
            title=f"Application {index + 1}/{len(self.applications)}",
            description=f"For campaign: **{self.campaign.get('book_title')}**",
            color=0x3498db
        )
        
        # Make applicant clickable
        applicant_id = app.get('discord_user_id')
        if applicant_id:
            applicant_mention = f"<@{applicant_id}>"
            embed.add_field(
                name="Applicant",
                value=f"{applicant_mention}\n({app.get('discord_username', 'Unknown')})",
                inline=True
            )
        else:
            embed.add_field(
                name="Applicant",
                value=app.get('discord_username', 'Unknown'),
                inline=True
            )
        
        embed.add_field(
            name="Book Title",
            value=f"[{book_data.get('book_title', 'Unknown')}]({book_data.get('book_url', '#')})",
            inline=True
        )
        embed.add_field(
            name="Author",
            value=book_data.get('author_name', 'Unknown'),
            inline=True
        )
        embed.add_field(
            name="Platform",
            value=book_data.get('platform', 'Unknown'),
            inline=True
        )
        
        # Show shoutout code if provided
        if book_data.get('shoutout_code'):
            shoutout_url = book_data['shoutout_code']
            # Truncate for display but keep URL intact
            if len(shoutout_url) > 50:
                display_text = shoutout_url[:50] + "..."
                embed.add_field(
                    name="✨ Shoutout Code Provided",
                    value=f"[{display_text}]({shoutout_url})",
                    inline=False
                )
            else:
                embed.add_field(
                    name="✨ Shoutout Code Provided",
                    value=shoutout_url,
                    inline=False
                )
        
        # Add book stats if available
        if app.get('book_stats'):
            stats = app['book_stats']
            stats_text = []
            if stats.get('followers') is not None:
                # Convert followers to int if it's a string, then format with comma separator
                try:
                    followers_count = int(stats['followers']) if isinstance(stats['followers'], str) else stats['followers']
                    stats_text.append(f"**Followers:** {followers_count:,}")
                except (ValueError, TypeError):
                    # If conversion fails, just display as-is
                    stats_text.append(f"**Followers:** {stats['followers']}")
                    
            if stats.get('rating'):
                try:
                    rating_value = float(stats['rating']) if isinstance(stats['rating'], str) else stats['rating']
                    stats_text.append(f"**Rating:** ⭐ {rating_value:.1f}/5")
                except (ValueError, TypeError):
                    stats_text.append(f"**Rating:** ⭐ {stats['rating']}/5")
                    
            if stats.get('launch_date'):
                stats_text.append(f"**Launched:** {stats['launch_date']}")
            
            if stats_text:
                embed.add_field(
                    name="Book Statistics",
                    value="\n".join(stats_text),
                    inline=False
                )
            
            if stats.get('shared_tags'):
                tags_list = ", ".join(stats['shared_tags'][:5])
                if len(stats['shared_tags']) > 5:
                    tags_list += f" (+{len(stats['shared_tags']) - 5} more)"
                embed.add_field(
                    name="Shared Tags with Your Book",
                    value=tags_list,
                    inline=False
                )
        
        if book_data.get('pitch'):
            embed.add_field(
                name="Pitch",
                value=book_data.get('pitch', 'No pitch provided')[:500],
                inline=False
            )
        
        if book_data.get('notes'):
            embed.add_field(
                name="Additional Notes",
                value=book_data.get('notes')[:300],
                inline=False
            )
        
        embed.add_field(
            name="Applied",
            value=app.get('application_date', 'Unknown'),
            inline=True
        )
        
        embed.set_footer(text=f"Application ID: {app.get('id', 'Unknown')}")
        
        return embed
    
    def update_buttons(self):
        """Update button states"""
        self.previous_button.disabled = self.current_index == 0
        self.next_button.disabled = self.current_index >= len(self.applications) - 1
    
    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot review these applications.", ephemeral=True)
            return
        
        self.current_index = max(0, self.current_index - 1)
        self.update_buttons()
        embed = self.create_application_embed(self.current_index)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.success)
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot approve this application.", ephemeral=True)
            return
        
        if self.current_index >= len(self.applications):
            await interaction.response.send_message("This application has already been processed.", ephemeral=True)
            return
        
        app = self.applications[self.current_index]
        # Show modal for optional date/chapter assignment
        modal = ApproveApplicationModal(self, app)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.danger)
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot decline this application.", ephemeral=True)
            return
        
        if self.current_index >= len(self.applications):
            await interaction.response.send_message("This application has already been processed.", ephemeral=True)
            return
        
        app = self.applications[self.current_index]
        # Show modal for decline reason
        modal = DeclineReasonModal(self, app)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot review these applications.", ephemeral=True)
            return
        
        self.current_index = min(len(self.applications) - 1, self.current_index + 1)
        self.update_buttons()
        embed = self.create_application_embed(self.current_index)
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def update_application_status(self, interaction: discord.Interaction, app_id: int, status: str, 
                                       decline_reason: str = None, shout_date: str = None, chapter: str = None):
        """Update application status via API and notify applicant"""
        try:
            # Defer the response first
            if not interaction.response.is_done():
                await interaction.response.defer()
            
            data = {
                'bot_token': self.module.wp_bot_token,
                'status': status,
                'campaign_creator_id': str(interaction.user.id),
                'decline_reason': decline_reason,
                'assigned_shout_date': shout_date,
                'assigned_chapter': chapter
            }
            
            url = f"{self.module.wp_api_url}/wp-json/rr-analytics/v1/shoutout/applications/{app_id}/status"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.module.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with self.module.session.put(url, json=data, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    # Get the application data before removing it
                    if self.current_index < len(self.applications):
                        current_app = self.applications[self.current_index]
                        
                        # Send notification with rate limiting
                        await self.notify_applicant(current_app, status, decline_reason, shout_date, chapter)
                        
                        # Add a small delay if processing multiple applications
                        if len(self.applications) > 1:
                            await asyncio.sleep(1)  # 1 second delay between processing
                        
                        # Remove the application from the list
                        self.applications.pop(self.current_index)
                    
                    if not self.applications:
                        await interaction.followup.edit_message(
                            message_id=interaction.message.id,
                            content="✅ All applications reviewed!",
                            embed=None,
                            view=None
                        )
                    else:
                        self.current_index = min(self.current_index, len(self.applications) - 1)
                        self.update_buttons()
                        embed = self.create_application_embed(self.current_index)
                        
                        await interaction.followup.edit_message(
                            message_id=interaction.message.id,
                            content=f"✅ Application {status}! Notification sent to applicant.",
                            embed=embed,
                            view=self
                        )
                else:
                    await interaction.followup.send(
                        f"❌ Failed to update application status.",
                        ephemeral=True
                    )
                    
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error updating application: {e}")
            try:
                await interaction.followup.send(
                    "❌ An error occurred while updating the application.",
                    ephemeral=True
                )
            except:
                pass
    
    async def notify_applicant(self, application: Dict, status: str, decline_reason: str = None, 
                              shout_date: str = None, chapter: str = None):
        """Send notification to applicant about their application status"""
        try:
            # Get applicant's Discord ID
            applicant_id = application.get('discord_user_id')
            if not applicant_id:
                logger.error(f"[SHOUTOUT_MODULE] No Discord ID for applicant")
                return
            
            # Create notification embed based on status
            if status == 'approved':
                embed = discord.Embed(
                    title="🎉 Application Approved!",
                    description=f"Your application to **{self.campaign.get('book_title')}** has been approved!",
                    color=0x00A86B
                )
                
                # Get campaign creator's Discord ID for mention
                creator_id = self.campaign.get('discord_user_id')
                creator_mention = f"<@{creator_id}>" if creator_id else self.campaign.get('discord_username', 'Unknown')
                
                # Make book title a link if URL exists
                book_url = self.campaign.get('book_url')
                book_title = self.campaign.get('book_title', 'Unknown')
                if book_url:
                    book_display = f"[{book_title}]({book_url})"
                else:
                    book_display = book_title
                
                embed.add_field(
                    name="Campaign Details",
                    value=(
                        f"**Book:** {book_display}\n"
                        f"**Author:** {creator_mention}\n"
                        f"**Platform:** {self.campaign.get('platform', 'Unknown')}"
                    ),
                    inline=False
                )
                
                # Show shoutout code if applicant provided one
                book_data = application.get('participant_book_data', {})
                if book_data.get('shoutout_code'):
                    embed.add_field(
                        name="✅ Your Shoutout Code",
                        value=f"You provided: {book_data['shoutout_code']}",
                        inline=False
                    )
                
                # Add schedule info if provided
                if shout_date or chapter:
                    schedule_info = []
                    if shout_date:
                        schedule_info.append(f"**Date:** {shout_date}")
                    if chapter:
                        schedule_info.append(f"**Chapter:** {chapter}")
                    
                    embed.add_field(
                        name="📅 Shoutout Schedule",
                        value="\n".join(schedule_info),
                        inline=False
                    )
                
                embed.add_field(
                    name="Next Steps",
                    value=(
                        "• The campaign creator will contact you with shoutout details\n"
                        "• Coordinate the timing and placement of your shoutouts\n"
                        "• Make sure to fulfill your shoutout commitment\n"
                        "• Use `/shoutout-my-applications` to track all your applications"
                    ),
                    inline=False
                )
            else:  # declined
                embed = discord.Embed(
                    title="📋 Application Update",
                    description=f"Your application to **{self.campaign.get('book_title')}** was not accepted.",
                    color=0xFFA500
                )
                
                if decline_reason:
                    embed.add_field(
                        name="Feedback from Campaign Creator",
                        value=decline_reason,
                        inline=False
                    )
                
                embed.add_field(
                    name="Don't Give Up!",
                    value=(
                        "• Browse other campaigns with `/shoutout-browse`\n"
                        "• Consider creating your own campaign\n"
                        "• Keep writing and trying!"
                    ),
                    inline=False
                )
                
                embed.add_field(
                    name="Track Your Applications",
                    value="Use `/shoutout-my-applications` to see all your applications and their statuses",
                    inline=False
                )
            
            embed.set_footer(text=f"Campaign ID: #{self.campaign.get('id', 'Unknown')}")
            
            # Use rate-limited DM sending
            await self.module.send_dm_with_ratelimit(int(applicant_id), embed)
            
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error notifying applicant: {e}")


class ApplicationConfirmView(discord.ui.View):
    """Unified view for confirming application to a campaign"""
    
    def __init__(self, module: ShoutoutModule, campaign_id: int, campaign: Dict):
        super().__init__(timeout=300)
        self.module = module
        self.campaign_id = campaign_id
        self.campaign = campaign
    
    @discord.ui.button(label="📝 Apply Now", style=discord.ButtonStyle.primary)
    async def apply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show application modal"""
        # Check if user is trying to apply to their own campaign
        campaign_creator_id = self.campaign.get('discord_user_id')
        if campaign_creator_id and str(interaction.user.id) == str(campaign_creator_id):
            await interaction.response.send_message(
                "❌ You cannot apply to your own campaign!",
                ephemeral=True
            )
            return
        
        modal = ApplicationModal(self.module, self.campaign_id, self.campaign)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel application"""
        await interaction.response.edit_message(
            content="Application cancelled.",
            embed=None,
            view=None
        )


class ApplicationModal(discord.ui.Modal, title="Shoutout Application"):
    """Unified modal for submitting application with optional shoutout code"""
    
    book_title = discord.ui.TextInput(
        label="Your Book Title",
        placeholder="Enter your book's title",
        required=True,
        max_length=200
    )
    
    author_name = discord.ui.TextInput(
        label="Author Name",
        placeholder="Your pen name or author name",
        required=True,
        max_length=100
    )
    
    book_url = discord.ui.TextInput(
        label="Book URL",
        placeholder="",
        required=True,
        max_length=500
    )
    
    shoutout_code = discord.ui.TextInput(
        label="Your Shoutout Code's URL",
        placeholder="https://docs.google.com/... (Get code: finitevoid.dev/shoutout)",
        required=False,
        max_length=500
    )
    
    pitch = discord.ui.TextInput(
        label="Why do you want to exchange shoutouts?",
        placeholder="Brief pitch about your book and why you're a good match",
        required=True,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, module: ShoutoutModule, campaign_id: int, campaign: Dict):
        super().__init__()
        self.module = module
        self.campaign_id = campaign_id
        self.campaign = campaign
        
        # Set the placeholder based on campaign platform
        platform = campaign.get('platform', 'Unknown')
        self.book_url.placeholder = f"Link to your book on {platform}"
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle application submission"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Validate book URL
            book_url = self.book_url.value.strip()
            if not (book_url.startswith('http://') or book_url.startswith('https://')):
                await interaction.followup.send(
                    "❌ Book URL must start with http:// or https://",
                    ephemeral=True
                )
                return
            
            # Validate URL format
            import re
            url_pattern = re.compile(
                r'^https?://'
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
                r'localhost|'
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
                r'(?::\d+)?'
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            
            if not url_pattern.match(book_url):
                await interaction.followup.send(
                    "❌ Please enter a valid URL for your book",
                    ephemeral=True
                )
                return
            
            # Check if user already applied with THIS SPECIFIC BOOK
            # First, get campaign details to check existing applications
            check_params = {
                'bot_token': self.module.wp_bot_token,
                'discord_user_id': str(interaction.user.id),
                'check_book_url': book_url  # Pass the book URL to check
            }
            
            check_url = f"{self.module.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns/{self.campaign_id}/details"
            headers = {
                'Authorization': f'Bearer {self.module.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with self.module.session.get(check_url, params=check_params, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    campaign_check = await response.json()
                    if campaign_check.get('already_applied'):
                        await interaction.followup.send(
                            f"❌ You have already applied to this campaign with the book: **{self.book_title.value}**\n"
                            "You can apply with a different book if you have one.",
                            ephemeral=True
                        )
                        return
            
            # Validate shoutout code URL if provided
            if self.shoutout_code.value:
                shoutout_url = self.shoutout_code.value.strip()
                if not (shoutout_url.startswith('http://') or shoutout_url.startswith('https://')):
                    await interaction.followup.send(
                        "❌ Shoutout code URL must start with http:// or https://",
                        ephemeral=True
                    )
                    return
                
                if not url_pattern.match(shoutout_url):
                    await interaction.followup.send(
                        "❌ Please enter a valid URL for your shoutout code",
                        ephemeral=True
                    )
                    return
            
            # Rest of the submission code remains the same...
            participant_book_data = {
                'book_title': self.book_title.value,
                'author_name': self.author_name.value,
                'book_url': book_url,
                'platform': self.campaign.get('platform'),
                'pitch': self.pitch.value,
                'shoutout_code': self.shoutout_code.value if self.shoutout_code.value else None,
                'notes': None
            }
            
            data = {
                'bot_token': self.module.wp_bot_token,
                'campaign_id': self.campaign_id,
                'discord_user_id': str(interaction.user.id),
                'discord_username': f"{interaction.user.name}#{interaction.user.discriminator}",
                'participant_book_data': participant_book_data
            }
            
            # Single API call - let the backend handle duplicate checking
            url = f"{self.module.wp_api_url}/wp-json/rr-analytics/v1/shoutout/applications"
            headers = {
                'Authorization': f'Bearer {self.module.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with self.module.session.post(url, json=data, headers=headers, timeout=timeout) as response:
                result = await response.json()
                
                if response.status == 200 and result.get('success'):
                    # Success handling...
                    embed = discord.Embed(
                        title="✅ Application Submitted!",
                        description=f"Your application for **{self.campaign.get('book_title')}** has been submitted",
                        color=0x00A86B
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    
                    # Notify creator with rate limiting
                    await self.notify_campaign_creator(interaction)
                    
                elif response.status == 400:
                    error_msg = result.get('message', 'Invalid application')
                    # Check if it's a duplicate book error
                    if 'already applied' in error_msg.lower() and 'book' in error_msg.lower():
                        await interaction.followup.send(
                            f"❌ You have already applied to this campaign with **{self.book_title.value}**\n"
                            "You can apply with a different book if you have one.",
                            ephemeral=True
                        )
                    else:
                        await interaction.followup.send(f"❌ {error_msg}", ephemeral=True)
                else:
                    await interaction.followup.send(
                        "❌ Failed to submit application. Please try again",
                        ephemeral=True
                    )
                    
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error submitting application: {e}")
            await interaction.followup.send(
                "❌ An error occurred while submitting your application",
                ephemeral=True
            )
    
    async def notify_campaign_creator(self, interaction: discord.Interaction):
        """Send DM notification to campaign creator about new application"""
        try:
            creator_id = self.campaign.get('discord_user_id')
            if not creator_id:
                return
            
            embed = discord.Embed(
                title="📬 New Shoutout Application!",
                description=f"Someone applied to your campaign: **{self.campaign.get('book_title')}**",
                color=0x3498db
            )
            embed.add_field(
                name="Applicant",
                value=f"{interaction.user.name}#{interaction.user.discriminator}",
                inline=True
            )
            embed.add_field(
                name="Their Book",
                value=self.book_title.value,
                inline=True
            )
            
            if self.shoutout_code.value:
                embed.add_field(
                    name="✨ Shoutout Code Provided",
                    value="The applicant has already provided their shoutout location!",
                    inline=False
                )
            
            embed.add_field(
                name="Review Applications",
                value="Use `/shoutout-my-campaigns` to review and manage applications",
                inline=False
            )
            
            await self.module.send_dm_with_ratelimit(int(creator_id), embed)
            
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error notifying creator: {e}")


class ApproveApplicationModal(discord.ui.Modal, title="Approve Application"):
    """Modal for approving application with optional date/chapter assignment"""
    
    shout_date = discord.ui.TextInput(
        label="Shoutout Date (Optional)",
        placeholder="YYYY-MM-DD (e.g., 2024-12-25)",
        required=False,
        max_length=10,
        min_length=10
    )
    
    chapter = discord.ui.TextInput(
        label="Assigned Chapter (Optional)",
        placeholder="e.g., Chapter 5, End of Book 1, Author's Note",
        required=False,
        max_length=200
    )
    
    notes = discord.ui.TextInput(
        label="Additional Instructions (Optional)",
        placeholder="Any special instructions for the shoutout",
        required=False,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, review_view: ApplicationReviewView, application: Dict):
        super().__init__()
        self.review_view = review_view
        self.application = application
        
        # Add helper text to date field
        import datetime
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        self.shout_date.placeholder = f"YYYY-MM-DD (e.g., {tomorrow})"
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle approval with optional scheduling"""
        # Validate date format if provided
        formatted_date = None
        if self.shout_date.value:
            try:
                # Parse the date to validate format
                import datetime
                date_obj = datetime.datetime.strptime(self.shout_date.value, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%Y-%m-%d')
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid date format. Please use YYYY-MM-DD (e.g., 2024-12-25)",
                    ephemeral=True
                )
                return
        
        await self.review_view.update_application_status(
            interaction,
            self.application.get('id'),
            'approved',
            None,
            formatted_date,
            self.chapter.value if self.chapter.value else None
        )


class DeclineReasonModal(discord.ui.Modal, title="Decline Application"):
    """Modal for providing optional reason when declining an application"""
    
    reason = discord.ui.TextInput(
        label="Reason for Declining (Optional)",
        placeholder="Provide feedback to help the applicant improve (optional)",
        required=False,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, review_view: ApplicationReviewView, application: Dict):
        super().__init__()
        self.review_view = review_view
        self.application = application
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle decline with optional reason"""
        reason_text = self.reason.value if self.reason.value else None
        await self.review_view.update_application_status(
            interaction, 
            self.application.get('id'), 
            'declined',
            reason_text,
            None,
            None
        )


class MyApplicationsView(discord.ui.View):
    """View for navigating through user's applications to other campaigns"""
    
    def __init__(self, module: ShoutoutModule, applications: List[Dict], user_id: int, filter_status: str):
        super().__init__(timeout=600)
        self.module = module
        self.applications = applications
        self.user_id = user_id
        self.filter_status = filter_status
        self.current_index = 0
        self.update_buttons()
    
    def create_application_embed(self, index: int) -> discord.Embed:
        """Create embed for a single application"""
        app = self.applications[index]
        
        # Determine color based on status
        status_colors = {
            'pending': 0xFFA500,
            'approved': 0x00A86B,
            'declined': 0xFF6B6B,
            'completed': 0x3498DB
        }
        
        embed = discord.Embed(
            title=f"Application {index + 1}/{len(self.applications)}",
            description=f"Campaign: **{app.get('campaign_book_title', 'Unknown')}**",
            color=status_colors.get(app.get('status', 'pending'), 0x808080)
        )
        
        # Campaign info
        embed.add_field(
            name="Campaign Author",
            value=app.get('campaign_creator', 'Unknown'),
            inline=True
        )
        
        embed.add_field(
            name="Platform",
            value=app.get('campaign_platform', 'Unknown'),
            inline=True
        )
        
        # Application status
        status = app.get('status', 'pending')
        status_display = {
            'pending': '⏳ Pending Review',
            'approved': '✅ Approved',
            'declined': '❌ Declined',
            'completed': '🏁 Completed'
        }
        
        embed.add_field(
            name="Status",
            value=status_display.get(status, status.title()),
            inline=True
        )
        
        # Your book details
        participant_data = app.get('participant_book_data', {})
        embed.add_field(
            name="Your Book",
            value=f"**{participant_data.get('book_title', 'Unknown')}**\nby {participant_data.get('author_name', 'Unknown')}",
            inline=False
        )
        
        # Show your shoutout code if provided
        if participant_data.get('shoutout_code'):
            embed.add_field(
                name="Your Shoutout Code",
                value=participant_data['shoutout_code'],
                inline=False
            )
        
        # If approved, show assignment details and campaign creator's shoutout code
        if status == 'approved':
            if app.get('assigned_shout_date') or app.get('assigned_chapter'):
                assignment_info = []
                if app.get('assigned_shout_date'):
                    assignment_info.append(f"📅 **Date:** {app['assigned_shout_date']}")
                if app.get('assigned_chapter'):
                    assignment_info.append(f"📖 **Chapter:** {app['assigned_chapter']}")
                
                embed.add_field(
                    name="Shoutout Assignment",
                    value="\n".join(assignment_info),
                    inline=False
                )
            
            # Show campaign creator's shoutout code if available
            if app.get('creator_shoutout_code'):
                embed.add_field(
                    name="Campaign Creator's Shoutout Location",
                    value=app['creator_shoutout_code'],
                    inline=False
                )
        
        # If declined, show reason if available
        elif status == 'declined' and app.get('notes'):
            embed.add_field(
                name="Feedback",
                value=app['notes'],
                inline=False
            )
        
        # Application date
        embed.add_field(
            name="Applied",
            value=app.get('application_date', 'Unknown'),
            inline=True
        )
        
        embed.set_footer(text=f"Application ID: {app.get('id', 'Unknown')}")
        
        return embed
    
    def update_buttons(self):
        """Update button states based on current index"""
        self.previous_button.disabled = self.current_index == 0
        self.next_button.disabled = self.current_index >= len(self.applications) - 1
    
    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous application"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your application list.", ephemeral=True)
            return
        
        self.current_index = max(0, self.current_index - 1)
        self.update_buttons()
        embed = self.create_application_embed(self.current_index)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next application"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your application list.", ephemeral=True)
            return
        
        self.current_index = min(len(self.applications) - 1, self.current_index + 1)
        self.update_buttons()
        embed = self.create_application_embed(self.current_index)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.secondary)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh application data"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your application list.", ephemeral=True)
            return
        
        await interaction.response.send_message("♻️ Refreshing applications...", ephemeral=True)
