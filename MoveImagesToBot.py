import time
from pathlib import Path
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

def move_images_to_bot():
    start = time.time()
    output_path = Path("SummonedImages")
    mob_worlddata = Archive.mmap("Mob-WorldData.wad")
    player_worlddata = Archive.mmap("Player-WorldData.wad")
    root = Archive.mmap("Root.wad")
    shared_worlddata = Archive.mmap("_Shared-WorldData.wad")
    de = BinDeserializer("types.json")
    tex_files_done = []
    mount_files_done = []
    for file in mob_worlddata.iter_glob("Character/**/*.tex"):
        filename = file.split("/")[-1].split(".")[0]
        print(f"Extracting {filename} from Mob-WorldData.wad")
        tex = de.deserialize_from_path(file, mob_worlddata)
        try:
            portrait_file = tex["m_baseTexture"].decode("utf-8").split("|")[-1]
            data = mob_worlddata[portrait_file]
        except:
            continue
        tex_files_done.append(portrait_file)
        portrait_filename = portrait_file.split("/")[-1]
        file_ext = portrait_file.split(".")[-1]
        output_file_path = output_path / (filename + "." + file_ext)
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in mob_worlddata.iter_glob("Character/**/*.jpf"):
        if file in tex_files_done:
            continue
        data = mob_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Mob-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in mob_worlddata.iter_glob("Character/**/*.dds"):
        if file in tex_files_done:
            continue
        data = mob_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Mob-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in mob_worlddata.iter_glob("MountPortraits/*.tex"):
        filename = file.split("/")[-1].split(".")[0]
        print(f"Extracting {filename} from Mob-WorldData.wad")
        tex = de.deserialize_from_path(file, mob_worlddata)
        try:
            portrait_file = tex["m_baseTexture"].decode("utf-8").split("|")[-1]
            data = mob_worlddata[portrait_file]
        except:
            continue
        tex_files_done.append(portrait_file)
        portrait_filename = portrait_file.split("/")[-1]
        file_ext = portrait_file.split(".")[-1]
        output_file_path = output_path / (filename + "." + file_ext)
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in mob_worlddata.iter_glob("MountPortraits/*.jpf"):
        if file in tex_files_done:
            continue
        data = mob_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Mob-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in mob_worlddata.iter_glob("MountPortraits/*.dds"):
        if file in tex_files_done:
            continue
        data = mob_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Mob-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in mob_worlddata.iter_glob("StateObjects/FX/**/*.dds"):
        if file in tex_files_done:
            continue
        data = mob_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Mob-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in player_worlddata.iter_glob("Character/Player/Icons/**/*.tex"):
        filename = file.split("/")[-1].split(".")[0]
        print(f"Extracting {filename} from Player-WorldData.wad")
        tex = de.deserialize_from_path(file, player_worlddata)
        try:
            portrait_file = tex["m_baseTexture"].decode("utf-8").split("|")[-1]
            data = player_worlddata[portrait_file]
        except:
            continue
        tex_files_done.append(portrait_file)
        portrait_filename = portrait_file.split("/")[-1]
        file_ext = portrait_file.split(".")[-1]
        output_file_path = output_path / (filename + "." + file_ext)
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in player_worlddata.iter_glob("Character/Player/Icons/**/*.dds"):
        if file in tex_files_done:
            continue
        data = player_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Player-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in player_worlddata.iter_glob("Character/Player/Icons/**/*.jpf"):
        if file in tex_files_done:
            continue
        data = player_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Player-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in player_worlddata.iter_glob("Character/Mounts/**/*.jpf"):
        if file in tex_files_done:
            continue
        data = player_worlddata[file]
        filename = file.split("/")[-1]
        if filename in mount_files_done:
            continue
        mount_files_done.append(filename)
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Player-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in root.iter_glob("GUI/Powers/*.dds"):
        data = root[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Root.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in root.iter_glob("GUI/Talents/*.dds"):
        data = root[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Root.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in root.iter_glob("GUI/Powers/*.dds"):
        data = root[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Root.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in root.iter_glob("GUI/Icons/*.dds"):
        data = root[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Root.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in root.iter_glob("Character/Player/Icons/**/*.dds"):
        data = root[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Root.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in root.iter_glob("Character/Player/Icons/**/*.jpf"):
        data = root[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Root.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in shared_worlddata.iter_glob("GUI/Powers/*.dds"):
        data = shared_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from _Shared-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in shared_worlddata.iter_glob("GUI/Powers/*.jpf"):
        data = shared_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from _Shared-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in shared_worlddata.iter_glob("GUI/Doubloons/*.dds"):
        data = shared_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from _Shared-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    print(f"Done! Wrote all files in {round(time.time() - start, 2)} seconds.")

if __name__ == "__main__":
    move_images_to_bot()