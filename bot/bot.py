import os
from datetime import datetime
from pathlib import Path

import aiosqlite
import discord
from discord.ext import commands
from loguru import logger

EXTENSIONS = Path(__file__).parent / "extensions"

FIND_ITEM_NAME_QUERY = """
SELECT locale_en.data FROM items
INNER JOIN locale_en ON locale_en.id == items.name
"""

FIND_PET_NAME_QUERY = """
SELECT locale_en.data FROM pets
INNER JOIN locale_en ON locale_en.id == pets.name
"""

FIND_POWER_NAME_QUERY = """
SELECT locale_en.data FROM powers
INNER JOIN locale_en ON locale_en.id == powers.name
"""

FIND_TALENT_NAME_QUERY = """
SELECT locale_en.data FROM talents
INNER JOIN locale_en ON locale_en.id == talents.name
"""

FIND_UNIT_NAME_QUERY = """
SELECT locale_en.data FROM units
INNER JOIN locale_en ON locale_en.id == units.name
"""

class TheBot(commands.Bot):
    def __init__(self, db_path: Path, **kwargs):
        super().__init__(**kwargs)

        self.ready_once = False
        self.db_path = db_path
        self.db = None
        self.item_list = []
        self.pet_list = []
        self.power_list = []
        self.talent_list = []
        self.unit_list = []
        self.uptime = datetime.now()

    async def on_ready(self):
        
        if self.ready_once:
            return
        self.ready_once = True
        
        # If we are not connected yet, connect to db.
        async with aiosqlite.connect(self.db_path) as db:
            self.db = await aiosqlite.connect(":memory:")
            await db.backup(self.db)

        # Put lists of things into the bot.
        async with self.db.execute(FIND_ITEM_NAME_QUERY) as cursor:
            tuple_item_list = await cursor.fetchall()

        for i in tuple_item_list:
            if i[0] not in self.item_list:
                self.item_list.append(i[0])

        async with self.db.execute(FIND_PET_NAME_QUERY) as cursor:
            tuple_pet_list = await cursor.fetchall()

        for i in tuple_pet_list:
            if i[0] not in self.pet_list:
                self.pet_list.append(i[0])
        
        async with self.db.execute(FIND_POWER_NAME_QUERY) as cursor:
            tuple_power_list = await cursor.fetchall()

        for i in tuple_power_list:
            if i[0] not in self.power_list:
                self.power_list.append(i[0])
        
        async with self.db.execute(FIND_TALENT_NAME_QUERY) as cursor:
            tuple_talent_list = await cursor.fetchall()

        for i in tuple_talent_list:
            if i[0] not in self.talent_list:
                self.talent_list.append(i[0])
        
        async with self.db.execute(FIND_UNIT_NAME_QUERY) as cursor:
            tuple_unit_list = await cursor.fetchall()

        for i in tuple_unit_list:
            if i[0] not in self.unit_list:
                self.unit_list.append(i[0])

        # Load required bot extensions.
        await self.load_extension("jishaku")
        ext_count = await self.load_extensions_from_dir(EXTENSIONS)

        await self.tree.sync()
        # Log information about the user.
        logger.info(f"Logged in as {self.user}")
        logger.info(f"Running with {ext_count} extensions")

    async def load_extensions_from_dir(self, path: Path) -> int:
        if not path.is_dir():
            return 0

        before = len(self.extensions.keys())

        extension_names = []
        current_working_directory = Path(os.getcwd())

        for subpath in path.glob("**/[!_]*.py"):  # Ignore if starts with _
            subpath = subpath.relative_to(current_working_directory)

            parts = subpath.with_suffix("").parts
            if parts[0] == ".":
                parts = parts[1:]

            extension_names.append(".".join(parts))

        for ext in extension_names:
            try:
                await self.load_extension(ext)
            except (commands.errors.ExtensionError, commands.errors.ExtensionFailed):
                logger.exception("Failed loading " + ext)

        return len(self.extensions.keys()) - before

    async def on_message(self, message: discord.Message, /):
        if message.author.bot:
            return

        ctx = await self.get_context(message)
        if ctx.command is not None:
            await self.invoke(ctx)

    async def close(self):
        await self.db.close()

    def run(self):
        super().run(os.environ["DISCORD_TOKEN"])
