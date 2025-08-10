"""
Discord Bot Shoutout Swap System Module - Complete Enhanced Version
Modular extension for the existing Discord Essence Bot
Preserves all original functionality and adds new commands
"""

import discord
from discord.ext import commands
import aiohttp
import json
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import logging

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
        
        # Register commands immediately
        self.register_commands()
        logger.info(f"[SHOUTOUT_MODULE] All commands registered")
    
    def register_commands(self):
        """Register all shoutout-related commands with the bot"""
        
        # ORIGINAL: Create campaign command - works everywhere
        @self.bot.tree.command(name="shoutout-campaign-create", description="Create a new shoutout campaign")
        async def shoutout_campaign_create(interaction: discord.Interaction):
            """Create a new shoutout campaign - works anywhere"""
            await self.handle_campaign_create(interaction)
        
        # ORIGINAL: Browse campaigns command
        @self.bot.tree.command(name="shoutout-browse", description="Browse available shoutout campaigns")
        @discord.app_commands.describe(
            genre="Filter by genre",
            platform="Filter by platform (Royal Road, Scribble Hub, Kindle, Audible, etc.)",
            min_followers="Minimum follower count",
            max_followers="Maximum follower count",
            server_only="Show only campaigns from this server"
        )
        async def shoutout_browse(
            interaction: discord.Interaction,
            genre: Optional[str] = None,
            platform: Optional[str] = None,
            min_followers: Optional[int] = None,
            max_followers: Optional[int] = None,
            server_only: Optional[bool] = False
        ):
            await self.handle_browse_campaigns(
                interaction, genre, platform, min_followers, max_followers, server_only
            )
        
        # NEW: My campaigns command - DMs only
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
        
        # NEW: Apply to campaign command
        @self.bot.tree.command(name="shoutout-apply", description="Apply to a specific shoutout campaign")
        @discord.app_commands.describe(
            campaign_id="The ID of the campaign to apply to"
        )
        async def shoutout_apply(
            interaction: discord.Interaction,
            campaign_id: int
        ):
            await self.handle_apply_to_campaign(interaction, campaign_id)
    
    # ORIGINAL METHOD - PRESERVED EXACTLY
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
    
    # ORIGINAL METHOD - PRESERVED EXACTLY
    async def handle_browse_campaigns(
        self,
        interaction: discord.Interaction,
        genre: Optional[str] = None,
        platform: Optional[str] = None,
        min_followers: Optional[int] = None,
        max_followers: Optional[int] = None,
        server_only: Optional[bool] = False
    ):
        """Handle browsing campaigns with filters"""
        try:
            await interaction.response.defer()
            logger.info(f"[SHOUTOUT_MODULE] Browse campaigns - deferred response")
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Failed to defer browse response: {e}")
            return
        
        logger.info(f"[SHOUTOUT_MODULE] Browse campaigns called by {interaction.user.id}")
        
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
                params['server_only'] = True
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns"
            headers = {
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            logger.info(f"[SHOUTOUT_MODULE] Fetching campaigns from: {url}")
            
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
    
    # ORIGINAL METHOD - PRESERVED EXACTLY
    def create_campaign_list_embed(self, campaigns: List[Dict]) -> discord.Embed:
        """Create embed showing list of campaigns"""
        embed = discord.Embed(
            title="📚 Available Shoutout Campaigns",
            description=f"Found {len(campaigns)} campaign(s)",
            color=0x00A86B
        )
        
        for i, campaign in enumerate(campaigns[:10]):  # Show max 10
            field_value = (
                f"**Author:** {campaign.get('author_name', 'Unknown')}\n"
                f"**Platform:** {campaign.get('platform', 'Unknown')}\n"
                f"**Slots:** {campaign.get('available_slots', 0)}\n"
                f"[View Book]({campaign.get('book_url', '#')})"
            )
            
            embed.add_field(
                name=f"{i+1}. {campaign.get('book_title', 'Unknown Book')}",
                value=field_value,
                inline=False
            )
        
        if len(campaigns) > 10:
            embed.add_field(
                name="More campaigns available",
                value=f"Showing 10 of {len(campaigns)} campaigns. Use filters to narrow results.",
                inline=False
            )
        
        embed.set_footer(text="Use /shoutout-campaign-details [id] to see full details")
        
        return embed
    
    # NEW METHOD: Handle my campaigns
    async def handle_my_campaigns(self, interaction: discord.Interaction, filter_status: str = "active"):
        """Handle viewing and managing user's own campaigns"""
        # DMs only for privacy
        if interaction.guild is not None:
            await interaction.response.send_message(
                "⚠️ This command only works in DMs for privacy. Please send me a direct message!",
                ephemeral=True
            )
            return
        
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
    
    # NEW METHOD: Handle apply to campaign
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
                    
                    # Add confirmation view
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
    
    # NEW METHOD: Create my campaigns embed
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
        
        # List pending applications (first 5)
        if pending > 0:
            pending_apps = [a for a in applications if a.get('status') == 'pending'][:5]
            app_list = []
            for app in pending_apps:
                app_list.append(f"• {app.get('discord_username', 'Unknown')} - {app.get('book_title', 'Unknown')}")
            
            embed.add_field(
                name="Recent Pending Applications",
                value="\n".join(app_list),
                inline=False
            )
            
            if pending > 5:
                embed.set_footer(text=f"And {pending - 5} more pending applications...")
        
        return embed


# ORIGINAL CLASS - PRESERVED WITH MODIFICATIONS
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
        
        modal = BookDetailsModal(self.module)
        await interaction.response.send_modal(modal)
        logger.info(f"[SHOUTOUT_MODULE] Book details modal sent to user {interaction.user.id}")


# ORIGINAL CLASS - PRESERVED EXACTLY
class BookDetailsModal(discord.ui.Modal, title="Book Details"):
    """Modal for entering book details"""
    
    book_title = discord.ui.TextInput(
        label="Book Title",
        placeholder="Enter your book's title",
        required=True,
        max_length=200
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
    
    author_name = discord.ui.TextInput(
        label="Author Name",
        placeholder="Your pen name or author name",
        required=True,
        max_length=100
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
        logger.info(f"[SHOUTOUT_MODULE] BookDetailsModal initialized")
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission - properly send all book data"""
        logger.info(f"[SHOUTOUT_MODULE] ========== MODAL SUBMIT START ==========")
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
                    "❌ Please enter a valid number for slots.",
                    ephemeral=True
                )
                return
                
            if slots < 1:
                logger.error(f"[SHOUTOUT_MODULE] Slots less than 1: {slots}")
                await interaction.followup.send(
                    "❌ You must offer at least 1 shoutout slot.",
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
                'book_url': self.book_url.value,
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
                        "❌ Server returned invalid response. Please try again.",
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
                        value=f"[View Book]({self.book_url.value})",
                        inline=False
                    )
                    embed.add_field(
                        name="Next Steps",
                        value=(
                            "• Your campaign is now live\n"
                            "• Use `/shoutout-my-campaigns` to manage applications\n"
                            "• Share your campaign ID with potential participants"
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
            logger.info(f"[SHOUTOUT_MODULE] ========== MODAL SUBMIT END ==========")


# NEW CLASSES for enhanced functionality
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
            self.manage_button.label = f"Manage Campaign #{current_campaign.get('id', '?')}"
    
    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary, custom_id="prev")
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
    
    @discord.ui.button(label="Manage Campaign", style=discord.ButtonStyle.primary, custom_id="manage")
    async def manage_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open management view for current campaign"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your campaign.", ephemeral=True)
            return
        
        current_campaign = self.campaigns[self.current_index]
        applications = current_campaign.get('applications', [])
        pending_apps = [a for a in applications if a.get('status') == 'pending']
        
        if not pending_apps:
            await interaction.response.send_message(
                "No pending applications to review for this campaign.",
                ephemeral=True
            )
            return
        
        view = ApplicationReviewView(self.module, current_campaign, pending_apps, interaction.user.id)
        embed = view.create_application_embed(0)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary, custom_id="next")
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
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.secondary, custom_id="refresh")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh campaign data"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your campaign list.", ephemeral=True)
            return
        
        await interaction.response.send_message("♻️ Refreshing campaigns...", ephemeral=True)


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
        """Create embed for a single application"""
        app = self.applications[index]
        book_data = app.get('participant_book_data', {})
        
        embed = discord.Embed(
            title=f"Application {index + 1}/{len(self.applications)}",
            description=f"For campaign: **{self.campaign.get('book_title')}**",
            color=0x3498db
        )
        
        embed.add_field(
            name="Applicant",
            value=app.get('discord_username', 'Unknown'),
            inline=True
        )
        embed.add_field(
            name="Book Title",
            value=book_data.get('book_title', 'Unknown'),
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
        embed.add_field(
            name="Book URL",
            value=f"[View Book]({book_data.get('book_url', '#')})",
            inline=False
        )
        
        if book_data.get('pitch'):
            embed.add_field(
                name="Pitch",
                value=book_data.get('pitch', 'No pitch provided')[:500],
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
        
        app = self.applications[self.current_index]
        await self.update_application_status(interaction, app.get('id'), 'approved')
    
    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.danger)
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot decline this application.", ephemeral=True)
            return
        
        app = self.applications[self.current_index]
        await self.update_application_status(interaction, app.get('id'), 'declined')
    
    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot review these applications.", ephemeral=True)
            return
        
        self.current_index = min(len(self.applications) - 1, self.current_index + 1)
        self.update_buttons()
        embed = self.create_application_embed(self.current_index)
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def update_application_status(self, interaction: discord.Interaction, app_id: int, status: str):
        """Update application status via API"""
        try:
            data = {
                'bot_token': self.module.wp_bot_token,
                'status': status,
                'campaign_creator_id': str(interaction.user.id)
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
                    self.applications.pop(self.current_index)
                    
                    if not self.applications:
                        await interaction.response.edit_message(
                            content="✅ All applications reviewed!",
                            embed=None,
                            view=None
                        )
                    else:
                        self.current_index = min(self.current_index, len(self.applications) - 1)
                        self.update_buttons()
                        embed = self.create_application_embed(self.current_index)
                        
                        await interaction.response.edit_message(
                            content=f"✅ Application {status}!",
                            embed=embed,
                            view=self
                        )
                else:
                    await interaction.response.send_message(
                        f"❌ Failed to update application status.",
                        ephemeral=True
                    )
                    
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error updating application: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while updating the application.",
                ephemeral=True
            )


class ApplicationConfirmView(discord.ui.View):
    """View for confirming application to a campaign"""
    
    def __init__(self, module: ShoutoutModule, campaign_id: int, campaign: Dict):
        super().__init__(timeout=300)
        self.module = module
        self.campaign_id = campaign_id
        self.campaign = campaign
    
    @discord.ui.button(label="📝 Apply Now", style=discord.ButtonStyle.primary)
    async def apply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show application modal"""
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
    """Modal for submitting application details"""
    
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
        placeholder="Link to your book on the same platform",
        required=True,
        max_length=500
    )
    
    pitch = discord.ui.TextInput(
        label="Why do you want to exchange shoutouts?",
        placeholder="Brief pitch about your book and why you're a good match",
        required=True,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    notes = discord.ui.TextInput(
        label="Additional Notes (Optional)",
        placeholder="Any additional information for the campaign creator",
        required=False,
        max_length=300,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, module: ShoutoutModule, campaign_id: int, campaign: Dict):
        super().__init__()
        self.module = module
        self.campaign_id = campaign_id
        self.campaign = campaign
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle application submission"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            participant_book_data = {
                'book_title': self.book_title.value,
                'author_name': self.author_name.value,
                'book_url': self.book_url.value,
                'platform': self.campaign.get('platform'),
                'pitch': self.pitch.value,
                'notes': self.notes.value if self.notes.value else None
            }
            
            data = {
                'bot_token': self.module.wp_bot_token,
                'campaign_id': self.campaign_id,
                'discord_user_id': str(interaction.user.id),
                'discord_username': f"{interaction.user.name}#{interaction.user.discriminator}",
                'participant_book_data': participant_book_data
            }
            
            url = f"{self.module.wp_api_url}/wp-json/rr-analytics/v1/shoutout/applications"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.module.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with self.module.session.post(url, json=data, headers=headers, timeout=timeout) as response:
                result = await response.json()
                
                if response.status == 200 and result.get('success'):
                    embed = discord.Embed(
                        title="✅ Application Submitted!",
                        description=f"Your application for **{self.campaign.get('book_title')}** has been submitted.",
                        color=0x00A86B
                    )
                    embed.add_field(
                        name="What's Next?",
                        value=(
                            "• The campaign creator will review your application\n"
                            "• You'll receive a DM when your application is reviewed\n"
                            "• Use `/shoutout-my-applications` to track your applications"
                        ),
                        inline=False
                    )
                    embed.add_field(
                        name="Your Book",
                        value=f"**{self.book_title.value}**\nby {self.author_name.value}",
                        inline=False
                    )
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    await self.notify_campaign_creator(interaction)
                    
                elif response.status == 400:
                    error_msg = result.get('message', 'Invalid application')
                    await interaction.followup.send(f"❌ {error_msg}", ephemeral=True)
                else:
                    await interaction.followup.send(
                        "❌ Failed to submit application. Please try again.",
                        ephemeral=True
                    )
                    
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error submitting application: {e}")
            await interaction.followup.send(
                "❌ An error occurred while submitting your application.",
                ephemeral=True
            )
    
    async def notify_campaign_creator(self, interaction: discord.Interaction):
        """Send DM notification to campaign creator about new application"""
        try:
            creator_id = self.campaign.get('discord_user_id')
            if not creator_id:
                return
            
            try:
                creator = await self.module.bot.fetch_user(int(creator_id))
            except:
                logger.error(f"[SHOUTOUT_MODULE] Could not find creator with ID {creator_id}")
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
            embed.add_field(
                name="Review Applications",
                value="Use `/shoutout-my-campaigns` to review and manage applications",
                inline=False
            )
            
            try:
                await creator.send(embed=embed)
            except discord.Forbidden:
                logger.info(f"[SHOUTOUT_MODULE] Could not DM creator {creator_id} - DMs disabled")
                
        except Exception as e:
            logger.error(f"[SHOUTOUT_MODULE] Error notifying creator: {e}")
