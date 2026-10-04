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

FIND_SHIP_NAME_QUERY = """
SELECT * FROM ships
INNER JOIN locale_en ON locale_en.id == ships.name
WHERE locale_en.data COLLATE NOCASE = ?
"""

FIND_OBJECT_NAME_QUERY = """
SELECT * FROM ships
WHERE ships.real_name == ? COLLATE NOCASE
"""

FIND_SHIPS_WITH_FILTER_PLACEHOLDER_QUERY = """
SELECT * FROM ships
INNER JOIN locale_en ON locale_en.id == ships.name
WHERE locale_en.data COLLATE NOCASE IN ({placeholders})
"""

FIND_DEFAULT_POWER_QUERY = """
SELECT * FROM ship_default_powers
WHERE ship_default_powers.ship == ?
"""

FIND_SHIP_UNITS_QUERY = """
SELECT * FROM ship_units
WHERE ship_units.ship == ?
"""

FIND_ROSTER_QUERY = """
SELECT * FROM roster_units
WHERE roster_units.roster == ?
"""

FIND_SHIP_ABILITY_QUERY = """
SELECT * FROM ship_abilities
WHERE ship_abilities.id == ?
"""

FIND_SHIP_UNIT_QUERY = """
SELECT * FROM units
WHERE units.id == ?
"""

class Ships(commands.GroupCog, name="ship"):
    def __init__(self, bot: TheBot):
        self.bot = bot
    
    async def fetch_ship(self, name: str):
        async with self.bot.db.execute(FIND_SHIP_NAME_QUERY, (name,)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_object_name(self, name: str):
        name_bytes = name.encode('utf-8')
        async with self.bot.db.execute(FIND_OBJECT_NAME_QUERY, (name_bytes,)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_ship_filter_list(self, items) -> List[tuple]:
        if isinstance(items, str):
            items = [items]

        results = []
        for chunk in database.sql_chunked(items, 900):  # Stay under SQLite's limit
            placeholders = database._make_placeholders(len(chunk))
            query = FIND_SHIPS_WITH_FILTER_PLACEHOLDER_QUERY.format(placeholders=placeholders)

            args = (
                *chunk,
            )

            async with self.bot.db.execute(query, args) as cursor:
                rows = await cursor.fetchall()

            results.extend(rows)

        return results
    
    async def fetch_default_powers(self, id: str):
        async with self.bot.db.execute(FIND_DEFAULT_POWER_QUERY, (id,)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_ship_units(self, id: str):
        async with self.bot.db.execute(FIND_SHIP_UNITS_QUERY, (id,)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_roster(self, id: str):
        async with self.bot.db.execute(FIND_ROSTER_QUERY, (id,)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_ship_ability(self, id: str):
        async with self.bot.db.execute(FIND_SHIP_ABILITY_QUERY, (id,)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_ship_unit(self, id: str):
        async with self.bot.db.execute(FIND_SHIP_UNIT_QUERY, (id,)) as cursor:
            return await cursor.fetchall()
    
    async def build_ship_embed(self, row):
        ship_id = row[0]
        real_name = row[2].decode('utf-8')
        ship_name = await database.translate_name(self.bot.db, row[1])
        ship_title = await database.translate_name(self.bot.db, row[4])
        try:
            ship_image = row[3].decode("utf-8")
        except:
            ship_image = ""
        ship_origin = row[5]
        ship_lvl_req = row[6]
        ship_class = row[8]

        ship_default_powers = await self.fetch_default_powers(ship_id)
        ship_units = await self.fetch_ship_units(ship_id)

        powers = []
        for power in ship_default_powers:
            powers.append(await self.fetch_ship_ability(power[2]))
        
        units = []
        boss = ""
        for unit in ship_units:
            if unit[2] == "Unit":
                units.append(await self.fetch_ship_unit(unit[3]))
                boss = await database.translate_name(self.bot.db, units[-1][0][1])
            elif unit[2] == "Roster":
                roster = await self.fetch_roster(unit[3])
                for roster_unit in roster:
                    units.append(await self.fetch_ship_unit(roster_unit[2]))
        
        power_string = ""
        for power in powers:
            power_string += f"{await database.translate_name(self.bot.db, power[0][1])} ({power[0][2].decode('utf-8')})\n"

        unit_string = ""
        for unit in units:
            unit_string += f"{await database.translate_name(self.bot.db, unit[0][1])} ({unit[0][2].decode('utf-8')})\n"

        desc_string = ""
        if ship_origin:
            desc_string += f"{ship_origin} Origin\n"
        
        author_string = ""
        if boss != "":
            if boss[-1] != "s":
                author_string += f"{boss}'s\n"
            else:
                author_string += f"{boss}'\n"
        author_string += f"{ship_name}\n"
        if ship_title and ship_title != ship_name:
            author_string += f"{ship_title}\n"
        author_string += f"({real_name}: {ship_id})"

        requirement_string = ""
        if ship_lvl_req > 1:
            requirement_string += f"Level {ship_lvl_req}+ only\n"

        embed = (
            discord.Embed(
                color=database.make_origin_color(ship_origin),
                description=desc_string,
            )
            .set_author(name=author_string)
        )

        if requirement_string != "":
            try:
                embed.add_field(name="Requirements", value=requirement_string, inline=False)
            except:
                pass
        
        if power_string != "":
            try:
                embed.add_field(name="Default Powers", value=power_string, inline=False)
            except:
                pass
        
        if unit_string != "":
            try:
                embed.add_field(name="Crew", value=unit_string, inline=False)
            except:
                pass

        discord_file = None
        if ship_image:
            try:
                image_name = ship_image.split(".")[0]
                png_file = f"{image_name}.png"
                png_name = png_file.replace(" ", "")
                png_name = os.path.basename(png_name)
                file_path = Path("PNG_Images") / png_name
                discord_file = discord.File(file_path, filename=png_name)
                embed.set_thumbnail(url=f"attachment://{png_name}")
            except:
                pass
        
        return embed, discord_file
    
    @app_commands.command(name="find", description="Finds a Pirate101 ship (ally or enemy) by name")
    @app_commands.describe(name="The name of the ship to search for")
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
            rows = await self.fetch_ship(name)
            if not rows:
                filtered_rows = await self.fetch_ship_filter_list(items=self.bot.ship_list)
                closest_rows = [(row, fuzz.token_set_ratio(name, row[-1]) + fuzz.ratio(name, row[-1])) for row in filtered_rows]
                closest_rows = sorted(closest_rows, key=lambda x: x[1], reverse=True)
                closest_rows = list(zip(*closest_rows))[0]
                rows = await self.fetch_ship(name=closest_rows[0][-1])
                if rows:
                    logger.info("Failed to find '{}' instead searching for {}", name, closest_rows[0][-1])
        
        if rows:
            embeds = [await self.build_ship_embed(row) for row in rows]
            sorted_embeds = sorted(embeds, key=lambda embed: embed[0].author.name)
            unzipped_embeds, unzipped_images = list(zip(*sorted_embeds))
            view = ItemView(unzipped_embeds, files=unzipped_images)
            await view.start(interaction)
        elif not use_object_name:
            logger.info("Failed to find '{}'", name)
            embed = discord.Embed(description=f"No items with name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
            await interaction.followup.send(embed=embed)

async def setup(bot: TheBot):
    await bot.add_cog(Ships(bot))