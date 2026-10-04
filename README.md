# Deacon-Bot
Repository for the Pirate101 Discord bot Deacon

# Usage

Head over to the [katsuba repository](https://github.com/vbe0201/katsuba) and follow installation instructions in the README. Also do the optional steps to install Python library bindings.

Then, head over to the [arrtype repository](https://github.com/wizspoil/arrtype) and follow README instructions to dump a types JSON from the game client.

To create the database the bot uses go to https://github.com/ItzGray/piratedb and follow the instructions. Copy items.db over when it is completed.

If you want images for the bot, copy Root.wad, _Shared-WorldData.wad, Mob-WorldData.wad, Player-WorldData.wad, and the type file you just dumped (as types.json) into the root directory of the bot.

Afterwards, run `py MoveImagesToBot.py` to move and convert all necessary images into the PNG_Images folder. (Note: Running the script requires an ImageMagick installation.)

Finally, edit the .env file to have the token of your discord bot.

Run `pipenv run bot` to run the bot.

# Other notes

A huge thanks to the people behind the similar [Kimerith WindHammer](https://github.com/MajorPain1/Kimerith-WindHammer) bot for Wizard101, from which I heavily used and referenced code. Without it, this project certainly would have taken a lot longer.

I also would like to take a moment to thank various members of The Atmoplex Discord server (particularly Alphastaire and _4815162342) for helping me when I was super stuck on a couple roadblocks.