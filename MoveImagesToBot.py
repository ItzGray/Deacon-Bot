from pathlib import Path
from katsuba.wad import Archive # type: ignore

def move_images_to_bot():
    output_path = Path("SummonedImages")
    mob_worlddata = Archive.mmap("Mob-WorldData.wad")
    player_worlddata = Archive.mmap("Player-WorldData.wad")
    for file in mob_worlddata.iter_glob("Character/*.jpf"):
        data = mob_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in mob_worlddata.iter_glob("Character/*.dds"):
        data = mob_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in player_worlddata.iter_glob("Character/Player/Icons/**/*.dds"):
        data = player_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    for file in player_worlddata.iter_glob("Character/Player/Icons/**/*.jpf"):
        data = player_worlddata[file]
        filename = file.split("/")[-1]
        output_file_path = output_path / filename
        with open(output_file_path, "wb") as output_file:
            output_file.write(data)
    print("Done!")

if __name__ == "__main__":
    move_images_to_bot()