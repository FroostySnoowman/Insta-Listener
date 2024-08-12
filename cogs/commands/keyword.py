import discord
import aiosqlite
import yaml
from discord import app_commands
from discord.ext import commands

with open('config.yml', 'r') as file:
    data = yaml.safe_load(file)

embed_color = data["General"]["EMBED_COLOR"]
keyword_categories = data["Keyword_Categories"]

class KeywordCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="keyword", description="Adds a keyword listener.")
    @app_commands.describe(keyword="What keywords should be listened for?")
    async def keyword(self, interaction: discord.Interaction, keyword: str) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        async with aiosqlite.connect('database.db') as db:
            full_categories = 0
            not_full = None

            for category in keyword_categories:
                channel = self.bot.get_channel(category)
                if channel:
                    if len(channel.channels) == 50:
                        full_categories += 1
                    else:
                        not_full = channel
                        break
            
            if full_categories == len(keyword_categories):
                embed = discord.Embed(title="Listener", description=f"All keyword categories are full, please contact an admin.", color=discord.Color.red())
                await interaction.followup.send(embed=embed)
                return

            channel = await not_full.create_text_channel(name=f"{keyword}")

            await db.execute('INSERT INTO keywords VALUES (?,?);', (channel.id, keyword))
            await db.commit()

            embed = discord.Embed(title="Listener", description=f"Successfully added the keyword listener for **{keyword}**.", color=discord.Color.from_str(embed_color))
            await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(KeywordCog(bot))