import discord
from discord.ext import commands
import random
import os

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)


def create_balanced_teams(players, team_size):

    random.shuffle(players)

    teams = [
        players[i:i + team_size]
        for i in range(0, len(players), team_size)
    ]

    return teams

class ShuffleView(discord.ui.View):

    def __init__(self, team_size):
        super().__init__(timeout=None)
        self.team_size = team_size

    @discord.ui.button(label="🔄 다시 섞기", style=discord.ButtonStyle.green)
    async def reshuffle(self, interaction: discord.Interaction, button):

        if interaction.user.voice is None:
            await interaction.response.send_message(
                "음성채널에 들어가 있어야 합니다.", ephemeral=True
            )
            return

        channel = interaction.user.voice.channel
        members = channel.members

        players = [
            m.display_name
            for m in members
            if "[📺관전중]" not in m.display_name
        ]

        teams = create_balanced_teams(players, self.team_size)

        embed = discord.Embed(
            title="🎮 랜덤 팀 결과 (다시 섞기)",
            description=f"음성채널: {channel.name}",
            color=0xf39c12
        )

        for i, team in enumerate(teams):
            embed.add_field(
                name=f"팀 {i+1}",
                value="\n".join(team),
                inline=False
            )

        await interaction.response.edit_message(embed=embed, view=self)


class TeamSelectView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    async def create_team(self, interaction, team_size):

        if interaction.user.voice is None:
            await interaction.response.send_message(
                "❌ 음성채널에 들어가 있어야 합니다.", ephemeral=True
            )
            return

        channel = interaction.user.voice.channel
        members = channel.members

        players = [
            m.display_name
            for m in members
            if "[📺관전중]" not in m.display_name
        ]

        if len(players) < 2:
            await interaction.response.send_message(
                "플레이어가 부족합니다.", ephemeral=True
            )
            return

        teams = create_balanced_teams(players, team_size)

        embed = discord.Embed(
            title="🎮 랜덤 팀 결과",
            description=f"음성채널: {channel.name}",
            color=0x2ecc71
        )

        for i, team in enumerate(teams):
            embed.add_field(
                name=f"팀 {i+1}",
                value="\n".join(team),
                inline=False
            )

        view = ShuffleView(team_size)

        await interaction.response.send_message(embed=embed, view=view)

    @discord.ui.button(label="2명 팀", style=discord.ButtonStyle.primary)
    async def team2(self, interaction, button):
        await self.create_team(interaction, 2)

    @discord.ui.button(label="3명 팀", style=discord.ButtonStyle.primary)
    async def team3(self, interaction, button):
        await self.create_team(interaction, 3)

    @discord.ui.button(label="4명 팀", style=discord.ButtonStyle.success)
    async def team4(self, interaction, button):
        await self.create_team(interaction, 4)

    @discord.ui.button(label="5명 팀", style=discord.ButtonStyle.secondary)
    async def team5(self, interaction, button):
        await self.create_team(interaction, 5)


@bot.tree.command(name="팀", description="랜덤 팀 생성")
async def team(interaction: discord.Interaction):

    embed = discord.Embed(
        title="👥 팀 생성",
        description="팀 인원을 선택하세요",
        color=0x3498db
    )

    await interaction.response.send_message(
        embed=embed,
        view=TeamSelectView()
    )


@bot.tree.command(name="관전", description="관전자 토글")
async def spectate(interaction: discord.Interaction):

    member = interaction.user

    if "[📺관전중]" in member.display_name:
        new_name = member.display_name.replace("[📺관전중]", "")
    else:
        new_name = "[📺관전중]" + member.display_name

    try:
        await member.edit(nick=new_name)

        await interaction.response.send_message(
            f"관전 상태 변경: {new_name}",
            ephemeral=True
        )

    except:
        await interaction.response.send_message(
            "닉네임 변경 권한이 없습니다.",
            ephemeral=True
        )


@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"{bot.user} 로그인 완료")
    print(f"슬래시 명령어 {len(synced)}개 동기화")


bot.run(TOKEN)
