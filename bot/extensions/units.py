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

FIND_UNITS_WITH_FILTER_QUERY = """
SELECT * FROM units
INNER JOIN locale_en ON locale_en.id == units.name
WHERE locale_en.data == ? COLLATE NOCASE
AND (? = 'Any' OR units.school = ?)
AND (? = 'Any' OR units.kind = ?)
COLLATE NOCASE
"""

FIND_UNIT_CONTAIN_STRING_QUERY = """
SELECT * FROM units
LEFT JOIN locale_en ON locale_en.id == units.name
WHERE INSTR(lower(locale_en.data), ?) > 0
"""

FIND_UNITS_CONTAIN_STRING_WITH_FILTER_QUERY = """
SELECT * FROM units
INNER JOIN locale_en ON locale_en.id == units.name
WHERE INSTR(lower(locale_en.data), ?) > 0
AND (? = 'Any' OR units.school = ?)
AND (? = 'Any' OR units.kind = ?)
COLLATE NOCASE
"""

FIND_UNIT_WITH_FILTER_PLACEHOLDER_QUERY = """
SELECT * FROM units
INNER JOIN locale_en ON locale_en.id == units.name
WHERE locale_en.data COLLATE NOCASE IN ({placeholders})
AND (? = 'Any' OR units.school = ?)
AND (? = 'Any' OR units.kind = ?)
COLLATE NOCASE
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
        
    async def fetch_unit_with_filter(self, name: str, school: str, kind: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_UNITS_WITH_FILTER_QUERY, (name,school,school,kind,kind)) as cursor:
            return await cursor.fetchall()
        
    async def fetch_unit_list(self, name: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_UNIT_CONTAIN_STRING_QUERY, (name,)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_unit_list_with_filter(self, name: str, school: str, kind: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_UNITS_CONTAIN_STRING_WITH_FILTER_QUERY, (name,school,school,kind,kind)) as cursor:
            return await cursor.fetchall()
        
    async def fetch_unit_stats(self, id: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_UNIT_STATS_QUERY, (id,)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_unit_talents(self, id: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_UNIT_TALENTS_QUERY, (id,)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_unit_filter_list(self, items, school: str, kind: str) -> List[tuple]:
        if isinstance(items, str):
            items = [items]

        results = []
        for chunk in database.sql_chunked(items, 900):  # Stay under SQLite's limit
            placeholders = database._make_placeholders(len(chunk))
            query = FIND_UNIT_WITH_FILTER_PLACEHOLDER_QUERY.format(placeholders=placeholders)

            args = (
                *chunk,
                school, school,
                kind, kind,
            )

            async with self.bot.db.execute(query, args) as cursor:
                rows = await cursor.fetchall()

            results.extend(rows)

        return results
        
    async def build_unit_embed(self, row):
        unit_id = row[0]
        real_name = row[2].decode("utf-8")

        unit_name = await database.translate_name(self.bot.db, row[1])
        unit_title = await database.translate_name(self.bot.db, row[4])
        unit_image = row[3].decode("utf-8")

        unit_school = row[5]
        unit_dmg_type = row[6]
        unit_primary_stat = database.translate_stat_flags(int(row[7]))

        unit_stats = await self.fetch_unit_stats(unit_id)
        unit_talents = await self.fetch_unit_talents(unit_id)

        stat_string = ""
        for stat in unit_stats:
            if stat[3] == "Set":
                stat_string += f"{stat[4]} {stat[2]} {database.get_stat_emoji(stat[2])}\n"
            elif stat[3] == "Multiply":
                stat_string += f"x{stat[4]} {stat[2]} {database.get_stat_emoji(stat[2])}\n"
            elif stat[3] == "Multiply Add":
                stat_string += f"x{round(stat[4] + 1, 2)} {stat[2]} {database.get_stat_emoji(stat[2])}\n"
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
                if object_name == "":
                    logger.info(f"Power ID {talent[3]} unnamed")
                    continue
                if talent[5] == "Template" or talent[5] == "Unknown":
                    starting_power_string += power_name + " " + " (" + object_name + ")\n"
                elif talent[5] == "Trained":
                    trained_power_string += power_name + " " + " (" + object_name + ")\n"
        if row[8] == 656670 and "Witch Hunter" not in trained_talent_string:
            trained_talent_string += "Witch Hunter 2\n"
        if row[8] == 656667 and "Alert" not in starting_talent_string:
            starting_talent_string += "Alert 1\n"
        
        title_string = ""
        if unit_name == unit_title or unit_title == "":
            title_string = ""
        else:
            title_string += "\n" + unit_title

        desc_string = ""
        desc_string += "Does " + unit_dmg_type + f" {database.get_stat_emoji(unit_dmg_type)}\n"
        desc_string += "Boosts from "
        for flag in range(len(unit_primary_stat)):
            desc_string += f"{database.get_stat_emoji(unit_primary_stat[flag])}/"
        desc_string = desc_string[:-1]
        desc_string += "\n"

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
            if len(starting_power_string) < 1024:
                embed.add_field(name="Starting Powers", value=starting_power_string, inline=True)
            else:
                first_starting_power_string = starting_power_string[:1024]
                second_starting_power_string = starting_power_string[1024:]
                last_indent = first_starting_power_string.split("\n")[-1]
                first_starting_power_string = first_starting_power_string.replace(last_indent, "", 1)
                embed.add_field(name="Starting Powers", value=first_starting_power_string, inline=True)
                embed.add_field(name="\u200b", value=f"{last_indent}{second_starting_power_string}", inline=True)
        
        if trained_power_string != "":
            embed.add_field(name="Trainable Powers", value=trained_power_string, inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=True)
        elif starting_power_string != "":
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=True)

        unit_tags = await database.fetch_unit_tags(self.bot.db, unit_id)
        banner_string = ""
        if b"WB_Beast" in unit_tags:
            banner_string += "Beastmaster Banners\n"
        if b"WB_Undead" in unit_tags:
            banner_string += "Baron Samedi's Standard\n"
        if b"WB_Fowl" in unit_tags:
            banner_string += "Imperator's Standard\n"
        if banner_string != "":
            embed.add_field(name="Banner Boosts", value=banner_string, inline=True)
        tag_string = ""
        if b"ADJ_Event_Boss" in unit_tags:
            tag_string += "Event Boss\n"
        if b"ADJ_Event_Base" in unit_tags or b"ADJ_Event_Elite" in unit_tags:
            tag_string += "Event Mob\n"
        if b"ADJ_AmberHorde" in unit_tags:
            tag_string += "Amber Horde\n"
        if b"ADJ_Armada" in unit_tags:
            tag_string += "Armada\n"
        if b"ADJ_Cutthroat" in unit_tags:
            tag_string += "Cutthroat\n"
        if b"ADJ_InoshishiBandit" in unit_tags or b"ADJ_InoshishiWarlord" in unit_tags:
            tag_string += "Inoshishi\n"
        if b"ADJ_NinjPig" in unit_tags:
            tag_string += "Ninja Pig\n"
        if b"ADJ_WharfRat" in unit_tags:
            tag_string += "Wharf Rat\n"
        if b"ADJ_Troggy" in unit_tags or b"ADJ_TroggyArcher" in unit_tags or b"ADJ_TroggyChief" in unit_tags or b"ADJ_TroggyShaman" in unit_tags or b"ADJ_TroggyWarrior" in unit_tags:
            tag_string += "Troggy\n"
        if b"ADJ_WaterMole" in unit_tags or b"ADJ_WaterMole_Rebel" in unit_tags or b"ADJ_Waponi" in unit_tags:
            tag_string += "Water Mole\n"
        if b"ADJ_Undead" in unit_tags:
            tag_string += "Undead\n"
        if b"ADJ_Ophidian" in unit_tags:
            tag_string += "Ophidian\n"
        if b"ADJ_Vulture" in unit_tags:
            tag_string += "Vulture\n"
        if b"ADJ_GNT_MR_Mob" in unit_tags:
            tag_string += "Aggrobah Job Gauntlet Mob\n"
        if b"ADJ_GNT_MR_Brute" in unit_tags:
            tag_string += "Aggrobah Job Gauntlet Brute\n"
        if b"ADJ_GNT_MR_Wailer" in unit_tags:
            tag_string += "Wailer\n"
        if b"KTArmada" in unit_tags:
            tag_string += "Zigazag Armada\n"
        if tag_string != "":
            embed.add_field(name="Tags", value=tag_string, inline=True)

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
    @app_commands.describe(name="The name of the unit to search for", school="The class of the unit", kind="Whether the unit is an ally or enemy")
    async def find(
        self,
        interaction: discord.Interaction,
        name: str,
        school: Optional[Literal["Buccaneer", "Privateer", "Witchdoctor", "Musketeer", "Swashbuckler"]] = "Any",
        kind: Optional[Literal["Ally", "Enemy"]] = "Any",
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
            if school != "Any" or kind != "Any":
                rows = await self.fetch_unit_with_filter(name, school, kind)
            else:
                rows = await self.fetch_unit(name)
            if not rows:
                filtered_rows = await self.fetch_unit_filter_list(items=self.bot.unit_list, school=school, kind=kind)
                closest_rows = [(row, fuzz.token_set_ratio(name, row[-1]) + fuzz.ratio(name, row[-1])) for row in filtered_rows]
                closest_rows = sorted(closest_rows, key=lambda x: x[1], reverse=True)
                closest_rows = list(zip(*closest_rows))[0]
                if school != "Any" or kind != "Any":
                    rows = await self.fetch_unit_with_filter(name=closest_rows[0][-1], school=school, kind=kind)
                else:
                    rows = await self.fetch_unit(name=closest_rows[0][-1])
                if rows:
                    logger.info("Failed to find '{}' instead searching for {}", name, closest_rows[0][-1])
        
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

    async def build_list_embed(self, rows: List[tuple], name: str):
        desc_strings = []
        desc_index = 0
        desc_strings.append("")
        for row in rows:
            real_name = row[2].decode("utf-8")
            unit_name = await database.translate_name(self.bot.db, row[1])
            unit_title = " - "
            unit_title += await database.translate_name(self.bot.db, row[4])
            if f" - {unit_name}" == unit_title or unit_title == " - ":
                unit_title = ""
            unit_school = row[5]
            if len(desc_strings[desc_index]) >= 1500:
                desc_index += 1
                desc_strings.append("")
            desc_strings[desc_index] += f"{database.get_school_emoji(unit_school)} {unit_name}{unit_title} ({real_name})\n"
        
        embeds = []
        for string in desc_strings:
            embed = discord.Embed(
                color=discord.Color.greyple(),
                description=string,
            ).set_author(name=f"Searching for: {name}", icon_url=emojis.UNIVERSAL.url)
            embeds.append(embed)

        return embeds
    
    @app_commands.command(name="list", description="Finds a list of units that contain a given string")
    @app_commands.describe(name="The name of the units to search for", school="The class of the units", kind="Whether the units are allies or enemies")
    async def list(
        self,
        interaction: discord.Interaction,
        name: str,
        school: Optional[Literal["Buccaneer", "Privateer", "Witchdoctor", "Musketeer", "Swashbuckler"]] = "Any",
        kind: Optional[Literal["Ally", "Enemy"]] = "Any",
    ):
        await interaction.response.defer()
        if type(interaction.channel) is DMChannel or type(interaction.channel) is PartialMessageable:
            logger.info("{} requested unit list for '{}'", interaction.user.name, name)
        else:
            logger.info("{} requested unit list for '{}' in channel #{} of {}", interaction.user.name, name, interaction.channel.name, interaction.guild.name)
        
        if school != "Any" or kind != "Any":
            rows = await self.fetch_unit_list_with_filter(name, school, kind)
        else:
            rows = await self.fetch_unit_list(name)
        
        if rows:
            view = ItemView(await self.build_list_embed(rows, name))
            try:
                await view.start(interaction)
            except discord.errors.HTTPException:
                logger.info("List for '{}' too long, sending back error message", name)
                embed = discord.Embed(description=f"Unit list for {name} too long! Try again with a more specific keyword.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
                await interaction.followup.send(embed=embed)
        else:
            logger.info("Failed to find list for '{}'", name)
            embed = discord.Embed(description=f"No units containing name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
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
            real_level = level
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
                        if curve_levels[stat + stat_level] >= real_level and curve_lvl2 == 0:
                            curve_lvl1 = curve_levels[stat + (stat_level - 1)]
                            curve_lvl2 = curve_levels[stat + stat_level]
                            curve_val1 = curve_values[stat + (stat_level - 1)]
                            curve_val2 = curve_values[stat + stat_level]
                        elif stat_level == curr_stat_count - 1:
                            try:
                                curve_lvl1 = curve_levels[stat + (stat_level - 1)]
                                curve_lvl2 = curve_levels[stat + stat_level]
                                curve_val1 = curve_values[stat + (stat_level - 1)]
                                curve_val2 = curve_values[stat + stat_level]
                                real_level = curve_lvl2
                            except:
                                raw_num = curve_values[stat + stat_level]
                        else: 
                            continue
                    try:
                        increment_num = (curve_val2 - curve_val1) / (curve_lvl2 - curve_lvl1)
                        raw_num = (curve_val1 + (increment_num * (real_level - curve_lvl1)))
                        lvl_num = round(1 / increment_num)
                        if lvl_num < 1:
                            lvl_num = 1
                    except:
                        pass
                elif curve_types[stat + 1] == "Bonus":
                    for stat_level in range(curr_stat_count):
                        if level >= curve_levels[stat + stat_level]:
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
                    lvl_count = math.floor(curve_lvl1 % lvl_num)
                    lvl_count -= 1
                    final_num = curve_val1 * modifier[4]
                    for level_inc in range(curve_lvl1, real_level + 1):
                        lvl_count += 1
                        if lvl_count >= lvl_num:
                            lvl_count = 0
                            final_num += ((increment_num * modifier[4]) * lvl_num)
                    no_operator = False
                elif modifier[3] == "Multiply Add":
                    lvl_count = math.floor(curve_lvl1 % lvl_num)
                    lvl_count -= 1
                    final_num = curve_val1 + (curve_val1 * modifier[4])
                    for level_inc in range(curve_lvl1, real_level + 1):
                        lvl_count += 1
                        if lvl_count >= lvl_num:
                            lvl_count = 0
                            final_num += ((increment_num + (increment_num * modifier[4])) * lvl_num)
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
            round_up_stats = ["Talent Slots", "Accuracy", "Dodge", "Armor"]
            if curr_stat in round_up_stats:
                final_num = round(final_num)
            else:
                final_num = math.floor(final_num)
            final_stats.append((curr_stat, final_num))
            stat += curr_stat_count

        return final_stats
    
    async def build_calc_embed(self, row, level: int):
        unit_id = row[0]
        real_name = row[2].decode("utf-8")

        unit_name = await database.translate_name(self.bot.db, row[1])
        unit_title = await database.translate_name(self.bot.db, row[4])
        try:
            unit_image = row[3].decode("utf-8")
        except:
            unit_image = ""

        title_string = ""
        if unit_name == unit_title or unit_title == "":
            title_string = ""
        else:
            title_string += "\n" + unit_title

        unit_school = row[5]
        unit_curve = row[8]

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
    
    @app_commands.command(name="calc", description="Calculates a unit's stats at a given level (WARNING: Slightly inaccurate)")
    @app_commands.describe(name="The name of the unit to search for")
    async def calc(
        self,
        interaction: discord.Interaction,
        name: str,
        level: int,
        school: Optional[Literal["Any", "Buccaneer", "Privateer", "Witchdoctor", "Musketeer", "Swashbuckler"]] = "Any",
        kind: Optional[Literal["Any", "Ally", "Enemy"]] = "Any",
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
            if school != "Any" or kind != "Any":
                rows = await self.fetch_unit_with_filter(name, school, kind)
            else:
                rows = await self.fetch_unit(name)
            if not rows:
                filtered_rows = await self.fetch_unit_filter_list(items=self.bot.unit_list, school=school, kind=kind)
                closest_rows = [(row, fuzz.token_set_ratio(name, row[-1]) + fuzz.ratio(name, row[-1])) for row in filtered_rows]
                closest_rows = sorted(closest_rows, key=lambda x: x[1], reverse=True)
                closest_rows = list(zip(*closest_rows))[0]
                if school != "Any" or kind != "Any":
                    rows = await self.fetch_unit_with_filter(name=closest_rows[0][-1], school=school, kind=kind)
                else:
                    rows = await self.fetch_unit(name=closest_rows[0][-1])
                if rows:
                    logger.info("Failed to find '{}' instead searching for {}", name, closest_rows[0][-1])

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