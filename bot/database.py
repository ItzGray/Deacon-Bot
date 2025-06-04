from enum import IntFlag, Enum
from struct import unpack
from typing import Tuple, List
from dataclasses import dataclass
from loguru import logger
import math

import discord

from .emojis import *
from .__main__ import ROOT_DIR, ITEMS_DB



_SCHOOL_COLORS = [
    discord.Color.greyple(), # Universal
    discord.Color.greyple(), # Universal
    discord.Color.red(), # Buccaneer
    discord.Color.blue(), # Privateer
    discord.Color.green(), # Witchdoctor
    discord.Color.orange(), # Musketeer
    discord.Color.purple(), # Swashbuckler
]

_PET_LEVELS = ["Baby", "Teen", "Adult", "Ancient", "Epic", "Mega", "Ultra"]

_SCHOOLS = [
    UNIVERSAL,
    UNIVERSAL,
    BUCCANEER,
    PRIVATEER,
    WITCHDOCTOR,
    MUSKETEER,
    SWASHBUCKLER,
]

_ITEMS = [
    HAT,
    OUTFIT,
    BOOTS,
    WEAPON,
    ACCESSORY,
    TOTEM,
    CHARM,
    RING,
    MOUNT,
]

_ITEMS_STR = [
    "Hat",
    "Outfit",
    "Boots",
    "Weapon",
    "Accessory",
    "Totem",
    "Charm",
    "Ring",
    "Mount",
]

_SCHOOLS_STR = [
    "Buccaneer",
    "Privateer",
    "Witchdoctor",
    "Musketeer",
    "Swashbuckler",
]


class StatFlags(IntFlag):
    Strength = 1 << 0
    Agility = 1 << 1
    Will = 1 << 2


class ItemFlags(IntFlag):
    NoTrade = 1 << 0
    NoSell = 1 << 1
    NoTrash = 1 << 2
    NoAuction = 1 << 3
    NoStitch = 1 << 4


@dataclass
class StatObject:
    order: int
    value: int
    string: str

    def to_string(self) -> str:
        if self.string.startswith(("Allows", "Invul", "Gives", "Maycasts", "-")):
            return self.string
        elif self.value > 0:
            return f"+{self.value}{self.string}"
        else:
            return f"{self.value}{self.string}"


def translate_flags(flag: int) -> List[str]:
    flags = []
    if flag & ItemFlags.NoTrade:
        flags.append("No Trade")
    if flag & ItemFlags.NoSell:
        flags.append("No Sell")
    if flag & ItemFlags.NoTrash:
        flags.append("No Trash")
    if flag & ItemFlags.NoAuction:
        flags.append("No Auction")
    if flag & ItemFlags.NoStitch:
        flags.append("No Stitch")

    return flags

def translate_stat_flags(flag: int) -> List[str]:
    flags = []
    if flag & StatFlags.Strength:
        flags.append("Strength")
    if flag & StatFlags.Agility:
        flags.append("Agility")
    if flag & StatFlags.Will:
        flags.append("Will")

    return flags

def _fnv_1a(data: bytes) -> int:
    state = 0xCBF2_9CE4_8422_2325
    for b in data:
        state ^= b
        state *= 0x0000_0100_0000_01B3
        state &= 0xFFFF_FFFF_FFFF_FFFF
    return state >> 1


_STAT_DISPLAY_TABLE = {
    # Maybe do things with this later
}


_STAT_ORDER_TABLE = [
    # Maybe do things with this later
]

def translate_stat(stat: int) -> Tuple[int, str, bool]:
    try:
        display_stat = _STAT_DISPLAY_TABLE[stat]
        order_number = _STAT_ORDER_TABLE.index(stat)
    except KeyError:
        display_stat = " Unknown Stat"
        order_number = 2000000
    
    return order_number, display_stat


def unpack_stat_value(value: int) -> float:
    raw = value.to_bytes(4, "little")
    return unpack("<f", raw)[0]

def unpack_int_list(value: int) -> List[int]:
    raw = value.to_bytes(88, "little")
    return unpack("<22i", raw)


def translate_school(school: int) -> discord.PartialEmoji:
    return _SCHOOLS[school]


def translate_equip_school(school: int) -> str:
    school_emoji = _SCHOOLS[school & 0x7FFF_FFFF]
    if school & (1 << 31) != 0:
        return f"All schools except {school_emoji}"
    elif school == 0:
        return f"{school_emoji}"
    else:
        return f"{school_emoji} only"


def make_school_color(school: int) -> discord.Color:
    return _SCHOOL_COLORS[school & 0x7FFF_FFFF]


def translate_pet_level(level: int) -> str:
    return _PET_LEVELS[level - 1]


_TYPE_EMOJIS = {
    "Accuracy_image": ACCURACY,
    "CriticalRating_image": CRIT,
    "Charm_image": CHARM,
    "Dodge_image": DODGE,
}

def translate_type_emoji(icon_name: str) -> PartialEmoji:
    try:
        return _TYPE_EMOJIS[icon_name]
    except KeyError:
        return _TYPE_EMOJIS["Random_image"]
    
async def translate_name(db, id: int) -> str:
    name = ""
    async with db.execute(
        "SELECT * FROM locale_en WHERE id == ?", (id,)
    ) as cursor:
        async for row in cursor:
            name = row[1]
    
    return name

async def translate_talent_name(db, id: int) -> str:
    name = ""
    async with db.execute(
        "SELECT * FROM talents WHERE id == ?", (id,)
    ) as cursor:
        async for row in cursor:
            name = await translate_name(db, row[1])
            object_name = row[2].decode("utf-8")
            if name == None:
                name = object_name
    return name, object_name

async def translate_power_name(db, id: int) -> str:
    name = ""
    async with db.execute(
        "SELECT * FROM powers WHERE id == ?", (id,)
    ) as cursor:
        async for row in cursor:
            name = await translate_name(db, row[1])
            object_name = row[2].decode("utf-8")
            if name == None:
                name = object_name
    return name, object_name

async def fetch_raw_item_stats(db, item: int) -> List[StatObject]:
    stats = []

    async with db.execute(
        "SELECT * FROM item_stats WHERE item == ?", (item,)
    ) as cursor:
        async for row in cursor:
            a = row[3]
            b = row[4]

            match row[2]:
                # Regular stat
                case "Stat":
                    order, stat = translate_stat(a)
                    stats.append(StatObject(order, b, stat))

    return stats

def getStatIndexFromList(statlist: List[StatObject], statorder: int) -> int:
    for i, stat in enumerate(statlist):
        if stat.order == statorder:
            return i

    return -1

async def sum_stats(db, existing_stats: List[StatObject], equipped_items: List[int]):
    existing_stats_dict = {stat.order: stat for stat in existing_stats}

    for item_id in equipped_items:
        for stat in await fetch_raw_item_stats(db, item_id):
            existing_stat = existing_stats_dict.get(stat.order)
            
            if existing_stat is not None:
                index = getStatIndexFromList(existing_stats, existing_stat.order)
                existing_stats[index].value = stat.value + existing_stat.value
            else:
                existing_stats.append(stat)
                existing_stats_dict[stat.order] = stat


def _make_placeholders(count: int) -> str:
    return ", ".join(["?"] * count)

def sql_chunked(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]