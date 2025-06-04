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

FIND_UNIT_QUERY = """
SELECT * FROM units
LEFT JOIN locale_en ON locale_en.id == units.name
WHERE locale_en.data == ? COLLATE NOCASE
"""

FIND_OBJECT_NAME_QUERY = """
SELECT * FROM units
INNER JOIN locale_en ON locale_en.id == units.name
WHERE units.real_name == ? COLLATE NOCASE
"""

FIND_UNIT_STATS_QUERY = """
SELECT * FROM unit_stats WHERE unit_stats.unit == ?
"""

FIND_UNIT_TALENTS_QUERY = """
SELECT * FROM unit_talents WHERE unit_talents.unit == ?
"""

class Units(commands.GroupCog, name="unit"):
    def __init__(self, bot: TheBot):
        self.bot = bot

    async def fetch_unit(self, name: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_UNIT_QUERY, (name,)) as cursor:
            return await cursor.fetchall()

    async def fetch_object_name(self, name: str) -> List[tuple]:
        name_bytes = name.encode('utf-8')
        async with self.bot.db.execute(FIND_OBJECT_NAME_QUERY, (name_bytes,)) as cursor:
            return await cursor.fetchall()
        
    async def fetch_unit_stats(self, id: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_UNIT_STATS_QUERY, (id,)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_unit_talents(self, id: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_UNIT_TALENTS_QUERY, (id,)) as cursor:
            return await cursor.fetchall()
        
    async def build_unit_embed(self, row):
        unit_id = row[0]
        real_name = row[2].decode("utf-8")

        unit_name = await database.translate_name(self.bot.db, row[1])
        unit_title = await database.translate_name(self.bot.db, row[4])
        unit_image = row[3].decode("utf-8")

        unit_school = row[5]
        unit_dmg_type = row[7]
        unit_primary_stat = database.translate_stat_flags(int(row[8]))
        unit_beast_flag = row[9]
        unit_undead_flag = row[10]
        unit_bird_flag = row[11]

        unit_stats = await self.fetch_unit_stats(unit_id)
        unit_talents = await self.fetch_unit_talents(unit_id)

        stat_string = ""
        for stat in unit_stats:
            if stat[3] == "Set":
                stat_string += str(stat[4]) + " " + stat[2] + "\n"
            elif stat[3] == "Multiply":
                stat_string += "x" + str(stat[4]) + " " + stat[2] + "\n"
            elif stat[3] == "Multiply Add":
                stat_string += "x" + str(stat[4] + 1) + " " + stat[2] + "\n"
            elif stat[3] == "Add" or stat[3] == "Set Add":
                if stat[4] < 0:
                    disp_operator = "-"
                else:
                    disp_operator = "+"
                stat_string += disp_operator + str(stat[4]) + " " + stat[2] + "\n"
        starting_talent_string = ""
        trained_talent_string = ""
        starting_power_string = ""
        trained_power_string = ""
        for talent in unit_talents:
            if talent[2] == "Talent":
                talent_name, object_name = await database.translate_talent_name(self.bot.db, talent[3])
                if talent_name == "":
                    talent_name = object_name
                if talent[5] == "Template" or talent[5] == "Unknown":
                    starting_talent_string += talent_name + " " + str(talent[4]) + "\n"
                elif talent[5] == "Trained":
                    trained_talent_string += talent_name + " " + str(talent[4]) + "\n"
            elif talent[2] == "Power":
                power_name, object_name = await database.translate_power_name(self.bot.db, talent[3])
                if talent[5] == "Template" or talent[5] == "Unknown":
                    starting_power_string += power_name + " " + " (" + object_name + ")\n"
                elif talent[5] == "Trained":
                    trained_power_string += power_name + " " + " (" + object_name + ")\n"
        
        title_string = ""
        if unit_name == unit_title or unit_title == None:
            title_string = ""
        else:
            title_string += "\n" + unit_title

        embed = (
            discord.Embed(
                # Make this actually do school colors later
                color=database.make_school_color(0),
            )
            .set_author(name=f"{unit_name} {title_string}\n({real_name}: {unit_id})")
            .add_field(name="Stat Modifiers", value=stat_string, inline=True)
            .add_field(name="\u200b", value="\u200b", inline=True)
            .add_field(name="\u200b", value="\u200b", inline=True)
        )

        if starting_talent_string != "":
            embed.add_field(name="Starting Talents", value=starting_talent_string, inline=True)
        else:
            embed.add_field(name="\u200b", value="\u200b", inline=True)
        
        if trained_talent_string != "":
            embed.add_field(name="Trainable Talents", value=trained_talent_string, inline=True)
        else:
            embed.add_field(name="\u200b", value="\u200b", inline=True)

        embed.add_field(name="\u200b", value="\u200b", inline=True)
        
        if starting_power_string != "":
            embed.add_field(name="Starting Powers", value=starting_power_string, inline=True)
        
        if trained_power_string != "":
            embed.add_field(name="Trainable Powers", value=trained_power_string, inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=True)

        if unit_image:
            try:
                image_name = (unit_image.split("|")[-1]).split(".")[0]
                png_file = f"{image_name}.png"
                png_name = png_file.replace(" ", "")
                png_name = os.path.basename(png_name)
                file_path = Path("PNG_Images") / png_name
                discord_file = discord.File(file_path, filename=png_name)
                embed.set_thumbnail(url=f"attachment://{png_name}")
            except:
                pass

        return embed
    
    @app_commands.command(name="find", description="Finds a Pirate101 unit by name")
    @app_commands.describe(name="The name of the unit to search for")
    async def find(
        self,
        interaction: discord.Interaction,
        name: str,
        use_object_name: Optional[bool] = False,
    ):
        await interaction.response.defer()
        if type(interaction.channel) is DMChannel or type(interaction.channel) is PartialMessageable:
            logger.info("{} requested unit '{}'", interaction.user.name, name)
        else:
            logger.info("{} requested unit '{}' in channel #{} of {}", interaction.user.name, name, interaction.channel.name, interaction.guild.name)
        
        if use_object_name:
            rows = await self.fetch_object_name(name)
            if not rows:
                embed = discord.Embed(description=f"No units with object name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
                await interaction.followup.send(embed=embed)
        
        else:
            rows = await self.fetch_unit(name)
        
        if rows:
            view = ItemView([await self.build_unit_embed(row) for row in rows])
            await view.start(interaction)
        elif not use_object_name:
            logger.info("Failed to find '{}'", name)
            embed = discord.Embed(description=f"No units with name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
            await interaction.followup.send(embed=embed)

async def setup(bot: TheBot):
    await bot.add_cog(Units(bot))