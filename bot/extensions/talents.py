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

FIND_TALENTS_WITH_FILTER_QUERY = """
SELECT * FROM talents
INNER JOIN locale_en ON locale_en.id == talents.name
WHERE locale_en.data == ? COLLATE NOCASE
AND (? = -1 OR talents.ranks = ?)
COLLATE NOCASE
"""

FIND_TALENT_CONTAIN_STRING_QUERY = """
SELECT * FROM talents
LEFT JOIN locale_en ON locale_en.id == talents.name
WHERE INSTR(lower(locale_en.data), ?) > 0
"""

FIND_TALENT_CONTAIN_STRING_WITH_FILTER_QUERY = """
SELECT * FROM talents
LEFT JOIN locale_en ON locale_en.id == talents.name
WHERE INSTR(lower(locale_en.data), ?) > 0
AND (? = -1 OR talents.ranks = ?)
COLLATE NOCASE
"""

FIND_TALENT_STATS_QUERY = """
SELECT * FROM talent_stats WHERE talent_stats.talent == ?
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
        
    async def fetch_talent_with_filter(self, name: str, ranks: int) -> List[tuple]:
        async with self.bot.db.execute(FIND_TALENTS_WITH_FILTER_QUERY, (name,ranks,ranks)) as cursor:
            return await cursor.fetchall()
        
    async def fetch_talent_list(self, name: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_TALENT_CONTAIN_STRING_QUERY, (name,)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_talent_list_with_filter(self, name: str, ranks: int) -> List[tuple]:
        async with self.bot.db.execute(FIND_TALENT_CONTAIN_STRING_WITH_FILTER_QUERY, (name,ranks,ranks)) as cursor:
            return await cursor.fetchall()
        
    async def fetch_talent_ranks(self, id: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_TALENT_RANKS_QUERY, (id,)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_talent_stats(self, id: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_TALENT_STATS_QUERY, (id,)) as cursor:
            return await cursor.fetchall()
    
    async def build_talent_embed(self, row):
        talent_id = row[0]
        real_name = row[2].decode("utf-8")

        talent_name = await database.translate_name(self.bot.db, row[1])
        try:
            talent_image = row[3].decode("utf-8")
        except:
            talent_image = ""

        talent_rank_num = row[4]

        talent_ranks = await self.fetch_talent_ranks(talent_id)

        talent_stats = await self.fetch_talent_stats(talent_id)

        talent_rank_nums = []
        talent_rank_descs = []
        talent_rank_reqs = []
        talent_rank_icons = []
        talent_rank_tooltips = []
        talent_rank_strings = []
        talent_stat_ranks = []
        talent_stat_operators = []
        talent_stat_stats = []
        talent_stat_values = []
        for rank in talent_ranks:
            icons = []
            tooltips = []
            talent_rank_nums.append(rank[2])
            talent_rank_descs.append(await database.translate_name(self.bot.db, rank[3]))
            talent_rank_reqs.append(rank[4])
            icons.append(rank[5].decode("utf-8"))
            icons.append(rank[6].decode("utf-8"))
            icons.append(rank[7].decode("utf-8"))
            talent_rank_icons.append(tuple(icons))
            tooltips.append(rank[8])
            tooltips.append(rank[9])
            tooltips.append(rank[10])
            talent_rank_tooltips.append(tuple(tooltips))
        for stat in talent_stats:
            talent_stat_ranks.append(stat[2])
            talent_stat_operators.append(stat[3])
            talent_stat_stats.append(stat[4])
            talent_stat_values.append(stat[5])
        for rank in range(len(talent_rank_nums)):
            talent_rank_desc = talent_rank_descs[rank]
            while "&" in talent_rank_desc:
                try:
                    desc_split = talent_rank_desc.split("&")[2]
                except:
                    break
                else:
                    desc_split = talent_rank_desc.split("&")[1]
                    desc_split_hash = database._fnv_1a(desc_split)
                    lang_lookup = await database.translate_name(self.bot.db, desc_split_hash)
                    if "<img src" in lang_lookup:
                        img_split = lang_lookup.split("'")[1]
                        slash_split = img_split.split("/")[-1]
                        ext_split = slash_split.split(".")[0]
                        try:
                            real_img = database._IMG_ICONS[ext_split]
                        except:
                            pass
                        else:
                            lang_lookup = lang_lookup.replace(lang_lookup, f"{real_img}")

                    talent_rank_desc = talent_rank_desc.replace(f"&{desc_split}&", lang_lookup)

            while "$" in talent_rank_desc:
                try:
                    desc_split = talent_rank_desc.split("$")[2]
                except:
                    break
                else:
                    desc_split = talent_rank_desc.split("$")[1]
                    try:
                        desc_img = database._STAT_ICONS[desc_split]
                    except:
                        pass
                    else:
                        talent_rank_desc = talent_rank_desc.replace(f"${desc_split}$", f"{desc_img}")
                    if "eBonus" in desc_split:
                        talent_rank_desc = talent_rank_desc.replace(f"${desc_split}$", f"{talent_stat_values[rank]}")
                    if "ePercent" in desc_split:
                        talent_rank_desc = talent_rank_desc.replace(f"${desc_split}$", f"{int(talent_stat_values[rank] * 100)}")
                    if "eIcon" in desc_split:
                        talent_rank_desc = talent_rank_desc.replace(f"${desc_split}$", f"{database.get_stat_emoji(talent_stat_stats[rank])}")
                talent_rank_desc = talent_rank_desc.replace(f"${desc_split}$", desc_split)

            talent_rank_desc = talent_rank_desc.replace("<br>", "\n")
            talent_rank_desc = talent_rank_desc.replace("\\n", "\n")
            talent_rank_desc = talent_rank_desc.replace("%%", "%")
            talent_rank_desc = talent_rank_desc.replace("#1:%.0", "")
            talent_rank_desc = talent_rank_desc.replace("#1:%+.0", "+")
            talent_rank_desc = talent_rank_desc.replace("#2:%.0", "")
            talent_rank_desc = talent_rank_desc.replace("%.0", "")
            talent_rank_strings.append(talent_rank_desc)
            icon_emojis = []
            tooltip_texts = []
            for icon in talent_rank_icons[rank]:
                if icon != "":
                    try:
                        icon_emojis.append(database._IMG_ICONS[icon.split(".")[0]])
                    except:
                        icon_emojis.append("")
                else:
                    icon_emojis.append("")
            for tooltip in talent_rank_tooltips[rank]:
                if tooltip != "":
                    try:
                        tooltip_text = await database.translate_name(self.bot.db, tooltip)
                        tooltip_texts.append(tooltip_text.replace("%%", "%"))
                    except:
                        tooltip_texts.append("")
                else:
                    tooltip_texts.append("")
            for pairing in range(len(icon_emojis)):
                if icon_emojis[pairing] == "" and tooltip_texts[pairing] == "":
                    pass
                else:
                    talent_rank_strings[rank] += f"\n{icon_emojis[pairing]} **{tooltip_texts[pairing]}**"
            if talent_rank_reqs[rank] != None:
                talent_rank_strings[rank] += "\n**Unit Lvl. Req: " + str(talent_rank_reqs[rank]) + "**"
        
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
        ranks: Optional[int] = -1,
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
            if ranks != -1:
                rows = await self.fetch_talent_with_filter(name, ranks)
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

    async def build_list_embed(self, rows: List[tuple], name: str):
        desc_string = ""
        for row in rows:
            real_name = row[2].decode("utf-8")
            talent_name = await database.translate_name(self.bot.db, row[1])
            desc_string += f"{talent_name} ({real_name})\n"
        
        embed = discord.Embed(
            color=discord.Color.greyple(),
            description=desc_string,
        ).set_author(name=f"Searching for: {name}", icon_url=emojis.UNIVERSAL.url)

        embeds = []
        embeds.append(embed)

        return embeds
    
    @app_commands.command(name="list", description="Finds a list of talents that contain a given string")
    @app_commands.describe(name="The name of the talents to search for")
    async def list(
        self,
        interaction: discord.Interaction,
        name: str,
        ranks: Optional[int] = -1,
    ):
        await interaction.response.defer()
        if type(interaction.channel) is DMChannel or type(interaction.channel) is PartialMessageable:
            logger.info("{} requested talent list for '{}'", interaction.user.name, name)
        else:
            logger.info("{} requested talent list for '{}' in channel #{} of {}", interaction.user.name, name, interaction.channel.name, interaction.guild.name)
        
        if ranks != -1:
            rows = await self.fetch_talent_list_with_filter(name, ranks)
        else:
            rows = await self.fetch_talent_list(name)
        
        if rows:
            view = ItemView(await self.build_list_embed(rows, name))
            try:
                await view.start(interaction)
            except discord.errors.HTTPException:
                logger.info("List for '{}' too long, sending back error message")
                embed = discord.Embed(description=f"Talent list for {name} too long! Try again with a more specific keyword.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
                await interaction.followup.send(embed=embed)
        else:
            logger.info("Failed to find list for '{}'", name)
            embed = discord.Embed(description=f"No talents containing name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
            await interaction.followup.send(embed=embed)

async def setup(bot: TheBot):
    await bot.add_cog(Talents(bot))