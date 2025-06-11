from typing import List, Optional, Literal
from fuzzywuzzy import process, fuzz
from operator import attrgetter
from pathlib import Path
import re
import os
import math
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
        unit_dmg_type = row[6]
        unit_primary_stat = database.translate_stat_flags(int(row[7]))
        unit_beast_flag = row[8]
        unit_undead_flag = row[9]
        unit_bird_flag = row[10]

        unit_stats = await self.fetch_unit_stats(unit_id)
        unit_talents = await self.fetch_unit_talents(unit_id)

        stat_string = ""
        for stat in unit_stats:
            if stat[3] == "Set":
                stat_string += f"{str(stat[4])} {stat[2]} {database.get_stat_emoji(stat[2])}\n"
            elif stat[3] == "Multiply":
                stat_string += f"x{str(stat[4])} {stat[2]} {database.get_stat_emoji(stat[2])}\n"
            elif stat[3] == "Multiply Add":
                stat_string += f"x{str(stat[4] + 1)} {stat[2]} {database.get_stat_emoji(stat[2])}\n"
            elif stat[3] == "Add" or stat[3] == "Set Add":
                if stat[4] < 0:
                    disp_operator = ""
                else:
                    disp_operator = "+"
                stat_string += f"{disp_operator}{str(stat[4])} {stat[2]} {database.get_stat_emoji(stat[2])}\n"
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
        if row[11] == 656670 and "Witch Hunter" not in trained_talent_string:
            trained_talent_string += "Witch Hunter 2\n"
        if row[11] == 656667 and "Alert" not in starting_talent_string:
            starting_talent_string += "Alert 1\n"
        
        title_string = ""
        if unit_name == unit_title or unit_title == "":
            title_string = ""
        else:
            title_string += "\n" + unit_title

        desc_string = ""
        desc_string += "Does " + unit_dmg_type + "\n"
        desc_string += "Boosts from "
        for flag in range(len(unit_primary_stat)):
            desc_string += f"{database.get_stat_emoji(unit_primary_stat[flag])}/"
        desc_string = desc_string[:-1]
        desc_string += "\n"
        if unit_beast_flag == 1:
            desc_string += "Boosted by the Beastmaster Banners\n"
        if unit_undead_flag == 1:
            desc_string += "Boosted by Baron Samedi's Standard\n"
        if unit_bird_flag == 1:
            desc_string += "Boosted by the Imperator's Standard\n"

        embed = (
            discord.Embed(
                color=database.make_school_color(unit_school),
                description=desc_string
            )
            .set_author(name=f"{unit_name} {title_string}\n({real_name}: {unit_id})", icon_url=database.get_school_icon_url(unit_school))
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

        discord_file = None
        if unit_image:
            try:
                image_name = unit_image.split(".")[0]
                png_file = f"{image_name}.png"
                png_name = png_file.replace(" ", "")
                png_name = os.path.basename(png_name)
                file_path = Path("PNG_Images") / png_name
                discord_file = discord.File(file_path, filename=png_name)
                embed.set_thumbnail(url=f"attachment://{png_name}")
            except:
                pass

        return embed, discord_file
    
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
            embeds = [await self.build_unit_embed(row) for row in rows]
            sorted_embeds = sorted(embeds, key=lambda embed: embed[0].author.name)
            unzipped_embeds, unzipped_images = list(zip(*sorted_embeds))
            view = ItemView(unzipped_embeds, files=unzipped_images)
            await view.start(interaction)
        elif not use_object_name:
            logger.info("Failed to find '{}'", name)
            embed = discord.Embed(description=f"No units with name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
            await interaction.followup.send(embed=embed)
    
    async def calc_unit_stats(self, curve, modifiers: List[tuple], level: int) -> List[tuple]:
        curve_stats, curve_types, curve_levels, curve_values = await database.fetch_curve(self.bot.db, curve)
        final_stats = []
        stats = []
        stat_counts = []
        last_stat = ""
        stat_count = 0
        for stat in curve_stats:
            if stat != last_stat:
                if stat_count > 0:
                    stats.append(last_stat)
                    stat_counts.append(stat_count)
                stat_count = 1
                last_stat = stat
            else:
                stat_count += 1
        try:
            stats.append(stat)
            stat_counts.append(stat_count)
        except: 
            pass
        stat = 0
        while stat < len(curve_stats):
            curr_stat = curve_stats[stat]
            stat_index = stats.index(curr_stat)
            curr_stat_count = stat_counts[stat_index]
            only_one = False
            if curr_stat_count == 1:
                only_one = True
            if only_one == False:
                raw_num = 0
                curve_lvl2 = 0
                curve_lvl1 = 0
                bonus_flag = False
                if curve_types[stat + 1] == "Regular":
                    for stat_level in range(curr_stat_count):
                        if curve_levels[stat + stat_level] > level and curve_lvl2 == 0:
                            curve_lvl1 = curve_levels[stat + (stat_level - 1)]
                            curve_lvl2 = curve_levels[stat + stat_level]
                            curve_val1 = curve_values[stat + (stat_level - 1)]
                            curve_val2 = curve_values[stat + stat_level]
                        elif stat_level == curr_stat_count - 1:
                            raw_num = curve_values[stat + stat_level]
                        else: 
                            continue
                    try:
                        increment_num = (curve_val2 - curve_val1) / (curve_lvl2 - curve_lvl1)
                        raw_num = (curve_val1 + (increment_num * (level - curve_lvl1)))
                    except:
                        pass
                elif curve_types[stat + 1] == "Bonus":
                    for stat_level in range(curr_stat_count):
                        if level > curve_levels[stat + stat_level]:
                            raw_num += curve_values[stat + stat_level]
                    bonus_flag = True
            else:
                raw_num = curve_values[stat]
            final_num = 0
            bonus_set = False
            no_operator = True
            for modifier in modifiers:
                if modifier[2] != curr_stat:
                    continue
                if raw_num == 0:
                    continue
                if bonus_set == True:
                    continue
                if modifier[3] == "Multiply":
                    final_num = raw_num * modifier[4]
                    no_operator = False
                elif modifier[3] == "Multiply Add":
                    final_num = raw_num + (raw_num * modifier[4])
                    no_operator = False
                elif modifier[3] == "Add" or modifier[3] == "Set Add":
                    if bonus_flag == True:
                        bonus_set = True
                    final_num = raw_num + modifier[4]
                    no_operator = False
                elif modifier[3] == "Set":
                    final_num = modifier[4]
                    no_operator = False
            if no_operator == True:
                final_num = raw_num
            final_stats.append((curr_stat, math.floor(final_num)))
            stat += curr_stat_count

        return final_stats
    
    async def build_calc_embed(self, row, level: int):
        unit_id = row[0]
        real_name = row[2].decode("utf-8")

        unit_name = await database.translate_name(self.bot.db, row[1])
        unit_title = await database.translate_name(self.bot.db, row[4])
        unit_image = row[3].decode("utf-8")

        title_string = ""
        if unit_name == unit_title or unit_title == "":
            title_string = ""
        else:
            title_string += "\n" + unit_title

        unit_school = row[5]
        unit_curve = row[11]

        unit_modifiers = await self.fetch_unit_stats(unit_id)

        unit_final_stats = await self.calc_unit_stats(unit_curve, unit_modifiers, level)

        final_stat_string = ""
        for stat in unit_final_stats:
            final_stat_string += f"{stat[1]} {stat[0]} {database.get_stat_emoji(stat[0])}\n"

        embed = (
            discord.Embed(
                color=database.make_school_color(unit_school),
            )
            .set_author(name=f"{unit_name} {title_string}\n({real_name}: {unit_id})\n", icon_url=database.get_school_icon_url(unit_school))
            .add_field(name=f"Stats for level {level}", value=final_stat_string, inline=True)
        )

        discord_file = None
        if unit_image:
            try:
                image_name = unit_image.split(".")[0]
                png_file = f"{image_name}.png"
                png_name = png_file.replace(" ", "")
                png_name = os.path.basename(png_name)
                file_path = Path("PNG_Images") / png_name
                discord_file = discord.File(file_path, filename=png_name)
                embed.set_thumbnail(url=f"attachment://{png_name}")
            except:
                pass

        return embed, discord_file
    
    @app_commands.command(name="calc", description="Calculates a unit's stats at a given level")
    @app_commands.describe(name="The name of the unit to search for")
    async def calc(
        self,
        interaction: discord.Interaction,
        name: str,
        level: int,
        use_object_name: Optional[bool] = False,
    ):
        await interaction.response.defer()
        if type(interaction.channel) is DMChannel or type(interaction.channel) is PartialMessageable:
            logger.info("{} requested unit stats for '{}' at level {}", interaction.user.name, name, level)
        else:
            logger.info("{} requested unit stats for '{}' at level {} in channel #{} of {}", interaction.user.name, name, level, interaction.channel.name, interaction.guild.name)
        
        if use_object_name:
            rows = await self.fetch_object_name(name)
            if not rows:
                embed = discord.Embed(description=f"No units with object name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
                await interaction.followup.send(embed=embed)
        
        else:
            rows = await self.fetch_unit(name)

        if rows:
            embeds = [await self.build_calc_embed(row, level) for row in rows]
            sorted_embeds = sorted(embeds, key=lambda embed: embed[0].author.name)
            unzipped_embeds, unzipped_images = list(zip(*sorted_embeds))
            view = ItemView(unzipped_embeds, files=unzipped_images)
            await view.start(interaction)
        elif not use_object_name:
            logger.info("Failed to find '{}'", name)
            embed = discord.Embed(description=f"No units with name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
            await interaction.followup.send(embed=embed)

async def setup(bot: TheBot):
    await bot.add_cog(Units(bot))