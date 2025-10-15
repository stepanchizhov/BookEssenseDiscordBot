"""
Promotional utilities for Discord Essence Bot
Contains functions for adding promotional messages to embeds
"""

import discord
import random
from typing import Optional, Dict, Any

# Track command usage for promotional messages
command_counter = 0

def get_promotional_field(force_show: bool = False) -> Optional[Dict[str, Any]]:
    """
    Get promotional field for embeds based on command counter
    
    Args:
        force_show: Force showing a promotional message regardless of counter
    
    Returns:
        Field data with name and value, or None if no promo should be shown
    """
    global command_counter
    
    # Only show promotional messages every 2 commands (or if forced)
    # Commented out to always show for now
    # if not force_show and command_counter % 2 != 0:
    #     return None
    
    # Define all promotional messages
    promo_messages = [
        {
            "text": "📖 You can also read Stepan Chizhov's",
            "url": "https://www.royalroad.com/fiction/105229/",
            "link_text": "The Dark Lady's Guide to Villainy!"
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
        },
        {
            "text": "📚 Join discussions about Royal Road and analytics!",
            "url": "https://discord.gg/v6SVD2Gbeh",
            "link_text": "RR Writer's Guild Community Discord"
        }
    ]
    
    # Rotate through promotional messages based on how many promos have been shown
    promo_index = (command_counter // 2 - 1) % len(promo_messages)
    promo = promo_messages[promo_index]
    
    # Create the Patreon goal message
    current_amount = 38  # Update this manually
    goal_amount = 70
    percentage = (current_amount / goal_amount) * 100
    bar_length = 10
    filled_length = int(bar_length * current_amount / goal_amount)
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    
    patreon_messages = [
        f"💸 {current_amount}/{goal_amount} followers [{bar}]\n {percentage:.0f}% Help keep these tools alive past autumn!",
        f"🎯 {current_amount}/{goal_amount} followers [{bar}]\n My hosting bills don't pay themselves, darling",
        f"⚡ {current_amount}/{goal_amount} followers [{bar}]\n These servers run on money, not magic (sadly)",
        f"🔥 {current_amount}/{goal_amount} followers [{bar}]\n Winter is coming... and so are the hosting bills",
        f"☕ {current_amount}/{goal_amount} followers [{bar}]\n Less than a coffee a month keeps the bot alive",
        f"🚀 {current_amount}/{goal_amount} followers [{bar}]\n Fuel the rocket, or it crashes in the autumn",
        f"💀 {current_amount}/{goal_amount} followers [{bar}]\n Save the bot from its impending doom this autumn",
        f"🎮 {current_amount}/{goal_amount} followers [{bar}]\n Insert coin to continue (autumn deadline approaching)",
        f"🌟 {current_amount}/{goal_amount} followers [{bar}]\n Be a hero, save a bot (and my sanity)",
        f"⏰ {current_amount}/{goal_amount} followers [{bar}]\n Tick tock, autumn's coming for these servers",
        f"🏴‍☠️ {current_amount}/{goal_amount} followers [{bar}]\n Even pirates need to pay for hosting",
        f"🎭 {current_amount}/{goal_amount} followers [{bar}]\n This bot's survival: a autumn tragedy in the making?",
        f"🍂 {current_amount}/{goal_amount} followers [{bar}]\n When autumn leaves fall, will this bot too?",
        f"💔 {current_amount}/{goal_amount} followers [{bar}]\n Don't let our beautiful friendship end this autumn",

        # Fantasy themed
        f"🐉 {current_amount}/{goal_amount} followers [{bar}]\n Dragons hoard gold, I just need server money",
        f"⚔️ {current_amount}/{goal_amount} followers [{bar}]\n Join the quest to defeat the Hosting Bill Boss",
        f"🧙 {current_amount}/{goal_amount} followers [{bar}]\n Even wizards can't conjure free servers",
        f"🏰 {current_amount}/{goal_amount} followers [{bar}]\n Help defend the castle from autumn's server shutdown",
        f"📜 {current_amount}/{goal_amount} followers [{bar}]\n The prophecy says: 'No coins by the end of autumn = darkness'",
        f"🦄 {current_amount}/{goal_amount} followers [{bar}]\n Unicorns are rare, but rarer still is free hosting",
        f"🗡️ {current_amount}/{goal_amount} followers [{bar}]\n Your coin pouch vs. the autumn deadline",
        f"🧝 {current_amount}/{goal_amount} followers [{bar}]\n Even elves pay their hosting bills (probably)",
        f"🔮 {current_amount}/{goal_amount} followers [{bar}]\n The crystal ball shows server death this autumn",
        f"👑 {current_amount}/{goal_amount} followers [{bar}]\n A kingdom for a server! (Or just 70 patrons)",
        
        # Sci-fi themed
        f"🚀 {current_amount}/{goal_amount} followers [{bar}]\n Houston, we have a funding problem",
        f"👽 {current_amount}/{goal_amount} followers [{bar}]\n Even aliens think 70 patrons can sustainable support our hosting",
        f"🛸 {current_amount}/{goal_amount} followers [{bar}]\n Warp drive offline. Reason: insufficient credits",
        f"🤖 {current_amount}/{goal_amount} followers [{bar}]\n CRITICAL ERROR: Funding.exe will terminate in the autumn",
        f"⚡ {current_amount}/{goal_amount} followers [{bar}]\n Flux capacitor needs 70 patrons to survive past autumn",
        f"🌌 {current_amount}/{goal_amount} followers [{bar}]\n In space, no one can hear servers die",
        f"🔬 {current_amount}/{goal_amount} followers [{bar}]\n Scientific fact: Servers need money to exist",
        f"🛰️ {current_amount}/{goal_amount} followers [{bar}]\n Ground control to Major Patron: please send funds",
        f"💫 {current_amount}/{goal_amount} followers [{bar}]\n Initiating emergency funding protocol before winter",
        f"🎛️ {current_amount}/{goal_amount} followers [{bar}]\n System critical: Power cells depleting by winter",
        
        # LitRPG themed
        f"💰 {current_amount}/{goal_amount} followers [{bar}]\n [QUEST] Save the Server - Reward: Eternal gratitude",
        f"📊 {current_amount}/{goal_amount} followers [{bar}]\n Server HP: {percentage:.0f}% - Critical damage at autumn!",
        f"⬆️ {current_amount}/{goal_amount} followers [{bar}]\n Level up my hosting budget! EXP to autumn: Limited",
        f"🎲 {current_amount}/{goal_amount} followers [{bar}]\n Roll for initiative against the Hosting Bill Monster",
        f"⚡ {current_amount}/{goal_amount} followers [{bar}]\n Mana: {percentage:.0f}% - Full depletion = autumn shutdown",
        f"🏆 {current_amount}/{goal_amount} followers [{bar}]\n Achievement Locked: 'Survive Past Autumn'",
        f"💎 {current_amount}/{goal_amount} followers [{bar}]\n [LEGENDARY QUEST] Prevent the Autumn Server Apocalypse",
        f"🗺️ {current_amount}/{goal_amount} followers [{bar}]\n Main Quest: Gather 70 Patrons Before Autumn's End",
        f"⚔️ {current_amount}/{goal_amount} followers [{bar}]\n DPS: Donations Per Server-month needed!",
        f"🛡️ {current_amount}/{goal_amount} followers [{bar}]\n Server Shield: {percentage:.0f}% - Breaks in the autumn",
        f"📈 {current_amount}/{goal_amount} followers [{bar}]\n Stats: Funding {percentage:.0f}% | Time: Winter approaching",
        f"🎯 {current_amount}/{goal_amount} followers [{bar}]\n Critical Hit needed on funding boss!",
        
        # Gaming themed
        f"🎮 {current_amount}/{goal_amount} followers [{bar}]\n Server will ragequit in the autumn without support",
        f"👾 {current_amount}/{goal_amount} followers [{bar}]\n Final boss: Autumn Hosting Bills - ${goal_amount} to defeat",
        f"🕹️ {current_amount}/{goal_amount} followers [{bar}]\n Game Over in the autumn? Insert coin to continue",
        f"🏁 {current_amount}/{goal_amount} followers [{bar}]\n Racing against autumn - currently in last place",
        f"🎯 {current_amount}/{goal_amount} followers [{bar}]\n 360 no-scope the hosting bills before winter",
        f"💣 {current_amount}/{goal_amount} followers [{bar}]\n Defuse the autumn shutdown bomb: 70 patrons required",
        f"🏅 {current_amount}/{goal_amount} followers [{bar}]\n Speedrun: Fund the server before winter%",
        f"🎪 {current_amount}/{goal_amount} followers [{bar}]\n This isn't pay-to-win, it's pay-to-exist",
        f"🔥 {current_amount}/{goal_amount} followers [{bar}]\n Combo meter: {percentage:.0f}% - Don't drop it before winter!",
        
        # Mixed/General sassy
        f"😅 {current_amount}/{goal_amount} followers [{bar}]\n Nervous laughter intensifies as winter approaches",
        f"🎭 {current_amount}/{goal_amount} followers [{bar}]\n To be or not to be (online after autumn)",
        f"📉 {current_amount}/{goal_amount} followers [{bar}]\n Hosting costs rise, patron support... help!",
        f"🎪 {current_amount}/{goal_amount} followers [{bar}]\n Welcome to the 'Please Fund Me' circus!",
        f"🌡️ {current_amount}/{goal_amount} followers [{bar}]\n Server health: {percentage:.0f}% - Terminal by winter",
        f"⏳ {current_amount}/{goal_amount} followers [{bar}]\n The sands of time (and funding) run low",
        f"🎨 {current_amount}/{goal_amount} followers [{bar}]\n Painting a masterpiece called 'Winter Server Death'",
        f"🍕 {current_amount}/{goal_amount} followers [{bar}]\n Skip one pizza, save a bot's life this autumn"
    ]
    
    patreon_text = random.choice(patreon_messages)
    
    # Combine both messages into the field value
    combined_value = (
        f"{promo['text']}\n[**{promo['link_text']}**]({promo['url']})\n\n"
        f"**━━━━━━━━━━━━━━━━━━━━━**\n"
        f"We achieved our extended goal (yay!), but currently, only two generous patrons cover more than a half of all contributions. We aren't out of the woods yet! We need to have {goal_amount} patrons to make the tool sustainable by the end of November. Please consider joining even at the lowest tier!\n"
        f"{patreon_text}\n"
        f"[**→ Support on Patreon**](https://patreon.com/stepanchizhov/membership)"
    )
    
    return {
        "name": "━━━━━━━━━━━━━━━━━━━━━",
        "value": combined_value,
        "inline": False
    }


def add_promotional_field(embed: discord.Embed, force_show: bool = False) -> discord.Embed:
    """
    Add promotional field to an embed if conditions are met
    
    Args:
        embed: The embed to add the field to
        force_show: Force showing a promotional message regardless of counter
    
    Returns:
        The embed with promotional field added (if applicable)
    """
    promo_field = get_promotional_field(force_show)
    
    if promo_field:
        embed.add_field(
            name=promo_field["name"],
            value=promo_field["value"],
            inline=promo_field["inline"]
        )
    
    return embed


def increment_command_counter() -> None:
    """Increment the global command counter"""
    global command_counter
    command_counter += 1


def get_command_counter() -> int:
    """Get the current command counter value"""
    global command_counter
    return command_counter


def reset_command_counter() -> None:
    """Reset the command counter to 0"""
    global command_counter
    command_counter = 0
