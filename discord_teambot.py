import discord
from discord.ext import commands
from discord import app_commands
import random
import os
import asyncio
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TOKEN = os.getenv("DISCORD_TOKEN")

ANNOUNCE_CHANNEL_ID = 1377672440783704219
NOGARI_CHANNEL_ID = 1477825330529046580
DATA_FILE = "shuffle_data.json"

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ===== 데이터 저장 =====
def load_data():
    today = get_kst_time().strftime("%Y-%m-%d")

    if not os.path.exists(DATA_FILE):
        return {"date": today, "count": 0}

    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    # 날짜 바뀌면 초기화
    if data.get("date") != today:
        data = {"date": today, "count": 0}

    return data


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


def get_kst_time():
    return datetime.now(ZoneInfo("Asia/Seoul"))


# ===== 팀 생성 =====
def create_balanced_teams(players, team_size):
    random.shuffle(players)
    return [players[i:i + team_size] for i in range(0, len(players), team_size)]


# ===== 노가리 이동 버튼 =====
class MoveToNogariView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🎤 노가리 방으로 이동", style=discord.ButtonStyle.primary)
    async def move(self, interaction: discord.Interaction, button):

        if interaction.user.voice is None:
            await interaction.response.send_message(
                "❌ 음성채널에 들어가 있어야 합니다.", ephemeral=True
            )
            return

        target_channel = interaction.guild.get_channel(NOGARI_CHANNEL_ID)

        if target_channel is None:
            await interaction.response.send_message(
                "❌ 노가리 채널을 찾을 수 없습니다.", ephemeral=True
            )
            return

        try:
            await interaction.user.move_to(target_channel)
            await interaction.response.send_message(
                "✅ 노가리 방으로 이동했습니다!", ephemeral=True
            )
        except:
            await interaction.response.send_message(
                "❌ 이동 권한이 없습니다.", ephemeral=True
            )


# ===== 다시 섞기 =====
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
            if "[📺관전중]" not in m.display_name and not m.bot
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


# ===== 팀 선택 =====
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
            if "[📺관전중]" not in m.display_name and not m.bot
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


# ===== 슬래시 명령어 =====
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

# ===== 팀섞기 공지 (N분 버전) =====
@bot.tree.command(name="팀섞기공지", description="N분 뒤 팀섞기 공지")
@app_commands.describe(minutes="몇 분 뒤에 팀섞기를 할지 입력")
async def announce_shuffle(interaction: discord.Interaction, minutes: int):

    if minutes <= 0 or minutes > 60:
        await interaction.response.send_message(
            "❌ 1분 ~ 60분 사이로 입력해주세요.", ephemeral=True
        )
        return

    data = load_data()

    # 날짜 보장
    today = get_kst_time().strftime("%Y-%m-%d")
    data["date"] = today

    data["count"] += 1
    save_data(data)

    count = data["count"]

    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)

    if channel is None:
        await interaction.response.send_message(
            "공지 채널을 찾을 수 없습니다.", ephemeral=True
        )
        return

    now = get_kst_time()
    target_time = now + timedelta(minutes=minutes)
    time_str = target_time.strftime("%H시 %M분")

    # 1차 공지
    embed = discord.Embed(
        title="📢 팀섞기 예정",
        description=f"**{minutes}분 뒤인 {time_str}에**\n오늘의 **{count}번째 팀섞기**가 진행됩니다!",
        color=0xf1c40f
    )

    embed.add_field(
        name="⏳ 준비해주세요",
        value="게임 마무리 및 이동 준비 부탁드립니다.",
        inline=False
    )

    await channel.send("@here", embed=embed)
    await interaction.response.send_message("공지 완료!", ephemeral=True)

    await asyncio.sleep(minutes * 60)

    # 2차 공지
    embed = discord.Embed(
        title="🚨 팀섞기 시작!",
        description=f"지금 **오늘의 {count}번째 팀섞기**가 진행됩니다!",
        color=0xe74c3c
    )

    embed.add_field(
        name="📍 이동",
        value="아래 버튼을 눌러 노가리 방으로 이동해주세요!",
        inline=False
    )

    view = MoveToNogariView()

    await channel.send("@here", embed=embed, view=view)


@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"{bot.user} 로그인 완료")
    print(f"슬래시 명령어 {len(synced)}개 동기화")


bot.run(TOKEN)
