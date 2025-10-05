#!/usr/bin/env python3
"""
Discord Essence Bot - Main Module
Modular architecture for Royal Road analytics and essence combinations
"""

import discord
from discord.ext import commands
import aiohttp
import os
import logging
import asyncio
import signal
import atexit
import sys
import time

# Import modules
from shoutout_module import ShoutoutModule
from book_claim_module import BookClaimModule
from rising_stars_prediction import RisingStarsPrediction
from chart_commands_module import ChartCommandsModule
from essence_commands_module import EssenceCommandsModule
from others_also_liked_module import OthersAlsoLikedModule
from rs_analysis_module import RSAnalysisModule
from promotional_utils import get_promotional_field, add_promotional_field
from shared_utils import tag_autocomplete, TAG_MAPPING, UNIQUE_TAGS

# Set up logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger('discord')

# Silence matplotlib warnings
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.getLogger('matplotlib.category').setLevel(logging.WARNING)

# Bot configuration
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
WP_API_URL = os.getenv('WP_API_URL', 'https://stepan.chizhov.com')
WP_BOT_TOKEN = os.getenv('WP_BOT_TOKEN')

# Log startup configuration
logger.info(f"[STARTUP] Bot Token exists: {'Yes' if BOT_TOKEN else 'No'}")
logger.info(f"[STARTUP] WP URL: {WP_API_URL}")
logger.info(f"[STARTUP] WP Bot Token exists: {'Yes' if WP_BOT_TOKEN else 'No'}")

# Initialize bot with command prefix (even though we'll use slash commands)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

# Global variables for modules
session = None
shoutout_module = None
book_claim_module = None
chart_module = None
essence_module = None
others_also_liked_module = None
rs_analysis_module = None

# Global command counter
command_counter = 0

async def get_session():
    """Get or create the aiohttp session"""
    global session
    if session is None or session.closed:
        session = aiohttp.ClientSession()
    return session

@bot.event
async def on_ready():
    """Initialize all modules when bot is ready"""
    global session, shoutout_module, book_claim_module, chart_module
    global essence_module, others_also_liked_module, rs_analysis_module
    
    session = await get_session()
    logger.info(f'[READY] {bot.user} has connected to Discord!')
    logger.info(f'[READY] Bot is in {len(bot.guilds)} guilds')
    
    # List all guilds
    for guild in bot.guilds:
        logger.info(f'[READY] - Guild: {guild.name} (ID: {guild.id})')
    
    try:
        # Initialize all modules
        logger.info("[READY] Initializing modules...")
        
        # Core modules from original bot
        shoutout_module = ShoutoutModule(
            bot, session, WP_API_URL, WP_BOT_TOKEN, tag_autocomplete
        )
        logger.info("✓ Shoutout module initialized")
        
        book_claim_module = BookClaimModule(
            bot, session, WP_API_URL, WP_BOT_TOKEN
        )
        logger.info("✓ Book claim module initialized")
        
        # Chart commands module
        chart_module = ChartCommandsModule(
            bot, session, WP_API_URL, WP_BOT_TOKEN,
            get_promotional_field_func=get_promotional_field,
            add_promotional_field_func=add_promotional_field
        )
        logger.info("✓ Chart commands module initialized")
        
        # Essence and brag commands module
        essence_module = EssenceCommandsModule(
            bot, session, WP_API_URL, WP_BOT_TOKEN,
            get_promotional_field_func=get_promotional_field,
            add_promotional_field_func=add_promotional_field,
            tag_autocomplete_func=tag_autocomplete
        )
        logger.info("✓ Essence commands module initialized")
        
        # Others Also Liked module
        others_also_liked_module = OthersAlsoLikedModule(
            bot, session, WP_API_URL, WP_BOT_TOKEN,
            add_promotional_field_func=add_promotional_field
        )
        logger.info("✓ Others Also Liked module initialized")
        
        # Rising Stars analysis module (RS Chart and RS Run)
        rs_analysis_module = RSAnalysisModule(
            bot, session, WP_API_URL, WP_BOT_TOKEN,
            add_promotional_field_func=add_promotional_field
        )
        logger.info("✓ RS Analysis module initialized")
        
        # Register standalone commands
        register_standalone_commands()
        logger.info("✓ Standalone commands registered")
        
        # Sync commands to Discord
        synced = await bot.tree.sync()
        logger.info(f"[SYNC] Successfully synced {len(synced)} command(s)")
        for cmd in synced:
            logger.info(f'[SYNC] - Command: {cmd.name}')
            
    except Exception as e:
        logger.error(f"[ERROR] During bot startup: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Test WordPress connection
    await test_wordpress_connection()

async def test_wordpress_connection():
    """Test the WordPress API connection"""
    logger.info(f"[TEST] Testing WordPress connection...")
    try:
        test_url = f"{WP_API_URL}/wp-json/rr-analytics/v1/health"
        headers = {
            'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)'
        }
        async with session.get(test_url, headers=headers) as response:
            logger.info(f'[TEST] WordPress health check: Status {response.status}')
            if response.status == 200:
                logger.info(f"[TEST] ✅ WordPress API is reachable!")
            else:
                response_text = await response.text()
                logger.info(f'[TEST] ❌ WordPress API returned error: {response_text[:200]}')
    except Exception as e:
        logger.info(f'[TEST] ❌ Failed to reach WordPress: {e}')

def register_standalone_commands():
    """Register standalone commands that don't belong to a specific module"""
    
    @bot.tree.command(name="ping", description="Test if the bot is responsive")
    async def ping(interaction: discord.Interaction):
        logger.info(f"[COMMAND] Ping command called by {interaction.user}")
        await interaction.response.send_message("Pong! The bot is online.", ephemeral=True)
    
    @bot.tree.command(name="test", description="Test WordPress API connection")
    async def test(interaction: discord.Interaction):
        logger.info(f"[COMMAND] Test command called by {interaction.user}")
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Test health endpoint
            health_url = f"{WP_API_URL}/wp-json/rr-analytics/v1/health"
            headers = {
                'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)'
            }
            async with session.get(health_url, headers=headers) as response:
                health_status = response.status
                health_text = await response.text()
                logger.info(f"[TEST] Health check: {health_status}")
            
            # Test essence endpoint
            test_data = {
                'tags': ['Fantasy', 'Magic'],
                'bot_token': WP_BOT_TOKEN
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Essence-Discord-Bot/1.0 (+https://stepan.chizhov.com)',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            essence_url = f"{WP_API_URL}/wp-json/rr-analytics/v1/essence-combination"
            async with session.post(
                essence_url,
                json=test_data,
                headers=headers
            ) as response:
                essence_status = response.status
                essence_text = await response.text()
                logger.info(f"[TEST] Essence endpoint: {essence_status}")
            
            # Create response embed
            embed = discord.Embed(
                title="🔧 WordPress API Test Results",
                color=0x00ff00 if health_status == 200 and essence_status == 200 else 0xff0000
            )
            
            embed.add_field(
                name="Health Check",
                value=f"{'✅' if health_status == 200 else '❌'} Status: {health_status}",
                inline=False
            )
            
            embed.add_field(
                name="Essence Endpoint",
                value=f"{'✅' if essence_status == 200 else '❌'} Status: {essence_status}",
                inline=False
            )
            
            if essence_status == 200:
                try:
                    import json
                    result = json.loads(essence_text)
                    embed.add_field(
                        name="Test Result",
                        value=f"Fantasy + Magic = {result.get('combination_name', 'Unknown')} ({result.get('book_count', 0)} books)",
                        inline=False
                    )
                except:
                    pass
            
            embed.add_field(
                name="API URL",
                value=f"`{WP_API_URL}`",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.info(f"[ERROR] Test command failed: {e}")
            await interaction.followup.send(
                f"❌ Test failed: {str(e)}",
                ephemeral=True
            )
    
    @bot.tree.command(name="help", description="Show detailed help information for all commands")
    async def help_command(interaction: discord.Interaction):
        """Display comprehensive help information"""
        embed = discord.Embed(
            title="🤖 Discord Essence Bot Help",
            description=(
                "**Discover rare Royal Road book combinations & track analytics!**\n\n"
                "🎯 **Quick Start:** `/e Fantasy Magic` or `/rr-followers 105229`\n"
                "💡 **Tip:** Use autocomplete in `/essence` by pressing Tab after typing the command\n\n"
                "📊 **All chart commands show 'all time' data by default**"
            ),
            color=0x5468ff
        )
        
        # Commands section
        embed.add_field(
            name="🎮 Commands Overview",
            value=(
                "**Essence Commands**\n"
                "`/essence` - Combine tags with autocomplete\n"
                "`/e` or `/combine` - Quick essence combination\n"
                "`/tags` - List all available tags\n"
                "`/brag` - Show your essence discoveries\n"
                "`/rr-stats` - Royal Road database statistics\n\n"
                
                "**Chart Commands**\n"
                "`/rr-followers` - Followers over time\n"
                "`/rr-views` - Views over time\n"
                "`/rr-average-views` - Average views & chapters\n"
                "`/rr-ratings` - Rating metrics over time\n\n"
                
                "**Analysis Commands**\n"
                "`/rr-others-also-liked` - Books referencing this book\n"
                "`/rr-others-also-liked-list` - Complete reference list\n"
                "`/rr-rs-chart` - Rising Stars impact analysis\n"
                "`/rr-rs-run` - Rising Stars appearance history\n\n"
                
                "**Utility Commands**\n"
                "`/ping` - Check if bot is online\n"
                "`/test` - Test API connection\n"
                "`/help` - Show this help message"
            ),
            inline=False
        )
        
        # Chart time formats
        embed.add_field(
            name="📊 Chart Time Formats",
            value=(
                "• `30` - Last 30 days\n"
                "• `all` - All available data (default)\n"
                "• `2024-01-01` - From specific date\n"
                "• `2024-01-01:2024-02-01` - Date range"
            ),
            inline=True
        )
        
        # Rarity tiers
        embed.add_field(
            name="💎 Essence Rarity Tiers",
            value=(
                "🌟 **Mythic** (≤0.15%)\n"
                "⭐ **Legendary** (≤0.3%)\n"
                "💜 **Epic** (≤0.5%)\n"
                "💙 **Rare** (≤1.0%)\n"
                "💚 **Uncommon** (≤5.0%)\n"
                "⚪ **Common** (>5.0%)"
            ),
            inline=True
        )
        
        # Examples
        embed.add_field(
            name="💡 Quick Examples",
            value=(
                "**Essence:** `/e Fantasy Magic`\n"
                "**Chart:** `/rr-followers 105229`\n"
                "**Analysis:** `/rr-rs-chart 105229`\n"
                "**Discovery:** `/brag`"
            ),
            inline=False
        )
        
        # Links and support
        embed.add_field(
            name="🔗 Links & Support",
            value=(
                "📖 [Read \"The Dark Lady's Guide to Villainy\"](https://www.royalroad.com/fiction/105229)\n"
                "🔍 [More Tools](https://stepan.chizhov.com)\n"
                "💬 [Support Discord](https://discord.gg/xvw9vbvrwj)\n"
                "❤️ [Support on Patreon](https://patreon.com/stepanchizhov)\n"
                "📚 [Community Discord](https://discord.gg/7Xrrf3Q5zp)"
            ),
            inline=False
        )
        
        embed.set_footer(text="Created by Stepan Chizhov • Data updated continuously")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_disconnect():
    """Handle bot disconnection"""
    logger.info(f"[DISCONNECT] Bot disconnected")

@bot.event
async def on_error(event, *args, **kwargs):
    """Handle errors globally"""
    import sys
    exc_type, exc_value, exc_traceback = sys.exc_info()
    
    if isinstance(exc_value, discord.HTTPException) and exc_value.status == 429:
        logger.warning(f"[GLOBAL] Rate limited in {event}: {exc_value}")
        # Don't crash, just log it
    else:
        # Log other errors
        logger.error(f"[GLOBAL] Error in {event}: {exc_type.__name__}: {exc_value}")

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors including rate limits"""
    if isinstance(error, discord.HTTPException) and error.status == 429:
        logger.warning(f"[COMMAND] Rate limited: {error}")
        try:
            await ctx.send("⚠️ Bot is being rate limited. Please try again in a few seconds.", ephemeral=True)
        except:
            pass  # Can't send message if we're rate limited
    elif isinstance(error, commands.CommandOnCooldown):
        logger.info(f"[COMMAND] Command on cooldown: {error}")
    else:
        # Log other errors
        logger.error(f"[COMMAND] Error: {type(error).__name__}: {error}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Handle application command errors"""
    logger.info(f"[ERROR] Command error: {type(error).__name__}: {error}")
    import traceback
    traceback.print_exc()
    
    if interaction.response.is_done():
        await interaction.followup.send("An error occurred!", ephemeral=True)
    else:
        await interaction.response.send_message("An error occurred!", ephemeral=True)

async def cleanup():
    """Cleanup handler for shutdown"""
    global session
    if session and not session.closed:
        await session.close()
        logger.info(f"[CLEANUP] Session closed")

def cleanup_handler():
    """Cleanup handler for shutdown"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(cleanup())
        else:
            loop.run_until_complete(cleanup())
    except:
        pass

# Register cleanup handlers
atexit.register(cleanup_handler)
signal.signal(signal.SIGTERM, lambda s, f: cleanup_handler())
signal.signal(signal.SIGINT, lambda s, f: cleanup_handler())

def main():
    """Main entry point"""
    if not BOT_TOKEN:
        logger.error("[ERROR] DISCORD_BOT_TOKEN environment variable not set!")
        exit(1)
    if not WP_BOT_TOKEN:
        logger.error("[ERROR] WP_BOT_TOKEN environment variable not set!")
        exit(1)
    
    # Add retry logic for rate limiting on startup
    max_retries = 5
    retry_delay = 1800  # Start with 30 minutes
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Starting bot (attempt {attempt + 1}/{max_retries})...")
            bot.run(BOT_TOKEN)
            break  # If successful, exit the loop
        except discord.errors.HTTPException as e:
            if e.status == 429 or "1015" in str(e):
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.error(f"Rate limited on startup. Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                if attempt == max_retries - 1:
                    logger.error("Max retries reached. Exiting.")
                    sys.exit(1)
            else:
                raise  # Re-raise non-rate-limit errors

if __name__ == "__main__":
    main()
