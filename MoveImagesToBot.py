from pathlib import Path
from katsuba.wad import Archive # type: ignore

def move_images_to_bot():
    output_path = Path("SummonedImages")
    mob_worlddata = Archive.mmap("Mob-WorldData.wad")
    player_worlddata = Archive.mmap("Player-WorldData.wad")
    root = Archive.mmap("Root.wad")
    shared_worlddata = Archive.mmap("_Shared-WorldData.wad")
    for file in mob_worlddata.iter_glob("Character/**/Portraits/*.jpf"):
        data = mob_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Mob-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in mob_worlddata.iter_glob("Character/**/Portrait/*.jpf"):
        data = mob_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Mob-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in mob_worlddata.iter_glob("Character/**/Portraits/*.dds"):
        data = mob_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Mob-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in player_worlddata.iter_glob("Character/Player/Icons/**/*.dds"):
        data = player_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Player-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in player_worlddata.iter_glob("Character/Player/Icons/**/*.jpf"):
        data = player_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Player-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in root.iter_glob("GUI/Powers/*.dds"):
        data = player_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Root.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in root.iter_glob("GUI/Talents/*.dds"):
        data = player_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from Root.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in shared_worlddata.iter_glob("GUI/Powers/*.dds"):
        data = player_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from _Shared-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in shared_worlddata.iter_glob("GUI/Powers/*.jpf"):
        data = player_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from _Shared-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in shared_worlddata.iter_glob("GUI/Doubloons/*.dds"):
        data = player_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        print(f"Extracting {filename} from _Shared-WorldData.wad")
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    print("Done!")

if __name__ == "__main__":
    move_images_to_bot()