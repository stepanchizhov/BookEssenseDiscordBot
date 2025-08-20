"""
Discord Bot Book Claim System Module
Modular extension for the Discord Essence Bot
Handles book claiming, approval workflow, and user book management
"""

import discord
from discord.ext import commands
import aiohttp
import json
import asyncio
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
import logging
from enum import Enum
import re

# Set up logging for this module
logger = logging.getLogger('discord')

class ClaimStatus(Enum):
    """Enum for claim request statuses"""
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    CANCELLED = "cancelled"

class BookClaimModule:
    """
    Modular book claim system for Discord bot
    Handles book claiming, approval workflow, and user book listings
    """
    
    def __init__(self, bot: commands.Bot, session: aiohttp.ClientSession, 
                 wp_api_url: str, wp_bot_token: str):
        self.bot = bot
        self.session = session
        self.wp_api_url = wp_api_url
        self.wp_bot_token = wp_bot_token
        
        logger.info(f"[BOOK_CLAIM_MODULE] Initializing module...")
        logger.info(f"[BOOK_CLAIM_MODULE] bot: {bot}")
        logger.info(f"[BOOK_CLAIM_MODULE] wp_api_url: {wp_api_url}")
        logger.info(f"[BOOK_CLAIM_MODULE] wp_bot_token: {'[SET]' if wp_bot_token else '[NOT SET]'}")
        
        # Register commands
        self.register_commands()
        logger.info(f"[BOOK_CLAIM_MODULE] All commands registered")
    
    def register_commands(self):
        """Register all book claim-related commands with the bot"""
        
        # Book claim command - available to all users
        @self.bot.tree.command(
            name="rr-claim-book",
            description="Claim ownership of a Royal Road book"
        )
        @discord.app_commands.describe(
            book_url="Royal Road book URL (e.g., https://www.royalroad.com/fiction/12345/book-title)",
            discord_server_url="Your Discord server URL (optional)",
            royal_road_user_id="Your Royal Road user ID (optional)",
            patreon_user_id="Your Patreon username (optional)",
            kindle_author_asin="Your Amazon Kindle author ASIN (optional)",
            scribble_hub_user_id="Your Scribble Hub user ID (optional)"
        )
        async def rr_claim_book(
            interaction: discord.Interaction,
            book_url: str,
            discord_server_url: Optional[str] = None,
            royal_road_user_id: Optional[str] = None,
            patreon_user_id: Optional[str] = None,
            kindle_author_asin: Optional[str] = None,
            scribble_hub_user_id: Optional[str] = None
        ):
            await self.claim_book(
                interaction, book_url, discord_server_url, royal_road_user_id,
                patreon_user_id, kindle_author_asin, scribble_hub_user_id
            )
        
        # Multiple book claim command - available to all users
        @self.bot.tree.command(
            name="rr-claim-multiple",
            description="Claim ownership of multiple Royal Road books (up to 5 at once)"
        )
        @discord.app_commands.describe(
            book_urls="Royal Road book URLs separated by commas or spaces",
            discord_server_url="Your Discord server URL (optional)",
            royal_road_user_id="Your Royal Road user ID (optional)",
            patreon_user_id="Your Patreon username (optional)",
            kindle_author_asin="Your Amazon Kindle author ASIN (optional)",
            scribble_hub_user_id="Your Scribble Hub user ID (optional)"
        )
        async def rr_claim_multiple(
            interaction: discord.Interaction,
            book_urls: str,
            discord_server_url: Optional[str] = None,
            royal_road_user_id: Optional[str] = None,
            patreon_user_id: Optional[str] = None,
            kindle_author_asin: Optional[str] = None,
            scribble_hub_user_id: Optional[str] = None
        ):
            await self.claim_multiple_books(
                interaction, book_urls, discord_server_url, royal_road_user_id,
                patreon_user_id, kindle_author_asin, scribble_hub_user_id
            )
        
        # Claim approval command - admin/mod only
        @self.bot.tree.command(
            name="rr-claim-approve",
            description="Approve or decline book ownership claims (Admin/Mod only)"
        )
        @discord.app_commands.describe(
            action="Action to take on the claim",
            claim_id="Claim request ID (leave empty to see pending claims)"
        )
        @discord.app_commands.choices(action=[
            discord.app_commands.Choice(name="View Pending", value="view"),
            discord.app_commands.Choice(name="Approve", value="approve"),
            discord.app_commands.Choice(name="Decline", value="decline")
        ])
        async def rr_claim_approve(
            interaction: discord.Interaction,
            action: str,
            claim_id: Optional[int] = None
        ):
            await self.manage_claims(interaction, action, claim_id)
        
        # My books command - public
        @self.bot.tree.command(
            name="rr-my-books",
            description="View your claimed Royal Road books and their statistics"
        )
        @discord.app_commands.describe(
            user="User to view books for (leave empty for yourself)"
        )
        async def rr_my_books(
            interaction: discord.Interaction,
            user: Optional[discord.User] = None
        ):
            await self.show_user_books(interaction, user)
    
    async def claim_book(self, interaction: discord.Interaction, book_url: str,
                         discord_server_url: Optional[str], royal_road_user_id: Optional[str],
                         patreon_user_id: Optional[str], kindle_author_asin: Optional[str],
                         scribble_hub_user_id: Optional[str]):
        """Handle book claim request"""
        await interaction.response.defer(ephemeral=True)
        
        logger.info(f"[BOOK_CLAIM_MODULE] Claim request from {interaction.user.name} for {book_url}")
        
        # Validate Royal Road URL
        rr_book_id = self.extract_rr_book_id(book_url)
        if not rr_book_id:
            await interaction.followup.send(
                "❌ Invalid Royal Road URL. Please provide a valid book URL like:\n"
                "`https://www.royalroad.com/fiction/12345/book-title`",
                ephemeral=True
            )
            return
        
        # Validate Discord server URL if provided
        if discord_server_url and not self.validate_discord_url(discord_server_url):
            await interaction.followup.send(
                "❌ Invalid Discord server URL. Please provide a valid invite link.",
                ephemeral=True
            )
            return
        
        try:
            # Submit claim request to WordPress
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-claim/submit"
            data = {
                'bot_token': self.wp_bot_token,
                'discord_user_id': str(interaction.user.id),
                'discord_username': interaction.user.name,
                'server_id': str(interaction.guild.id) if interaction.guild else None,
                'server_name': interaction.guild.name if interaction.guild else "DM",
                'book_url': book_url,
                'royal_road_book_id': rr_book_id,
                'discord_server_url': discord_server_url,
                'royal_road_user_id': royal_road_user_id,
                'patreon_user_id': patreon_user_id,
                'kindle_author_asin': kindle_author_asin,
                'scribble_hub_user_id': scribble_hub_user_id
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            async with self.session.post(url, json=data, headers=headers) as response:
                result = await response.json()
                
                if response.status == 200 and result.get('success'):
                    claim_id = result.get('claim_id')
                    book_title = result.get('book_title', 'Unknown Book')
                    server_verified = result.get('server_verified', False)
                    
                    embed = discord.Embed(
                        title="✅ Book Claim Submitted",
                        description=f"Your claim for **{book_title}** has been submitted for review.",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Claim ID", value=f"`#{claim_id}`", inline=True)
                    embed.add_field(name="Status", value="⏳ Pending Review", inline=True)
                    
                    if not server_verified:
                        embed.add_field(
                            name="⚠️ Server Not Verified",
                            value=(
                                "This server is not yet verified for claim approvals.\n"
                                "Please join [Stepan's Discord](https://discord.gg/xvw9vbvrwj) to get your claim approved.\n"
                                "Server admins can also request verification there."
                            ),
                            inline=False
                        )
                        
                        # Send public message about verification
                        await interaction.followup.send(
                            "📢 **Book Claim Submitted!**\n"
                            f"{interaction.user.mention} has submitted a claim for **{book_title}**.\n\n"
                            "⚠️ This server is not verified for claim approvals. "
                            "Please join [Stepan's Discord](https://discord.gg/xvw9vbvrwj) to get your claim reviewed.\n"
                            "Server admins can also request verification to enable local claim processing.",
                            ephemeral=False
                        )
                    else:
                        embed.add_field(
                            name="What's Next?",
                            value="An administrator will review your claim shortly. "
                                  "You'll be notified once it's approved or if additional information is needed.",
                            inline=False
                        )
                        
                        # Notify admins in a designated channel if configured
                        await self.notify_admins_of_new_claim(interaction.guild, claim_id, book_title, interaction.user)
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    
                elif result.get('error') == 'already_claimed':
                    await interaction.followup.send(
                        f"❌ This book is already claimed by another user.\n"
                        f"Owner: {result.get('owner_name', 'Unknown')}",
                        ephemeral=True
                    )
                elif result.get('error') == 'pending_claim':
                    await interaction.followup.send(
                        f"⏳ You already have a pending claim for this book.\n"
                        f"Claim ID: `#{result.get('claim_id')}`\n"
                        f"Please wait for it to be reviewed.",
                        ephemeral=True
                    )
                else:
                    error_msg = result.get('message', 'Unknown error occurred')
                    await interaction.followup.send(
                        f"❌ Failed to submit claim: {error_msg}",
                        ephemeral=True
                    )
                    
        except Exception as e:
            logger.error(f"[BOOK_CLAIM_MODULE] Error submitting claim: {e}")
            await interaction.followup.send(
                "❌ An error occurred while submitting your claim. Please try again later.",
                ephemeral=True
            )
    
    async def claim_multiple_books(self, interaction: discord.Interaction, book_urls: str,
                                   discord_server_url: Optional[str], royal_road_user_id: Optional[str],
                                   patreon_user_id: Optional[str], kindle_author_asin: Optional[str],
                                   scribble_hub_user_id: Optional[str]):
        """Handle multiple book claim requests"""
        await interaction.response.defer(ephemeral=True)
        
        # Parse book URLs (split by comma, space, or newline)
        import re
        url_pattern = r'https?://[^\s,]+'
        urls = re.findall(url_pattern, book_urls)
        
        if not urls:
            await interaction.followup.send(
                "❌ No valid URLs found. Please provide Royal Road book URLs separated by commas or spaces.",
                ephemeral=True
            )
            return
        
        if len(urls) > 5:
            await interaction.followup.send(
                "❌ Too many books! You can claim up to 5 books at once.\n"
                f"You provided {len(urls)} URLs. Please try again with 5 or fewer.",
                ephemeral=True
            )
            return
        
        # Validate all URLs first
        valid_books = []
        for url in urls:
            rr_book_id = self.extract_rr_book_id(url)
            if rr_book_id:
                valid_books.append((url, rr_book_id))
            else:
                await interaction.followup.send(
                    f"❌ Invalid Royal Road URL: {url}\n"
                    "All URLs must be valid Royal Road book links.",
                    ephemeral=True
                )
                return
        
        # Submit all claims
        results = []
        errors = []
        
        for book_url, rr_book_id in valid_books:
            try:
                url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-claim/submit"
                data = {
                    'bot_token': self.wp_bot_token,
                    'discord_user_id': str(interaction.user.id),
                    'discord_username': interaction.user.name,
                    'server_id': str(interaction.guild.id) if interaction.guild else None,
                    'server_name': interaction.guild.name if interaction.guild else "DM",
                    'book_url': book_url,
                    'royal_road_book_id': rr_book_id,
                    'discord_server_url': discord_server_url,
                    'royal_road_user_id': royal_road_user_id,
                    'patreon_user_id': patreon_user_id,
                    'kindle_author_asin': kindle_author_asin,
                    'scribble_hub_user_id': scribble_hub_user_id,
                    'batch_claim': True  # Flag for batch processing
                }
                
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.wp_bot_token}',
                    'User-Agent': 'Essence-Discord-Bot/1.0'
                }
                
                async with self.session.post(url, json=data, headers=headers) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get('success'):
                        results.append({
                            'title': result.get('book_title', 'Unknown'),
                            'claim_id': result.get('claim_id'),
                            'status': 'submitted'
                        })
                    elif result.get('error') == 'already_claimed':
                        errors.append(f"**{result.get('book_title', 'Unknown')}**: Already claimed by {result.get('owner_name')}")
                    elif result.get('error') == 'pending_claim':
                        errors.append(f"**{result.get('book_title', 'Unknown')}**: You already have a pending claim")
                    else:
                        errors.append(f"**Book ID {rr_book_id}**: {result.get('message', 'Unknown error')}")
                        
            except Exception as e:
                logger.error(f"[BOOK_CLAIM_MODULE] Error claiming book {rr_book_id}: {e}")
                errors.append(f"**Book ID {rr_book_id}**: Failed to submit")
        
        # Create response embed
        embed = discord.Embed(
            title="📚 Multiple Book Claim Results",
            color=discord.Color.blue() if results else discord.Color.red()
        )
        
        if results:
            success_text = "\n".join([f"✅ **{r['title']}** - Claim #{r['claim_id']}" for r in results])
            embed.add_field(
                name=f"Successfully Submitted ({len(results)})",
                value=success_text[:1024],  # Discord field limit
                inline=False
            )
        
        if errors:
            error_text = "\n".join([f"❌ {e}" for e in errors])
            embed.add_field(
                name=f"Failed ({len(errors)})",
                value=error_text[:1024],  # Discord field limit
                inline=False
            )
        
        # Check server verification status
        server_verified = await self.check_server_verification(interaction.guild.id if interaction.guild else None)
        
        if not server_verified and results:
            embed.add_field(
                name="⚠️ Server Not Verified",
                value=(
                    "This server is not verified for claim approvals.\n"
                    "Join [Stepan's Discord](https://discord.gg/xvw9vbvrwj) to get your claims reviewed."
                ),
                inline=False
            )
            
            # Public notification for unverified servers
            if len(results) > 0:
                await interaction.followup.send(
                    f"📢 **Multiple Claims Submitted!**\n"
                    f"{interaction.user.mention} has submitted {len(results)} book claim(s).\n\n"
                    "⚠️ This server is not verified. Visit [Stepan's Discord](https://discord.gg/xvw9vbvrwj) for claim reviews.",
                    ephemeral=False
                )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def manage_claims(self, interaction: discord.Interaction, action: str, claim_id: Optional[int]):
        """Handle claim approval/rejection (admin/mod only)"""
        await interaction.response.defer(ephemeral=True)
        
        # Check user permissions
        is_authorized = await self.check_user_authorization(interaction.user)
        if not is_authorized:
            await interaction.followup.send(
                "❌ You don't have permission to manage book claims.\n"
                "This command is only available to administrators and moderators.",
                ephemeral=True
            )
            return
        
        try:
            if action == "view":
                # Get pending claims
                url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-claim/pending"
                params = {
                    'bot_token': self.wp_bot_token,
                    'discord_user_id': str(interaction.user.id)
                }
                
                headers = {
                    'Authorization': f'Bearer {self.wp_bot_token}',
                    'User-Agent': 'Essence-Discord-Bot/1.0'
                }
                
                async with self.session.get(url, params=params, headers=headers) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get('success'):
                        claims = result.get('claims', [])
                        
                        if not claims:
                            await interaction.followup.send(
                                "✅ No pending claims to review.",
                                ephemeral=True
                            )
                            return
                        
                        # Create paginated embed for pending claims
                        embed = discord.Embed(
                            title="📋 Pending Book Claims",
                            description=f"Found {len(claims)} pending claim(s)",
                            color=discord.Color.blue()
                        )
                        
                        for claim in claims[:10]:  # Show first 10
                            embed.add_field(
                                name=f"Claim #{claim['id']} - {claim['book_title']}",
                                value=(
                                    f"**User:** {claim['discord_username']}\n"
                                    f"**Book:** [Link]({claim['book_url']})\n"
                                    f"**Submitted:** {claim['created_at']}"
                                ),
                                inline=False
                            )
                        
                        if len(claims) > 10:
                            embed.set_footer(text=f"Showing 10 of {len(claims)} claims")
                        
                        await interaction.followup.send(embed=embed, ephemeral=True)
                    else:
                        await interaction.followup.send(
                            "❌ Failed to retrieve pending claims.",
                            ephemeral=True
                        )
                        
            elif action in ["approve", "decline"]:
                if not claim_id:
                    await interaction.followup.send(
                        f"❌ Please provide a claim ID to {action}.",
                        ephemeral=True
                    )
                    return
                
                # Process claim approval/rejection
                url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-claim/process"
                data = {
                    'bot_token': self.wp_bot_token,
                    'claim_id': claim_id,
                    'action': action,
                    'processor_discord_id': str(interaction.user.id),
                    'processor_discord_username': interaction.user.name,
                    'processor_server_id': str(interaction.guild.id) if interaction.guild else None,
                    'processor_server_name': interaction.guild.name if interaction.guild else "DM"
                }
                
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.wp_bot_token}',
                    'User-Agent': 'Essence-Discord-Bot/1.0'
                }
                
                async with self.session.post(url, json=data, headers=headers) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get('success'):
                        status_emoji = "✅" if action == "approve" else "❌"
                        status_text = "approved" if action == "approve" else "declined"
                        
                        embed = discord.Embed(
                            title=f"{status_emoji} Claim {status_text.capitalize()}",
                            description=f"Claim #{claim_id} has been {status_text}.",
                            color=discord.Color.green() if action == "approve" else discord.Color.red()
                        )
                        embed.add_field(name="Book", value=result.get('book_title', 'Unknown'), inline=True)
                        embed.add_field(name="Claimant", value=result.get('claimant_username', 'Unknown'), inline=True)
                        
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        
                        # Notify the claimant
                        await self.notify_claimant(result.get('claimant_discord_id'), claim_id, action, result.get('book_title'))
                        
                    else:
                        error_msg = result.get('message', 'Unknown error')
                        await interaction.followup.send(
                            f"❌ Failed to {action} claim: {error_msg}",
                            ephemeral=True
                        )
                        
        except Exception as e:
            logger.error(f"[BOOK_CLAIM_MODULE] Error managing claims: {e}")
            await interaction.followup.send(
                "❌ An error occurred while processing the claim.",
                ephemeral=True
            )
    
    async def show_user_books(self, interaction: discord.Interaction, user: Optional[discord.User]):
        """Display user's claimed books and statistics"""
        await interaction.response.defer()
        
        target_user = user or interaction.user
        
        try:
            # Get user's books from WordPress
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-claim/user-books"
            params = {
                'bot_token': self.wp_bot_token,
                'discord_user_id': str(target_user.id)
            }
            
            headers = {
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            async with self.session.get(url, params=params, headers=headers) as response:
                result = await response.json()
                
                if response.status == 200 and result.get('success'):
                    books = result.get('books', [])
                    
                    if not books:
                        embed = discord.Embed(
                            title=f"📚 {target_user.display_name}'s Books",
                            description="No claimed books found.",
                            color=discord.Color.greyple()
                        )
                        await interaction.followup.send(embed=embed)
                        return
                    
                    # Create rich embed with book statistics
                    embed = discord.Embed(
                        title=f"📚 {target_user.display_name}'s Royal Road Books",
                        description=f"Managing {len(books)} book(s)",
                        color=discord.Color.blue()
                    )
                    
                    total_followers = 0
                    total_views = 0
                    
                    for book in books[:5]:  # Show first 5 books
                        # Format statistics
                        followers = self.format_number(book.get('followers', 0))
                        views = self.format_number(book.get('total_views', 0))
                        rating = book.get('rating', 'N/A')
                        
                        # Rising Stars info
                        rs_info = "Not in Rising Stars"
                        if book.get('rising_stars_rank'):
                            rs_info = f"🌟 Rising Stars #{book['rising_stars_rank']}"
                        
                        embed.add_field(
                            name=book['title'],
                            value=(
                                f"**Author:** {book.get('author', 'Unknown')}\n"
                                f"**Followers:** {followers} | **Views:** {views}\n"
                                f"**Rating:** ⭐ {rating}\n"
                                f"**Status:** {rs_info}\n"
                                f"[Read on Royal Road]({book['url']})"
                            ),
                            inline=False
                        )
                        
                        total_followers += book.get('followers', 0)
                        total_views += book.get('total_views', 0)
                    
                    if len(books) > 5:
                        embed.add_field(
                            name="",
                            value=f"*...and {len(books) - 5} more book(s)*",
                            inline=False
                        )
                    
                    # Add summary statistics
                    embed.set_footer(
                        text=f"Total: {self.format_number(total_followers)} followers | {self.format_number(total_views)} views"
                    )
                    
                    # Set thumbnail to user's avatar
                    embed.set_thumbnail(url=target_user.display_avatar.url)
                    
                    await interaction.followup.send(embed=embed)
                    
                else:
                    await interaction.followup.send(
                        f"❌ Failed to retrieve books: {result.get('message', 'Unknown error')}",
                        ephemeral=True
                    )
                    
        except Exception as e:
            logger.error(f"[BOOK_CLAIM_MODULE] Error fetching user books: {e}")
            await interaction.followup.send(
                "❌ An error occurred while fetching books.",
                ephemeral=True
            )
    
    # Helper methods
    
    def extract_rr_book_id(self, url: str) -> Optional[int]:
        """Extract Royal Road book ID from URL"""
        patterns = [
            r'royalroad\.com/fiction/(\d+)',
            r'fiction/(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return int(match.group(1))
        return None
    
    def validate_discord_url(self, url: str) -> bool:
        """Validate Discord invite URL"""
        patterns = [
            r'discord\.gg/[a-zA-Z0-9]+',
            r'discord\.com/invite/[a-zA-Z0-9]+',
            r'discordapp\.com/invite/[a-zA-Z0-9]+'
        ]
        
        for pattern in patterns:
            if re.search(pattern, url):
                return True
        return False
    
    async def check_user_authorization(self, user: discord.User) -> bool:
        """Check if user has admin/mod permissions"""
        try:
            # Check with WordPress API for user roles
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-claim/check-authorization"
            params = {
                'bot_token': self.wp_bot_token,
                'discord_user_id': str(user.id)
            }
            
            headers = {
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('authorized', False)
                    
        except Exception as e:
            logger.error(f"[BOOK_CLAIM_MODULE] Error checking authorization: {e}")
        
        return False
    
    async def check_server_verification(self, server_id: Optional[str]) -> bool:
        """Check if server is verified for claim processing"""
        if not server_id:
            return False
            
        try:
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-claim/check-server"
            params = {
                'bot_token': self.wp_bot_token,
                'server_id': server_id
            }
            
            headers = {
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('verified', False)
                    
        except Exception as e:
            logger.error(f"[BOOK_CLAIM_MODULE] Error checking server verification: {e}")
        
        return False
    
    async def notify_admins_of_new_claim(self, guild: discord.Guild, claim_id: int, 
                                         book_title: str, user: discord.User):
        """Notify administrators of new claim requests in configured channel"""
        if not guild:
            return
            
        try:
            # Get configured notification channel from WordPress
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-claim/notification-channel"
            params = {
                'bot_token': self.wp_bot_token,
                'server_id': str(guild.id)
            }
            
            headers = {
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    channel_id = result.get('channel_id')
                    
                    if channel_id:
                        channel = guild.get_channel(int(channel_id))
                        if channel:
                            embed = discord.Embed(
                                title="📋 New Book Claim Request",
                                description=f"A new claim has been submitted for review.",
                                color=discord.Color.blue()
                            )
                            embed.add_field(name="Claim ID", value=f"`#{claim_id}`", inline=True)
                            embed.add_field(name="Book", value=book_title, inline=True)
                            embed.add_field(name="Claimant", value=f"{user.mention} ({user.name})", inline=False)
                            embed.add_field(
                                name="Action Required",
                                value="Use `/rr-claim-approve action:View Pending` to review",
                                inline=False
                            )
                            embed.set_footer(text=f"Submitted at {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
                            
                            await channel.send(embed=embed)
                            logger.info(f"[BOOK_CLAIM_MODULE] Notified admins in channel {channel_id}")
                            
        except Exception as e:
            logger.error(f"[BOOK_CLAIM_MODULE] Failed to notify admins: {e}")
    
    async def notify_claimant(self, discord_id: str, claim_id: int, action: str, book_title: str):
        """Send DM to claimant about their claim status"""
        try:
            user = await self.bot.fetch_user(int(discord_id))
            if user:
                status_emoji = "✅" if action == "approve" else "❌"
                status_text = "approved" if action == "approve" else "declined"
                
                embed = discord.Embed(
                    title=f"{status_emoji} Your Book Claim Has Been {status_text.capitalize()}",
                    description=f"Your claim (#{claim_id}) for **{book_title}** has been {status_text}.",
                    color=discord.Color.green() if action == "approve" else discord.Color.red()
                )
                
                if action == "approve":
                    embed.add_field(
                        name="What's Next?",
                        value="You can now use `/rr-my-books` to view your claimed books and their statistics.",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Need Help?",
                        value="If you believe this was a mistake, please contact an administrator in [Stepan's Discord](https://discord.gg/xvw9vbvrwj).",
                        inline=False
                    )
                
                await user.send(embed=embed)
                logger.info(f"[BOOK_CLAIM_MODULE] Notified {user.name} about claim #{claim_id} {status_text}")
                
        except Exception as e:
            logger.error(f"[BOOK_CLAIM_MODULE] Failed to notify user {discord_id}: {e}")
    
    def format_number(self, num: int) -> str:
        """Format large numbers with K/M suffixes"""
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num/1_000:.1f}K"
        return str(num)
