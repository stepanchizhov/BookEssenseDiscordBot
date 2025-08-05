"""
Discord Bot Shoutout Swap System Module
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
    
    def __init__(self, bot: commands.Bot, session: aiohttp.ClientSession, wp_api_url: str, wp_bot_token: str, tag_autocomplete_func=None, get_user_info_func=None):
        self.bot = bot
        self.session = session
        self.wp_api_url = wp_api_url
        self.wp_bot_token = wp_bot_token
        self.tag_autocomplete = tag_autocomplete_func
        self.get_user_info = get_user_info_func
        
        # Register commands immediately
        self.register_commands()
    
    def register_commands(self):
        """Register all shoutout-related commands with the bot"""
        
        # Create command instances
        campaign_create_cmd = discord.app_commands.Command(
            name="shoutout-campaign-create",
            description="Create a new shoutout campaign (DM only)",
            callback=self.shoutout_campaign_create
        )
        
        browse_cmd = discord.app_commands.Command(
            name="shoutout-browse",
            description="Browse available shoutout campaigns",
            callback=self.shoutout_browse
        )
        
        # Add parameters to browse command
        browse_cmd.add_parameter(
            name="genre",
            description="Filter by book genre/tags",
            required=False,
            type=discord.app_commands.AppCommandOptionType.string
        )
        browse_cmd.add_parameter(
            name="platform", 
            description="Filter by preferred platform",
            required=False,
            type=discord.app_commands.AppCommandOptionType.string
        )
        browse_cmd.add_parameter(
            name="min_followers",
            description="Minimum follower requirement", 
            required=False,
            type=discord.app_commands.AppCommandOptionType.integer
        )
        browse_cmd.add_parameter(
            name="max_followers",
            description="Maximum follower limit",
            required=False,
            type=discord.app_commands.AppCommandOptionType.integer
        )
        browse_cmd.add_parameter(
            name="server_only",
            description="Only show campaigns from current server",
            required=False,
            type=discord.app_commands.AppCommandOptionType.boolean
        )
        
        # Add autocomplete for genre and platform
        @browse_cmd.autocomplete('genre')
        async def genre_autocomplete(interaction: discord.Interaction, current: str):
            # Use the tag_autocomplete function if available, otherwise fallback to static list
            if self.tag_autocomplete:
                return await self.tag_autocomplete(interaction, current)
            else:
                # Fallback to static genre list
                genres = [
                    "Fantasy", "Action", "Adventure", "Romance", "Sci-fi", "LitRPG", 
                    "Portal Fantasy", "Magic", "Progression", "Slice of Life",
                    "Drama", "Comedy", "Horror", "Mystery", "Thriller"
                ]
                return [
                    discord.app_commands.Choice(name=genre, value=genre)
                    for genre in genres if current.lower() in genre.lower()
                ][:25]
        
        @browse_cmd.autocomplete('platform')
        async def platform_autocomplete(interaction: discord.Interaction, current: str):
            platforms = ["Royal Road", "Scribble Hub", "Kindle", "Audible", "Other"]
            return [
                discord.app_commands.Choice(name=platform, value=platform.lower().replace(" ", "_"))
                for platform in platforms if current.lower() in platform.lower()
            ]
        
        # Add commands to the bot tree
        self.bot.tree.add_command(campaign_create_cmd)
        self.bot.tree.add_command(browse_cmd)
        
        logger.info("[SHOUTOUT_MODULE] Commands registered successfully")
    
    async def shoutout_campaign_create(self, interaction: discord.Interaction):
        """Create a new shoutout campaign - only works in DMs"""
        if interaction.guild is not None:
            await interaction.response.send_message(
                "❌ Campaign creation only works in DMs for privacy. Please send me a direct message and try again!",
                ephemeral=True
            )
            return
        
        await self.handle_campaign_create(interaction)
    
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
    
    async def check_user_tier(self, discord_user_id: str) -> str:
        """Check user's subscription tier using the main bot's user info function"""
        if self.get_user_info:
            try:
                # Use the same user info function as the main bot
                # This should make the same API call and return the result dict
                result = await self.get_user_info(discord_user_id)
                tier = result.get('user_tier', 'free')
                logger.info(f"[SHOUTOUT_MODULE] User {discord_user_id} has tier: {tier}")
                return tier
            except Exception as e:
                logger.error(f"[SHOUTOUT_MODULE] Error checking user tier: {e}")
                return 'free'
        else:
            logger.warning(f"[SHOUTOUT_MODULE] No get_user_info function provided, defaulting to free")
            return 'free'
    
    async def handle_campaign_create(self, interaction: discord.Interaction):
        """Handle campaign creation workflow"""
        await interaction.response.defer(ephemeral=True)
        
        # Check user tier
        user_tier = await self.check_user_tier(str(interaction.user.id))
        
        if user_tier == 'free':
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
                name="Coming Soon",
                value="Full public access will be available once testing is complete.",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # User has access, start campaign creation
        await self.start_campaign_creation_flow(interaction)
    
    async def start_campaign_creation_flow(self, interaction: discord.Interaction):
        """Start the multi-step campaign creation process"""
        embed = discord.Embed(
            title="📚 Create Shoutout Campaign",
            description="Let's create your shoutout campaign! We'll collect information in steps.",
            color=0x00d4aa
        )
        embed.add_field(
            name="Step 1: Basic Information",
            value="First, let's get your book details and campaign settings.",
            inline=False
        )
        
        # Send a follow-up message with button to start the process
        view = CampaignCreateView(self)
        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )
        await interaction.followup.send(
            "Click the button below to start creating your campaign:",
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
        """Handle browsing available campaigns"""
        await interaction.response.defer()
        
        # Build filters
        filters = {}
        if genre:
            filters['genre'] = genre
        if platform:
            filters['platform'] = platform
        if min_followers:
            filters['min_followers'] = min_followers
        if max_followers:
            filters['max_followers'] = max_followers
        if server_only and interaction.guild:
            filters['server_id'] = str(interaction.guild.id)
        
        # Add user context
        filters['discord_user_id'] = str(interaction.user.id)
        
        try:
            campaigns = await self.fetch_campaigns(filters)
            
            if not campaigns:
                embed = discord.Embed(
                    title="📭 No Campaigns Found",
                    description="No shoutout campaigns match your criteria. Try adjusting your filters!",
                    color=0xffa726
                )
                embed.add_field(
                    name="💡 Tip",
                    value="Remove some filters or create your own campaign with `/shoutout-campaign-create`",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create paginated view
            view = CampaignBrowseView(self, campaigns, filters)
            embed = await view.create_page_embed(0)
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error browsing campaigns: {e}")
            await interaction.followup.send(
                "❌ Error retrieving campaigns. Please try again later!",
                ephemeral=True
            )
    
    async def fetch_campaigns(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch campaigns from WordPress API with filters"""
        url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns"
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)',
            'X-Requested-With': 'XMLHttpRequest',
            'Authorization': f'Bearer {self.wp_bot_token}'
        }
        
        # Add filters as query parameters
        params = {}
        for key, value in filters.items():
            if value is not None:
                params[key] = value
        
        async with self.session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('campaigns', [])
            else:
                logger.error(f"Failed to fetch campaigns: {response.status}")
                raise Exception(f"API error: {response.status}")
    
    async def create_campaign(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new campaign via WordPress API"""
        url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/shoutout/campaigns"
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)',
            'X-Requested-With': 'XMLHttpRequest',
            'Authorization': f'Bearer {self.wp_bot_token}'
        }
        
        async with self.session.post(url, headers=headers, json=campaign_data) as response:
            if response.status == 201:
                return await response.json()
            else:
                error_text = await response.text()
                logger.error(f"Failed to create campaign: {response.status} - {error_text}")
                raise Exception(f"API error: {response.status}")


# Rest of the View and Modal classes remain the same...
class CampaignCreateView(discord.ui.View):
    """View for campaign creation with start button"""
    
    def __init__(self, shoutout_module: ShoutoutModule):
        super().__init__(timeout=300)
        self.shoutout_module = shoutout_module
    
    @discord.ui.button(label="Start Campaign Creation", style=discord.ButtonStyle.primary, emoji="📝")
    async def start_creation(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CampaignBasicInfoModal(self.shoutout_module)
        await interaction.response.send_modal(modal)


class CampaignBasicInfoModal(discord.ui.Modal, title="Campaign Basic Info"):
    """Modal for collecting basic campaign information"""
    
    def __init__(self, shoutout_module: ShoutoutModule):
        super().__init__()
        self.shoutout_module = shoutout_module
    
    book_title = discord.ui.TextInput(
        label="Book Title",
        placeholder="Enter your book title...",
        max_length=200,
        required=True
    )
    
    author_name = discord.ui.TextInput(
        label="Author Name",
        placeholder="Your author name...",
        max_length=100,
        required=True
    )
    
    platform = discord.ui.TextInput(
        label="Platform",
        placeholder="Royal Road, Scribble Hub, Kindle, etc.",
        max_length=50,
        required=True
    )
    
    book_url = discord.ui.TextInput(
        label="Book URL",
        placeholder="https://www.royalroad.com/fiction/12345/your-book",
        max_length=500,
        required=True
    )
    
    available_slots = discord.ui.TextInput(
        label="Available Slots",
        placeholder="How many shoutout slots do you offer? (e.g., 5)",
        max_length=3,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Validate slots number
        try:
            slots = int(self.available_slots.value)
            if slots <= 0 or slots > 100:
                raise ValueError("Invalid slot count")
        except ValueError:
            await interaction.followup.send(
                "❌ Available slots must be a number between 1 and 100!",
                ephemeral=True
            )
            return
        
        # Store data and proceed to next step
        campaign_data = {
            'discord_user_id': str(interaction.user.id),
            'discord_username': interaction.user.display_name,
            'server_id': str(interaction.guild.id) if interaction.guild else None,
            'book_title': self.book_title.value,
            'author_name': self.author_name.value,
            'platform': self.platform.value.lower().replace(' ', '_'),
            'book_url': self.book_url.value,
            'available_slots': slots,
            'campaign_status': 'draft'
        }
        
        # Show next step
        await self.show_advanced_settings(interaction, campaign_data)
    
    async def show_advanced_settings(self, interaction: discord.Interaction, campaign_data: Dict[str, Any]):
        """Show advanced settings step"""
        embed = discord.Embed(
            title="📚 Campaign Creation - Step 2",
            description="Great! Now let's set up advanced settings for your campaign.",
            color=0x00d4aa
        )
        embed.add_field(
            name="Book Details Saved",
            value=f"**{campaign_data['book_title']}** by {campaign_data['author_name']}\n"
                  f"Platform: {campaign_data['platform'].replace('_', ' ').title()}\n"
                  f"Slots: {campaign_data['available_slots']}",
            inline=False
        )
        
        view = CampaignAdvancedView(self.shoutout_module, campaign_data)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class CampaignAdvancedView(discord.ui.View):
    """View for advanced campaign settings"""
    
    def __init__(self, shoutout_module: ShoutoutModule, campaign_data: Dict[str, Any]):
        super().__init__(timeout=300)
        self.shoutout_module = shoutout_module
        self.campaign_data = campaign_data
    
    @discord.ui.button(label="Set Requirements", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def set_requirements(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CampaignRequirementsModal(self.shoutout_module, self.campaign_data)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Skip & Create Campaign", style=discord.ButtonStyle.primary, emoji="✅")
    async def create_campaign(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.finalize_campaign(interaction)
    
    async def finalize_campaign(self, interaction: discord.Interaction):
        """Create the campaign with collected data"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Set default settings if not set
            if 'campaign_settings' not in self.campaign_data:
                self.campaign_data['campaign_settings'] = {}
            
            # Add metadata
            self.campaign_data['created_at'] = datetime.utcnow().isoformat()
            self.campaign_data['campaign_status'] = 'active'
            
            result = await self.shoutout_module.create_campaign(self.campaign_data)
            
            embed = discord.Embed(
                title="🎉 Campaign Created Successfully!",
                description=f"Your shoutout campaign **{self.campaign_data['book_title']}** is now live!",
                color=0x57f287
            )
            embed.add_field(
                name="Campaign ID",
                value=f"`{result.get('campaign_id', 'N/A')}`",
                inline=True
            )
            embed.add_field(
                name="Available Slots",
                value=str(self.campaign_data['available_slots']),
                inline=True
            )
            embed.add_field(
                name="Next Steps",
                value="• Monitor applications with `/shoutout-my-campaigns`\n"
                      "• Approve participants that match your criteria\n"
                      "• Coordinate shoutout exchanges",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error creating campaign: {e}")
            await interaction.followup.send(
                "❌ Error creating campaign. Please try again later!",
                ephemeral=True
            )


class CampaignRequirementsModal(discord.ui.Modal, title="Campaign Requirements"):
    """Modal for setting campaign requirements"""
    
    def __init__(self, shoutout_module: ShoutoutModule, campaign_data: Dict[str, Any]):
        super().__init__()
        self.shoutout_module = shoutout_module
        self.campaign_data = campaign_data
    
    min_followers = discord.ui.TextInput(
        label="Minimum Followers (optional)",
        placeholder="e.g., 100",
        max_length=10,
        required=False
    )
    
    preferred_genres = discord.ui.TextInput(
        label="Preferred Genres (optional)",
        placeholder="Fantasy, LitRPG, Adventure (comma separated)",
        max_length=200,
        required=False
    )
    
    additional_notes = discord.ui.TextInput(
        label="Additional Requirements (optional)",
        placeholder="Any other requirements for participants...",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Process requirements
        settings = {}
        
        if self.min_followers.value:
            try:
                settings['min_followers'] = int(self.min_followers.value)
            except ValueError:
                await interaction.followup.send(
                    "❌ Minimum followers must be a valid number!",
                    ephemeral=True
                )
                return
        
        if self.preferred_genres.value:
            genres = [g.strip() for g in self.preferred_genres.value.split(',')]
            settings['preferred_genres'] = genres
        
        if self.additional_notes.value:
            settings['additional_notes'] = self.additional_notes.value
        
        self.campaign_data['campaign_settings'] = settings
        
        # Create final campaign
        view = CampaignAdvancedView(self.shoutout_module, self.campaign_data)
        await view.finalize_campaign(interaction)


class CampaignBrowseView(discord.ui.View):
    """View for browsing campaigns with pagination"""
    
    def __init__(self, shoutout_module: ShoutoutModule, campaigns: List[Dict[str, Any]], filters: Dict[str, Any]):
        super().__init__(timeout=300)
        self.shoutout_module = shoutout_module
        self.campaigns = campaigns
        self.filters = filters
        self.current_page = 0
        self.per_page = 1  # Show one campaign per page for detailed view
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page"""
        total_pages = (len(self.campaigns) + self.per_page - 1) // self.per_page
        
        # Find buttons and update their state
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.custom_id == "prev":
                    item.disabled = self.current_page == 0
                elif item.custom_id == "next":
                    item.disabled = self.current_page >= total_pages - 1
    
    async def create_page_embed(self, page: int) -> discord.Embed:
        """Create embed for a specific page"""
        if not self.campaigns:
            return discord.Embed(
                title="📭 No Campaigns Found",
                description="No campaigns match your criteria.",
                color=0xffa726
            )
        
        campaign = self.campaigns[page]
        total_pages = (len(self.campaigns) + self.per_page - 1) // self.per_page
        
        embed = discord.Embed(
            title=f"📚 {campaign.get('book_title', 'Unknown Title')}",
            description=f"by {campaign.get('author_name', 'Unknown Author')}",
            color=0x00d4aa
        )
        
        # Add campaign details
        embed.add_field(
            name="Platform",
            value=campaign.get('platform', 'unknown').replace('_', ' ').title(),
            inline=True
        )
        embed.add_field(
            name="Available Slots",
            value=f"{campaign.get('available_slots', 0)} slots",
            inline=True
        )
        embed.add_field(
            name="Creator",
            value=campaign.get('discord_username', 'Unknown'),
            inline=True
        )
        
        if campaign.get('book_url'):
            embed.add_field(
                name="Book Link",
                value=f"[Read on Platform]({campaign['book_url']})",
                inline=False
            )
        
        # Add requirements if any
        settings = campaign.get('campaign_settings', {})
        if settings:
            requirements = []
            if settings.get('min_followers'):
                requirements.append(f"Min {settings['min_followers']} followers")
            if settings.get('preferred_genres'):
                requirements.append(f"Genres: {', '.join(settings['preferred_genres'])}")
            
            if requirements:
                embed.add_field(
                    name="Requirements",
                    value="\n".join(requirements),
                    inline=False
                )
        
        embed.set_footer(text=f"Page {page + 1} of {total_pages} • Campaign ID: {campaign.get('id', 'N/A')}")
        
        return embed
    
    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, custom_id="prev")
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = await self.create_page_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary, custom_id="next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        total_pages = (len(self.campaigns) + self.per_page - 1) // self.per_page
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = await self.create_page_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Apply to Campaign", style=discord.ButtonStyle.primary, emoji="📝")
    async def apply_to_campaign(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.campaigns:
            await interaction.response.send_message(
                "❌ No campaign to apply to!",
                ephemeral=True
            )
            return
        
        campaign = self.campaigns[self.current_page]
        modal = CampaignApplicationModal(self.shoutout_module, campaign)
        await interaction.response.send_modal(modal)


class CampaignApplicationModal(discord.ui.Modal, title="Apply to Campaign"):
    """Modal for applying to a campaign"""
    
    def __init__(self, shoutout_module: ShoutoutModule, campaign: Dict[str, Any]):
        super().__init__()
        self.shoutout_module = shoutout_module
        self.campaign = campaign
    
    book_title = discord.ui.TextInput(
        label="Your Book Title",
        placeholder="Enter your book title...",
        max_length=200,
        required=True
    )
    
    book_platform = discord.ui.TextInput(
        label="Platform",
        placeholder="Royal Road, Scribble Hub, Kindle, etc.",
        max_length=50,
        required=True
    )
    
    book_url = discord.ui.TextInput(
        label="Book URL",
        placeholder="https://www.royalroad.com/fiction/12345/your-book",
        max_length=500,
        required=True
    )
    
    why_apply = discord.ui.TextInput(
        label="Why are you applying?",
        placeholder="Brief message about why you want to exchange shoutouts...",
        style=discord.TextStyle.paragraph,
        max_length=300,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Prepare application data
        application_data = {
            'campaign_id': self.campaign.get('id'),
            'discord_user_id': str(interaction.user.id),
            'discord_username': interaction.user.display_name,
            'participant_book_data': {
                'title': self.book_title.value,
                'platform': self.book_platform.value,
                'url': self.book_url.value,
                'application_message': self.why_apply.value
            },
            'status': 'pending'
        }
        
        try:
            # Submit application via API
            await self.submit_application(application_data)
            
            embed = discord.Embed(
                title="✅ Application Submitted!",
                description=f"Your application to **{self.campaign.get('book_title')}** has been submitted.",
                color=0x57f287
            )
            embed.add_field(
                name="Next Steps",
                value="• Wait for the campaign creator to review your application\n"
                      "• You'll be notified if you're approved\n"
                      "• Track your applications with `/shoutout-my-applications`",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error submitting application: {e}")
            await interaction.followup.send(
                "❌ Error submitting application. Please try again later!",
                ephemeral=True
            )
    
    async def submit_application(self, application_data: Dict[str, Any]):
        """Submit application via WordPress API"""
        url = f"{self.shoutout_module.wp_api_url}/wp-json/rr-analytics/v1/shoutout/applications"
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)',
            'X-Requested-With': 'XMLHttpRequest',
            'Authorization': f'Bearer {self.shoutout_module.wp_bot_token}'
        }
        
        async with self.shoutout_module.session.post(url, headers=headers, json=application_data) as response:
            if response.status != 201:
                error_text = await response.text()
                logger.error(f"Failed to submit application: {response.status} - {error_text}")
                raise Exception(f"API error: {response.status}")
