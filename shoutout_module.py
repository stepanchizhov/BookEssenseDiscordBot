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

logger = logging.getLogger(__name__)

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
        # Remove the get_user_info_func parameter as we'll handle this directly

        print(f"[SHOUTOUT_MODULE] bot {bot}")
        print(f"[SHOUTOUT_MODULE] session {session}")
        print(f"[SHOUTOUT_MODULE] wp_api_url {wp_api_url}")
        print(f"[SHOUTOUT_MODULE] wp_bot_token {wp_bot_token}")
        
        # Register commands immediately
        self.register_commands()
    
    def register_commands(self):
        """Register all shoutout-related commands with the bot"""
        
        # Create campaign creation command
        @self.bot.tree.command(name="shoutout-campaign-create", description="Create a new shoutout campaign (DM only)")
        async def shoutout_campaign_create(interaction: discord.Interaction):
            """Create a new shoutout campaign - only works in DMs"""
            # Check if in DM BEFORE deferring to respond faster
            if interaction.guild is not None:
                try:
                    await interaction.response.send_message(
                        "❌ Campaign creation only works in DMs for privacy. Please send me a direct message and try again!",
                        ephemeral=True
                    )
                except:
                    pass  # If interaction expired, just ignore
                return
            
            # Now handle the actual campaign creation
            await self.handle_campaign_create(interaction)
        
        # Browse campaigns command
        @self.bot.tree.command(name="shoutout-browse", description="Browse available shoutout campaigns")
        @discord.app_commands.describe(
            genre="Filter by genre",
            platform="Filter by platform (royal road, scribble hub, kindle, etc.)",
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
            await self.shoutout_browse(
                interaction, genre, platform, min_followers, max_followers, server_only
            )
    
    async def shoutout_browse(
        self, 
        interaction: discord.Interaction,
        genre: Optional[str] = None,
        platform: Optional[str] = None, 
        min_followers: Optional[int] = None,
        max_followers: Optional[int] = None,
        server_only: Optional[bool] = False
    ):
        """Browse available shoutout campaigns"""
        await self.handle_browse_campaigns(
            interaction, genre, platform, min_followers, max_followers, server_only
        )
    
    async def handle_campaign_create(self, interaction: discord.Interaction):
        """Handle campaign creation workflow"""
        # Try to defer immediately, but handle the case where it might fail
        try:
            await interaction.response.defer(ephemeral=True)
            deferred = True
        except discord.errors.NotFound:
            # Interaction already expired, we can't do anything
            print(f"[SHOUTOUT_MODULE] Interaction expired before defer")
            return
        except Exception as e:
            print(f"[SHOUTOUT_MODULE] Error deferring: {e}")
            deferred = False

        print(f"[SHOUTOUT_MODULE] ========== CAMPAIGN CREATE START ==========")
        print(f"[SHOUTOUT_MODULE] User ID: {interaction.user.id}")
        print(f"[SHOUTOUT_MODULE] User Name: {interaction.user.name}")
        print(f"[SHOUTOUT_MODULE] Discriminator: {interaction.user.discriminator}")
        print(f"[SHOUTOUT_MODULE] Deferred: {deferred}")
        
        try:
            # Build the request data
            discord_username = f"{interaction.user.name}#{interaction.user.discriminator}"
            
            data = {
                'bot_token': self.wp_bot_token,
                'discord_user_id': str(interaction.user.id),
                'discord_username': discord_username,
                'check_tier_only': True  # Just checking tier first
            }
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns"
            
            # Log the request details
            print(f"[SHOUTOUT_MODULE] API URL: {url}")
            print(f"[SHOUTOUT_MODULE] Request data: {json.dumps(data, indent=2)}")
            print(f"[SHOUTOUT_MODULE] Bot token (first 10 chars): {self.wp_bot_token[:10] if self.wp_bot_token else 'None'}...")
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            print(f"[SHOUTOUT_MODULE] Making POST request to WordPress API...")
            
            # Set a timeout for the API request
            timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout
            
            async with self.session.post(url, json=data, headers=headers, timeout=timeout) as response:
                # Log response details
                print(f"[SHOUTOUT_MODULE] Response status: {response.status}")
                
                response_text = await response.text()
                print(f"[SHOUTOUT_MODULE] Response body (first 500 chars): {response_text[:500]}")
                
                # Try to parse JSON
                try:
                    result = json.loads(response_text)
                    print(f"[SHOUTOUT_MODULE] Parsed response: {json.dumps(result, indent=2)}")
                except json.JSONDecodeError as e:
                    print(f"[SHOUTOUT_MODULE] JSON decode error: {e}")
                    print(f"[SHOUTOUT_MODULE] Raw response was: {response_text[:1000]}")
                    
                    # Check if it's an HTML error page
                    if '<html' in response_text.lower():
                        print(f"[SHOUTOUT_MODULE] Received HTML instead of JSON - likely a WordPress error page")
                    
                    # Send error message
                    if deferred:
                        await interaction.followup.send(
                            "❌ Server returned invalid response. The API endpoint may not be properly configured.",
                            ephemeral=True
                        )
                    else:
                        try:
                            await interaction.response.send_message(
                                "❌ Server returned invalid response. The API endpoint may not be properly configured.",
                                ephemeral=True
                            )
                        except:
                            pass
                    return
                
                # Handle the response based on status and content
                if response.status == 200 and result.get('has_access'):
                    print(f"[SHOUTOUT_MODULE] User has access! Tier: {result.get('user_tier', 'unknown')}")
                    
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
                    print(f"[SHOUTOUT_MODULE] User doesn't have access. Response: {result}")
                    
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
                    else:
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        
        except asyncio.TimeoutError:
            print(f"[SHOUTOUT_MODULE] Request timeout after 5 seconds")
            error_msg = "❌ Request timed out. The server may be slow or unavailable."
            
            if deferred:
                await interaction.followup.send(error_msg, ephemeral=True)
            else:
                try:
                    await interaction.response.send_message(error_msg, ephemeral=True)
                except:
                    pass
                    
        except aiohttp.ClientError as e:
            print(f"[SHOUTOUT_MODULE] Client error: {type(e).__name__}: {e}")
            error_msg = "❌ Network error occurred. Please check your connection and try again."
            
            if deferred:
                await interaction.followup.send(error_msg, ephemeral=True)
            else:
                try:
                    await interaction.response.send_message(error_msg, ephemeral=True)
                except:
                    pass
                    
        except Exception as e:
            print(f"[SHOUTOUT_MODULE] Unexpected error: {type(e).__name__}: {e}")
            import traceback
            print(f"[SHOUTOUT_MODULE] Traceback: {traceback.format_exc()}")
            
            error_msg = "❌ An unexpected error occurred. Please try again later."
            
            if deferred:
                await interaction.followup.send(error_msg, ephemeral=True)
            else:
                try:
                    await interaction.response.send_message(error_msg, ephemeral=True)
                except:
                    pass
        
        finally:
            print(f"[SHOUTOUT_MODULE] ========== CAMPAIGN CREATE END ==========")
    
    async def start_campaign_creation_flow(self, interaction: discord.Interaction, user_tier: str):
        """Start the actual campaign creation flow for users with access"""
        # Create initial form/modal for campaign details
        embed = discord.Embed(
            title="📝 Create Shoutout Campaign",
            description=f"Welcome! Your tier: **{user_tier.upper()}**\n\nLet's set up your shoutout campaign.",
            color=0x00A86B
        )
        
        embed.add_field(
            name="Step 1: Book Details",
            value="Please provide your book information",
            inline=False
        )
        
        # Create view with buttons for next steps
        view = CampaignCreationView(self, interaction.user.id, user_tier)
        
        await interaction.followup.send(
            embed=embed,
            view=view,
            ephemeral=True
        )
    
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
        await interaction.response.defer()
        
        try:
            # Build API request
            params = {
                'bot_token': self.wp_bot_token,
                'discord_user_id': str(interaction.user.id),
                'discord_username': f"{interaction.user.name}#{interaction.user.discriminator}"
            }
            
            # Add filters
            if genre:
                params['genre'] = genre
            if platform:
                params['platform'] = platform
            if min_followers is not None:
                params['min_followers'] = min_followers
            if max_followers is not None:
                params['max_followers'] = max_followers
            if server_only and interaction.guild:
                params['server_id'] = str(interaction.guild.id)
            
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns"
            headers = {
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    campaigns = result.get('campaigns', [])
                    
                    if campaigns:
                        embed = self.create_campaign_list_embed(campaigns)
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send(
                            "No campaigns found matching your criteria. Try adjusting your filters!",
                            ephemeral=True
                        )
                else:
                    await interaction.followup.send(
                        "❌ Failed to fetch campaigns. Please try again later.",
                        ephemeral=True
                    )
                    
        except Exception as e:
            print(f"[SHOUTOUT_MODULE] Error browsing campaigns: {e}")
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
        placeholder="Royal Road, Scribble Hub, Kindle, etc.",
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
        placeholder="How many shoutouts can you offer? (minimum 1)",  # Updated placeholder
        required=True,
        max_length=4  #(up to 9999 slots)
    )
    
    def __init__(self, module: ShoutoutModule):
        super().__init__()
        self.module = module
    
async def on_submit(self, interaction: discord.Interaction):
    """Handle modal submission - properly send all book data"""
    await interaction.response.defer(ephemeral=True)
    
    print(f"[SHOUTOUT_MODULE] Modal submitted by {interaction.user.id}")
    
    try:
        # Validate slots number - only check that it's greater than 0
        try:
            slots = int(self.available_slots.value)
        except ValueError:
            await interaction.followup.send(
                "❌ Please enter a valid number for slots.",
                ephemeral=True
            )
            return
            
        if slots < 1:
            await interaction.followup.send(
                "❌ You must offer at least 1 shoutout slot.",
                ephemeral=True
            )
            return
        
        # Get server ID if in a guild (for DMs, it will be None)
        server_id = str(interaction.guild.id) if interaction.guild else None
        
        # Get username in the correct format
        discord_username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        # Create campaign via API with ALL book data
        data = {
            'bot_token': self.module.wp_bot_token,
            'discord_user_id': str(interaction.user.id),
            'discord_username': discord_username,
            # Book data from modal
            'book_title': self.book_title.value,
            'book_url': self.book_url.value,
            'platform': self.platform.value.lower(),
            'author_name': self.author_name.value,
            'available_slots': slots,
            # Server info
            'server_id': server_id,
            # Campaign settings
            'campaign_settings': {
                'auto_approve': False,
                'require_mutual_server': False
            }
        }
        
        # Log what we're sending
        print(f"[SHOUTOUT_MODULE] Sending campaign data:")
        for key, value in data.items():
            if key == 'bot_token':
                print(f"[SHOUTOUT_MODULE]   {key}: [hidden]")
            else:
                print(f"[SHOUTOUT_MODULE]   {key}: {value}")
        
        url = f"{self.module.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.module.wp_bot_token}',
            'User-Agent': 'Essence-Discord-Bot/1.0'
        }
        
        async with self.module.session.post(url, json=data, headers=headers, timeout=10) as response:
            response_text = await response.text()
            print(f"[SHOUTOUT_MODULE] Response status: {response.status}")
            print(f"[SHOUTOUT_MODULE] Response: {response_text[:500]}")
            
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                print(f"[SHOUTOUT_MODULE] Failed to parse JSON response")
                await interaction.followup.send(
                    "❌ Server returned invalid response. Please try again.",
                    ephemeral=True
                )
                return
            
            if response.status == 200 and result.get('success'):
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
                    value=self.platform.value,
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
            else:
                error_msg = result.get('message', 'Unknown error occurred')
                print(f"[SHOUTOUT_MODULE] Campaign creation failed: {error_msg}")
                await interaction.followup.send(
                    f"❌ Failed to create campaign: {error_msg}",
                    ephemeral=True
                )
                
    except aiohttp.ClientError as e:
        print(f"[SHOUTOUT_MODULE] Network error: {type(e).__name__}: {e}")
        await interaction.followup.send(
            "❌ Network error occurred. Please check your connection and try again.",
            ephemeral=True
        )
    except Exception as e:
        print(f"[SHOUTOUT_MODULE] Error creating campaign: {type(e).__name__}: {e}")
        import traceback
        print(f"[SHOUTOUT_MODULE] Traceback: {traceback.format_exc()}")
        
        await interaction.followup.send(
            "❌ An error occurred while creating your campaign. Please try again.",
            ephemeral=True
        )
        
async with self.module.session.post(url, json=data, headers=headers, timeout=10) as response:
    response_text = await response.text()
    print(f"[SHOUTOUT_MODULE] Response status: {response.status}")
    print(f"[SHOUTOUT_MODULE] Response: {response_text[:500]}")
    
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        print(f"[SHOUTOUT_MODULE] Failed to parse JSON response")
        await interaction.followup.send(
            "❌ Server returned invalid response. Please try again.",
            ephemeral=True
        )
        return
    
    if response.status == 200 and result.get('success'):
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
            value=self.platform.value,
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
    else:
        error_msg = result.get('message', 'Unknown error occurred')
        print(f"[SHOUTOUT_MODULE] Campaign creation failed: {error_msg}")
        await interaction.followup.send(
            f"❌ Failed to create campaign: {error_msg}",
            ephemeral=True
        )
                
    except Exception as e:
        print(f"[SHOUTOUT_MODULE] Error creating campaign: {type(e).__name__}: {e}")
        import traceback
        print(f"[SHOUTOUT_MODULE] Traceback: {traceback.format_exc()}")
        
        await interaction.followup.send(
            "❌ An error occurred while creating your campaign. Please try again.",
            ephemeral=True
        )
