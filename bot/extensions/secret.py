from typing import List, Optional, Literal
from fuzzywuzzy import process, fuzz
from operator import attrgetter
from pathlib import Path
import re
import os
from random import choice
from datetime import datetime
import pytz

import discord
from discord import app_commands, PartialMessageable, DMChannel
from discord.ext import commands
from loguru import logger

from .. import TheBot, database, emojis
from ..menus import ItemView

SEPARATE_TRAINER_MESSAGES = [
"""
<t:1750482000:t> - <t:1750485600:t>
<t:1750492800:t> - <t:1750496400:t>
<t:1750503600:t> - <t:1750507200:t>
<t:1750514400:t> - <t:1750518000:t>
<t:1750525200:t> - <t:1750528800:t>
<t:1750536000:t> - <t:1750539600:t>
<t:1750546800:t> - <t:1750550400:t>
<t:1750557600:t> - <t:1750561200:t>
""",
"""
<t:1750485600:t> - <t:1750489200:t>
<t:1750496400:t> - <t:1750500000:t>
<t:1750507200:t> - <t:1750510800:t>
<t:1750518000:t> - <t:1750521600:t>
<t:1750528800:t> - <t:1750532400:t>
<t:1750539600:t> - <t:1750543200:t>
<t:1750550400:t> - <t:1750554000:t>
<t:1750561200:t> - <t:1750564800:t>
""",
"""
<t:1750489200:t> - <t:1750492800:t>
<t:1750500000:t> - <t:1750503600:t>
<t:1750510800:t> - <t:1750514400:t>
<t:1750521600:t> - <t:1750525200:t>
<t:1750532400:t> - <t:1750536000:t>
<t:1750543200:t> - <t:1750546800:t>
<t:1750554000:t> - <t:1750557600:t>
<t:1750564800:t> - <t:1750482000:t>
"""
]

class Secret(commands.GroupCog, name="secret"):
    def __init__(self, bot: TheBot):
        self.bot = bot
    
    @app_commands.command(name="now", description="Displays the current secret trainer")
    async def now(
        self,
        interaction: discord.Interaction,
    ):
        await interaction.response.defer()
        if type(interaction.channel) is DMChannel or type(interaction.channel) is PartialMessageable:
            logger.info("{} requested current secret trainer", interaction.user.name)
        else:
            logger.info("{} requested current secret trainer in channel #{} of {}", interaction.user.name, interaction.channel.name, interaction.guild.name)
        
        time = datetime.now(pytz.utc).astimezone(pytz.timezone("CST6CDT"))
        current_hour = time.hour
        trainers = ["Kurotadori (Staffy)", "Firenzian (Shooty)", "Lost Hoplite (Melee)"]
        colors = [discord.Color.green(), discord.Color.orange(), discord.Color.red()]
        portraits = ["Portrait_MS_Karasu_Tier_01", "Portrait_AQ_Centaur_02", "Portrait_AQ_Skeleton_Hoplite_02"]
        trainer = trainers[current_hour % 3]
        color = colors[current_hour % 3]
        portrait = portraits[current_hour % 3]
        try:
            next_trainer = trainers[(current_hour % 3) + 1]
        except:
            next_trainer = trainers[0]
        if current_hour == 23:
            next_hour = 0
        else:
            next_hour = current_hour + 1
        next_timestamp = int(datetime(time.year, time.month, time.day, next_hour, 0, 0).timestamp())
        embed = discord.Embed(
            color=color,
            description=f"The current secret trainer is **{trainer}**\nThe next secret trainer is going to be **{next_trainer}** <t:{next_timestamp}:R>",
        ).set_author(name=f"Current secret trainer", icon_url=emojis.UNIVERSAL.url)
        try:
            image_name = portrait
            png_file = f"{image_name}.png"
            png_name = png_file.replace(" ", "")
            png_name = os.path.basename(png_name)
            file_path = Path("PNG_Images") / png_name
            discord_file = discord.File(file_path, filename=png_name)
            embed.set_thumbnail(url=f"attachment://{png_name}")
        except:
            pass
        embeds = []
        files = []
        embeds.append(embed)
        files.append(discord_file)
        view = ItemView(embeds, files=files)
        await view.start(interaction)
    
    @app_commands.command(name="type", description="Displays the schedule for a certain secret trainer")
    async def type(
        self,
        interaction: discord.Interaction,
        trainer: Literal["Kurotadori (Staffy)", "Firenzian (Shooty)", "Lost Hoplite (Melee)"],
    ):
        await interaction.response.defer()
        if type(interaction.channel) is DMChannel or type(interaction.channel) is PartialMessageable:
            logger.info("{} requested the schedule for {}", interaction.user.name, trainer)
        else:
            logger.info("{} requested the schedule for {} in channel #{} of {}", interaction.user.name, trainer, interaction.channel.name, interaction.guild.name)
        
        if trainer == "Kurotadori (Staffy)":
            message = SEPARATE_TRAINER_MESSAGES[0]
            color = discord.Color.green()
            emoji = emojis.STAFFY.url
            portrait = "Portrait_MS_Karasu_Tier_01"
        elif trainer == "Firenzian (Shooty)":
            message = SEPARATE_TRAINER_MESSAGES[1]
            color = discord.Color.orange()
            emoji = emojis.SHOOTY.url
            portrait = "Portrait_AQ_Centaur_02"
        elif trainer == "Lost Hoplite (Melee)":
            message = SEPARATE_TRAINER_MESSAGES[2]
            color = discord.Color.red()
            emoji = emojis.SLASHY.url
            portrait = "Portrait_AQ_Skeleton_Hoplite_02"
        
        trainer_split = trainer.split("(")[0][:-1]
        
        embed = discord.Embed(
            color=color,
            description=message,
        ).set_author(name=f"{trainer_split}'s schedule", icon_url=emoji)

        try:
            image_name = portrait
            png_file = f"{image_name}.png"
            png_name = png_file.replace(" ", "")
            png_name = os.path.basename(png_name)
            file_path = Path("PNG_Images") / png_name
            discord_file = discord.File(file_path, filename=png_name)
            embed.set_thumbnail(url=f"attachment://{png_name}")
        except:
            pass
        embeds = []
        files = []
        embeds.append(embed)
        files.append(discord_file)
        view = ItemView(embeds, files=files)
        await view.start(interaction)


async def setup(bot: TheBot):
    await bot.add_cog(Secret(bot))