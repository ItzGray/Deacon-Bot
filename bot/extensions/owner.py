import discord
from discord import app_commands, PartialMessageable, DMChannel
from discord.ext import commands
from loguru import logger

from .. import TheBot

class Owner(commands.Cog):
    def __init__(self, bot: TheBot):
        self.bot = bot

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync(
        self,
        ctx
    ):
        await self.bot.tree.sync()
        logger.info("Command tree synced.")
        await ctx.send("Command tree synced.")
    
    @commands.command(name="reload")
    @commands.is_owner()
    async def reload(
        self,
        ctx,
        extension: str
    ):
        try:
            await self.bot.reload_extension(f"bot.extensions.{extension}")
            await self.bot.tree.sync()
            logger.info(f"Extension {extension} reloaded.")
            await ctx.send(f"Extension {extension} reloaded.")
        except Exception as e:
            logger.info(f"Failed to reload extension {extension}: {e}")
            await ctx.send(f"Failed to reload extension {extension}: {e}")

    @commands.command(name="load")
    @commands.is_owner()
    async def load(
        self,
        ctx,
        extension: str
    ):
        try:
            await self.bot.load_extension(f"bot.extensions.{extension}")
            await self.bot.tree.sync()
            logger.info(f"Extension {extension} loaded.")
            await ctx.send(f"Extension {extension} loaded.")
        except Exception as e:
            logger.info(f"Failed to load extension {extension}: {e}")
            await ctx.send(f"Failed to load extension {extension}: {e}")

async def setup(bot: TheBot):
    await bot.add_cog(Owner(bot))