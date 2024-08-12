import discord
import aiosqlite
import asyncio
import yaml
from discord import app_commands
from discord.ext import commands
from typing import Optional

with open('config.yml', 'r') as file:
    data = yaml.safe_load(file)

embed_color = data["General"]["EMBED_COLOR"]

class UnlistenCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="unlisten", description="Removes a Instagram listener.")
    @app_commands.describe(username="What Instagram account should the bot no longer listen to?")
    async def unlisten(self, interaction: discord.Interaction, username: Optional[str]) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        async with aiosqlite.connect('database.db') as db:
            if username:
                cursor = await db.execute('SELECT * FROM listeners WHERE username=?', (username,))
                username_in_db = await cursor.fetchone()

                if not username_in_db:
                    embed = discord.Embed(title="Listener", description=f"**{username}** is not in the database.", color=discord.Color.red())
                    await interaction.followup.send(embed=embed)
                    return

                channel = self.bot.get_channel(username_in_db[1])
                
                await db.execute('DELETE FROM listeners WHERE username=?', (username, ))
                await db.commit()
            else:
                cursor = await db.execute('SELECT * FROM listeners WHERE channel_id=?', (interaction.channel.id,))
                channel_id_db = await cursor.fetchone()

                if not channel_id_db:
                    embed = discord.Embed(title="Listener", description=f"**{interaction.channel.mention}** is not in the database.", color=discord.Color.red())
                    await interaction.followup.send(embed=embed)
                    return

                username = channel_id_db[0]
                channel = self.bot.get_channel(channel_id_db[1])

                await db.execute('DELETE FROM listeners WHERE channel_id=?', (interaction.channel.id, ))
                await db.commit()

            embed = discord.Embed(title="Listener", description=f"**{username}** is no longer being listened to for new tweets.", color=discord.Color.red())
            if channel:
                embed.set_footer(text="Channel deleting in 5 seconds.")
            await interaction.followup.send(embed=embed)

            if channel:
                await asyncio.sleep(5)
                await channel.delete()

async def setup(bot):
    await bot.add_cog(UnlistenCog(bot))