"""
Discord Bot Shoutout Swap System Module - Fixed Version
Modular extension for the existing Discord Essence Bot
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
logger = logging.getLogger('discord')  # Use the same logger as discord.py

class ShoutoutModule:
    """
    Modular shoutout swap system for Discord bot
    Handles campaign creation, browsing, and application management
    """
    
    def __init__(self, bot: commands.Bot, session: aiohttp.ClientSession, wp_api_url: str, wp_bot_token: str, tag_autocomplete_func=None):
        self.bot = bot
        self.session = session
        self.wp_api_url = wp_api_url
        self.wp_bot_token = wp_bot_token
        self.tag_autocomplete = tag_autocomplete_func

        # Use logger instead of print
        logger.info(f"[SHOUTOUT_MODULE] Initializing...")
        logger.info(f"[SHOUTOUT_MODULE] bot: {bot}")
        logger.info(f"[SHOUTOUT_MODULE] wp_api_url: {wp_api_url}")
        logger.info(f"[SHOUTOUT_MODULE] wp_bot_token: {'[SET]' if wp_bot_token else '[NOT SET]'}")
        
        # Register commands immediately
        self.register_commands()
        logger.info(f"[SHOUTOUT_MODULE] Commands registered")
    
    def register_commands(self):
        """Register all shoutout-related commands with the bot"""
        
        # Create campaign creation command - works everywhere
        @self.bot.tree.command(name="shoutout-campaign-create", description="Create a new shoutout campaign")
        async def shoutout_campaign_create(interaction: discord.Interaction):
            """Create a new shoutout campaign - works anywhere"""
            await self.handle_campaign_create(interaction)
        
        # Browse campaigns command
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
            # Call the handler method directly
            await self.handle_browse_campaigns(
                interaction, genre, platform, min_followers, max_followers, server_only
            )
    
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
                'server_name': server_name,  # Add server name
                'check_tier_only': True  # Just checking tier first
            }
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns"
            
            # Log the request details
            logger.info(f"[SHOUTOUT_MODULE] API URL: {url}")
            logger.info(f"[SHOUTOUT_MODULE] Request data: {json.dumps({k: v if k != 'bot_token' else '[hidden]' for k, v in data.items()})}")
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            logger.info(f"[SHOUTOUT_MODULE] Making POST request to WordPress API...")
            
            # Set a timeout for the API request
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with self.session.post(url, json=data, headers=headers, timeout=timeout) as response:
                # Log response details
                logger.info(f"[SHOUTOUT_MODULE] Response status: {response.status}")
                
                response_text = await response.text()
                logger.info(f"[SHOUTOUT_MODULE] Response body (first 500 chars): {response_text[:500]}")
                
                # Try to parse JSON
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
                    # User doesn't have access or error
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
        # Defer immediately to avoid timeout
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


class CampaignCreationView(discord.ui.View):
    """View for campaign creation workflow"""
    
    def __init__(self, module: ShoutoutModule, user_id: int, user_tier: str):
        super().__init__(timeout=300)  # 5 minute timeout
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


class BookDetailsModal(discord.ui.Modal, title="Book Details"):
    """Modal for entering book details - rest of the class continues as before..."""
    
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
            # Log the values received
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
            
            # Get server ID and name if in a guild (for DMs, they will be None)
            if interaction.guild:
                server_id = str(interaction.guild.id)
                server_name = interaction.guild.name
                logger.info(f"[SHOUTOUT_MODULE] Server ID: {server_id}")
                logger.info(f"[SHOUTOUT_MODULE] Server Name: {server_name}")
            else:
                server_id = None
                server_name = None
                logger.info(f"[SHOUTOUT_MODULE] No server (DM)")
            
            # Get username in the correct format
            discord_username = f"{interaction.user.name}#{interaction.user.discriminator}"
            logger.info(f"[SHOUTOUT_MODULE] Discord username: {discord_username}")
            
            # Create campaign via API with ALL book data
            data = {
                'bot_token': self.module.wp_bot_token,
                'discord_user_id': str(interaction.user.id),
                'discord_username': discord_username,
                # Book data from modal
                'book_title': self.book_title.value,
                'book_url': self.book_url.value,
                'platform': self.platform.value,
                'author_name': self.author_name.value,
                'available_slots': slots,
                # Server info - including name
                'server_id': server_id,
                'server_name': server_name,  # Add server name
                # Campaign settings
                'campaign_settings': {
                    'auto_approve': False,
                    'require_mutual_server': False
                }
            }
            
            # Log what we're sending (hide token)
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
            
            # Make the API request
            timeout = aiohttp.ClientTimeout(total=10)
            async with self.module.session.post(url, json=data, headers=headers, timeout=timeout) as response:
                logger.info(f"[SHOUTOUT_MODULE] Response status: {response.status}")
                response_text = await response.text()
                logger.info(f"[SHOUTOUT_MODULE] Response text (first 500): {response_text[:500]}")
                
                # Try to parse JSON response
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
                
                # Handle response based on status
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
                        value=self.platform.value.title(),  # Display with title case
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
