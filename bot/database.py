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
    PET_POWER,
    PHYSICAL_DAMAGE,
    MAGICAL_DAMAGE,
    PRIMARY_STATS,
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
    "Pet Power",
    "Physical Damage",
    "Magical Damage",
    "Primary Stat",
]

_WEAPON_TYPES = [
    SHOOTY,
    SLASHY,
    SMASHY,
    STABBY,
    STAFFY,
]

_WEAPON_TYPES_STR = [
    "Shooty",
    "Slashy",
    "Smashy",
    "Stabby",
    "Staffy",
]

_OTHER = [
    TIMER,
    BUFF,
    DEBUFF,
    ENEMY_TERRITORY,
    TALENT_STAR,
]

_STAT_ICONS = {
    "DAMAGE_BASE_ICON": WEAPON_POWER,
    "ARMOR_ICON": ARMOR,
    "CRIT_RATING_ICON": CRIT,
    "ACCURACY_ICON": ACCURACY,
    "AGILITY_ICON": AGILITY,
    "STRENGTH_ICON": STRENGTH,
    "SPELL_POWER_ICON": SPELL_POWER,
    "DODGE_ICON": DODGE,
    "ATTACK_RANGE_ICON": ATTACK_RANGE,
    "MOVE_RANGE_ICON": MOVEMENT_RANGE,
    "CURRENT_HP_ICON": HEALTH,
    "DAMAGE_PHYSICAL_ICON": PHYSICAL_DAMAGE,
    "MAX_HP_ICON": HEALTH,
    "ICON_MOVEMENT_RANGE": MOVEMENT_RANGE,
    "WILL_ICON": WILL,
}

_IMG_ICONS = {
    "Icon_Timer_Med": TIMER,
    "Icon_Buff_Bad": DEBUFF,
    "Icon_Buff_Good": BUFF,
    "Icon_Area_Enemy_Territory_Med": ENEMY_TERRITORY,
    "Icon_Attribute_Slash_Med": SLASHY,
    "Icon_Attribute_Axe_Med": SMASHY,
    "Icon_Attribute_Kris_Med": STABBY,
    "Icon_Attribute_Pistol_Med": SHOOTY,
    "Icon_Attribute_Staff_Med": STAFFY,
    "Icon_Talent_Star_Yellow_01": TALENT_STAR,
}

_DOT_ICONS = {
    "Bleed": BLEED,
    "Poison": POISON,
    "Heal": HEALTH,
    "Curse": CURSE,
}

PVP_TAG = {
    0: "Allowed Everywhere",
    1: "No PvP",
    2: "PvP Only",
}

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
    if isinstance(data, str):
        data = data.encode()
    
    state = 0xCBF2_9CE4_8422_2325
    for b in data:
        state ^= b
        state *= 0x0000_0100_0000_01B3
        state &= 0xFFFF_FFFF_FFFF_FFFF
    return state >> 1

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
    object_name = ""
    async with db.execute(
        "SELECT * FROM powers WHERE id == ?", (id,)
    ) as cursor:
        async for row in cursor:
            name = await translate_name(db, row[1])
            object_name = row[2].decode("utf-8")
            if name == None:
                name = object_name
    return name, object_name

async def translate_unit_name(db, id: int) -> str:
    name = ""
    async with db.execute(
        "SELECT * FROM units WHERE id == ?", (id,)
    ) as cursor:
        async for row in cursor:
            name = await translate_name(db, row[1])
            object_name = row[2].decode("utf-8")
            if name == None:
                name = object_name
    return name, object_name

async def lang_lookup_by_id(db, hash: int) -> str:
    name = ""
    async with db.execute(
        "SELECT * FROM locale_en WHERE id == ?", (hash,)
    ) as cursor:
        async for row in cursor:
            name = row[1]
    return name

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

def get_weapon_type_emoji(type: str) -> str:
    weapon_types = type.split("/")
    weapon_type_string = ""
    for weapon_type in weapon_types:
        weapon_type_string += f"{_WEAPON_TYPES[_WEAPON_TYPES_STR.index(weapon_type)]}/"
    weapon_type_string = weapon_type_string[:-1]
    return weapon_type_string

async def get_ability_damage(db, ability: str):
    dmg_type = ""
    async with db.execute(
        "SELECT * FROM power_info WHERE power_info.power == ?", (ability,)
    ) as cursor:
        async for row in cursor:
            dmg_type = row[3]
    
    final_text = ""
    
    async with db.execute(
        "SELECT * FROM power_adjustments WHERE power_adjustments.power == ?", (ability,)
    ) as cursor:
        async for row in cursor:
            if row[4] == "Set" or row[4] == "Multiply Add":
                final_text += f"+ x{row[6]}{get_stat_emoji(row[5])} "
    final_text = final_text[2:-1]
    final_text = f"({final_text})"
    return final_text, dmg_type

def _make_placeholders(count: int) -> str:
    return ", ".join(["?"] * count)

def sql_chunked(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]