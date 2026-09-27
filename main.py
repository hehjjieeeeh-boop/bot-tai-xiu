import discord
import random
import json
import os
import re
import time
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ========== TIEN TE ==========
def parse_tien(s):
    s = str(s).lower().strip().replace(",", "").replace(" ", "")
    m = re.match(r"^(\d+(\.\d+)?)(k|m)?$", s)
    if not m:
        raise ValueError("Tien khong hop le")
    n = float(m.group(1))
    u = m.group(3)
    if u == "k":
        n *= 1000
    elif u == "m":
        n *= 1000000
    return int(n)

def fmt(n):
    n = int(n)
    if n >= 1000000:
        s = f"{n/1000000:.1f}".rstrip('0').rstrip('.')
        return f"{s}M"
    if n >= 1000:
        s = f"{n/1000:.1f}".rstrip('0').rstrip('.')
        return f"{s}k"
    return str(n)

# ========== DATA ==========
DB = "data.json"
balances = {}
cau_history = []
last_claim = {}

def save():
    try:
        with open(DB, "w", encoding="utf-8") as f:
            json.dump({
                "balances": balances,
                "cau": cau_history[-30:],
                "last": last_claim
            }, f)
    except Exception as e:
        print("save err", e)

def load():
    global balances, cau_history, last_claim
    if os.path.exists(DB):
        try:
            with open(DB, "r", encoding="utf-8") as f:
                d = json.load(f)
                balances = d.get("balances", {})
                cau_history = d.get("cau", [])
                last_claim = d.get("last", {})
        except Exception as e:
            print("load err", e)

load()

def get_bal(uid):
    return balances.get(str(uid), 10000)

def add_bal(uid, amount):
    uid = str(uid)
    balances[uid] = get_bal(uid) + amount
    save()

# ========== READY ==========
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Da sync {len(synced)} lenh | Online {bot.user}")
    except Exception as e:
        print("sync err", e)

# ========== TAIXIU ==========
@bot.tree.command(name="taixiu", description="Choi tai xiu")
@discord.app_commands.describe(tien="So tien: 10k, 1m...", lua_chon="Chon tai hoac xiu")
async def taixiu(interaction: discord.Interaction, tien: str, lua_chon: str):
    await interaction.response.defer()
    try:
        tien_v = parse_tien(tien)
    except:
        await interaction.followup.send("❌ Tien khong hop le! VD: 10k, 500k, 1m")
        return

    lua_chon = lua_chon.lower().strip()
    if lua_chon not in ["tai", "xiu"]:
        await interaction.followup.send("❌ Chi duoc chon `tai` hoac `xiu`")
        return

    uid = str(interaction.user.id)
    bal = get_bal(uid)

    if tien_v <= 0:
        await interaction.followup.send("❌ Tien cuoc phai > 0")
        return
    if tien_v > bal:
        await interaction.followup.send(f"❌ Khong du xu! Ban co {fmt(bal)} xu")
        return

    x1 = random.randint(1, 6)
    x2 = random.randint(1, 6)
    x3 = random.randint(1, 6)
    tong = x1 + x2 + x3

    if x1 == x2 == x3:
        win = False
        kq = "Bao 🏠"
        kq_ngan = "B"
    else:
        real = "xiu" if 4 <= tong <= 10 else "tai"
        win = (real == lua_chon)
        kq = "Xiu" if real == "xiu" else "Tai"
        kq_ngan = "X" if real == "xiu" else "T"

    cau_history.append(kq_ngan)
    if len(cau_history) > 30:
        cau_history.pop(0)

    if win:
        balances[uid] = bal + tien_v
    else:
        balances[uid] = bal - tien_v
    save()

    icon = "✅ THANG" if win else "❌ THUA"
    cau_str = " ".join(cau_history[-10:])

    msg = (
        f"🎲 **KET QUA TAI XIU**\n"
        f"🎯 Xuc xac: `{x1} - {x2} - {x3}` (Tong {tong})\n"
        f"📊 Ket qua: **{kq}** | Ban chon: **{lua_chon.upper()}**\n"
        f"{icon} `{fmt(tien_v)} xu`\n"
        f"💰 So du: **{fmt(balances[uid])} xu**\n"
        f"📈 Cau: {cau_str}"
    )
    await interaction.followup.send(msg)

# ========== SOXU ==========
@bot.tree.command(name="soxu", description="Xem so xu cua ban")
async def soxu(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    await interaction.response.send_message(f"💰 Ban co **{fmt(get_bal(uid))} xu**")

# ========== CHUYENTIEN ==========
@bot.tree.command(name="chuyentien", description="Chuyen xu cho nguoi khac")
@discord.app_commands.describe(nguoi="Nguoi nhan", tien="So tien: 10k, 1m...")
async def chuyentien(interaction: discord.Interaction, nguoi: discord.Member, tien: str):
    await interaction.response.defer()
    if nguoi.bot:
        await interaction.followup.send("❌ Khong chuyen cho bot duoc")
        return
    try:
        tien_v = parse_tien(tien)
    except:
        await interaction.followup.send("❌ Tien khong hop le!")
        return

    uid = str(interaction.user.id)
    tid = str(nguoi.id)
    if uid == tid:
        await interaction.followup.send("❌ Khong tu chuyen cho chinh minh")
        return

    bal = get_bal(uid)
    if tien_v <= 0:
        await interaction.followup.send("❌ Tien phai > 0")
        return
    if tien_v > bal:
        await interaction.followup.send(f"❌ Khong du xu! Ban co {fmt(bal)} xu")
        return

    balances[uid] = bal - tien_v
    balances[tid] = get_bal(tid) + tien_v
    save()
    await interaction.followup.send(
        f"✅ Da chuyen **{fmt(tien_v)} xu** cho {nguoi.mention}\n"
        f"💰 So du cua ban: **{fmt(balances[uid])} xu**"
    )

# ========== NHANXU ==========
@bot.tree.command(name="nhanxu", description="Nhan 50k xu mien phi moi 24h")
async def nhanxu(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    now = int(time.time())
    last = last_claim.get(uid, 0)
    conlai = 86400 - (now - last)

    if conlai > 0:
        h = conlai // 3600
        m = (conlai % 3600) // 60
        s = conlai % 60
        await interaction.response.send_message(
            f"⏳ Ban da nhan roi! Quay lai sau **{h}h {m}p {s}s**",
            ephemeral=True
        )
        return

    last_claim[uid] = now
    balances[uid] = get_bal(uid) + 50000
    save()
    await interaction.response.send_message(
        f"🎁 Nhan thanh cong **{fmt(50000)} xu**!\n"
        f"💰 So du: **{fmt(balances[uid])} xu**\n"
        f"⏰ Quay lai sau 24h nhe"
    )

# ========== CAU ==========
@bot.tree.command(name="cau", description="Xem cau tai xiu gan day")
async def cau(interaction: discord.Interaction):
    if not cau_history:
        await interaction.response.send_message("📈 Chua co cau nao")
        return
    cau_str = " ".join(cau_history[-20:])
    await interaction.response.send_message(f"📈 Cau 20 tay gan nhat:\n`{cau_str}`\n(T=Xiu, T=Tai, B=Bao)")

# ========== BXH ==========
@bot.tree.command(name="bxh", description="Bang xep hang giau nhat")
async def bxh(interaction: discord.Interaction):
    if not balances:
        await interaction.response.send_message("Chua co du lieu")
        return
    top = sorted(balances.items(), key=lambda x: x[1], reverse=True)[:10]
    msg = "🏆 **BANG XEP HANG**\n"
    for i, (uid, bal) in enumerate(top, 1):
        msg += f"{i}. <@{uid}> - {fmt(bal)} xu\n"
    await interaction.response.send_message(msg)

bot.run(TOKEN)
