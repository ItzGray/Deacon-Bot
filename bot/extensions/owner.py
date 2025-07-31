from typing import List, Optional, Literal
from fuzzywuzzy import process, fuzz
from operator import attrgetter
from pathlib import Path
import re
import os
from random import choice

import discord
from discord import app_commands, PartialMessageable, DMChannel
from discord.ext import commands
from loguru import logger

from .. import TheBot, database, emojis
from ..menus import ItemView

class Owner(commands.Cog):
    def __init__(self, bot: TheBot):
        self.bot = bot

    @commands.command(name="sync", description="Syncs the bot's command tree")
    @commands.is_owner()
    async def sync(
        self,
        ctx
    ):
        await self.bot.tree.sync()
        logger.info("Command tree synced.")
        await ctx.send("Command tree synced.")

async def setup(bot: TheBot):
    await bot.add_cog(Owner(bot))