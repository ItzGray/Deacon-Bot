import time
import aiosqlite
import os
import asyncio
from pathlib import Path
from wand.image import Image
from katsuba.wad import Archive # type: ignore
from katsuba.op import * # type: ignore

class BinDeserializer:
    def __init__(self, types_path: Path):
        opts = SerializerOptions()
        opts.flags = 1
        opts.shallow = False
        opts.skip_unknown_types = True
        opts.djb2_only = True
        
        self.types = TypeList.open(types_path)

        self.ser = Serializer(opts, self.types)

    def deserialize(self, data):
        return self.ser.deserialize(data)
    
    def deserialize_from_path(self, path: str, archive: Archive):
        try:
            to_return = archive.deserialize(path, self.ser)
        except:
            to_return = None
        return to_return

async def move_images_to_bot():
    start = time.time()
    output_dir = Path.cwd() / "PNG_Images"
    output_dir.mkdir(parents=True, exist_ok=True)
    mob_worlddata = Archive.mmap("Mob-WorldData.wad")
    player_worlddata = Archive.mmap("Player-WorldData.wad")
    root = Archive.mmap("Root.wad")
    shared_worlddata = Archive.mmap("_Shared-WorldData.wad")
    de = BinDeserializer("types.json")
    async with aiosqlite.connect("items.db") as temp_db:
        db = await aiosqlite.connect(":memory:")
        await temp_db.backup(db)
    async with db.execute(
        "SELECT * FROM vdfs"
    ) as cursor:
        async for row in cursor:
            if row[2] == "":
                continue
            print(f"Processing: {row[2]}")
            full_path = row[2]
            if full_path.startswith("|_Shared|WorldData|"):
                wad = shared_worlddata
            elif full_path.startswith("|Mob|WorldData|"):
                wad = mob_worlddata
            elif full_path.startswith("|Player|WorldData|"):
                wad = player_worlddata
            path = full_path.split("|")[-1]
            try:
                path = path.split("?")[0]
            except:
                pass
            try:
                data = wad[path]
            except:
                data = root[path]
            if row[1] == "Image":
                if path.split(".")[-1] == "tex":
                    deserialized_data = de.deserialize(data[4:])
                    real_image_path = deserialized_data["m_baseTexture"].decode("utf-8")
                    if real_image_path.startswith("|_Shared|WorldData|"):
                        wad = shared_worlddata
                    elif real_image_path.startswith("|Mob|WorldData|"):
                        wad = mob_worlddata
                    elif real_image_path.startswith("|Player|WorldData|"):
                        wad = player_worlddata
                    path = real_image_path.split("|")[-1]
                    try:
                        real_image_data = wad[path]
                    except:
                        try:
                            real_image_data = root[path]
                        except:
                            print("No real image path!")
                            continue
                    data = real_image_data
                output_path = output_dir / f"{path.split("/")[-1].split(".")[0]}.png"
                with Image(blob=data) as img:
                    try:
                        img.save(filename=output_path)
                    except:
                        print(f"Failed to save {output_path}!")
            elif row[1] == "VDF":
                final_path = path
                deserialized_data = de.deserialize(data[4:])
                behaviors = deserialized_data["m_behaviors"]
                draw_behavior = None
                for behavior in behaviors:
                    if behavior["m_behaviorName"] == b"DrawBehavior":
                        draw_behavior = behavior
                        break
                if draw_behavior != None:
                    try:
                        image = draw_behavior["m_icons"][0].decode("utf-8")
                    except:
                        try:
                            image = row[3]
                        except:
                            print("No image path!")
                            continue
                    image_split = image.split("/")[-1]
                    try:
                        image_split = image_split.split("?")[0]
                    except:
                        pass
                    if image.startswith("|_Shared|WorldData|"):
                        wad = shared_worlddata
                    elif image.startswith("|Mob|WorldData|"):
                        wad = mob_worlddata
                    elif image.startswith("|Player|WorldData|"):
                        wad = player_worlddata
                    path = image.split("|")[-1].split("?")[0]
                    try:
                        data = wad[path]
                    except:
                        try:
                            data = root[path]
                        except:
                            print("No image path!")
                            continue
                    if image_split.split(".")[-1] == "tex":
                        deserialized_data = de.deserialize(data[4:])
                        real_image_path = deserialized_data["m_baseTexture"].decode("utf-8")
                        if real_image_path.startswith("|_Shared|WorldData|"):
                            wad = shared_worlddata
                        elif real_image_path.startswith("|Mob|WorldData|"):
                            wad = mob_worlddata
                        elif real_image_path.startswith("|Player|WorldData|"):
                            wad = player_worlddata
                        path = real_image_path.split("|")[-1]
                        try:
                            real_image_data = wad[path]
                        except:
                            try:
                                real_image_data = root[path]
                            except:
                                print("No real image path!")
                                continue
                    else:
                        real_image_data = data
                    output_path = output_dir / f"{final_path.split("/")[-1].split(".")[0]}.png"
                    with Image(blob=real_image_data) as img:
                        try:
                            img.save(filename=output_path)
                        except:
                            print(f"Failed to save {output_path}!")
    await db.close()
    print(f"Done! Wrote all files in {round(time.time() - start, 2)} seconds.")
    return

if __name__ == "__main__":
    asyncio.run(move_images_to_bot())