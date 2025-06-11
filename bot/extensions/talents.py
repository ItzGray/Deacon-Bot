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

FIND_TALENT_QUERY = """
SELECT * FROM talents
LEFT JOIN locale_en ON locale_en.id == talents.name
WHERE locale_en.data == ? COLLATE NOCASE
"""

FIND_OBJECT_NAME_QUERY = """
SELECT * FROM talents
INNER JOIN locale_en ON locale_en.id == talents.name
WHERE talents.real_name == ? COLLATE NOCASE
"""

FIND_TALENT_RANKS_QUERY = """
SELECT * FROM talent_ranks WHERE talent_ranks.talent == ?
"""

class Talents(commands.GroupCog, name="talent"):
    def __init__(self, bot: TheBot):
        self.bot = bot

    async def fetch_talent(self, name: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_TALENT_QUERY, (name,)) as cursor:
            return await cursor.fetchall()

    async def fetch_object_name(self, name: str) -> List[tuple]:
        name_bytes = name.encode('utf-8')
        async with self.bot.db.execute(FIND_OBJECT_NAME_QUERY, (name_bytes,)) as cursor:
            return await cursor.fetchall()
        
    async def fetch_talent_ranks(self, id: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_TALENT_RANKS_QUERY, (id,)) as cursor:
            return await cursor.fetchall()
    
    async def build_talent_embed(self, row):
        talent_id = row[0]
        real_name = row[2].decode("utf-8")

        talent_name = await database.translate_name(self.bot.db, row[1])
        talent_image = row[3].decode("utf-8")

        talent_rank_num = row[4]

        talent_ranks = await self.fetch_talent_ranks(talent_id)

        talent_rank_nums = []
        talent_rank_descs = []
        talent_rank_reqs = []
        talent_rank_strings = []
        for rank in talent_ranks:
            talent_rank_nums.append(rank[2])
            talent_rank_descs.append(await database.translate_name(self.bot.db, rank[3]))
            talent_rank_reqs.append(rank[4])
        for rank in range(len(talent_rank_nums)):
            talent_rank_strings.append(talent_rank_descs[rank])
            if talent_rank_reqs[rank] != None:
                talent_rank_strings[rank] += "\nLevel Requirement for Units: " + str(talent_rank_reqs[rank])
        
        embed = (
            discord.Embed(
                color=discord.Color.greyple(),
            )
            .set_author(name=f"{talent_name}\n({real_name}: {talent_id})")
            .add_field(name="\u200b", value="\u200b", inline=True)
            .add_field(name="\u200b", value="\u200b", inline=True)
            .add_field(name="\u200b", value="\u200b", inline=True)
        )

        discord_file = None
        if talent_image:
            try:
                image_name = talent_image.split(".")[0]
                png_file = f"{image_name}.png"
                png_name = png_file.replace(" ", "")
                png_name = os.path.basename(png_name)
                file_path = Path("PNG_Images") / png_name
                discord_file = discord.File(file_path, filename=png_name)
                embed.set_thumbnail(url=f"attachment://{png_name}")
            except:
                pass

        for rank in range(len(talent_rank_strings)):
            embed.add_field(name=f"Rank {talent_rank_nums[rank]}", value=talent_rank_strings[rank], inline=True)

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
            logger.info("{} requested talent '{}'", interaction.user.name, name)
        else:
            logger.info("{} requested talent '{}' in channel #{} of {}", interaction.user.name, name, interaction.channel.name, interaction.guild.name)
        
        if use_object_name:
            rows = await self.fetch_object_name(name)
            if not rows:
                embed = discord.Embed(description=f"No talents with object name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
                await interaction.followup.send(embed=embed)
        
        else:
            rows = await self.fetch_talent(name)
        
        if rows:
            embeds = [await self.build_talent_embed(row) for row in rows]
            sorted_embeds = sorted(embeds, key=lambda embed: embed[0].author.name)
            unzipped_embeds, unzipped_images = list(zip(*sorted_embeds))
            view = ItemView(unzipped_embeds, files=unzipped_images)
            await view.start(interaction)
        elif not use_object_name:
            logger.info("Failed to find '{}'", name)
            embed = discord.Embed(description=f"No talents with name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
            await interaction.followup.send(embed=embed)

async def setup(bot: TheBot):
    await bot.add_cog(Talents(bot))