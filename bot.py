
import os
import json
import discord
from discord.ext import commands
from discord import app_commands

# ==========================================
# CONFIGURATION
# ==========================================

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

DATA_FILE = "emoji_marks.json"

# Optional: Set this environment variable for instant
# command syncing in your server during testing.
GUILD_ID = os.getenv("DISCORD_GUILD_ID")


# ==========================================
# INTENTS
# ==========================================

intents = discord.Intents.default()
intents.message_content = True


# ==========================================
# DATA STORAGE
# ==========================================

def load_marks():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as error:
            print(f"Failed to load marks: {error}")

    return {}


def save_marks():
    temp_file = DATA_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(marks, f, indent=4)

    os.replace(temp_file, DATA_FILE)


marks = load_marks()


# ==========================================
# BOT CLASS
# ==========================================

class EmojiMarkBot(commands.Bot):

    async def setup_hook(self):

        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))

            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)

            print(f"Synced {len(synced)} commands to server.")

        else:
            synced = await self.tree.sync()

            print(f"Synced {len(synced)} global commands.")

        print("Slash commands are ready!")


bot = EmojiMarkBot(
    command_prefix="!",
    intents=intents
)


# ==========================================
# BOT READY
# ==========================================

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")
    print(f"Loaded {len(marks)} emoji marks.")
    print("Emoji Mark system is running!")


# ==========================================
# /EMOJIMARK
# ==========================================

@bot.tree.command(
    name="emojimark",
    description="Automatically react to a user's messages."
)
@app_commands.describe(
    user="Choose the user to mark.",
    emoji="Choose the emoji to react with."
)
async def emojimark(
    interaction: discord.Interaction,
    user: discord.Member,
    emoji: str
):

    await interaction.response.defer(ephemeral=True)

    if not interaction.guild:
        await interaction.followup.send(
            "This command only works in servers."
        )
        return

    emoji = emoji.strip()

    if not emoji:
        await interaction.followup.send(
            "Please provide an emoji."
        )
        return

    key = f"{interaction.guild.id}:{user.id}"

    marks[key] = {
        "emoji": emoji,
        "user": user.id,
        "guild": interaction.guild.id
    }

    try:
        save_marks()
    except OSError as error:
        print(f"Failed to save marks: {error}")

        await interaction.followup.send(
            "Failed to save the emoji mark. Please try again."
        )
        return

    await interaction.followup.send(
        f"Successfully marked {user.mention} with {emoji}!\n"
        "I'll automatically react to their messages."
    )

    print(
        f"{interaction.user} marked {user} with {emoji}"
    )


# ==========================================
# /UNEMOJIMARK
# ==========================================

@bot.tree.command(
    name="unemojimark",
    description="Remove automatic reactions from a user."
)
@app_commands.describe(
    user="Choose the user to unmark."
)
async def unemojimark(
    interaction: discord.Interaction,
    user: discord.Member
):

    await interaction.response.defer(ephemeral=True)

    if not interaction.guild:
        await interaction.followup.send(
            "This command only works in servers."
        )
        return

    key = f"{interaction.guild.id}:{user.id}"

    if key not in marks:
        await interaction.followup.send(
            f"{user.mention} isn't marked."
        )
        return

    del marks[key]

    try:
        save_marks()
    except OSError as error:
        print(f"Failed to save marks: {error}")

        await interaction.followup.send(
            "Failed to save changes. Please try again."
        )
        return

    await interaction.followup.send(
        f"Successfully unmarked {user.mention}!"
    )

    print(f"{interaction.user} unmarked {user}")


# ==========================================
# AUTOMATIC REACTIONS
# ==========================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.guild is None:
        return

    key = f"{message.guild.id}:{message.author.id}"

    if key in marks:

        emoji = marks[key]["emoji"]

        try:
            await message.add_reaction(emoji)

            print(
                f"Reacted to {message.author}'s message with {emoji}"
            )

        except discord.Forbidden:
            print(
                f"Missing permission to react in {message.channel}"
            )

        except discord.HTTPException as error:
            print(f"Reaction failed: {error}")

    await bot.process_commands(message)


# ==========================================
# ERROR HANDLING
# ==========================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    print(f"Command error: {error}")

    message = f"Something went wrong: {error}"

    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                message,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                message,
                ephemeral=True
            )

    except discord.HTTPException:
        pass


# ==========================================
# START BOT
# ==========================================

if __name__ == "__main__":

    if not TOKEN:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN is missing from environment variables!"
        )

    bot.run(TOKEN)
