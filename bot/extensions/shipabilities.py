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

FIND_SHIP_ABILITY_NAME_QUERY = """
SELECT * FROM ship_abilities
INNER JOIN locale_en ON locale_en.id == ship_abilities.name
WHERE locale_en.data COLLATE NOCASE = ?
"""

FIND_OBJECT_NAME_QUERY = """
SELECT * FROM ship_abilities
WHERE ship_abilities.real_name == ? COLLATE NOCASE
"""

FIND_SHIP_ABILITIES_WITH_FILTER_PLACEHOLDER_QUERY = """
SELECT * FROM ship_abilities
INNER JOIN locale_en ON locale_en.id == ship_abilities.name
WHERE locale_en.data COLLATE NOCASE IN ({placeholders})
"""

class ShipAbilities(commands.GroupCog, name="shipability"):
    def __init__(self, bot: TheBot):
        self.bot = bot

    async def fetch_ship_ability(self, name: str):
        async with self.bot.db.execute(FIND_SHIP_ABILITY_NAME_QUERY, (name,)) as cursor:
            return await cursor.fetchall()

    async def fetch_object_name(self, name: str):
        name_bytes = name.encode('utf-8')
        async with self.bot.db.execute(FIND_OBJECT_NAME_QUERY, (name_bytes,)) as cursor:
            return await cursor.fetchall()

    async def fetch_ship_ability_filter_list(self, items) -> List[tuple]:
        if isinstance(items, str):
            items = [items]

        results = []
        for chunk in database.sql_chunked(items, 900):  # Stay under SQLite's limit
            placeholders = database._make_placeholders(len(chunk))
            query = FIND_SHIP_ABILITIES_WITH_FILTER_PLACEHOLDER_QUERY.format(placeholders=placeholders)

            args = (
                *chunk,
            )

            async with self.bot.db.execute(query, args) as cursor:
                rows = await cursor.fetchall()

            results.extend(rows)

        return results

    async def build_ship_ability_embed(self, row):
        power_id = row[0]
        real_name = row[2].decode("utf-8")

        power_name = await database.translate_name(self.bot.db, row[1])
        try:
            power_image = row[3].decode("utf-8")
        except:
            power_image = row[3]
        power_desc = await database.translate_name(self.bot.db, row[4])

        close_accuracy = row[5]
        long_accuracy = row[6]
        cooldown = row[7]

        acc_cooldown_str = ""
        if close_accuracy == long_accuracy:
            if close_accuracy <= 100:
                acc_cooldown_str += f"**{close_accuracy}% {emojis.SHIP_ACCURACY}**\n"
        else:
            acc_cooldown_str += f"**Short Range: {close_accuracy}% {emojis.SHIP_ACCURACY}**\n**Long Range: {long_accuracy}% {emojis.SHIP_ACCURACY}**\n"
        acc_cooldown_str += f"**{cooldown} {emojis.TIMER}**\n"

        power_desc = power_desc.replace(r"\n", "\n")
        while "&" in power_desc:
            try:
                desc_split = power_desc.split("&")[2]
            except:
                break
            else:
                desc_split = power_desc.split("&")[1]
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
                        if ext_split == "Icon_Attribute_Damage":
                            real_img = emojis.PHYSICAL_DAMAGE
                        lang_lookup = lang_lookup.replace(lang_lookup, f"{real_img}")

                power_desc = power_desc.replace(f"&{desc_split}&", lang_lookup)

        power_desc = power_desc.replace("$SHIP_MAX_SPEED_ICON$", f"{emojis.SHIP_MAX_SPEED}")

        embed = (
            discord.Embed(
                color=discord.Color.greyple()
            )
            .set_author(name=f"{power_name}\n({real_name}: {power_id})")
            .add_field(name="Description", value=power_desc, inline=False)
            .add_field(name="", value=acc_cooldown_str, inline=True)
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

    @app_commands.command(name="find", description="Finds a Pirate101 ship power by name")
    @app_commands.describe(name="The name of the ship power to search for")
    async def find(
        self,
        interaction: discord.Interaction,
        name: str,
        use_object_name: Optional[bool] = False,
    ):
        await interaction.response.defer()
        if type(interaction.channel) is DMChannel or type(interaction.channel) is PartialMessageable:
            logger.info("{} requested ship ability '{}'", interaction.user.name, name)
        else:
            logger.info("{} requested ship ability '{}' in channel #{} of {}", interaction.user.name, name, interaction.channel.name, interaction.guild.name)
        
        if use_object_name:
            rows = await self.fetch_object_name(name)
            if not rows:
                embed = discord.Embed(description=f"No ship abilities with object name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
                await interaction.followup.send(embed=embed)
        
        else:
            rows = await self.fetch_ship_ability(name)
            if not rows:
                filtered_rows = await self.fetch_ship_ability_filter_list(items=self.bot.ship_list)
                closest_rows = [(row, fuzz.token_set_ratio(name, row[-1]) + fuzz.ratio(name, row[-1])) for row in filtered_rows]
                closest_rows = sorted(closest_rows, key=lambda x: x[1], reverse=True)
                closest_rows = list(zip(*closest_rows))[0]
                rows = await self.fetch_ship_ability(name=closest_rows[0][-1])
                if rows:
                    logger.info("Failed to find '{}' instead searching for {}", name, closest_rows[0][-1])
        
        if rows:
            embeds = [await self.build_ship_ability_embed(row) for row in rows]
            sorted_embeds = sorted(embeds, key=lambda embed: embed[0].author.name)
            unzipped_embeds, unzipped_images = list(zip(*sorted_embeds))
            view = ItemView(unzipped_embeds, files=unzipped_images)
            await view.start(interaction)
        elif not use_object_name:
            logger.info("Failed to find '{}'", name)
            embed = discord.Embed(description=f"No ship abilities with name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
            await interaction.followup.send(embed=embed)

async def setup(bot: TheBot):
    await bot.add_cog(ShipAbilities(bot))