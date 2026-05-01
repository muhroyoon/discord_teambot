import os
import random

import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)


class TeamSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_team(self, interaction: discord.Interaction, team_size: int):
        if interaction.user.voice is None:
            await interaction.response.send_message("❌ 음성채널에 있어야 합니다.", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        members = channel.members

        players = [
            member.display_name
            for member in members
            if "[📺관전중]" not in member.display_name and not member.bot
        ]

        if len(players) < 2:
            await interaction.response.send_message("플레이어 부족", ephemeral=True)
            return

        random.shuffle(players)
        teams = [players[i:i + team_size] for i in range(0, len(players), team_size)]

        embed = discord.Embed(
            title="🎮 랜덤 팀 결과",
            description=f"채널: {channel.name}",
            color=0x2ECC71,
        )

        for index, team in enumerate(teams, start=1):
            embed.add_field(name=f"팀 {index}", value="\n".join(team), inline=False)

        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="2명 팀", style=discord.ButtonStyle.primary)
    async def team2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_team(interaction, 2)

    @discord.ui.button(label="3명 팀", style=discord.ButtonStyle.primary)
    async def team3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_team(interaction, 3)

    @discord.ui.button(label="4명 팀", style=discord.ButtonStyle.success)
    async def team4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_team(interaction, 4)

    @discord.ui.button(label="5명 팀", style=discord.ButtonStyle.secondary)
    async def team5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_team(interaction, 5)


@bot.tree.command(name="팀", description="랜덤 팀 생성")
async def team(interaction: discord.Interaction):
    embed = discord.Embed(
        title="👥 팀 생성",
        description="팀 인원을 선택하세요",
        color=0x3498DB,
    )

    await interaction.response.send_message(embed=embed, view=TeamSelectView())


@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"{bot.user} 로그인 완료")
    print(f"슬래시 명령어 {len(synced)}개 동기화")


bot.run(TOKEN)
