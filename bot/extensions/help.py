from typing import List, Optional, Literal
from fuzzywuzzy import process, fuzz
from operator import itemgetter

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from .. import TheBot

HELP_DESCRIPTION = """
**/help**: Displays this message\n
**/item find**: Finds the item's ingame stats. Parameters: Name, Class, Kind, Level\n
**/item list**: Finds a list of items containing a given string. Parameters: Name, Class, Kind, Level\n
**/unit find**: Finds the unit's ingame stats. Parameters: Name, Class, Kind\n
**/unit list**: Finds a list of units containing a given string. Parameters: Name, Class, Kind\n
**/pet find**: Finds the pet as shown in the files. Parameters: Name\n
**/pet list**: Finds a list of pets containing a given string. Parameters: Name\n
**/talent find**: Finds the talent as shown in the files. Parameters: Name, Ranks\n
**/talent list**: Finds a list of talents containing a given string. Parameters: Name, Ranks\n
**/power find**: Finds the power as shown in the files. Parameters: Name\n
**/power list**: Finds a list of powers containing a given string. Parameters: Name\n
"""

class Help(commands.Cog):
    def __init__(self, bot: TheBot):
        self.bot = bot

    @app_commands.command(name="help", description="Provides a list of commands Deacon can do")
    async def find(
        self, 
        interaction: discord.Interaction, 
    ):
        embed = discord.Embed(
            title=f"Deacon's commands",
            color=discord.Color.greyple(),
            description=HELP_DESCRIPTION,
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot: TheBot):
    await bot.add_cog(Help(bot))
