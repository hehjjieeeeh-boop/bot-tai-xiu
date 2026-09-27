import discord, random, json, os, re, time
from discord.ext import commands

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
def is_banned(uid):
    uid=str(uid)
    unb=banned_until.get(uid,0)
    if unb>int(time.time()):
        return True
    # hết ban -> tự động xoá nợ nếu có flag
    if unb!=0 and unb<=int(time.time()):
        # nếu bị ban do không trả được, đã xoá nợ lúc ban
        banned_until.pop(uid,None); save()
    return False

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Online {bot.user}")

@bot.tree.command(name="taixiu",description="Choi tai xiu")
async def taixiu(interaction: discord.Interaction, tien: str, lua_chon: str):
    await interaction.response.defer()
    uid=str(interaction.user.id)
    # check ban
    bt=banned_until.get(uid,0)
    now=int(time.time())
    if bt>now:
        conlai=bt-now; h=conlai//3600; m=(conlai%3600)//60
        await interaction.followup.send(f"🚫 Ban bi cam choi {h}h {m}p vi no xu!")
        return
    if bt!=0 and bt<=now:
        banned_until.pop(uid,None); save()
    try: tien_v=parse_tien(tien)
    except:
        await interaction.followup.send("❌ Tien khong hop le! VD: 10k, 1m"); return
    lua_chon=lua_chon.lower().strip()
    if lua_chon not in ["tai","xiu"]:
        await interaction.followup.send("❌ Chon tai hoac xiu"); return
    bal=get_bal(uid)
    if tien_v<=0:
        await interaction.followup.send("❌ Tien > 0"); return
    if tien_v>bal:
        await interaction.followup.send(f"❌ Khong du xu! Ban co {fmt(bal)} xu"); return
    x1=random.randint(1,6); x2=random.randint(1,6); x3=random.randint(1,6)
    tong=x1+x2+x3
    if x1==x2==x3:
        win=False; kq="Bao 🏠"; kn="B"
    else:
        real="xiu" if 4<=tong<=10 else "tai"
        win=(real==lua_chon); kq="Xiu" if real=="xiu" else "Tai"; kn="X" if real=="xiu" else "T"
    cau_history.append(kn)
    balances[uid]=bal+tien_v if win else bal-tien_v
    save()
    icon="✅ THANG" if win else "❌ THUA"
    cau_str=" ".join(cau_history[-10:])
    await interaction.followup.send(f"🎲 {x1}-{x2}-{x3} (Tong {tong}) => **{kq}**\n{icon} `{fmt(tien_v)} xu`\n💰 Du: **{fmt(balances[uid])} xu**\n📈 Cau: {cau_str}")

@bot.tree.command(name="soxu",description="Xem so xu")
async def soxu(interaction: discord.Interaction):
    uid=str(interaction.user.id)
    debt=int(debts.get(uid,0))
    msg=f"💰 Ban co **{fmt(get_bal(uid))} xu**"
    if debt>0: msg+=f"\n💸 No: **{fmt(debt)} xu**"
    await interaction.response.send_message(msg)

@bot.tree.command(name="chuyentien",description="Chuyen xu")
async def chuyentien(interaction: discord.Interaction, nguoi: discord.Member, tien: str):
    await interaction.response.defer()
    try: tien_v=parse_tien(tien)
    except:
        await interaction.followup.send("❌ Tien khong hop le!"); return
    uid=str(interaction.user.id); tid=str(nguoi.id); bal=get_bal(uid)
    if tien_v<=0 or tien_v>bal:
        await interaction.followup.send("❌ Khong du xu!"); return
    balances[uid]=bal-tien_v; balances[tid]=get_bal(tid)+tien_v; save()
    await interaction.followup.send(f"✅ Da chuyen **{fmt(tien_v)} xu** cho {nguoi.mention}\n💰 Du: **{fmt(balances[uid])} xu**")

@bot.tree.command(name="nhanxu",description="Nhan 50k xu moi 24h")
async def nhanxu(interaction: discord.Interaction):
    uid=str(interaction.user.id); now=int(time.time())
    last=last_claim.get(uid,0); conlai=86400-(now-last)
    if conlai>0:
        h=conlai//3600; m=(conlai%3600)//60
        await interaction.response.send_message(f"⏳ Cho {h}h {m}p nua!",ephemeral=True); return
    last_claim[uid]=now; balances[uid]=get_bal(uid)+50000; save()
    await interaction.response.send_message(f"🎁 +**{fmt(50000)} xu**! Du: **{fmt(balances[uid])} xu**")

@bot.tree.command(name="congxu",description="Cong xu (Admin)")
async def congxu(interaction: discord.Interaction, nguoi: discord.Member, tien: str):
    if str(interaction.user.id) not in ADMIN_IDS:
        await interaction.response.send_message("❌ Ban khong co quyen!",ephemeral=True); return
    try: tien_v=parse_tien(tien)
    except:
        await interaction.response.send_message("❌ Tien khong hop le!"); return
    tid=str(nguoi.id); balances[tid]=get_bal(tid)+tien_v; save()
    await interaction.response.send_message(f"✅ Da cong **{fmt(tien_v)} xu** cho {nguoi.mention}\n💰 Ho co: **{fmt(balances[tid])} xu**")

@bot.tree.command(name="vayxu",description="Vay xu, toi da 10M/tuan")
async def vayxu(interaction: discord.Interaction, tien: str):
    await interaction.response.defer()
    uid=str(interaction.user.id); now=int(time.time())
    try: tien_v=parse_tien(tien)
    except:
        await interaction.followup.send("❌ Tien khong hop le!"); return
    if tien_v<=0:
        await interaction.followup.send("❌ Tien > 0"); return
    # tính tổng đã vay trong 7 ngày
    logs=vay_log.get(uid,[])
    logs=[x for x in logs if now-x[0] < 7*86400]
    tong_tuan=sum(x[1] for x in logs)
    if tong_tuan+tien_v > 10000000:
        await interaction.followup.send(f"❌ Gioi han 10M/tuan! Da vay {fmt(tong_tuan)}/10M tuan nay")
        return
    logs.append([now,tien_v]); vay_log[uid]=logs
    balances[uid]=get_bal(uid)+tien_v
    debts[uid]=int(debts.get(uid,0))+tien_v
    save()
    await interaction.followup.send(f"💸 Vay thanh cong **{fmt(tien_v)} xu**!\n💰 Du: **{fmt(balances[uid])} xu**\n💸 Tong no: **{fmt(debts[uid])} xu**")

@bot.tree.command(name="trano",description="Tra no xu")
async def trano(interaction: discord.Interaction, tien: str):
    await interaction.response.defer()
    uid=str(interaction.user.id); now=int(time.time())
    debt=int(debts.get(uid,0))
    if debt<=0:
        await interaction.followup.send("✅ Ban khong co no!"); return
    try: tien_v=parse_tien(tien)
    except:
        await interaction.followup.send("❌ Tien khong hop le!"); return
    if tien_v<=0:
        await interaction.followup.send("❌ Tien > 0"); return
    if tien_v>debt: tien_v=debt
    bal=get_bal(uid)
    if bal < tien_v:
        # không đủ -> cấm 2 tiếng, xoá nợ
        banned_until[uid]=now+7200
        debts[uid]=0
        save()
        await interaction.followup.send(f"🚫 Khong du xu tra ({fmt(bal)}/{fmt(tien_v)})!\nBi cam choi 2 tieng va da xoa no **{fmt(debt)} xu**!")
        return
    balances[uid]=bal-tien_v
    debts[uid]=debt-tien_v
    save()
    await interaction.followup.send(f"✅ Da tra **{fmt(tien_v)} xu**!\n💸 No con lai: **{fmt(debts[uid])} xu**\n💰 Du: **{fmt(balances[uid])} xu**")

@bot.tree.command(name="cau",description="Xem cau")
async def cau(interaction: discord.Interaction):
    if not cau_history:
        await interaction.response.send_message("Chua co cau"); return
    await interaction.response.send_message(f"📈 Cau: `{' '.join(cau_history[-20:])}`")

@bot.tree.command(name="bxh",description="BXH giau nhat")
async def bxh(interaction: discord.Interaction):
    top=sorted(balances.items(),key=lambda x:x[1],reverse=True)[:10]
    msg="🏆 **BXH**\n"
    for i,(u,b) in enumerate(top,1): msg+=f"{i}. <@{u}> - {fmt(b)} xu\n"
    await interaction.response.send_message(msg)

bot.run(TOKEN)
