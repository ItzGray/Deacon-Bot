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

FIND_POWER_QUERY = """
SELECT * FROM powers
LEFT JOIN locale_en ON locale_en.id == powers.name
WHERE locale_en.data == ? COLLATE NOCASE
"""

FIND_OBJECT_NAME_QUERY = """
SELECT * FROM powers
INNER JOIN locale_en ON locale_en.id == powers.name
WHERE powers.real_name == ? COLLATE NOCASE
"""

class Powers(commands.GroupCog, name="power"):
    def __init__(self, bot: TheBot):
        self.bot = bot
    
    async def fetch_power(self, name: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_POWER_QUERY, (name,)) as cursor:
            return await cursor.fetchall()

    async def fetch_object_name(self, name: str) -> List[tuple]:
        name_bytes = name.encode('utf-8')
        async with self.bot.db.execute(FIND_OBJECT_NAME_QUERY, (name_bytes,)) as cursor:
            return await cursor.fetchall()
        
    async def build_power_embed(self, row):
        power_id = row[0]
        real_name = row[2].decode("utf-8")

        power_name = await database.translate_name(self.bot.db, row[1])
        power_image = row[3].decode("utf-8")
        power_desc = await database.translate_name(self.bot.db, row[4])

        pvp_tag = row[5]

        embed = (
            discord.Embed(
                color=database.make_school_color(0),
            )
            .set_author(name=f"{power_name}\n({real_name}: {power_id})")
            .add_field(name="Description", value=power_desc, inline=False)
        )

        discord_file = None
        if power_image:
            try:
                image_name = power_image.split(".")[0]
                png_file = f"{image_name}.png"
                png_name = png_file.replace(" ", "")
                png_name = os.path.basename(png_name)
                file_path = Path("PNG_Images") / png_name
                discord_file = discord.File(file_path, filename=png_name)
                embed.set_thumbnail(url=f"attachment://{png_name}")
            except:
                pass
        
        return embed, discord_file
    
    @app_commands.command(name="find", description="Finds a Pirate101 talent by name")
    @app_commands.describe(name="The name of the talent to search for")
    async def find(
        self,
        interaction: discord.Interaction,
        name: str,
        use_object_name: Optional[bool] = False,
    ):
        await interaction.response.defer()
        if type(interaction.channel) is DMChannel or type(interaction.channel) is PartialMessageable:
            logger.info("{} requested power '{}'", interaction.user.name, name)
        else:
            logger.info("{} requested power '{}' in channel #{} of {}", interaction.user.name, name, interaction.channel.name, interaction.guild.name)
        
        if use_object_name:
            rows = await self.fetch_object_name(name)
            if not rows:
                embed = discord.Embed(description=f"No powers with object name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
                await interaction.followup.send(embed=embed)
        
        else:
            rows = await self.fetch_power(name)
        
        if rows:
            embeds = [await self.build_power_embed(row) for row in rows]
            sorted_embeds = sorted(embeds, key=lambda embed: embed[0].author.name)
            unzipped_embeds, unzipped_images = list(zip(*sorted_embeds))
            view = ItemView(unzipped_embeds, files=unzipped_images)
            await view.start(interaction)
        elif not use_object_name:
            logger.info("Failed to find '{}'", name)
            embed = discord.Embed(description=f"No powers with name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
            await interaction.followup.send(embed=embed)

async def setup(bot: TheBot):
    await bot.add_cog(Powers(bot))