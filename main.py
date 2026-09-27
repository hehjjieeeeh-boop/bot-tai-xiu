import discord, random, json, os, re, time
from discord.ext import commands
from discord import app_commands

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ADMIN_IDS = {"1470776105333162071", "1279776338160652300"}

def parse_tien(s):
    s=str(s).lower().strip().replace(",","").replace(" ","")
    m=re.match(r"^(\d+(\.\d+)?)(k|m)?$", s)
    if not m: raise ValueError
    n=float(m.group(1)); u=m.group(3)
    if u=="k": n*=1000
    elif u=="m": n*=1000000
    return int(n)

def fmt(n):
    n=int(n)
    if n>=1000000:
        s=f"{n/1000000:.1f}".rstrip('0').rstrip('.')
        return f"{s}M"
    if n>=1000:
        s=f"{n/1000:.1f}".rstrip('0').rstrip('.')
        return f"{s}k"
    return str(n)

DB="data.json"
balances={}; cau_history=[]; last_claim={}
debts={}; vay_log={}; banned_until={}

def save():
    with open(DB,"w",encoding="utf-8") as f:
        json.dump({"balances":balances,"cau":cau_history[-30:],"last":last_claim,"debts":debts,"vay_log":vay_log,"banned":banned_until},f)
def load():
    global balances,cau_history,last_claim,debts,vay_log,banned_until
    if os.path.exists(DB):
        try:
            d=json.load(open(DB))
            balances=d.get("balances",{}); cau_history=d.get("cau",[])
            last_claim=d.get("last",{}); debts=d.get("debts",{})
            vay_log=d.get("vay_log",{}); banned_until=d.get("banned",{})
        except: pass
load()

def get_bal(uid): return balances.get(str(uid),10000)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Online {bot.user}")

# ========== TAIXIU VOI LUA CHON ==========
@bot.tree.command(name="taixiu",description="Choi tai xiu")
@app_commands.choices(
    tien=[
        app_commands.Choice(name="1k", value="1k"),
        app_commands.Choice(name="5k", value="5k"),
        app_commands.Choice(name="10k", value="10k"),
        app_commands.Choice(name="50k", value="50k"),
        app_commands.Choice(name="100k", value="100k"),
        app_commands.Choice(name="500k", value="500k"),
        app_commands.Choice(name="1M", value="1m"),
        app_commands.Choice(name="5M", value="5m"),
        app_commands.Choice(name="10M", value="10m"),
        app_commands.Choice(name="100M", value="100m"),
    ],
    lua_chon=[
        app_commands.Choice(name="Tài", value="tai"),
        app_commands.Choice(name="Xỉu", value="xiu"),
    ]
)
async def taixiu(interaction: discord.Interaction, tien: app_commands.Choice[str], lua_chon: app_commands.Choice[str]):
    await interaction.response.defer()
    tien_v = parse_tien(tien.value)
    chon = lua_chon.value
    uid=str(interaction.user.id); now=int(time.time())
    bt=banned_until.get(uid,0)
    if bt>now:
        conlai=bt-now; h=conlai//3600; m=(conlai%3600)//60
        await interaction.followup.send(f"🚫 Bi cam choi {h}h {m}p!"); return
    if bt!=0 and bt<=now:
        banned_until.pop(uid,None); save()
    bal=get_bal(uid)
    if tien_v>bal:
        await interaction.followup.send(f"❌ Khong du xu! Ban co {fmt(bal)} xu"); return
    x1=random.randint(1,6); x2=random.randint(1,6); x3=random.randint(1,6)
    tong=x1+x2+x3
    if x1==x2==x3:
        win=False; kq="Bao 🏠"; kn="B"
    else:
        real="xiu" if 4<=tong<=10 else "tai"
        win=(real==chon); kq="Xỉu" if real=="xiu" else "Tài"; kn="X" if real=="xiu" else "T"
    cau_history.append(kn)
    balances[uid]=bal+tien_v if win else bal-tien_v
    save()
    icon="✅ THẮNG" if win else "❌ THUA"
    await interaction.followup.send(f"🎲 {x1}-{x2}-{x3} (Tổng {tong}) => **{kq}**\n{icon} `{fmt(tien_v)} xu`\n💰 Dư: **{fmt(balances[uid])} xu**\n📈 Cầu: {' '.join(cau_history[-10:])}")

@bot.tree.command(name="soxu",description="Xem so xu")
async def soxu(interaction: discord.Interaction):
    uid=str(interaction.user.id); debt=int(debts.get(uid,0))
    msg=f"💰 Bạn có **{fmt(get_bal(uid))} xu**"
    if debt>0: msg+=f"\n💸 Nợ: **{fmt(debt)} xu**"
    await interaction.response.send_message(msg)

@bot.tree.command(name="chuyentien",description="Chuyen xu")
async def chuyentien(interaction: discord.Interaction, nguoi: discord.Member, tien: str):
    await interaction.response.defer()
    try: tien_v=parse_tien(tien)
    except:
        await interaction.followup.send("❌ Tiền không hợp lệ!"); return
    uid=str(interaction.user.id); tid=str(nguoi.id); bal=get_bal(uid)
    if tien_v<=0 or tien_v>bal:
        await interaction.followup.send("❌ Không đủ xu!"); return
    balances[uid]=bal-tien_v; balances[tid]=get_bal(tid)+tien_v; save()
    await interaction.followup.send(f"✅ Đã chuyển **{fmt(tien_v)} xu** cho {nguoi.mention}")

@bot.tree.command(name="nhanxu",description="Nhan 50k xu moi 24h")
async def nhanxu(interaction: discord.Interaction):
    uid=str(interaction.user.id); now=int(time.time())
    last=last_claim.get(uid,0); conlai=86400-(now-last)
    if conlai>0:
        h=conlai//3600; m=(conlai%3600)//60
        await interaction.response.send_message(f"⏳ Chờ {h}h {m}p nữa!",ephemeral=True); return
    last_claim[uid]=now; balances[uid]=get_bal(uid)+50000; save()
    await interaction.response.send_message(f"🎁 +**{fmt(50000)} xu**! Dư: **{fmt(balances[uid])} xu**")

@bot.tree.command(name="congxu",description="Cong xu (Admin)")
async def congxu(interaction: discord.Interaction, nguoi: discord.Member, tien: str):
    if str(interaction.user.id) not in ADMIN_IDS:
        await interaction.response.send_message("❌ Không có quyền!",ephemeral=True); return
    try: tien_v=parse_tien(tien)
    except:
        await interaction.response.send_message("❌ Tiền không hợp lệ!"); return
    tid=str(nguoi.id); balances[tid]=get_bal(tid)+tien_v; save()
    await interaction.response.send_message(f"✅ Đã cộng **{fmt(tien_v)} xu** cho {nguoi.mention}")

@bot.tree.command(name="bocam",description="Bo cam cho nguoi khac (Admin)")
async def bocam(interaction: discord.Interaction, nguoi: discord.Member):
    if str(interaction.user.id) not in ADMIN_IDS:
        await interaction.response.send_message("❌ Không có quyền!",ephemeral=True); return
    tid=str(nguoi.id)
    if tid in banned_until:
        banned_until.pop(tid,None); save()
        await interaction.response.send_message(f"✅ Đã bỏ cấm cho {nguoi.mention}")
    else:
        await interaction.response.send_message(f"ℹ️ {nguoi.mention} không bị cấm")

@bot.tree.command(name="vayxu",description="Vay xu toi da 5M/tuan")
async def vayxu(interaction: discord.Interaction, tien: str):
    await interaction.response.defer()
    uid=str(interaction.user.id); now=int(time.time())
    try: tien_v=parse_tien(tien)
    except:
        await interaction.followup.send("❌ Tiền không hợp lệ!"); return
    if tien_v<=0:
        await interaction.followup.send("❌ Tiền > 0"); return
    logs=[x for x in vay_log.get(uid,[]) if now-x[0] < 7*86400]
    tong_tuan=sum(x[1] for x in logs)
    if tong_tuan+tien_v>5000000:
        await interaction.followup.send(f"❌ Giới hạn 5M/tuần! Đã vay {fmt(tong_tuan)}/5M"); return
    logs.append([now,tien_v]); vay_log[uid]=logs
    balances[uid]=get_bal(uid)+tien_v; debts[uid]=int(debts.get(uid,0))+tien_v; save()
    await interaction.followup.send(f"💸 Vay **{fmt(tien_v)} xu** thành công!\n💸 Nợ: **{fmt(debts[uid])} xu**")

@bot.tree.command(name="trano",description="Tra no xu")
async def trano(interaction: discord.Interaction, tien: str):
    await interaction.response.defer()
    uid=str(interaction.user.id); now=int(time.time())
    debt=int(debts.get(uid,0))
    if debt<=0:
        await interaction.followup.send("✅ Không có nợ!"); return
    try: tien_v=parse_tien(tien)
    except:
        await interaction.followup.send("❌ Tiền không hợp lệ!"); return
    if tien_v>debt: tien_v=debt
    bal=get_bal(uid)
    if bal < tien_v:
        banned_until[uid]=now+14400 # 4 tieng
        debts[uid]=0; save()
        await interaction.followup.send(f"🚫 Không đủ xu trả! Bị cấm 4 tiếng và xoá nợ **{fmt(debt)} xu**!"); return
    balances[uid]=bal-tien_v; debts[uid]=debt-tien_v; save()
    await interaction.followup.send(f"✅ Đã trả **{fmt(tien_v)} xu**!\n💸 Nợ còn: **{fmt(debts[uid])} xu**")

@bot.tree.command(name="cau",description="Xem cau")
async def cau(interaction: discord.Interaction):
    if not cau_history:
        await interaction.response.send_message("Chưa có cầu"); return
    await interaction.response.send_message(f"📈 Cầu: `{' '.join(cau_history[-20:])}`")

@bot.tree.command(name="bxh",description="Top 10 nguoi giau nhat")
async def bxh(interaction: discord.Interaction):
    await interaction.response.defer()
    if not balances:
        await interaction.followup.send("Chưa có dữ liệu!"); return
    top=sorted(balances.items(),key=lambda x:x[1],reverse=True)[:10]
    msg="🏆 **TOP 10 NGƯỜI GIÀU NHẤT**\n\n"
    medals=["🥇","🥈","🥉","4.","5.","6.","7.","8.","9.","10."]
    for i,(uid,bal) in enumerate(top):
        try:
            user=await bot.fetch_user(int(uid)); name=user.display_name
        except: name=f"User {uid[:6]}"
        msg+=f"{medals[i]} {name} - **{fmt(bal)} xu**\n"
    await interaction.followup.send(msg)

bot.run(TOKEN)
