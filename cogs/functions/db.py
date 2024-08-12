import discord
import aiosqlite
import sqlite3
import yaml
from discord.ext import commands
from discord import app_commands
from typing import Literal

with open('config.yml', 'r') as file:
    data = yaml.safe_load(file)

embed_color = data["General"]["EMBED_COLOR"]

async def check_tables():
    await keywords()
    await listeners()

async def refresh_table(table: str):
    if table == "Keywords":
        await keywords(True)
    if table == "Listeners":
        await listeners(True)

async def listeners(delete: bool = False):
    async with aiosqlite.connect('database.db') as db:
        if delete:
            try:
                await db.execute('DROP TABLE listeners')
                await db.commit()
            except sqlite3.OperationalError:
                pass

        try:
            await db.execute('SELECT * FROM listeners')
        except sqlite3.OperationalError:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS listeners (
                    username STRING,
                    channel_id INTEGER,
                    posts JSON
                )
            """)
            await db.commit()

async def keywords(delete: bool = False):
    async with aiosqlite.connect('database.db') as db:
        if delete:
            try:
                await db.execute('DROP TABLE keywords')
                await db.commit()
            except sqlite3.OperationalError:
                pass

        try:
            await db.execute('SELECT * FROM keywords')
        except sqlite3.OperationalError:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS keywords (
                    channel_id INTEGER,
                    keyword STRING
                )
            """)
            await db.commit()

class SQLiteCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="refreshtable", description="Refreshes an SQLite table!")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(table="What table should be refreshed?")
    async def refreshtable(self, interaction: discord.Interaction, table: Literal["Keywords", "Listeners"]) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        if await self.bot.is_owner(interaction.user):
            await refresh_table(table)
            embed = discord.Embed(description=f"Successfully refreshed the table **{table}**!", color=discord.Color.from_str(embed_color))
        else:
            embed = discord.Embed("You do not have permission to use this command!", color=discord.Color.red())
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SQLiteCog(bot))