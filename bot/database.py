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
    discord.Color.red(), # Buccaneer
    discord.Color.yellow(), # Privateer
    discord.Color.green(), # Witchdoctor
    discord.Color.orange(), # Musketeer
    discord.Color.purple(), # Swashbuckler
]

_SCHOOLS = [
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
]

_SCHOOLS_STR = [
    None, # Universal
    "Buccaneer",
    "Privateer",
    "Witchdoctor",
    "Musketeer",
    "Swashbuckler",
]

_STATS = [
    HEALTH,
    ENERGY,
    WEAPON_POWER,
    SPELL_POWER,
    ARMOR,
    MAGIC_RESIST,
    ACCURACY,
    CRIT,
    DODGE,
    STRENGTH,
    AGILITY,
    WILL,
    ARMOR_PENETRATION,
    ATTACK_RANGE,
    MOVEMENT_RANGE,
    GRIT,
    GUILE,
    GUTS,
    PET_POWER,
]

_STATS_STR = [
    "Max Health",
    "Max Energy",
    "Weapon Power",
    "Spell Power",
    "Armor",
    "Magic Resist",
    "Accuracy",
    "Crit Rating",
    "Dodge",
    "Strength",
    "Agility",
    "Will",
    "Armor Penetration",
    "Attack Range",
    "Movement Range",
    "Grit",
    "Guile",
    "Guts",
    "Power",
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


def make_school_color(school: str) -> discord.Color:
    return _SCHOOL_COLORS[_SCHOOLS_STR.index(school)]


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

async def fetch_curve(db, curve):
    stats = []
    types = []
    levels = []
    values = []
    async with db.execute(
        "SELECT * FROM curve_points WHERE curve_points.curve == ?", (curve,)
    ) as cursor:
        async for row in cursor:
            stats.append(row[2])
            types.append(row[3])
            levels.append(row[4])
            values.append(row[5])
    
    return stats, types, levels, values

def get_item_icon_url(item_type: str) -> str:
    try:
        logger.info(_ITEMS_STR.index(item_type))
        return _ITEMS[_ITEMS_STR.index(item_type)].url
    except:
        return ""

def get_school_icon_url(school: str) -> str:
    try:
        return _SCHOOLS[_SCHOOLS_STR.index(school)].url
    except:
        return ""

def get_item_emoji(item_type: str):
    return _ITEMS[_ITEMS_STR.index(item_type)]
    
def get_school_emoji(school: str):
    return _SCHOOLS[_SCHOOLS_STR.index(school)]
    
def get_stat_emoji(stat: str):
    try:
        return _STATS[_STATS_STR.index(stat)]
    except:
        return ""

def _make_placeholders(count: int) -> str:
    return ", ".join(["?"] * count)

def sql_chunked(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]