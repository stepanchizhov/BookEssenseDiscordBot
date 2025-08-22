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
import random

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
        
        # Initialize command counter for promotional messages
        self.command_counter = 0
        
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
            book_identifier="Royal Road book URL or ID (e.g., https://www.royalroad.com/fiction/12345 or 12345)",
            discord_server_url="Your Discord server URL (optional)",
            royal_road_user_id="Your Royal Road user ID (optional)",
            patreon_user_id="Your Patreon username (optional)",
            kindle_author_asin="Your Amazon Kindle author ASIN (optional)",
            scribble_hub_user_id="Your Scribble Hub user ID (optional)"
        )
        async def rr_claim_book(
            interaction: discord.Interaction,
            book_identifier: str,
            discord_server_url: Optional[str] = None,
            royal_road_user_id: Optional[str] = None,
            patreon_user_id: Optional[str] = None,
            kindle_author_asin: Optional[str] = None,
            scribble_hub_user_id: Optional[str] = None
        ):
            await self.claim_book(
                interaction, book_identifier, discord_server_url, royal_road_user_id,
                patreon_user_id, kindle_author_asin, scribble_hub_user_id
            )
        
        # Multiple book claim command - available to all users
        @self.bot.tree.command(
            name="rr-claim-multiple",
            description="Claim ownership of multiple Royal Road books (up to 5 at once)"
        )
        @discord.app_commands.describe(
            book_identifiers="Royal Road book URLs or IDs separated by commas or spaces (e.g., 12345, 67890 or URLs)",
            discord_server_url="Your Discord server URL (optional)",
            royal_road_user_id="Your Royal Road user ID (optional)",
            patreon_user_id="Your Patreon username (optional)",
            kindle_author_asin="Your Amazon Kindle author ASIN (optional)",
            scribble_hub_user_id="Your Scribble Hub user ID (optional)"
        )
        async def rr_claim_multiple(
            interaction: discord.Interaction,
            book_identifiers: str,
            discord_server_url: Optional[str] = None,
            royal_road_user_id: Optional[str] = None,
            patreon_user_id: Optional[str] = None,
            kindle_author_asin: Optional[str] = None,
            scribble_hub_user_id: Optional[str] = None
        ):
            await self.claim_multiple_books(
                interaction, book_identifiers, discord_server_url, royal_road_user_id,
                patreon_user_id, kindle_author_asin, scribble_hub_user_id
            )
        
        # Claim approval command - admin/mod only
        @self.bot.tree.command(
            name="rr-claim-approve",
            description="Approve or decline book ownership claims (Admin/Mod only)"
        )
        @discord.app_commands.describe(
            action="Action to take on the claim",
            claim_ids="Claim request ID(s) - single ID or comma-separated list (leave empty to see pending claims)"
        )
        @discord.app_commands.choices(action=[
            discord.app_commands.Choice(name="View Pending", value="view"),
            discord.app_commands.Choice(name="Approve", value="approve"),
            discord.app_commands.Choice(name="Decline", value="decline")
        ])
        async def rr_claim_approve(
            interaction: discord.Interaction,
            action: str,
            claim_ids: Optional[str] = None
        ):
            await self.manage_claims(interaction, action, claim_ids)
        
        # Set notification channel command - admin/mod only
        @self.bot.tree.command(
            name="rr-claim-set-channel",
            description="Set this channel for book claim notifications (Admin/Mod only)"
        )
        @discord.app_commands.describe(
            action="Enable or disable notifications in this channel"
        )
        @discord.app_commands.choices(action=[
            discord.app_commands.Choice(name="Enable notifications here", value="enable"),
            discord.app_commands.Choice(name="Disable notifications", value="disable"),
            discord.app_commands.Choice(name="Check current settings", value="check")
        ])
        async def rr_claim_set_channel(
            interaction: discord.Interaction,
            action: str
        ):
            await self.set_notification_channel(interaction, action)
        
        # Verify server command - bot admin only
        @self.bot.tree.command(
            name="rr-claim-verify-server",
            description="Verify this server for book claim processing (Bot Admin only)"
        )
        @discord.app_commands.describe(
            action="Action to take for this server"
        )
        @discord.app_commands.choices(action=[
            discord.app_commands.Choice(name="Verify this server", value="verify"),
            discord.app_commands.Choice(name="Unverify this server", value="unverify"),
            discord.app_commands.Choice(name="Check verification status", value="check")
        ])
        async def rr_claim_verify_server(
            interaction: discord.Interaction,
            action: str
        ):
            await self.verify_server(interaction, action)
        
        # Add moderator command - bot admin or supermod
        @self.bot.tree.command(
            name="rr-claim-add-moderator",
            description="Add or remove claim moderators for this server (Admin/Supermod only)"
        )
        @discord.app_commands.describe(
            user="User to add/remove as moderator",
            action="Add or remove moderator status",
            role="Role level to assign (Supermod only for supermod role)"
        )
        @discord.app_commands.choices(action=[
            discord.app_commands.Choice(name="Add as moderator", value="add"),
            discord.app_commands.Choice(name="Remove moderator", value="remove")
        ])
        @discord.app_commands.choices(role=[
            discord.app_commands.Choice(name="Moderator", value="moderator"),
            discord.app_commands.Choice(name="Supermod", value="supermod")
        ])
        async def rr_claim_add_moderator(
            interaction: discord.Interaction,
            user: discord.User,
            action: str,
            role: str = "moderator"
        ):
            await self.manage_moderator(interaction, user, action, role)
        
        # List moderators command - public
        @self.bot.tree.command(
            name="rr-claim-list-moderators",
            description="List all claim moderators for this server"
        )
        async def rr_claim_list_moderators(
            interaction: discord.Interaction
        ):
            await self.list_moderators(interaction)
        
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
    
    async def claim_book(self, interaction: discord.Interaction, book_identifier: str,
                         discord_server_url: Optional[str], royal_road_user_id: Optional[str],
                         patreon_user_id: Optional[str], kindle_author_asin: Optional[str],
                         scribble_hub_user_id: Optional[str]):
        """Handle book claim request"""
        await interaction.response.defer(ephemeral=True)
        
        logger.info(f"[BOOK_CLAIM_MODULE] Claim request from {interaction.user.name} for {book_identifier}")
        
        # Parse book identifier (URL or ID)
        rr_book_id, book_url = self.parse_book_identifier(book_identifier)
        
        if not rr_book_id:
            await interaction.followup.send(
                "❌ Invalid input. Please provide either:\n"
                "• A Royal Road book URL (e.g., `https://www.royalroad.com/fiction/12345/book-title`)\n"
                "• A Royal Road book ID (e.g., `12345`)",
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
                    embed.add_field(name="Book ID", value=f"`{rr_book_id}`", inline=True)
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
                            f"{interaction.user.mention} has submitted a claim for **{book_title}** (ID: {rr_book_id}).\n\n"
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
                    
                    # Send public notification to configured channel
                    await self.send_claim_notification(
                        interaction.guild, 
                        claim_id, 
                        book_title, 
                        rr_book_id,
                        interaction.user,
                        "submitted"
                    )
                    
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
    
    async def claim_multiple_books(self, interaction: discord.Interaction, book_identifiers: str,
                                   discord_server_url: Optional[str], royal_road_user_id: Optional[str],
                                   patreon_user_id: Optional[str], kindle_author_asin: Optional[str],
                                   scribble_hub_user_id: Optional[str]):
        """Handle multiple book claim requests"""
        await interaction.response.defer(ephemeral=True)
        
        # Parse book identifiers (URLs or IDs separated by various delimiters)
        import re
        
        # Split by common delimiters: comma, space, newline, semicolon
        potential_identifiers = re.split(r'[,\s\n;]+', book_identifiers)
        
        # Process each identifier
        valid_books = []
        for identifier in potential_identifiers:
            identifier = identifier.strip()
            if not identifier:
                continue
                
            rr_book_id, book_url = self.parse_book_identifier(identifier)
            if rr_book_id:
                valid_books.append((book_url, rr_book_id))
        
        if not valid_books:
            await interaction.followup.send(
                "❌ No valid book identifiers found. Please provide Royal Road book URLs or IDs separated by commas or spaces.\n"
                "Examples:\n"
                "• `12345, 67890, 11111`\n"
                "• `https://www.royalroad.com/fiction/12345 https://www.royalroad.com/fiction/67890`",
                ephemeral=True
            )
            return
        
        if len(valid_books) > 5:
            await interaction.followup.send(
                "❌ Too many books! You can claim up to 5 books at once.\n"
                f"You provided {len(valid_books)} books. Please try again with 5 or fewer.",
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
                            'title': result.get('book_title', f'Book {rr_book_id}'),
                            'claim_id': result.get('claim_id'),
                            'book_id': rr_book_id,
                            'status': 'submitted'
                        })
                    elif result.get('error') == 'already_claimed':
                        errors.append(f"**ID {rr_book_id}**: Already claimed by {result.get('owner_name')}")
                    elif result.get('error') == 'pending_claim':
                        errors.append(f"**ID {rr_book_id}**: You already have a pending claim")
                    else:
                        errors.append(f"**ID {rr_book_id}**: {result.get('message', 'Unknown error')}")
                        
            except Exception as e:
                logger.error(f"[BOOK_CLAIM_MODULE] Error claiming book {rr_book_id}: {e}")
                errors.append(f"**ID {rr_book_id}**: Failed to submit")
        
        # Create response embed
        embed = discord.Embed(
            title="📚 Multiple Book Claim Results",
            color=discord.Color.blue() if results else discord.Color.red()
        )
        
        if results:
            success_text = "\n".join([f"✅ **{r['title']}** (ID: {r['book_id']}) - Claim #{r['claim_id']}" for r in results])
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
                book_ids = ", ".join([str(r['book_id']) for r in results])
                await interaction.followup.send(
                    f"📢 **Multiple Claims Submitted!**\n"
                    f"{interaction.user.mention} has submitted {len(results)} book claim(s) for IDs: {book_ids}\n\n"
                    "⚠️ This server is not verified. Visit [Stepan's Discord](https://discord.gg/xvw9vbvrwj) for claim reviews.",
                    ephemeral=False
                )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def manage_claims(self, interaction: discord.Interaction, action: str, claim_ids: Optional[str]):
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
                # Check if user is bot admin
                is_bot_owner = await self.is_bot_admin(interaction.user)
                
                # Get pending claims
                url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-claim/pending"
                params = {
                    'bot_token': self.wp_bot_token,
                    'discord_user_id': str(interaction.user.id)
                }
                
                # Add server filter for non-admins
                if not is_bot_owner and interaction.guild:
                    params['server_id'] = str(interaction.guild.id)
                
                headers = {
                    'Authorization': f'Bearer {self.wp_bot_token}',
                    'User-Agent': 'Essence-Discord-Bot/1.0'
                }
                
                async with self.session.get(url, params=params, headers=headers) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get('success'):
                        all_claims = result.get('claims', [])
                        
                        # Filter claims by server for non-admins
                        if not is_bot_owner and interaction.guild:
                            claims = [
                                claim for claim in all_claims 
                                if claim.get('server_id') == str(interaction.guild.id)
                            ]
                        else:
                            claims = all_claims
                        
                        if not claims:
                            if not is_bot_owner and interaction.guild:
                                await interaction.followup.send(
                                    "✅ No pending claims to review in this server.",
                                    ephemeral=True
                                )
                            else:
                                await interaction.followup.send(
                                    "✅ No pending claims to review.",
                                    ephemeral=True
                                )
                            return
                        
                        # Create paginated embed for pending claims
                        title = "📋 Pending Book Claims"
                        if not is_bot_owner and interaction.guild:
                            title = f"📋 Pending Book Claims for {interaction.guild.name}"
                        
                        embed = discord.Embed(
                            title=title,
                            description=f"Found {len(claims)} pending claim(s)",
                            color=discord.Color.blue()
                        )
                        
                        for claim in claims[:10]:  # Show first 10
                            # Create Discord user mention
                            user_mention = f"<@{claim['discord_user_id']}>"
                            
                            # Format the field with Discord mention
                            field_value = (
                                f"**Claimant:** {user_mention}\n"
                                f"**Book:** [View on RR]({claim['book_url']})\n"
                                f"**Server:** {claim.get('server_name', 'Unknown')}\n"
                                f"**Submitted:** {claim['created_at']}"
                            )
                            
                            embed.add_field(
                                name=f"Claim #{claim['id']} - {claim['book_title']}",
                                value=field_value,
                                inline=False
                            )
                        
                        if len(claims) > 10:
                            embed.set_footer(text=f"Showing 10 of {len(claims)} claims | Use claim IDs to process")
                        else:
                            embed.set_footer(text="Use `/rr-claim-approve action:Approve/Decline claim_ids:NUMBER` or comma-separated list to process")
                        
                        await interaction.followup.send(embed=embed, ephemeral=True)
                    else:
                        await interaction.followup.send(
                            "❌ Failed to retrieve pending claims.",
                            ephemeral=True
                        )
                        
            elif action in ["approve", "decline"]:
                if not claim_ids:
                    await interaction.followup.send(
                        f"❌ Please provide claim ID(s) to {action}.\n"
                        f"Example: `/rr-claim-approve action:{action.capitalize()} claim_ids:123` or `claim_ids:123,456,789`",
                        ephemeral=True
                    )
                    return
                
                # Parse multiple claim IDs
                import re
                claim_id_list = []
                
                # Split by comma, space, or semicolon
                potential_ids = re.split(r'[,\s;]+', claim_ids.strip())
                for id_str in potential_ids:
                    id_str = id_str.strip()
                    if id_str.isdigit():
                        claim_id_list.append(int(id_str))
                
                if not claim_id_list:
                    await interaction.followup.send(
                        f"❌ No valid claim IDs found. Please provide numeric IDs.\n"
                        f"Example: `123` or `123,456,789`",
                        ephemeral=True
                    )
                    return
                
                # Process each claim
                success_count = 0
                failed_claims = []
                
                # Send initial acknowledgment for multiple claims
                if len(claim_id_list) > 1:
                    await interaction.followup.send(
                        f"Processing {len(claim_id_list)} claim(s)...",
                        ephemeral=True
                    )
                else:
                    # For single claim, just acknowledge silently
                    await interaction.followup.send(
                        f"Processing claim #{claim_id_list[0]}...",
                        ephemeral=True
                    )
                
                for claim_id in claim_id_list:
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
                            
                            # Create Discord mentions for the claimant and processor
                            claimant_mention = f"<@{result.get('claimant_discord_id')}>"
                            processor_mention = f"<@{interaction.user.id}>"
                            
                            embed = discord.Embed(
                                title=f"{status_emoji} Claim {status_text.capitalize()}",
                                description=f"Claim #{claim_id} has been {status_text}.",
                                color=discord.Color.green() if action == "approve" else discord.Color.red()
                            )
                            embed.add_field(name="Book", value=result.get('book_title', 'Unknown'), inline=True)
                            embed.add_field(name="Claimant", value=claimant_mention, inline=True)
                            embed.add_field(name="Processed by", value=processor_mention, inline=True)
                            
                            # Send PUBLIC message for each processed claim
                            # Use followup.send with ephemeral=False for public visibility
                            await interaction.followup.send(embed=embed, ephemeral=False)
                            
                            success_count += 1
                            
                            # Send notification if claim was approved
                            if action == "approve":
                                # Try to get the guild where the claim was made
                                claim_guild = None
                                if result.get('claim_server_id'):
                                    claim_guild = self.bot.get_guild(int(result['claim_server_id']))
                                
                                if claim_guild:
                                    await self.send_claim_notification(
                                        claim_guild,
                                        claim_id,
                                        result.get('book_title'),
                                        result.get('royal_road_book_id'),
                                        None,  # We'll fetch the user by ID
                                        "approved",
                                        result.get('claimant_discord_id')
                                    )
                            
                            # Notify the claimant via DM
                            await self.notify_claimant(result.get('claimant_discord_id'), claim_id, action, result.get('book_title'))
                            
                        else:
                            error_msg = result.get('message', 'Unknown error')
                            failed_claims.append(f"Claim #{claim_id}: {error_msg}")
                
                # Send summary if there were failures
                if failed_claims and len(claim_id_list) > 1:
                    error_embed = discord.Embed(
                        title="⚠️ Some claims could not be processed",
                        description="\n".join(failed_claims),
                        color=discord.Color.orange()
                    )
                    await interaction.followup.send(embed=error_embed, ephemeral=False)
                        
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
        
        logger.info(f"[BOOK_CLAIM_MODULE] Fetching books for user: {target_user.name} (ID: {target_user.id})")
        
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
            
            logger.info(f"[BOOK_CLAIM_MODULE] Making request to: {url}")
            logger.info(f"[BOOK_CLAIM_MODULE] With discord_user_id: {params['discord_user_id']}")
            
            async with self.session.get(url, params=params, headers=headers) as response:
                result = await response.json()
                
                logger.info(f"[BOOK_CLAIM_MODULE] Response status: {response.status}")
                logger.info(f"[BOOK_CLAIM_MODULE] Response data: {json.dumps(result, indent=2)}")
                
                if response.status == 200 and result.get('success'):
                    books = result.get('books', [])
                    total_count = result.get('total_count', len(books))
                    
                    logger.info(f"[BOOK_CLAIM_MODULE] Found {total_count} books")
                    
                    if not books:
                        embed = discord.Embed(
                            title=f"📚 {target_user.display_name}'s Books",
                            description="No claimed books found.",
                            color=discord.Color.greyple()
                        )
                        
                        # Add debug information only if it's the user checking their own books
                        if target_user.id == interaction.user.id:
                            embed.add_field(
                                name="No books?",
                                value=(
                                    "If you believe you should have books showing:\n"
                                    "• Make sure your claims have been approved\n"
                                    "• Use `/rr-claim-book` to submit a claim\n"
                                    "• Contact an admin if you need help"
                                ),
                                inline=False
                            )
                            # Only show Discord ID in logs, not in the embed
                            logger.info(f"[BOOK_CLAIM_MODULE] No books found for Discord ID: {target_user.id}")
                        
                        await interaction.followup.send(embed=embed)
                        return
                    
                    # Create rich embed with book statistics
                    embed = discord.Embed(
                        title=f"📚 {target_user.display_name}'s Royal Road Books",
                        description=f"Has {len(books)} book(s)",
                        color=discord.Color.blue()
                    )
                    
                    total_followers = 0
                    total_views = 0
                    
                    for book in books[:5]:  # Show first 5 books
                        # Format statistics
                        followers = self.format_number(book.get('followers', 0))
                        views = self.format_number(book.get('total_views', 0))
                        
                        # Handle rating - check both 'rating' and 'overall_score' fields
                        rating = book.get('rating') or book.get('overall_score')
                        if rating and rating > 0:
                            rating_display = f"{rating:.2f}" if isinstance(rating, (int, float)) else str(rating)
                        else:
                            rating_display = "N/A"
                        
                        chapters = book.get('chapters', 0)
                        status = book.get('status', 'Unknown')
                        
                        # Build the book field value
                        field_value = (
                            f"**Author:** {book.get('author', 'Unknown')}\n"
                            f"**Followers:** {followers} | **Views:** {views}\n"
                            f"**Rating:** ⭐ {rating_display} | **Chapters:** {chapters}\n"
                            f"**Status:** {status}\n"
                            f"[Read on Royal Road]({book['url']})"
                        )
                        
                        embed.add_field(
                            name=book['title'],
                            value=field_value,
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
                    error_msg = result.get('message', 'Unknown error')
                    logger.error(f"[BOOK_CLAIM_MODULE] Failed to retrieve books: {error_msg}")
                    
                    await interaction.followup.send(
                        f"❌ Failed to retrieve books: {error_msg}",
                        ephemeral=True
                    )
                    
        except Exception as e:
            logger.error(f"[BOOK_CLAIM_MODULE] Error fetching user books: {e}")
            import traceback
            logger.error(f"[BOOK_CLAIM_MODULE] Traceback: {traceback.format_exc()}")
            
            await interaction.followup.send(
                "❌ An error occurred while fetching books. Please try again later.",
                ephemeral=True
            )
    
    # Helper methods
    
    def parse_book_identifier(self, identifier: str) -> Tuple[Optional[int], str]:
        """
        Parse book identifier which can be either a URL or just an ID
        Returns: (book_id, book_url) tuple
        """
        identifier = identifier.strip()
        
        # First check if it's just a number (book ID)
        if identifier.isdigit():
            book_id = int(identifier)
            book_url = f"https://www.royalroad.com/fiction/{book_id}"
            return book_id, book_url
        
        # Check if it's a URL
        rr_book_id = self.extract_rr_book_id(identifier)
        if rr_book_id:
            return rr_book_id, identifier
        
        # Check if it's a number with some extra characters (e.g., "#12345" or "ID:12345")
        import re
        match = re.search(r'\b(\d+)\b', identifier)
        if match:
            book_id = int(match.group(1))
            # Verify it's a reasonable book ID (not too small, not too large)
            if 1 <= book_id <= 9999999:
                book_url = f"https://www.royalroad.com/fiction/{book_id}"
                return book_id, book_url
        
        return None, ""
    
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
    
    async def set_notification_channel(self, interaction: discord.Interaction, action: str):
        """Set or update the notification channel for book claims"""
        await interaction.response.defer(ephemeral=True)
        
        # Check if this is in a guild
        if not interaction.guild:
            await interaction.followup.send(
                "❌ This command can only be used in a server channel.",
                ephemeral=True
            )
            return
        
        # Check user permissions (must be admin/mod)
        is_authorized = await self.check_user_authorization(interaction.user)
        if not is_authorized:
            # Also check Discord server permissions as fallback
            if not interaction.user.guild_permissions.manage_guild:
                await interaction.followup.send(
                    "❌ You need Administrator or Manage Server permissions to configure notifications.\n"
                    "Or be registered as a moderator in the book claim system.",
                    ephemeral=True
                )
                return
        
        try:
            if action == "check":
                # Check current settings
                url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-claim/notification-channel"
                params = {
                    'bot_token': self.wp_bot_token,
                    'server_id': str(interaction.guild.id)
                }
                
                headers = {
                    'Authorization': f'Bearer {self.wp_bot_token}',
                    'User-Agent': 'Essence-Discord-Bot/1.0'
                }
                
                async with self.session.get(url, params=params, headers=headers) as response:
                    result = await response.json()
                    
                    embed = discord.Embed(
                        title="📋 Notification Channel Settings",
                        color=discord.Color.blue()
                    )
                    
                    if result.get('channel_id'):
                        channel = interaction.guild.get_channel(int(result['channel_id']))
                        if channel:
                            embed.add_field(
                                name="Current Channel",
                                value=f"{channel.mention}",
                                inline=False
                            )
                        else:
                            embed.add_field(
                                name="Current Channel",
                                value=f"Channel ID {result['channel_id']} (channel not found)",
                                inline=False
                            )
                    else:
                        embed.add_field(
                            name="Current Channel",
                            value="❌ No notification channel set",
                            inline=False
                        )
                    
                    # Check if server is verified
                    server_verified = await self.check_server_verification(str(interaction.guild.id))
                    embed.add_field(
                        name="Server Status",
                        value="✅ Verified" if server_verified else "❌ Not Verified",
                        inline=True
                    )
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    
            elif action == "enable":
                # Set this channel as notification channel
                url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-claim/set-notification-channel"
                data = {
                    'bot_token': self.wp_bot_token,
                    'server_id': str(interaction.guild.id),
                    'server_name': interaction.guild.name,
                    'channel_id': str(interaction.channel.id),
                    'channel_name': interaction.channel.name,
                    'set_by_discord_id': str(interaction.user.id),
                    'set_by_discord_username': interaction.user.name
                }
                
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.wp_bot_token}',
                    'User-Agent': 'Essence-Discord-Bot/1.0'
                }
                
                async with self.session.post(url, json=data, headers=headers) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get('success'):
                        embed = discord.Embed(
                            title="✅ Notification Channel Set",
                            description=f"Book claim notifications will now be sent to {interaction.channel.mention}",
                            color=discord.Color.green()
                        )
                        
                        if not result.get('server_verified'):
                            embed.add_field(
                                name="⚠️ Server Not Verified",
                                value=(
                                    "Your server is not yet verified for processing claims.\n"
                                    "Contact an administrator in [Stepan's Discord](https://discord.gg/xvw9vbvrwj) to request verification."
                                ),
                                inline=False
                            )
                        else:
                            embed.add_field(
                                name="What's Next?",
                                value=(
                                    "• New claim notifications will appear here\n"
                                    "• Use `/rr-claim-approve` to manage claims\n"
                                    "• Moderators can process claims from this server"
                                ),
                                inline=False
                            )
                        
                        await interaction.followup.send(embed=embed, ephemeral=False)
                        
                        # Send a test notification
                        test_embed = discord.Embed(
                            title="🔔 Notification Channel Configured",
                            description="This channel will now receive book claim notifications.",
                            color=discord.Color.blue()
                        )
                        test_embed.set_footer(text=f"Configured by {interaction.user.name}")
                        await interaction.channel.send(embed=test_embed)
                        
                    else:
                        error_msg = result.get('message', 'Failed to set notification channel')
                        await interaction.followup.send(
                            f"❌ {error_msg}",
                            ephemeral=True
                        )
                        
            elif action == "disable":
                # Remove notification channel
                url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-claim/remove-notification-channel"
                data = {
                    'bot_token': self.wp_bot_token,
                    'server_id': str(interaction.guild.id),
                    'removed_by_discord_id': str(interaction.user.id),
                    'removed_by_discord_username': interaction.user.name
                }
                
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.wp_bot_token}',
                    'User-Agent': 'Essence-Discord-Bot/1.0'
                }
                
                async with self.session.post(url, json=data, headers=headers) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get('success'):
                        embed = discord.Embed(
                            title="✅ Notifications Disabled",
                            description="Book claim notifications have been disabled for this server.",
                            color=discord.Color.orange()
                        )
                        await interaction.followup.send(embed=embed, ephemeral=True)
                    else:
                        error_msg = result.get('message', 'Failed to disable notifications')
                        await interaction.followup.send(
                            f"❌ {error_msg}",
                            ephemeral=True
                        )
                        
        except Exception as e:
            logger.error(f"[BOOK_CLAIM_MODULE] Error setting notification channel: {e}")
            await interaction.followup.send(
                "❌ An error occurred while configuring the notification channel.",
                ephemeral=True
            )
    
    async def verify_server(self, interaction: discord.Interaction, action: str):
        """Verify or unverify a server for claim processing (Bot admin only)"""
        await interaction.response.defer(ephemeral=True)
        
        # Check if user is bot administrator
        if not await self.is_bot_admin(interaction.user):
            await interaction.followup.send(
                "❌ Only bot administrators can verify servers.",
                ephemeral=True
            )
            return
        
        if not interaction.guild:
            await interaction.followup.send(
                "❌ This command can only be used in a server.",
                ephemeral=True
            )
            return
        
        try:
            if action == "check":
                # Check current verification status
                verified = await self.check_server_verification(str(interaction.guild.id))
                
                embed = discord.Embed(
                    title="🔍 Server Verification Status",
                    color=discord.Color.green() if verified else discord.Color.orange()
                )
                embed.add_field(
                    name="Status",
                    value="✅ Verified" if verified else "❌ Not Verified",
                    inline=False
                )
                embed.add_field(
                    name="Server",
                    value=f"{interaction.guild.name}\nID: {interaction.guild.id}",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            elif action == "verify":
                # Verify the server
                url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-claim/verify-server"
                data = {
                    'bot_token': self.wp_bot_token,
                    'server_id': str(interaction.guild.id),
                    'server_name': interaction.guild.name,
                    'verified_by_discord_id': str(interaction.user.id),
                    'verified_by_discord_username': interaction.user.name,
                    'verify': True
                }
                
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.wp_bot_token}',
                    'User-Agent': 'Essence-Discord-Bot/1.0'
                }
                
                async with self.session.post(url, json=data, headers=headers) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get('success'):
                        embed = discord.Embed(
                            title="✅ Server Verified",
                            description=f"{interaction.guild.name} is now verified for claim processing.",
                            color=discord.Color.green()
                        )
                        embed.add_field(
                            name="What this means",
                            value=(
                                "• Moderators can process claims locally\n"
                                "• Claims don't require external approval\n"
                                "• Notifications work in configured channels"
                            ),
                            inline=False
                        )
                        
                        await interaction.followup.send(embed=embed, ephemeral=False)
                    else:
                        await interaction.followup.send(
                            f"❌ Failed to verify server: {result.get('message', 'Unknown error')}",
                            ephemeral=True
                        )
                        
            elif action == "unverify":
                # Unverify the server
                url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-claim/verify-server"
                data = {
                    'bot_token': self.wp_bot_token,
                    'server_id': str(interaction.guild.id),
                    'verified_by_discord_id': str(interaction.user.id),
                    'verified_by_discord_username': interaction.user.name,
                    'verify': False
                }
                
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.wp_bot_token}',
                    'User-Agent': 'Essence-Discord-Bot/1.0'
                }
                
                async with self.session.post(url, json=data, headers=headers) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get('success'):
                        await interaction.followup.send(
                            f"✅ Server {interaction.guild.name} has been unverified.",
                            ephemeral=True
                        )
                    else:
                        await interaction.followup.send(
                            f"❌ Failed to unverify server: {result.get('message', 'Unknown error')}",
                            ephemeral=True
                        )
                        
        except Exception as e:
            logger.error(f"[BOOK_CLAIM_MODULE] Error verifying server: {e}")
            await interaction.followup.send(
                "❌ An error occurred while processing server verification.",
                ephemeral=True
            )
    
    async def manage_moderator(self, interaction: discord.Interaction, user: discord.User, action: str, role: str = "moderator"):
        """Add or remove moderators for this server (Bot admin or supermod)"""
        await interaction.response.defer(ephemeral=True)
        
        # Check if user is bot administrator or supermod
        is_admin = await self.is_bot_admin(interaction.user)
        is_supermod = await self.is_server_supermod(interaction.user, interaction.guild.id if interaction.guild else None)
        
        if not is_admin and not is_supermod:
            await interaction.followup.send(
                "❌ Only bot administrators or server supermods can manage moderators.",
                ephemeral=True
            )
            return
        
        # Only bot admins can assign supermod role
        if role == "supermod" and not is_admin:
            await interaction.followup.send(
                "❌ Only bot administrators can assign supermod role.",
                ephemeral=True
            )
            return
        
        if not interaction.guild:
            await interaction.followup.send(
                "❌ This command can only be used in a server.",
                ephemeral=True
            )
            return
        
        try:
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-claim/manage-moderator"
            data = {
                'bot_token': self.wp_bot_token,
                'server_id': str(interaction.guild.id),
                'server_name': interaction.guild.name,
                'moderator_discord_id': str(user.id),
                'moderator_discord_username': user.name,
                'action': action,
                'role': role,
                'added_by_discord_id': str(interaction.user.id),
                'added_by_discord_username': interaction.user.name
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            async with self.session.post(url, json=data, headers=headers) as response:
                result = await response.json()
                
                if response.status == 200 and result.get('success'):
                    if action == "add":
                        role_display = "supermod" if role == "supermod" else "moderator"
                        embed = discord.Embed(
                            title=f"✅ {role_display.capitalize()} Added",
                            description=f"{user.mention} is now a {role_display} for {interaction.guild.name}",
                            color=discord.Color.green()
                        )
                        
                        permissions = [
                            "• Can view pending claims",
                            "• Can approve/decline claims",
                            "• Can set notification channels"
                        ]
                        
                        if role == "supermod":
                            permissions.append("• Can add/remove moderators")
                            permissions.append("• Can manage server settings")
                        
                        embed.add_field(
                            name="Permissions",
                            value="\n".join(permissions),
                            inline=False
                        )
                        
                        # Send DM to the new moderator
                        try:
                            dm_embed = discord.Embed(
                                title=f"🎉 You've been added as a {role_display}!",
                                description=f"You are now a {role_display} for **{interaction.guild.name}**",
                                color=discord.Color.green()
                            )
                            dm_embed.add_field(
                                name="Added by",
                                value=f"{interaction.user.mention} ({interaction.user.name})",
                                inline=False
                            )
                            dm_embed.add_field(
                                name="Your Permissions",
                                value="\n".join(permissions),
                                inline=False
                            )
                            dm_embed.add_field(
                                name="Getting Started",
                                value=(
                                    "• Use `/rr-claim-approve action:View Pending` to see pending claims\n"
                                    "• Use `/rr-claim-approve action:Approve/Decline claim_ids:NUMBER` to process claims\n"
                                    "• Use `/rr-claim-set-channel` to configure notifications\n"
                                    "Please be responsible about your new abilities. Check accounts before verifying the books. If needed, request screenshots of the author interface for confirmation."
                                ),
                                inline=False
                            )
                            await user.send(embed=dm_embed)
                        except Exception as e:
                            logger.info(f"[BOOK_CLAIM_MODULE] Could not DM user {user.name}: {e}")
                    else:
                        embed = discord.Embed(
                            title="✅ Moderator Removed",
                            description=f"{user.mention} is no longer a moderator for {interaction.guild.name}",
                            color=discord.Color.orange()
                        )
                        
                        # Send DM to the removed moderator
                        try:
                            dm_embed = discord.Embed(
                                title="Moderator Status Removed",
                                description=f"Your moderator status for **{interaction.guild.name}** has been removed.",
                                color=discord.Color.orange()
                            )
                            dm_embed.add_field(
                                name="Removed by",
                                value=f"{interaction.user.mention} ({interaction.user.name})",
                                inline=False
                            )
                            dm_embed.add_field(
                                name="Note",
                                value="You no longer have access to claim management commands for this server.",
                                inline=False
                            )
                            await user.send(embed=dm_embed)
                        except Exception as e:
                            logger.info(f"[BOOK_CLAIM_MODULE] Could not DM user {user.name}: {e}")
                    
                    await interaction.followup.send(embed=embed, ephemeral=False)
                else:
                    await interaction.followup.send(
                        f"❌ Failed to {action} moderator: {result.get('message', 'Unknown error')}",
                        ephemeral=True
                    )
                    
        except Exception as e:
            logger.error(f"[BOOK_CLAIM_MODULE] Error managing moderator: {e}")
            await interaction.followup.send(
                "❌ An error occurred while managing moderator.",
                ephemeral=True
            )
    
    async def list_moderators(self, interaction: discord.Interaction):
        """List all moderators for this server"""
        await interaction.response.defer()
        
        if not interaction.guild:
            await interaction.followup.send(
                "❌ This command can only be used in a server.",
                ephemeral=True
            )
            return
        
        try:
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-claim/list-moderators"
            params = {
                'bot_token': self.wp_bot_token,
                'server_id': str(interaction.guild.id)
            }
            
            headers = {
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            async with self.session.get(url, params=params, headers=headers) as response:
                result = await response.json()
                
                if response.status == 200 and result.get('success'):
                    moderators = result.get('moderators', [])
                    
                    embed = discord.Embed(
                        title=f"👮 Claim Moderators for {interaction.guild.name}",
                        color=discord.Color.blue()
                    )
                    
                    if moderators:
                        mod_list = []
                        for mod in moderators:
                            user_mention = f"<@{mod['discord_user_id']}>"
                            role = mod.get('role', 'moderator')
                            
                            # UPDATED: Show special label for bot owner
                            if mod['discord_user_id'] == "422444787002507266":  # Your Discord ID
                                role_display = "Book Essence bot owner"
                            else:
                                role_display = role
                            
                            mod_list.append(f"{user_mention} ({role_display})")
                        
                        embed.add_field(
                            name=f"Active Moderators ({len(moderators)})",
                            value="\n".join(mod_list),
                            inline=False
                        )
                    else:
                        embed.description = "No moderators configured for this server."
                    
                    # Add server verification status
                    is_verified = result.get('server_verified', False)
                    embed.add_field(
                        name="Server Status",
                        value="✅ Verified" if is_verified else "❌ Not Verified",
                        inline=True
                    )
                    
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(
                        "❌ Failed to retrieve moderator list.",
                        ephemeral=True
                    )
                    
        except Exception as e:
            logger.error(f"[BOOK_CLAIM_MODULE] Error listing moderators: {e}")
            await interaction.followup.send(
                "❌ An error occurred while fetching moderator list.",
                ephemeral=True
            )

    def get_patreon_goal_footer(self):
        """
        Get Patreon goal tracker footer for all promo embeds with random sassy messages
        
        Returns:
            dict: Footer data with text and icon_url
        """
        current_amount = 69  # Update this manually
        goal_amount = 400
        percentage = (current_amount / goal_amount) * 100
        
        # Create a simple text progress bar
        bar_length = 10
        filled_length = int(bar_length * current_amount / goal_amount)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        # Random sassy messages
        messages = [
            f"💸 ${current_amount}/${goal_amount} [{bar}] {percentage:.0f}% • Help keep these tools alive past autumn!",
            f"🎯 ${current_amount}/${goal_amount} [{bar}] • My hosting bills don't pay themselves, darling",
            f"⚡ ${current_amount}/${goal_amount} [{bar}] • These servers run on money, not magic (sadly)",
            f"🔥 ${current_amount}/${goal_amount} [{bar}] • Winter is coming... and so are the hosting bills",
            f"☕ ${current_amount}/${goal_amount} [{bar}] • Less than a coffee a month keeps the bot alive",
            f"🚀 ${current_amount}/${goal_amount} [{bar}] • Fuel the rocket, or it crashes in autumn",
            f"💀 ${current_amount}/${goal_amount} [{bar}] • Save the bot from its impending doom this autumn",
            f"🎮 ${current_amount}/${goal_amount} [{bar}] • Insert coin to continue (autumn deadline approaching)",
            f"🌟 ${current_amount}/${goal_amount} [{bar}] • Be a hero, save a bot (and my sanity)",
            f"⏰ ${current_amount}/${goal_amount} [{bar}] • Tick tock, autumn's coming for these servers",
            f"🏴‍☠️ ${current_amount}/${goal_amount} [{bar}] • Even pirates need to pay for hosting",
            f"🎭 ${current_amount}/${goal_amount} [{bar}] • This bot's survival: a autumn tragedy in the making?",
            f"🍂 ${current_amount}/${goal_amount} [{bar}] • When autumn leaves fall, will this bot too?",
            f"💔 ${current_amount}/${goal_amount} [{bar}] • Don't let our beautiful friendship end this autumn"
        ]
        
        # Pick a random message and append the Patreon link
        footer_text = f"{random.choice(messages)} → patreon.com/stepanchizhov"
        
        return {
            "text": footer_text,
            "icon_url": "https://c10.patreonusercontent.com/4/patreon-media/p/campaign/11811304/452ff3e5d93f4024bd088d1f946816a7/1.png?token-time=1735689600&token-hash=lhJLOkRMlPghgMYa2BL-2LBF-emdN_y4F6K1OxIbW5E%3D"  # Optional: Add a small Patreon logo
        }
    
    def get_promotional_field(self, force_show=False):
        """
        Get promotional field for embeds based on command counter
        
        Args:
            force_show (bool): Force showing a promotional message regardless of counter
        
        Returns:
            dict: Field data with name and value, or None if no promo should be shown
        """
        # Only show promotional messages every 2 commands (or if forced)
        if not force_show and self.command_counter % 2 != 0:
            return None
        
        # Define all promotional messages
        promo_messages = [
            {
                "text": "📖 You can also read Stepan Chizhov's",
                "url": "https://www.royalroad.com/fiction/105229/",
                "link_text": "The Dark Lady's Guide to Villainy!"
            },
            {
                "text": "❤️ If you like this and other tools made by Stepan Chizhov:",
                "url": "https://www.patreon.com/stepanchizhov",
                "link_text": "Support his work on Patreon!"
            },
            {
                "text": "🔍 Find more analytical tools for Royal Road authors and readers!",
                "url": "https://stepan.chizhov.com",
                "link_text": "Visit stepan.chizhov.com"
            },
            {
                "text": "💬 Need help or have suggestions?",
                "url": "https://discord.gg/xvw9vbvrwj",
                "link_text": "Join our Support Discord"
            },
            {
                "text": "📚 Join discussions about Royal Road and analytics!",
                "url": "https://discord.gg/7Xrrf3Q5zp",
                "link_text": "Immersive Ink Community Discord"
            }
        ]
        
        # Rotate through promotional messages based on how many promos have been shown
        promo_index = (self.command_counter // 2 - 1) % len(promo_messages)
        promo = promo_messages[promo_index]
        
        return {
            "name": "━━━━━━━━━━━━━━━━━━━━━",
            "value": f"{promo['text']}\n[**{promo['link_text']}**]({promo['url']})",
            "inline": False
        }
    
    async def send_claim_notification(self, guild: discord.Guild, claim_id: int,
                                     book_title: str, book_id: int, user: Optional[discord.User],
                                     notification_type: str, user_discord_id: Optional[str] = None):
        """Send public notification to configured channel"""
        if not guild:
            return
        
        # Increment command counter for promotional messages
        self.command_counter += 1
        
        try:
            # Get configured notification channel
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
                    
                    if not channel_id:
                        logger.info(f"[BOOK_CLAIM_MODULE] No notification channel configured for server {guild.id}")
                        return
                    
                    channel = guild.get_channel(int(channel_id))
                    if not channel:
                        logger.error(f"[BOOK_CLAIM_MODULE] Channel {channel_id} not found in guild")
                        return
                    
                    # Create notification embed based on type
                    if notification_type == "submitted":
                        embed = discord.Embed(
                            title="📖 New Book Claim Submitted",
                            color=discord.Color.blue()
                        )
                        embed.add_field(name="Claim ID", value=f"`#{claim_id}`", inline=True)
                        embed.add_field(name="Book", value=book_title, inline=True)
                        embed.add_field(name="Book ID", value=f"`{book_id}`", inline=True)
                        
                        if user:
                            embed.add_field(
                                name="Claimant",
                                value=f"{user.mention} ({user.name})",
                                inline=False
                            )
                        
                        embed.add_field(
                            name="Action Required",
                            value="Moderators: Use `/rr-claim-approve action:View Pending` to review",
                            inline=False
                        )
                        
                        # Add promotional field
                        promo_field = self.get_promotional_field()
                        if promo_field:
                            embed.add_field(**promo_field)
                            # Add the Patreon goal footer to ALL embeds that have promos
                            footer_data = self.get_patreon_goal_footer()
                            embed.set_footer(**footer_data)
                        
                        embed.set_footer(text=f"Submitted at {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
                        
                    elif notification_type == "approved":
                        # Fetch user if we only have ID
                        if user_discord_id and not user:
                            try:
                                user = await self.bot.fetch_user(int(user_discord_id))
                            except:
                                user = None
                        
                        embed = discord.Embed(
                            title="✅ Book Claim Approved",
                            color=discord.Color.green()
                        )
                        embed.add_field(
                            name="Book", 
                            value=f"[{book_title}](https://www.royalroad.com/fiction/{book_id})",
                            inline=True
                        )
                        
                        if user:
                            embed.add_field(
                                name="Author",
                                value=f"This book is now assigned to {user.mention}!",
                                inline=False
                            )
                        
                        # Add promotional field (force show for approved claims)
                        promo_field = self.get_promotional_field(force_show=True)
                        if promo_field:
                            embed.add_field(**promo_field)
                            # Add the Patreon goal footer to ALL embeds that have promos
                            footer_data = self.get_patreon_goal_footer()
                            embed.set_footer(**footer_data)
                        
                        embed.set_footer(text="Congratulations to the author! 🎉")
                    
                    await channel.send(embed=embed)
                    logger.info(f"[BOOK_CLAIM_MODULE] Sent {notification_type} notification to channel {channel_id}")
                    
        except Exception as e:
            logger.error(f"[BOOK_CLAIM_MODULE] Failed to send notification: {e}")
    
    async def is_server_supermod(self, user: discord.User, server_id: int) -> bool:
        """Check if user is a supermod for the specified server"""
        if not server_id:
            return False
            
        try:
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-claim/check-supermod"
            params = {
                'bot_token': self.wp_bot_token,
                'discord_user_id': str(user.id),
                'server_id': str(server_id)
            }
            
            headers = {
                'Authorization': f'Bearer {self.wp_bot_token}',
                'User-Agent': 'Essence-Discord-Bot/1.0'
            }
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('is_supermod', False)
                    
        except Exception as e:
            logger.error(f"[BOOK_CLAIM_MODULE] Error checking supermod status: {e}")
        
        return False
    
    async def is_bot_admin(self, user: discord.User) -> bool:
        """Check if user is a bot administrator"""
        try:
            url = f"{self.wp_api_url}/wp-json/rr-analytics/v1/book-claim/check-bot-admin"
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
                    return result.get('is_admin', False)
                    
        except Exception as e:
            logger.error(f"[BOOK_CLAIM_MODULE] Error checking bot admin status: {e}")
        
        # Fallback: Check against hardcoded admin ID (you)
        return str(user.id) == "422444787002507266"  # Your Discord ID
    
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
