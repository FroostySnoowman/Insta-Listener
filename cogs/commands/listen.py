import discord
import instaloader
import aiosqlite
import yaml
import json
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime

with open('config.yml', 'r') as file:
    data = yaml.safe_load(file)

guild_id = data["General"]["GUILD_ID"]
embed_color = data["General"]["EMBED_COLOR"]
ping_role_id = data["Roles"]["PING_ROLE_ID"]
listening_categories = data["Listening_Categories"]
instagram_username = data["Instagram"]["USERNAME"]
instagram_password = data["Instagram"]["PASSWORD"]

class ListenCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def cog_load(self):
        self.listenerLoop.start()

    @tasks.loop(minutes=5)
    async def listenerLoop(self):
        async with aiosqlite.connect('database.db') as db:
            guild = self.bot.get_guild(guild_id)
            ping_role = guild.get_role(ping_role_id)

            cursor = await db.execute('SELECT * FROM listeners')
            listeners = await cursor.fetchall()

            L = instaloader.Instaloader()
            L.login(instagram_username, instagram_password)

            for listener in listeners:
                username = listener[0]
                channel_id = listener[1]
                posts = listener[2]

                profile = instaloader.Profile.from_username(L.context, username)
                profile_image_url = profile.profile_pic_url
                channel = self.bot.get_channel(channel_id)
                posts_list = json.loads(posts)

                if not channel:
                    await db.execute('DELETE FROM listeners WHERE username=?', (username,))
                    await db.commit()
                    continue

                posts = []

                posts.extend(profile.get_posts())
                posts.extend(profile.get_igtv_posts())

                if posts:
                    most_recent_post = None
                    most_recent_post_date = None

                    for post in posts:
                        if most_recent_post_date is None or post.date > most_recent_post_date:
                            most_recent_post = post
                            most_recent_post_date = post.date

                    if most_recent_post:
                        post_url = f"https://www.instagram.com/p/{most_recent_post.shortcode}/"
                        post_description = most_recent_post.caption or "No description provided."

                        if post_url in posts_list:
                            continue
                    
                        cursor = await db.execute('SELECT * FROM keywords')
                        keywords = await cursor.fetchall()

                        for keyword in keywords:
                            if keyword[1] in post_description:
                                keyword_channel = self.bot.get_channel(keyword[0])
                                if not keyword_channel:
                                    await db.execute('DELETE FROM keywords WHERE keyword=?', (keyword[1],))
                                    await db.commit()
                                    continue

                                embed = discord.Embed(title="Listener", description=f"""
[New Keyword Post By **{username}**]({post_url})

{post_description}
""", color=discord.Color.from_str(embed_color))
                                embed.set_author(name=username, icon_url=profile_image_url)
                                embed.timestamp = datetime.now()
                                await keyword_channel.send(content=ping_role.mention, embed=embed)

                        posts_list.append(post_url)

                        updated_posts = json.dumps(posts_list)

                        await db.execute('UPDATE listeners SET posts=? WHERE username=?', (updated_posts, username))
                        await db.commit()

                        embed = discord.Embed(title="Listener", description=f"""
[New Post By **{username}**]({post_url})

{post_description}
""", color=discord.Color.from_str(embed_color))
                        embed.set_author(name=username, icon_url=profile_image_url)
                        embed.timestamp = datetime.now()

                        await channel.send(content=ping_role.mention, embed=embed)

    @listenerLoop.before_loop
    async def before_my_task(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="listen", description="Sets up a Instagram listener.")
    @app_commands.describe(username="What Instagram account should the bot listen to?")
    async def listen(self, interaction: discord.Interaction, username: str) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        async with aiosqlite.connect('database.db') as db:

            full_categories = 0
            not_full = None

            for category in listening_categories:
                channel = self.bot.get_channel(category)
                if channel:
                    if len(channel.channels) == 50:
                        full_categories += 1
                    else:
                        not_full = channel
                        break
            
            if full_categories == len(listening_categories):
                embed = discord.Embed(title="Listener", description=f"All listening categories are full, please contact an admin.", color=discord.Color.red())
                await interaction.followup.send(embed=embed)
                return

            cursor = await db.execute('SELECT * FROM listeners WHERE username=?', (username,))
            username_in_db = await cursor.fetchone()

            if username_in_db is not None:
                embed = discord.Embed(title="Listener", description=f"**{username}** is already in the database.", color=discord.Color.red())
                await interaction.followup.send(embed=embed)
                return
            
            L = instaloader.Instaloader()
            
            try:
                profile = instaloader.Profile.from_username(L.context, username)
            except:
                embed = discord.Embed(title="Listener", description=f"**{username}** is an invalid Instagram username.", color=discord.Color.red())
                await interaction.followup.send(embed=embed)
                return

            post_list = json.dumps([])

            channel = await not_full.create_text_channel(name=f"{username}")

            await db.execute('INSERT INTO listeners VALUES (?,?,?);', (username, channel.id, post_list))
            await db.commit()

            embed = discord.Embed(title="Listener", description=f"**{username}** is now being listened for new Instagram posts.", color=discord.Color.from_str(embed_color))
            await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ListenCog(bot))