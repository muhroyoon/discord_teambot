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
DATA_FILE = "/data/shuffle_data.json"

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== 시간 =====
def get_kst_time():
    return datetime.now(ZoneInfo("Asia/Seoul"))

# ===== 데이터 =====
def load_data():
    today = get_kst_time().strftime("%Y-%m-%d")

    if not os.path.exists(DATA_FILE):
        return {"date": today, "count": 0, "schedule": []}

    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    if data.get("date") != today:
        data["date"] = today
        data["count"] = 0

    if "schedule" not in data:
        data["schedule"] = []

    return data


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


# ===== 노가리 이동 =====
class MoveToNogariView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🎤 팀섞대기방으로 이동", style=discord.ButtonStyle.primary)
    async def move(self, interaction: discord.Interaction, button):

        if interaction.user.voice is None:
            await interaction.response.send_message("❌ 음성채널에 있어야 합니다.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(NOGARI_CHANNEL_ID)

        try:
            await interaction.user.move_to(channel)
            await interaction.response.send_message("✅ 이동 완료!", ephemeral=True)
        except:
            await interaction.response.send_message("❌ 이동 실패", ephemeral=True)

# ===== 팀 섞기 UI =====
class TeamSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_team(self, interaction, team_size):

        if interaction.user.voice is None:
            await interaction.response.send_message("❌ 음성채널에 있어야 합니다.", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        members = channel.members

        players = [
            m.display_name
            for m in members
            if "[📺관전중]" not in m.display_name and not m.bot
        ]

        if len(players) < 2:
            await interaction.response.send_message("플레이어 부족", ephemeral=True)
            return

        random.shuffle(players)
        teams = [players[i:i + team_size] for i in range(0, len(players), team_size)]

        embed = discord.Embed(
            title="🎮 랜덤 팀 결과",
            description=f"채널: {channel.name}",
            color=0x2ecc71
        )

        for i, team in enumerate(teams):
            embed.add_field(name=f"팀 {i+1}", value="\n".join(team), inline=False)

        await interaction.response.send_message(embed=embed)

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
        
# ===== 팀 생성 함수 =====
def create_balanced_teams(players, team_size):
    random.shuffle(players)
    return [players[i:i + team_size] for i in range(0, len(players), team_size)]

# ===== 다음 스케줄 =====
def get_next_schedule():
    data = load_data()
    schedule = data.get("schedule", [])

    now = get_kst_time()
    targets = []

    for t in schedule:
        hour, minute = map(int, t.split(":"))
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if hour < 5 and target < now:
            target += timedelta(days=1)

        if target > now:
            targets.append(target)

    if not targets:
        if not schedule:
            return None

        first = schedule[0]
        hour, minute = map(int, first.split(":"))
        return now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=1)

    return min(targets)


# ===== 자동 루프 =====
async def auto_shuffle_loop():
    await bot.wait_until_ready()

    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)

    while not bot.is_closed():

        data = load_data()

        if not data["schedule"]:
            await asyncio.sleep(60)
            continue

        next_time = get_next_schedule()
        now = get_kst_time()

        announce_time = next_time - timedelta(minutes=20)
        now = get_kst_time()

        wait1 = (announce_time - now).total_seconds()

        if wait1 > 0:
            await asyncio.sleep(wait1)
        else:
            print("⚠️ 1차 공지 시간 이미 지남 → 즉시 발송")

        # ===== 1차 공지 =====
        embed = discord.Embed(
            title="⏳ 팀 섞기 카운트다운 시작",
            description=(
                f"🕒 **{next_time.strftime('%H시 %M분')}**\n"
                f"🎮 오늘의 **{data['count'] + 1}번째 팀 섞기 진행 예정**\n\n"
                f"⚠️ 게임 마무리 준비해 주세요!!"
            ),
            color=0xf1c40f
        )

        await channel.send("@here", embed=embed)

        # ===== 2차 공지 =====
        wait2 = (next_time - get_kst_time()).total_seconds()
        if wait2 > 0:
            await asyncio.sleep(wait2)

        data["count"] += 1
        save_data(data)
        count = data["count"]

        embed = discord.Embed(
            title="🚨 팀 섞기 시작!!",
            description=(
                f"🔥 오늘의 **{count}번째 팀 섞기가 시작 되었습니다.**\n\n"
                f"📍 이동해 주세요!!"
            ),
            color=0xe74c3c
        )

        await channel.send("@here", embed=embed, view=MoveToNogariView())

# ===== 팀 섞기 명령어 =====
@bot.tree.command(name="팀", description="랜덤 팀 생성")
async def team(interaction: discord.Interaction):

    embed = discord.Embed(
        title="👥 팀 생성",
        description="팀 인원을 선택하세요",
        color=0x3498db
    )

    await interaction.response.send_message(embed=embed, view=TeamSelectView())

# ===== 시간 설정 =====
@bot.tree.command(name="팀섞기시간설정", description="팀섞기 시간 설정")
async def set_schedule(interaction: discord.Interaction, times: str):

    time_list = times.split()

    for t in time_list:
        try:
            datetime.strptime(t, "%H:%M")
        except:
            await interaction.response.send_message(f"❌ 잘못된 형식: {t}", ephemeral=True)
            return

    data = load_data()
    data["schedule"] = time_list
    save_data(data)

    await interaction.response.send_message(
        f"✅ 설정 완료: {' , '.join(time_list)}",
        ephemeral=True
    )


# ===== 시간 확인 =====
@bot.tree.command(name="팀섞기시간확인", description="현재 시간 확인")
async def check_schedule(interaction: discord.Interaction):

    data = load_data()
    schedule = data.get("schedule", [])

    if not schedule:
        await interaction.response.send_message("❌ 설정 없음", ephemeral=True)
        return

    await interaction.response.send_message(
        f"📅 {' , '.join(schedule)}",
        ephemeral=True
    )


# ===== 시작 =====
@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"{bot.user} 로그인 완료")
    print(f"슬래시 명령어 {len(synced)}개 동기화")

    bot.loop.create_task(auto_shuffle_loop())


bot.run(TOKEN)
