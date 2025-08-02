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

FIND_PET_QUERY = """
SELECT * FROM pets
LEFT JOIN locale_en ON locale_en.id == pets.name
WHERE locale_en.data == ? COLLATE NOCASE
"""

FIND_OBJECT_NAME_QUERY = """
SELECT * FROM pets
INNER JOIN locale_en ON locale_en.id == pets.name
WHERE pets.real_name == ? COLLATE NOCASE
"""

TALENT_NAME_ID_QUERY_1 = """
SELECT * FROM indiv_pet_talents WHERE indiv_pet_talents.pet == ?
"""

TALENT_NAME_ID_QUERY_2 = """
SELECT * FROM pet_talents WHERE pet_talents.id == ?
"""

POWER_NAME_ID_QUERY_1 = """
SELECT * FROM indiv_pet_powers WHERE indiv_pet_powers.pet == ?
"""

POWER_NAME_ID_QUERY_2 = """
SELECT * FROM pet_powers WHERE pet_powers.id == ?
"""

FIND_PET_CONTAIN_STRING_QUERY = """
SELECT * FROM pets
LEFT JOIN locale_en ON locale_en.id == pets.name
WHERE INSTR(lower(locale_en.data), ?) > 0
"""

FIND_PET_PLACEHOLDER_QUERY = """
SELECT * FROM pets
INNER JOIN locale_en ON locale_en.id == pets.name
WHERE locale_en.data COLLATE NOCASE IN ({placeholders})
"""

def remove_indices(lst, indices):
    return [value for index, value in enumerate(lst) if index not in indices]

class Pets(commands.GroupCog, name="pet"):
    def __init__(self, bot: TheBot):
        self.bot = bot

    async def fetch_pet(self, name: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_PET_QUERY, (name,)) as cursor:
            return await cursor.fetchall()
        
    async def fetch_object_name(self, name: str) -> List[tuple]:
        name_bytes = name.encode('utf-8')
        async with self.bot.db.execute(FIND_OBJECT_NAME_QUERY, (name_bytes,)) as cursor:
            return await cursor.fetchall()

    async def fetch_pet_list(self, name: str) -> List[tuple]:
        async with self.bot.db.execute(FIND_PET_CONTAIN_STRING_QUERY, (name,)) as cursor:
            return await cursor.fetchall()
    
    async def fetch_pet_talents(self, id: str) -> List[tuple]:
        talents = []
        async with self.bot.db.execute(TALENT_NAME_ID_QUERY_1, (id,)) as cursor:
            async for row in cursor:
                talents.append(str(row[2]))

        final_talents = []
        for talent in range(len(talents)):
            async with self.bot.db.execute(TALENT_NAME_ID_QUERY_2, (talents[talent],)) as cursor:
                final_talents.append(await cursor.fetchall())
        
        return final_talents
        
    async def fetch_pet_powers(self, id: str) -> List[tuple]:
        powers = []
        async with self.bot.db.execute(POWER_NAME_ID_QUERY_1, (id,)) as cursor:
            async for row in cursor:
                powers.append(str(row[2]))

        final_powers = []
        for power in range(len(powers)):
            async with self.bot.db.execute(POWER_NAME_ID_QUERY_2, (powers[power],)) as cursor:
                final_powers.append(await cursor.fetchall())
        
        return final_powers
    
    async def fetch_pet_filter_list(self, items) -> List[tuple]:
        if isinstance(items, str):
            items = [items]

        results = []
        for chunk in database.sql_chunked(items, 900):  # Stay under SQLite's limit
            placeholders = database._make_placeholders(len(chunk))
            query = FIND_PET_PLACEHOLDER_QUERY.format(placeholders=placeholders)

            args = (
                *chunk,
            )

            async with self.bot.db.execute(query, args) as cursor:
                rows = await cursor.fetchall()

            results.extend(rows)

        return results

    async def build_pet_embed(self, row):
        pet_id = row[0]
        real_name = row[2].decode("utf-8")
        
        strength = row[4]
        agility = row[5]
        will = row[6]
        stat_power = row[7]
        guts = row[8]
        guile = row[9]
        grit = row[10]
        health = row[11]

        pet_name = await database.translate_name(self.bot.db, row[1])
        try:
            pet_image = row[3].decode("utf-8")
        except:
            pet_image = ""
        pet_flags = row[12]

        talents = await self.fetch_pet_talents(pet_id)
        powers = await self.fetch_pet_powers(pet_id)

        talents = sorted(talents, key=lambda talent: talent[0])
        powers = sorted(powers, key=lambda power: power[0])

        talents_unsorted = []
        talent_ids_unsorted = []
        talent_rarities_unsorted = []
        for talent in talents:
            if talent[0][1] == None:
                talents_unsorted.append(talent[0][2].decode("utf-8"))
            else:
                talents_unsorted.append(await database.translate_name(self.bot.db, talent[0][1]))
            talent_ids_unsorted.append(talent[0][0])
            talent_rarities_unsorted.append(talent[0][5])
        talent_string = ""
        for talent in range(len(talents_unsorted)):
            talent_string += f"{database.get_rarity_emoji(talent_rarities_unsorted[talent])} {talents_unsorted[talent]}\n"
        powers_unsorted = []
        power_ids_unsorted = []
        power_rarities_unsorted = []
        for power in powers:
            if power[0][1] == None:
                if power[0][2][:4] == "TEST":
                    powers_unsorted.append(power[0][2].decode("utf-8"))
                else:
                    power_name, object_name = await database.translate_power_name(self.bot.db, power[0][6])
                    powers_unsorted.append(power_name)
            else:
                powers_unsorted.append(await database.translate_name(self.bot.db, power[0][1]))
            power_ids_unsorted.append(power[0][0])
            power_rarities_unsorted.append(power[0][5])
        power_string = ""
        for power in range(len(powers_unsorted)):
            power_string += f"{database.get_rarity_emoji(power_rarities_unsorted[power])} {str(powers_unsorted[power])}\n"
        
        pet_stat_string = ""
        pet_stat_string += f"{strength} Strength {database.get_stat_emoji('Strength')}\n"
        pet_stat_string += f"{agility} Agility {database.get_stat_emoji('Agility')}\n"
        pet_stat_string += f"{will} Will {database.get_stat_emoji('Will')}\n"
        pet_stat_string += f"{stat_power} Power {database.get_stat_emoji('Pet Power')}\n"
        pet_stat_string += f"{guts} Guts {database.get_stat_emoji('Pet Guts')}\n"
        pet_stat_string += f"{guile} Guile {database.get_stat_emoji('Pet Guile')}\n"
        pet_stat_string += f"{grit} Grit {database.get_stat_emoji('Pet Grit')}\n"
        pet_stat_string += f"{health} Max Health {database.get_stat_emoji('Max Health')}\n"

        embed = (
            discord.Embed(
                color=discord.Color.greyple(),
            )
            .set_author(name=f"{pet_name}\n({real_name}: {pet_id})", icon_url=emojis.PET.url)
            .add_field(name="Base Talents", value=talent_string, inline=True)
            .add_field(name="Base Powers", value=power_string, inline=True)
            .add_field(name="Max Stats", value=pet_stat_string, inline=False)
        )

        discord_file = None
        if pet_image:
            try:
                image_name = pet_image.split(".")[0]
                png_file = f"{image_name}.png"
                png_name = png_file.replace(" ", "")
                png_name = os.path.basename(png_name)
                file_path = Path("PNG_Images") / png_name
                discord_file = discord.File(file_path, filename=png_name)
                embed.set_thumbnail(url=f"attachment://{png_name}")
            except:
                pass


        flags = database.translate_flags(pet_flags)
        if len(flags) > 0:
            embed.add_field(name="Flags", value="\n".join(flags))

        return embed, discord_file


    @app_commands.command(name="find", description="Finds a Pirate101 pet by name")
    @app_commands.describe(name="The name of the pet to search for")
    async def find(
        self, 
        interaction: discord.Interaction, 
        name: str,
        use_object_name: Optional[bool] = False,
    ):
        await interaction.response.defer()
        if type(interaction.channel) is DMChannel or type(interaction.channel) is PartialMessageable:
            logger.info("{} requested pet '{}'", interaction.user.name, name)
        else:
            logger.info("{} requested pet '{}' in channel #{} of {}", interaction.user.name, name, interaction.channel.name, interaction.guild.name)

        if use_object_name:
            rows = await self.fetch_object_name(name)
            if not rows:
                embed = discord.Embed(description=f"No pets with object name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
                await interaction.followup.send(embed=embed)

        else:
            rows = await self.fetch_pet(name)

        if not rows:
            filtered_rows = await self.fetch_pet_filter_list(items=self.bot.pet_list)
            closest_rows = [(row, fuzz.token_set_ratio(name, row[-1]) + fuzz.ratio(name, row[-1])) for row in filtered_rows]
            closest_rows = sorted(closest_rows, key=lambda x: x[1], reverse=True)
            closest_rows = list(zip(*closest_rows))[0]
            rows = await self.fetch_pet(name=closest_rows[0][-1])
            if rows:
                logger.info("Failed to find '{}' instead searching for {}", name, closest_rows[0][-1])

        if rows:
            embeds = [await self.build_pet_embed(row) for row in rows]
            sorted_embeds = sorted(embeds, key=lambda embed: embed[0].author.name)
            unzipped_embeds, unzipped_images = list(zip(*sorted_embeds))
            view = ItemView(unzipped_embeds, files=unzipped_images)
            try:
                await view.start(interaction)
            except discord.errors.HTTPException:
                logger.info("List for '{}' too long, sending back error message")
                embed = discord.Embed(description=f"Pet list for {name} too long! Try again with a more specific keyword.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
                await interaction.followup.send(embed=embed)
        elif not use_object_name:
            logger.info("Failed to find '{}'", name)
            embed = discord.Embed(description=f"No pets with name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
            await interaction.followup.send(embed=embed)

    async def build_list_embed(self, rows: List[tuple], name: str):
        desc_strings = []
        desc_index = 0
        desc_strings.append("")
        for row in rows:
            real_name = row[2].decode("utf-8")
            pet_name = await database.translate_name(self.bot.db, row[1])
            if len(desc_strings[desc_index]) >= 1000:
                desc_index += 1
                desc_strings.append("")
            desc_strings[desc_index] += f"{pet_name} ({real_name})\n"
        
        embeds = []
        for string in desc_strings:
            embed = discord.Embed(
                color=discord.Color.greyple(),
                description=string,
            ).set_author(name=f"Searching for: {name}", icon_url=emojis.UNIVERSAL.url)
            embeds.append(embed)

        return embeds

    @app_commands.command(name="list", description="Finds a list of pet names that contain the string")
    @app_commands.describe(name="The name of the pets to search for")
    async def list(
        self,
        interaction: discord.Interaction,
        name: str,
    ):
        await interaction.response.defer()
        if type(interaction.channel) is DMChannel or type(interaction.channel) is PartialMessageable:
            logger.info("{} requested pet list for '{}'", interaction.user.name, name)
        else:
            logger.info("{} requested pet list for '{}' in channel #{} of {}", interaction.user.name, name, interaction.channel.name, interaction.guild.name)
        
        rows = await self.fetch_pet_list(name)
        
        if rows:
            view = ItemView(await self.build_list_embed(rows, name))
            try:
                await view.start(interaction)
            except discord.errors.HTTPException:
                logger.info("List for '{}' too long, sending back error message", name)
                embed = discord.Embed(description=f"Pet list for {name} too long! Try again with a more specific keyword.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
                await interaction.followup.send(embed=embed)
        else:
            logger.info("Failed to find list for '{}'", name)
            embed = discord.Embed(description=f"No pets containing name {name} found.").set_author(name=f"Searching: {name}", icon_url=emojis.UNIVERSAL.url)
            await interaction.followup.send(embed=embed)

async def setup(bot: TheBot):
    await bot.add_cog(Pets(bot))
