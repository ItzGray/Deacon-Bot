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

from .talents import Talents
from .powers import Powers
from .. import TheBot, database, emojis
from ..menus import ItemView

FIND_ITEM_QUERY = """
SELECT * FROM ship_items
LEFT JOIN locale_en ON locale_en.id == ship_items.name
WHERE locale_en.data == ? COLLATE NOCASE
"""

FIND_OBJECT_NAME_QUERY = """
SELECT * FROM ship_items
WHERE ship_items.real_name == ? COLLATE NOCASE
"""

FIND_ITEM_STATS_QUERY = """
SELECT * FROM ship_item_stats WHERE ship_item_stats.item == ?
"""

FIND_ITEMS_WITH_FILTER_QUERY = """
SELECT * FROM ship_items
INNER JOIN locale_en ON locale_en.id == ship_items.name
WHERE locale_en.data == ? COLLATE NOCASE
AND (? = 'All' OR ship_items.equip_origin = ?)
AND (? = 'Any' OR ship_items.item_type = ?)
AND (? = -1 OR ship_items.equip_naut_level >= ?)
COLLATE NOCASE
"""

FIND_ITEM_CONTAIN_STRING_QUERY = """
SELECT * FROM ship_items
LEFT JOIN locale_en ON locale_en.id == ship_items.name
WHERE INSTR(lower(locale_en.data), ?) > 0
"""

FIND_ITEMS_CONTAIN_STRING_WITH_FILTER_QUERY = """
SELECT * FROM ship_items
INNER JOIN locale_en ON locale_en.id == ship_items.name
WHERE INSTR(lower(locale_en.data), ?) > 0
AND (? = 'All' OR ship_items.equip_origin = ?)
AND (? = 'Any' OR ship_items.item_type = ?)
AND (? = -1 OR ship_items.equip_naut_level >= ?)
COLLATE NOCASE
"""

FIND_ITEMS_WITH_FILTER_PLACEHOLDER_QUERY = """
SELECT * FROM ship_items
INNER JOIN locale_en ON locale_en.id == ship_items.name
WHERE locale_en.data COLLATE NOCASE IN ({placeholders})
AND (? = 'Any' OR ship_items.equip_origin = ?)
AND (? = 'Any' OR ship_items.item_type = ?)
AND (? = -1 OR ship_items.equip_naut_level >= ?)
COLLATE NOCASE
"""

class ShipItems(commands.GroupCog, name="shipitem"):
    def __init__(self, bot: TheBot):
        self.bot = bot

    async def fetch_item(self, name: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_ITEM_QUERY, (name,)) as cursor:
            return await cursor.fetchall()
        
    async def fetch_object_name(self, name: str) -> List[tuple]:
        name_bytes = name.encode('utf-8')
        async with self.bot.db.execute(FIND_OBJECT_NAME_QUERY, (name_bytes,)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_item_with_filter(self, name: str, origin: str, kind: str, level: int):
        async with self.bot.db.execute(FIND_ITEMS_WITH_FILTER_QUERY, (name,origin,origin,kind,kind,level,level)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_item_list(self, name: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_ITEM_CONTAIN_STRING_QUERY, (name,)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_item_list_with_filter(self, name: str, origin: str, kind: str, level: int):
        async with self.bot.db.execute(FIND_ITEMS_CONTAIN_STRING_WITH_FILTER_QUERY, (name,origin,origin,kind,kind,level,level)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_item_stats(self, id: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_ITEM_STATS_QUERY, (id,)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_item_filter_list(self, items, origin: str, kind: str, level: int) -> List[tuple]:
        if isinstance(items, str):
            items = [items]

        results = []
        for chunk in database.sql_chunked(items, 900):  # Stay under SQLite's limit
            placeholders = database._make_placeholders(len(chunk))
            query = FIND_ITEMS_WITH_FILTER_PLACEHOLDER_QUERY.format(placeholders=placeholders)

            args = (
                *chunk,
                origin, origin,
                kind, kind,
                level, level
            )

            async with self.bot.db.execute(query, args) as cursor:
                rows = await cursor.fetchall()

            results.extend(rows)

        return results
    
    async def build_item_embed(self, row):
        item_id = row[0]
        real_name = row[2].decode("utf-8")

        item_name = await database.translate_name(self.bot.db, row[1])
        try:
            item_image = row[3].decode("utf-8")
        except:
            item_image = ""
        item_type = row[4]
        item_flags = row[5]
        item_reqs = [row[6], row[7], row[8]]

        stats = await self.fetch_item_stats(item_id)

        item_powers = []
        item_stats = []
        for stat in stats:
            if stat[2] == "Power":
                item_powers.append(stat)
            else:
                item_stats.append(stat)
        
        stat_string = ""
        round_arr_1 = ["Boost Speed", "Turning Speed"]
        round_arr_2 = ["Max Boost Fuel Capacity"]
        round_arr_3 = ["Acceleration", "Maximum Speed"]
        round_arr_4 = ["Boost Fuel Efficiency"]
        for stat in item_stats:
            if stat[3] in round_arr_1:
                stat_rounded = round(stat[4], 2)
                stat_rounded_int = int(stat_rounded * 100)
                stat_string += "+" + str(stat_rounded_int) + "%"
                if stat_string[1] == "-":
                    stat_string = stat_string[1:]
            elif stat[3] in round_arr_2:
                stat_rounded = round(stat[4], 2)
                stat_rounded_int = int((stat_rounded - 1) * 100)
                stat_string += "+" + str(stat_rounded_int) + "%"
                if stat_string[1] == "-":
                    stat_string = stat_string[1:]
            elif stat[3] in round_arr_3:
                stat_rounded = round(stat[4], 2)
                stat_rounded_int = int(stat_rounded / 100)
                stat_string += "+" + str(stat_rounded_int) + "%"
                if stat_string[1] == "-":
                    stat_string = stat_string[1:]
            elif stat[3] in round_arr_4:
                stat_rounded = round(stat[4], 2)
                stat_rounded_int = int((1 - stat_rounded) * 100)
                stat_string += "+" + str(stat_rounded_int) + "%"
                if stat_string[1] == "-":
                    stat_string = stat_string[1:]
            else:
                stat_string += "+" + str(stat[4])
            stat_string += f" {str(stat[3])} {database.get_ship_stat_emoji(str(stat[3]))}\n"
        
        for power in item_powers:
            power_name, object_name = await database.translate_ship_power_name(self.bot.db, power[3])
            stat_string += "Gives " + power_name + " (" + object_name + ")\n"
        
        requirement_string = ""
        if item_reqs[0] != "All":
            requirement_string += f"{item_reqs[0]} Origin\n"
        if item_reqs[1] > 1:
            requirement_string += "Level " + str(item_reqs[1]) + "+ only\n"
        if item_reqs[2] > 1:
            requirement_string += "Nautical Level " + str(item_reqs[2]) + "+ only\n"
        
        embed = (
            discord.Embed(
                color=database.make_origin_color(item_reqs[0]),
            )
            .set_author(name=f"{item_name}\n({real_name}: {item_id})", icon_url=database.get_ship_item_icon_url(item_type))
            .add_field(name="Stats", value=stat_string, inline=True)
        )

        discord_file = None
        if item_image:
            try:
                image_name = item_image.split(".")[0]
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
        
        return embed, discord_file
    
    @app_commands.command(name="find", description="Finds a Pirate101 ship item by name")
    @app_commands.describe(name="The name of the item to search for", kind="The type of item to search for", nautical_level="The nautical level the item requires (also includes items that require a higher level)")
    async def find(
        self,
        interaction: discord.Interaction,
        name: str,
        origin: Optional[Literal["All", "Raft", "Pirate", "Monquistador", "Bison", "Samoorai", "Royal Navy", "Eagle"]] = "Any",
        kind: Optional[Literal["Armor", "Anchor", "Cannons", "Horn", "Figurehead", "Rudder", "Sails", "Wheel"]] = "Any",
        nautical_level: Optional[int] = -1,
        use_object_name: Optional[bool] = False,
    ):
        await interaction.response.defer()
        if type(interaction.channel) is DMChannel or type(interaction.channel) is PartialMessageable:
            logger.info("{} requested ship item '{}'", interaction.user.name, name)
        else:
            logger.info("{} requested ship item '{}' in channel #{} of {}", interaction.user.name, name, interaction.channel.name, interaction.guild.name)
        
        if use_object_name:
            rows = await self.fetch_object_name(name)
            if not rows:
                embed = discord.Embed(description=f"No ship items with object name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
                await interaction.followup.send(embed=embed)
        
        else:
            if origin != "Any" or kind != "Any" or nautical_level != -1:
                rows = await self.fetch_item_with_filter(name, origin, kind, nautical_level)
            else:
                rows = await self.fetch_item(name)
            if not rows:
                filtered_rows = await self.fetch_item_filter_list(items=self.bot.ship_item_list, origin=origin, kind=kind, level=nautical_level)
                closest_rows = [(row, fuzz.token_set_ratio(name, row[-1]) + fuzz.ratio(name, row[-1])) for row in filtered_rows]
                closest_rows = sorted(closest_rows, key=lambda x: x[1], reverse=True)
                closest_rows = list(zip(*closest_rows))[0]
                if origin != "Any" or kind != "Any" or nautical_level != -1:
                    rows = await self.fetch_item_with_filter(name=closest_rows[0][-1], origin=origin, kind=kind, level=nautical_level)
                else:
                    rows = await self.fetch_item(name=closest_rows[0][-1])
                if rows:
                    logger.info("Failed to find '{}' instead searching for {}", name, closest_rows[0][-1])
        
        if rows:
            embeds = [await self.build_item_embed(row) for row in rows]
            sorted_embeds = sorted(embeds, key=lambda embed: embed[0].author.name)
            unzipped_embeds, unzipped_images = list(zip(*sorted_embeds))
            view = ItemView(unzipped_embeds, files=unzipped_images)
            await view.start(interaction)
        elif not use_object_name:
            logger.info("Failed to find '{}'", name)
            embed = discord.Embed(description=f"No ship items with name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
            await interaction.followup.send(embed=embed)

async def setup(bot: TheBot):
    await bot.add_cog(ShipItems(bot))