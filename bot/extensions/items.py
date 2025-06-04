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

FIND_ITEM_QUERY = """
SELECT * FROM items
LEFT JOIN locale_en ON locale_en.id == items.name
WHERE locale_en.data == ? COLLATE NOCASE
"""

FIND_OBJECT_NAME_QUERY = """
SELECT * FROM items
INNER JOIN locale_en ON locale_en.id == items.name
WHERE items.real_name == ? COLLATE NOCASE
"""

FIND_ITEM_STATS_QUERY = """
SELECT * FROM item_stats WHERE item_stats.item == ?
"""

class Items(commands.GroupCog, name="item"):
    def __init__(self, bot: TheBot):
        self.bot = bot
    
    async def fetch_item(self, name: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_ITEM_QUERY, (name,)) as cursor:
            return await cursor.fetchall()

    async def fetch_object_name(self, name: str) -> List[tuple]:
        name_bytes = name.encode('utf-8')
        async with self.bot.db.execute(FIND_OBJECT_NAME_QUERY, (name_bytes,)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_item_stats(self, id: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_ITEM_STATS_QUERY, (id,)) as cursor:
            return await cursor.fetchall()
        
    async def build_item_embed(self, row):
        item_id = row[0]
        real_name = row[2].decode("utf-8")

        item_name = await database.translate_name(self.bot.db, row[1])
        item_image = row[3].decode("utf-8")
        item_flags = row[5]
        item_reqs = [row[6], row[7], row[8], row[9]]

        stats = await self.fetch_item_stats(item_id)

        item_talents = []
        item_powers = []
        item_stats = []
        weapon_types = []
        for stat in stats:
            if stat[2] == "Talent":
                item_talents.append(stat)
            elif stat[2] == "Power":
                item_powers.append(stat)
            elif stat[2] == "Weapon Type":
                weapon_types.append(stat)
            else:
                item_stats.append(stat)
        
        stat_string = ""
        if weapon_types != []:
            for type in weapon_types:
                if "Damage" in str(type[3]):
                    stat_string += "Does " + type[3] + "\n"
                elif isinstance(type[3], str):
                    stat_string += type[3] + " Weapon\n"
                elif isinstance(type[3], int) and type[3] != None:
                    primary_stat_flags = database.translate_stat_flags(type[3])
                    stat_string += "Boosts from "
                    for flag in range(len(primary_stat_flags)):
                        try:
                            test = primary_stat_flags[flag + 1]
                        except:
                            test = primary_stat_flags[flag - 1]
                            if test == primary_stat_flags[flag]:
                                stat_string += primary_stat_flags[flag]
                            else:
                                stat_string += " or " + primary_stat_flags[flag]
                        else:
                            stat_string += primary_stat_flags[flag] + ", "
                    stat_string += "\n"
                    
        for stat in item_stats:
            if stat[4] < 1:
                stat_rounded = round(stat[4], 2)
                stat_rounded_int = int(stat_rounded * 100)
                stat_string += "+" + str(stat_rounded_int) + "%"
            else:
                stat_string += "+" + str(stat[4])
            stat_string += " " + str(stat[3]) + "\n"
        
        for talent in item_talents:
            talent_name, object_name = await database.translate_talent_name(self.bot.db, talent[3])
            stat_string += "+1 Rank of " + talent_name + " (" + object_name + ")\n"

        for power in item_powers:
            power_name, object_name = await database.translate_power_name(self.bot.db, power[3])
            stat_string += "+1 copy of " + power_name + " (" + object_name + ")\n"

        requirement_string = ""
        if item_reqs[0]:
            requirement_string += item_reqs[0] + " only\n"
        if item_reqs[1] > 1:
            requirement_string += "Level " + str(item_reqs[1]) + "+ only\n"
        if item_reqs[2]:
            talent_req, object_req = await database.translate_talent_name(self.bot.db, item_reqs[2])
            requirement_string += "Talent: " + str(talent_req) + " " + str(item_reqs[3]) + " (" + object_req + ")\n"
        
        embed = (
            discord.Embed(
                # Make this actually do school colors later
                color=database.make_school_color(0),
            )
            .set_author(name=f"{item_name}\n({real_name}: {item_id})")
            .add_field(name="Stats", value=stat_string, inline=True)
        )

        if item_image:
            try:
                image_name = (item_image.split("|")[-1]).split(".")[0]
                png_file = f"{image_name}.png"
                png_name = png_file.replace(" ", "")
                png_name = os.path.basename(png_name)
                file_path = Path("PNG_Images") / png_name
                discord_file = discord.File(file_path, filename=png_name)
                embed.set_thumbnail(url=f"attachment://{png_name}")
            except:
                pass
        
        if requirement_string != "":
            try:
                embed.add_field(name="Requirements", value=requirement_string, inline=False)
            except:
                pass

        flags = database.translate_flags(item_flags)
        if len(flags) > 0:
            embed.add_field(name="Flags", value="\n".join(flags), inline=False)
        
        return embed
    
    @app_commands.command(name="find", description="Finds a Pirate101 item by name")
    @app_commands.describe(name="The name of the item to search for")
    async def find(
        self,
        interaction: discord.Interaction,
        name: str,
        use_object_name: Optional[bool] = False,
    ):
        await interaction.response.defer()
        if type(interaction.channel) is DMChannel or type(interaction.channel) is PartialMessageable:
            logger.info("{} requested item '{}'", interaction.user.name, name)
        else:
            logger.info("{} requested item '{}' in channel #{} of {}", interaction.user.name, name, interaction.channel.name, interaction.guild.name)
        
        if use_object_name:
            rows = await self.fetch_object_name(name)
            if not rows:
                embed = discord.Embed(description=f"No items with object name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
                await interaction.followup.send(embed=embed)
        
        else:
            rows = await self.fetch_item(name)
        
        if rows:
            view = ItemView([await self.build_item_embed(row) for row in rows])
            await view.start(interaction)
        elif not use_object_name:
            logger.info("Failed to find '{}'", name)
            embed = discord.Embed(description=f"No items with name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
            await interaction.followup.send(embed=embed)

async def setup(bot: TheBot):
    await bot.add_cog(Items(bot))