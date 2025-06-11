# Deacon-Bot
Repository for the Pirate101 Discord bot Deacon

# Usage

Head over to the [katsuba repository](https://github.com/vbe0201/katsuba) and follow installation instructions in the README. Also do the optional steps to install Python library bindings.

Then, head over to the [arrtype repository](https://github.com/wizspoil/arrtype) and follow README instructions to dump a types JSON from the game client.

If you want images for the bot, create a SummonedImages folder and copy Root.wad, _Shared-WorldData.wad, Mob-WorldData.wad, Player-WorldData.wad, and the type file you just dumped (as types.json) into the root directory of the bot. Afterwards, run `py MoveImagesToBot.py` to move all the necessary images into the folder.

After all images are in, run `py DDS_To_PNG.py` to convert it all to PNG_Images

To create the database the bot uses go to https://github.com/ItzGray/piratedb and follow the instructions. Copy items.db over when it is completed

Finally, edit the .env file to have the token of your discord bot

Run `pipenv run bot` to run the bot

# Other notes

A huge thanks to the people behind the similar [Kimerith WindHammer](https://github.com/MajorPain1/Kimerith-WindHammer) bot for Wizard101, from which I heavily used and referenced code. Without it, this project certainly would have taken a lot longer.