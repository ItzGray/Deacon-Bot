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

FIND_POWER_CONTAIN_STRING_QUERY = """
SELECT * FROM powers
LEFT JOIN locale_en ON locale_en.id == powers.name
WHERE INSTR(lower(locale_en.data), ?) > 0
"""

FIND_POWER_ADJUSTMENTS_QUERY = """
SELECT * FROM power_adjustments WHERE power_adjustments.power == ?
"""

FIND_POWER_INFO_QUERY = """
SELECT * FROM power_info WHERE power_info.power == ?
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
        
    async def fetch_power_list(self, name: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_POWER_CONTAIN_STRING_QUERY, (name,)) as cursor:
            return await cursor.fetchall()
        
    async def fetch_power_adjustments(self, id: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_POWER_ADJUSTMENTS_QUERY, (id,)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_power_info(self, id: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_POWER_INFO_QUERY, (id,)) as cursor:
            return await cursor.fetchall()
        
    async def build_power_embed(self, row):
        power_id = row[0]
        real_name = row[2].decode("utf-8")

        power_name = await database.translate_name(self.bot.db, row[1])
        try:
            power_image = row[3].decode("utf-8")
        except:
            power_image = row[3]
        power_desc = await database.translate_name(self.bot.db, row[4])

        power_adjustments = await self.fetch_power_adjustments(power_id)
        power_info = await self.fetch_power_info(power_id)

        power_adjustment_nums = []
        power_adjustment_types = []
        power_operators = []
        power_mult_stats = []
        power_mult_amounts = []
        for adjustment in power_adjustments:
            power_adjustment_nums.append(adjustment[2])
            power_adjustment_types.append(adjustment[3])
            power_operators.append(adjustment[4])
            power_mult_stats.append(adjustment[5])
            power_mult_amounts.append(adjustment[6])

        power_types = []
        power_dmg_types = []
        power_durations = []
        power_stats = []
        power_summons = []
        power_percents = []
        for info in power_info:
            power_types.append(info[2])
            power_dmg_types.append(info[3])
            power_durations.append(info[4])
            power_stats.append(info[5])
            power_summons.append(info[6])
            power_percents.append(info[7])

        while "&" in power_desc:
            try:
                desc_split = power_desc.split("&")[2]
            except:
                break
            else:
                desc_split = power_desc.split("&")[1]
                desc_split_hash = database._fnv_1a(desc_split)
                lang_lookup = await database.lang_lookup_by_id(self.bot.db, desc_split_hash)
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

                power_desc = power_desc.replace(f"&{desc_split}&", lang_lookup)

        debuff = False
        while "$" in power_desc:
            try:
                desc_split = power_desc.split("$")[2]
            except:
                break
            else:
                desc_split = power_desc.split("$")[1]
                try:
                    desc_img = database._STAT_ICONS[desc_split]
                except:
                    pass
                else:
                    power_desc = power_desc.replace(f"${desc_split}$", f"{desc_img}")
                    continue
                if "eDuration" in desc_split:
                    try:
                        duration_num = int(desc_split[-1])
                    except:
                        duration_num = 1
                    durations = []
                    for duration in power_durations:
                        if duration != -1:
                            durations.append(duration)
                    try:
                        power_desc = power_desc.replace(f"${desc_split}$", str(durations[duration_num - 1]))
                        continue
                    except:
                        pass
                if "ePercent" in desc_split:
                    try:
                        percent_num = int(desc_split[-1])
                    except:
                        percent_num = 1
                    percents = []
                    for percent in range(len(power_percents)):
                        if power_percents[percent] != -1:
                            power_percent = power_percents[percent]
                            if power_dmg_types[percent] == "Debuff":
                                debuff = True
                            percents.append(power_percent)
                    power_desc = power_desc.replace(f"${desc_split}$", str(percents[percent_num - 1]))
                    continue
                if "eValue" in desc_split:
                    try:
                        value_num = int(desc_split[-1])
                    except:
                        value_num = 0
                    operators = []
                    stats = []
                    amounts = []
                    for value in range(len(power_mult_amounts)):
                        if power_adjustment_nums[value] == value_num:
                            operators.append(power_operators[value])
                            stats.append(power_mult_stats[value])
                            amounts.append(power_mult_amounts[value])
                    final_text = ""
                    for value in range(len(amounts)):
                        if operators[value] == "Set" or operators[value] == "Multiply Add":
                            final_text += f"+ x{amounts[value]}{database.get_stat_emoji(stats[value])} "
                    final_text = final_text[2:-1]
                    final_text = f"({final_text})"
                    power_desc = power_desc.replace(f"${desc_split}$", final_text)
                if "eDamage" in desc_split:
                    try:
                        value_num = int(desc_split[-1])
                    except:
                        value_num = 0
                    if "eAbility" not in desc_split:
                        operators = []
                        dmg_stats = []
                        amounts = []
                        for value in range(len(power_mult_amounts)):
                            if power_adjustment_nums[value] == value_num:
                                operators.append(power_operators[value])
                                dmg_stats.append(power_mult_stats[value])
                                amounts.append(power_mult_amounts[value])
                        final_text = ""
                        for value in range(len(amounts)):
                            if operators[value] == "Set" or operators[value] == "Multiply Add":
                                final_text += f"+ x{amounts[value]}{database.get_stat_emoji(dmg_stats[value])} "
                        final_text = final_text[2:-1]
                        final_text = f"({final_text})"
                        power_desc = power_desc.replace(f"${desc_split}$", final_text)
                    else:
                        ability_damage, ability_dmg_type = await database.get_ability_damage(self.bot.db, power_summons[-1])
                        power_desc = power_desc.replace(f"${desc_split}$", ability_damage)
                if "eModifyPercent" in desc_split:
                    percents = []
                    for percent in power_percents:
                        if percent != -1:
                            percents.append(100 - percent)
                    power_desc = power_desc.replace(f"${desc_split}$", f"{percents[0]}")
                if "eSpongeAmount" in desc_split:
                    sponge_stats = []
                    sponge_amounts = []
                    for amount in range(len(power_adjustment_types)):
                        sponge_stats.append(power_mult_stats[amount])
                        sponge_amounts.append(power_mult_amounts[amount])
                    if len(sponge_stats) == 0:
                        power_stat = round(float(power_stats[0]))
                        power_desc = power_desc.replace(f"${desc_split}$", f"{power_stat}")
                    else:
                        power_desc = power_desc.replace(f"${desc_split}$", f"(x{sponge_amounts[0]} {database.get_stat_emoji(sponge_stats[0])})")
                if "ePulseAmount" in desc_split:
                    try:
                        value_num = int(desc_split[-1])
                    except:
                        value_num = 0
                    operators = []
                    dmg_stats = []
                    amounts = []
                    for value in range(len(power_mult_amounts)):
                        if power_adjustment_nums[value] == value_num:
                            operators.append(power_operators[value])
                            dmg_stats.append(power_mult_stats[value])
                            amounts.append(power_mult_amounts[value])
                    final_text = ""
                    for value in range(len(amounts)):
                        if operators[value] == "Set" or operators[value] == "Multiply Add":
                            final_text += f"+ x{amounts[value]}{database.get_stat_emoji(dmg_stats[value])} "
                    final_text = final_text[2:-1]
                    final_text = f"({final_text})"
                    power_desc = power_desc.replace(f"${desc_split}$", final_text)
                if "eEffectIcon" in desc_split:
                    try:
                        value_num = int(desc_split[-1])
                    except:
                        try:
                            value_test = value_num
                        except:
                            value_num = 0
                        else:
                            pass
                    power_desc = power_desc.replace(f"${desc_split}$", f"{database._DOT_ICONS[power_dmg_types[value_num]]}")
                if "eHeal" in desc_split:
                    try:
                        value_num = int(desc_split[-1])
                    except:
                        value_num = 0
                    operators = []
                    heal_stats = []
                    amounts = []
                    for value in range(len(power_mult_amounts)):
                        if power_adjustment_nums[value] == value_num:
                            operators.append(power_operators[value])
                            heal_stats.append(power_mult_stats[value])
                            amounts.append(power_mult_amounts[value])
                    final_text = ""
                    for value in range(len(amounts)):
                        if operators[value] == "Set" or operators[value] == "Multiply Add":
                            final_text += f"+ x{amounts[value]}{database.get_stat_emoji(heal_stats[value])} "
                    final_text = final_text[2:-1]
                    final_text = f"({final_text})"
                    power_desc = power_desc.replace(f"${desc_split}$", final_text)
                if "eBonus" in desc_split:
                    try:
                        bonus_num = int(desc_split[-1])
                    except:
                        bonus_num = 1
                    bonuses = []
                    for bonus in range(len(power_percents)):
                        if power_percents[bonus] != -1:
                            power_bonus = power_percents[bonus]
                            if power_dmg_types[bonus] == "Debuff":
                                debuff = True
                            power_bonus = int(power_bonus / 100)
                            bonuses.append(power_bonus)
                    power_desc = power_desc.replace(f"${desc_split}$", str(bonuses[bonus_num - 1]))
                    continue
                if "eIcon" in desc_split:
                    try:
                        icon_num = int(desc_split[-1])
                    except:
                        icon_num = 1
                        try:
                            test_mult = stats[0]
                            icon_num = 0
                        except:
                            pass
                        try:
                            test_mult = dmg_stats[0]
                            icon_num = 0
                        except:
                            pass
                    try:
                        percent_length = len(percents)
                    except:
                        pass
                    else:
                        if percent_length > 0:
                            stats = []
                            for stat in range(len(power_stats)):
                                if power_stats[stat] != "" and power_percents[stat] != -1:
                                    stats.append(power_stats[stat])
                            stat_emojis = []
                            for stat in stats:
                                stat_emojis.append(database.get_stat_emoji(stat))
                            power_desc = power_desc.replace(f"${desc_split}$", f"{stat_emojis[icon_num - 1]}")
                            continue
                    try:
                        bonus_length = len(bonuses)
                    except:
                        pass
                    else:
                        if bonus_length > 0:
                            stats = []
                            for stat in range(len(power_stats)):
                                if power_stats[stat] != "" and power_percents[stat] != -1:
                                    stats.append(power_stats[stat])
                            stat_emojis = []
                            for stat in stats:
                                stat_emojis.append(database.get_stat_emoji(stat))
                            power_desc = power_desc.replace(f"${desc_split}$", f"{stat_emojis[icon_num - 1]}")
                            continue
                    try:
                        test_mult = stats[0]
                    except:
                        pass
                    else:
                        stat_icon = power_stats[icon_num]
                        power_desc = power_desc.replace(f"${desc_split}$", f"{database.get_stat_emoji(stat_icon)} ")
                    try:
                        test = ability_dmg_type
                    except:
                        pass
                    else:
                        try:
                            dmg_type = ability_dmg_type
                            dmg_type_text = ""
                            if dmg_type == "Inherit":
                                dmg_type_text = f"{database.get_stat_emoji('Physical Damage')}/{database.get_stat_emoji('Magical Damage')}"
                            else:
                                dmg_type_text = f"{database.get_stat_emoji(dmg_type)}"
                            power_desc = power_desc.replace(f"${desc_split}$", f"{dmg_type_text} ")
                            continue
                        except:
                            pass
                    try:
                        test_mult = dmg_stats[0]
                    except:
                        pass
                    else:
                        try:
                            dmg_type = power_dmg_types[icon_num]
                            dmg_type_text = ""
                            if dmg_type == "Inherit":
                                dmg_type_text = f"{database.get_stat_emoji('Physical Damage')}/{database.get_stat_emoji('Magical Damage')}"
                            else:
                                dmg_type_text = f"{database.get_stat_emoji(dmg_type)}"
                            power_desc = power_desc.replace(f"${desc_split}$", f"{dmg_type_text} ")
                            continue
                        except:
                            pass
                    try:
                        test_mult = heal_stats[0]
                    except:
                        pass
                    else:
                        power_desc = power_desc.replace(f"${desc_split}$", f"{database.get_stat_emoji('Max Health')}")
                            
                power_desc = power_desc.replace(f"${desc_split}$", f"{desc_split}")
        
        power_desc = power_desc.replace("<br>", "\n")
        power_desc = power_desc.replace("\\n", "\n")
        power_desc = power_desc.replace("%%", "%")
        if debuff == False:
            power_desc = power_desc.replace("#1:%+.0", "+")
        else:
            power_desc = power_desc.replace("#1:%+.0", "-")
        power_desc = power_desc.replace("#1:%.0", "")
        power_desc = power_desc.replace("#2:%.0", "")
        power_desc = power_desc.replace("#3:%.0", "-")
        power_desc = power_desc.replace("%.0", "")

        pvp_tag = row[5]

        embed = (
            discord.Embed(
                color=discord.Color.greyple(),
            )
            .set_author(name=f"{power_name}\n({real_name}: {power_id})")
            .add_field(name="Description", value=power_desc, inline=False)
            .add_field(name="\u200b", value=f"**{database.PVP_TAG[pvp_tag]}**", inline=False)
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
    
    async def build_list_embed(self, rows: List[tuple], name: str):
        desc_string = ""
        for row in rows:
            real_name = row[2].decode("utf-8")
            power_name = await database.translate_name(self.bot.db, row[1])
            desc_string += f"{power_name} ({real_name})\n"
        
        embed = discord.Embed(
            color=discord.Color.greyple(),
            description=desc_string,
        ).set_author(name=f"Searching for: {name}", icon_url=emojis.UNIVERSAL.url)

        embeds = []
        embeds.append(embed)

        return embeds

    @app_commands.command(name="list", description="Finds a list of power names that contain the string")
    @app_commands.describe(name="The name of the powers to search for")
    async def list(
        self,
        interaction: discord.Interaction,
        name: str,
    ):
        await interaction.response.defer()
        if type(interaction.channel) is DMChannel or type(interaction.channel) is PartialMessageable:
            logger.info("{} requested power list for '{}'", interaction.user.name, name)
        else:
            logger.info("{} requested power list for '{}' in channel #{} of {}", interaction.user.name, name, interaction.channel.name, interaction.guild.name)
        
        rows = await self.fetch_power_list(name)
        
        if rows:
            view = ItemView(await self.build_list_embed(rows, name))
            try:
                await view.start(interaction)
            except discord.errors.HTTPException:
                logger.info("List for '{}' too long, sending back error message")
                embed = discord.Embed(description=f"Power list for {name} too long! Try again with a more specific keyword.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
                await interaction.followup.send(embed=embed)
        else:
            logger.info("Failed to find list for '{}'", name)
            embed = discord.Embed(description=f"No powers containing name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
            await interaction.followup.send(embed=embed)

async def setup(bot: TheBot):
    await bot.add_cog(Powers(bot))