import discord, random, json, os, re
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- utils ----------
def parse_tien(s):
    s=str(s).lower().strip().replace(",","")
    m=re.match(r"^(\d+(\.\d+)?)(k|m)?$", s)
    if not m: raise ValueError
    n=float(m.group(1)); u=m.group(3)
    if u=="k": n*=1000
    elif u=="m": n*=1000000
    return int(n)

def fmt(n):
    n=int(n)
    if n>=1_000_000:
        s=f"{n/1_000_000:.1f}".rstrip('0').rstrip('.')
        return f"{s}M"
    if n>=1_000:
        s=f"{n/1_000:.1f}".rstrip('0').rstrip('.')
        return f"{s}k"
    return str(n)

# ---------- data ----------
balances={}
cau_history=[]
DB="data.json"
def save():
    with open(DB,"w") as f: json.dump({"balances":balances,"cau":cau_history[-20:]},f)
def load():
    global balances,cau_history
    if os.path.exists(DB):
        try:
            d=json.load(open(DB))
            balances=d.get("balances",{}); cau_history=d.get("cau",[])
        except: pass
load()

# ---------- events ----------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Online {bot.user}")

# ---------- commands ----------
@bot.tree.command(name="taixiu",description="Chơi tài xỉu")
async def taixiu(interaction: discord.Interaction, tien: str, lua_chon: str):
    await interaction.response.defer()
    try:
        tien_v=parse_tien(tien)
    except:
        await interaction.followup.send("❌ Tiền không hợp lệ! VD: 10k, 1m")
        return
    lua_chon=lua_chon.lower()
    if lua_chon not in ["tai","xiu"]:
        await interaction.followup.send("❌ Chọn tai hoặc xiu")
        return
    uid=str(interaction.user.id)
    bal=balances.get(uid,10000)
    if tien_v<=0:
        await interaction.followup.send("❌ Tiền phải > 0")
        return
    if tien_v>bal:
        await interaction.followup.send(f"❌ Không đủ xu! Bạn có {fmt(bal)} xu")
        return
    try:
        x1=random.randint(1,6); x2=random.randint(1,6); x3=random.randint(1,6)
        tong=x1+x2+x3
        if x1==x2==x3:
            win=False; kq="Bão 🏠"
        else:
            real="xiu" if 4<=tong<=10 else "tai"
            win=(real==lua_chon)
            kq="Xỉu" if real=="xiu" else "Tài"
        cau_history.append(kq)
        balances[uid]=bal+tien_v if win else bal-tien_v
        save()
        icon="✅" if win else "❌"
        await interaction.followup.send(f"🎲 {x1}-{x2}-{x3} (Tổng {tong}) => {kq}\n{icon} {'Thắng' if win else 'Thua'} {fmt(tien_v)} xu\n💰 Dư: {fmt(balances[uid])} xu")
    except Exception as e:
        print("tx err",e)
        await interaction.followup.send("❌ Lỗi, thử lại")

@bot.tree.command(name="soxu",description="Xem số xu")
async def soxu(interaction: discord.Interaction):
    uid=str(interaction.user.id)
    bal=balances.get(uid,10000)
    await interaction.response.send_message(f"💰 Bạn có {fmt(bal)} xu")

@bot.tree.command(name="chuyentien",description="Chuyen tien cho nguoi khac")
async def chuyentien(interaction: discord.Interaction, nguoi: discord.Member, tien: str):
    await interaction.response.defer()
    try: tien_v=parse_tien(tien)
    except:
        await interaction.followup.send("❌ Tiền không hợp lệ!")
        return
    uid=str(interaction.user.id); tid=str(nguoi.id)
    bal=balances.get(uid,10000)
    if tien_v<=0 or tien_v>bal:
        await interaction.followup.send("❌ Không đủ xu!")
        return
    balances[uid]=bal-tien_v
    balances[tid]=balances.get(tid,10000)+tien_v
    save()
    await interaction.followup.send(f"✅ Đã chuyển {fmt(tien_v)} xu cho {nguoi.display_name}\n💰 Dư: {fmt(balances[uid])} xu")

@bot.tree.command(name="daily",description="Nhận xu hàng ngày")
async def daily(interaction: discord.Interaction):
    uid=str(interaction.user.id)
    balances[uid]=balances.get(uid,10000)+5000
    save()
    await interaction.response.send_message(f"🎁 +{fmt(5000)} xu! Dư: {fmt(balances[uid])} xu")

bot.run(TOKEN)
