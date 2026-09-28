import discord, random, json, os, re, time, datetime, sys
from discord.ext import commands, tasks
from discord import app_commands

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ADMIN_IDS = {"1470776105333162071", "1279776338160652300"}
BXH_CHANNEL_ID = 1553764675626467388
REWARDS = {1:20000000,2:15000000,3:10000000,4:7000000,5:6000000,6:5000000,7:4000000,8:3000000,9:2000000,10:1000000}

VAY_LIMIT_NGAY = 2000000
VAY_HAN_GIO = 20
BAN_GIO = 3

def parse_tien(s):
    s=str(s).lower().strip().replace(",","").replace(" ","")
    if s in ("all","allin","tatay"):
        return "ALL"
    m=re.match(r"^(\d+(\.\d+)?)(k|m|b|t)?$", s)
    if not m: raise ValueError
    n=float(m.group(1)); u=m.group(3)
    if u=="k": n*=1_000
    elif u=="m": n*=1_000_000
    elif u=="b": n*=1_000_000_000
    elif u=="t": n*=1_000_000_000_000
    return int(n)

def fmt(n):
    n=int(n)
    if n>=1_000_000_000_000:
        s=f"{n/1_000_000_000_000:.1f}".rstrip('0').rstrip('.')
        return f"{s}T"
    if n>=1_000_000_000:
        s=f"{n/1_000_000_000:.1f}".rstrip('0').rstrip('.')
        return f"{s}B"
    if n>=1_000_000:
        s=f"{n/1_000_000:.1f}".rstrip('0').rstrip('.')
        return f"{s}M"
    if n>=1_000:
        s=f"{n/1_000:.1f}".rstrip('0').rstrip('.')
        return f"{s}k"
    return str(n)

DB="data.json"
balances={}; cau_history=[]; last_claim={}
debts={}; vay_log={}; banned_until={}
debts_time={}
bxh_msg_id=None; last_reset_date=""

def save():
    try:
        with open(DB,"w",encoding="utf-8") as f:
            json.dump({"balances":balances,"cau":cau_history[-30:],"last":last_claim,"debts":debts,"vay_log":vay_log,"banned":banned_until,"debts_time":debts_time,"bxh_msg":bxh_msg_id,"reset":last_reset_date},f)
    except Exception as e:
        print(f"Loi save: {e}")
def load():
    global balances,cau_history,last_claim,debts,vay_log,banned_until,debts_time,bxh_msg_id,last_reset_date
    if os.path.exists(DB):
        try:
            d=json.load(open(DB,encoding="utf-8"))
            balances=d.get("balances",{}); cau_history=d.get("cau",[])
            last_claim=d.get("last",{}); debts=d.get("debts",{})
            vay_log=d.get("vay_log",{}); banned_until=d.get("banned",{})
            debts_time=d.get("debts_time",{}); bxh_msg_id=d.get("bxh_msg"); last_reset_date=d.get("reset","")
        except Exception as e:
            print(f"Loi load DB, dung DB moi: {e}")
load()
def get_bal(uid): return balances.get(str(uid),10000)

TIEN_GOISAN = ["all","1k","10k","100k","1m","10m","100m","1b","10b","1t"]
async def tien_autocomplete(interaction: discord.Interaction, current: str):
    cur=current.lower().strip()
    out=[]
    for v in TIEN_GOISAN:
        if cur in v.lower() or not cur:
            out.append(app_commands.Choice(name=v, value=v))
    if cur and cur not in TIEN_GOISAN:
        try:
            parse_tien(cur)
            out.insert(0, app_commands.Choice(name=f"{cur} (tuy chinh)", value=cur))
        except: pass
    return out[:25]

def build_bxh_text():
    if not balances: return "Chua co du lieu!"
    top=sorted(balances.items(),key=lambda x:x[1],reverse=True)[:10]
    msg="🏆 **BANG XEP HANG - TOP 10 GIAU NHAT**\n⏰ Reset + thuong luc 00:00 hang ngay\n\n"
    medals=["🥇","🥈","🥉","4.","5.","6.","7.","8.","9.","10."]
    for i,(uid,bal) in enumerate(top):
        r=REWARDS.get(i+1,0)
        msg+=f"{medals[i]} <@{uid}> - **{fmt(bal)} xu** (thuong {fmt(r)})\n"
    msg+=f"\n📊 Cap nhat 2h/lan | Tong {len(balances)} nguoi choi"
    return msg

@tasks.loop(hours=2)
async def auto_bxh_update():
    global bxh_msg_id
    print(">>> Dang cap nhat BXH...", flush=True)
    try:
        ch = bot.get_channel(BXH_CHANNEL_ID)
        if not ch:
            ch = await bot.fetch_channel(BXH_CHANNEL_ID)
        text = build_bxh_text()
        if bxh_msg_id:
            try:
                old = await ch.fetch_message(bxh_msg_id)
                await old.edit(content=text)
                print(">>> Da edit BXH cu", flush=True)
                return
            except Exception as e:
                print(f">>> Khong edit duoc ({e}), se gui moi", flush=True)
        m = await ch.send(text)
        bxh_msg_id = m.id; save()
        print(f">>> Da gui BXH moi: {m.id}", flush=True)
    except Exception as e:
        print(f">>> LOI BXH: {e}", flush=True)

@auto_bxh_update.before_loop
async def before_bxh():
    await bot.wait_until_ready()

@tasks.loop(minutes=1)
async def daily_reset_check():
    global last_reset_date
    now_vn=datetime.datetime.utcnow()+datetime.timedelta(hours=7)
    today=now_vn.strftime("%Y-%m-%d")
    if now_vn.hour==0 and now_vn.minute<2 and last_reset_date!=today:
        last_reset_date=today
        top=sorted(balances.items(),key=lambda x:x[1],reverse=True)[:10]
        try:
            ch=bot.get_channel(BXH_CHANNEL_ID)
            if not ch:
                ch=await bot.fetch_channel(BXH_CHANNEL_ID)
        except: ch=None
        msg="🎉 **KET QUA BXH NGAY "+today+"**\n\n"
        for i,(uid,bal) in enumerate(top):
            rank=i+1; rw=REWARDS.get(rank,0)
            balances[uid]=get_bal(uid)+rw
            msg+=f"{rank}. <@{uid}> nhan **{fmt(rw)} xu**\n"
        save()
        if ch:
            try: await ch.send(msg)
            except: pass
        try: await auto_bxh_update()
        except: pass

@tasks.loop(minutes=1)
async def check_no_tra():
    now=int(time.time())
    changed=False
    han_giay=VAY_HAN_GIO*3600
    for uid in list(debts.keys()):
        debt=int(debts.get(uid,0))
        if debt>0:
            vt=int(debts_time.get(uid,0))
            if vt!=0 and now-vt>=han_giay:
                if banned_until.get(uid,0) < now:
                    banned_until[uid]=now+BAN_GIO*3600
                    debts[uid]=0
                    debts_time.pop(uid,None)
                    changed=True
                    try:
                        user=await bot.fetch_user(int(uid))
                        await user.send(f"🚫 Ban vay {fmt(debt)} xu qua {VAY_HAN_GIO}h khong tra nen bi cam {BAN_GIO} tieng va da xoa no!")
                    except: pass
    if changed: save()

@bot.event
async def on_ready():
    print(f"Online {bot.user} - BXH channel: {BXH_CHANNEL_ID}", flush=True)
    await bot.tree.sync()
    if not auto_bxh_update.is_running():
        auto_bxh_update.start()
    if not daily_reset_check.is_running():
        daily_reset_check.start()
    if not check_no_tra.is_running():
        check_no_tra.start()

@bot.tree.command(name="taixiu",description="Choi tai xiu - nhap all de tat tay")
@app_commands.autocomplete(tien=tien_autocomplete)
@app_commands.choices(lua_chon=[app_commands.Choice(name="Tai",value="tai"),app_commands.Choice(name="Xiu",value="xiu")])
async def taixiu(interaction: discord.Interaction, tien: str, lua_chon: app_commands.Choice[str]):
    await interaction.response.defer()
    uid=str(interaction.user.id)
    bal=get_bal(uid)
    try:
        p=parse_tien(tien)
        tien_v=bal if p=="ALL" else p
    except:
        await interaction.followup.send("❌ Tien khong hop le! VD: 10k, 1m, 1b, all"); return
    chon=lua_chon.value
    now=int(time.time())
    bt=banned_until.get(uid,0)
    if bt>now:
        conlai=bt-now; h=conlai//3600; m=(conlai%3600)//60
        await interaction.followup.send(f"🚫 Bi cam choi {h}h {m}p!"); return
    if bt!=0 and bt<=now:
        banned_until.pop(uid,None); save()
    if tien_v<=0:
        await interaction.followup.send("❌ Tien > 0 (ban khong con xu de all!)"); return
    if tien_v>bal:
        await interaction.followup.send(f"❌ Khong du xu! Ban co {fmt(bal)} xu"); return
    def roll_dice_for(target):
        while True:
            x1=random.randint(1,6); x2=random.randint(1,6); x3=random.randint(1,6)
            if x1==x2==x3: continue
            tong=x1+x2+x3
            if target=="xiu" and 4<=tong<=10: return x1,x2,x3,tong
            if target=="tai" and 11<=tong<=17: return x1,x2,x3,tong
    if random.random() < 0.028:
        x=random.randint(1,6); x1=x2=x3=x; tong=x*3
        win=False; kq="Bao 🏠"; kn="B"
    else:
        last = cau_history[-1] if cau_history else None
        if last in ("T","X") and random.random() < 0.40:
            target = "tai" if last=="T" else "xiu"
        else:
            target = random.choice(["tai","xiu"])
        x1,x2,x3,tong = roll_dice_for(target)
        real=target
        win=(real==chon); kq="Xiu" if real=="xiu" else "Tai"; kn="X" if real=="xiu" else "T"
    cau_history.append(kn)
    balances[uid]=bal+tien_v if win else bal-tien_v
    save()
    icon="✅ THANG" if win else "❌ THUA"
    all_tag=" (ALL IN)" if str(tien).lower() in ("all","allin","tatay") else ""
    await interaction.followup.send(f"🎲 {x1}-{x2}-{x3} (Tong {tong}) => **{kq}**\n{icon} `{fmt(tien_v)} xu`{all_tag}\n💰 Du: **{fmt(balances[uid])} xu**\n📈 Cau: {' '.join(cau_history[-10:])}")

@bot.tree.command(name="soxu",description="Xem so xu")
async def soxu(interaction: discord.Interaction):
    uid=str(interaction.user.id); debt=int(debts.get(uid,0))
    msg=f"💰 Ban co **{fmt(get_bal(uid))} xu**"
    if debt>0:
        vt=int(debts_time.get(uid,0)); now=int(time.time())
        conlai=VAY_HAN_GIO*3600-(now-vt) if vt else 0
        h=max(0,conlai//3600)
        msg+=f"\n💸 No: **{fmt(debt)} xu** (con {h}h de tra)"
    await interaction.response.send_message(msg)

@bot.tree.command(name="chuyentien",description="Chuyen xu")
async def chuyentien(interaction: discord.Interaction, nguoi: discord.Member, tien: str):
    await interaction.response.defer()
    try:
        p=parse_tien(tien)
        if p=="ALL":
            await interaction.followup.send("❌ Khong dung all o day!"); return
        tien_v=p
    except:
        await interaction.followup.send("❌ Tien khong hop le!"); return
    uid=str(interaction.user.id); tid=str(nguoi.id); bal=get_bal(uid)
    if tien_v<=0 or tien_v>bal:
        await interaction.followup.send("❌ Khong du xu!"); return
    balances[uid]=bal-tien_v; balances[tid]=get_bal(tid)+tien_v; save()
    await interaction.followup.send(f"✅ Da chuyen **{fmt(tien_v)} xu** cho {nguoi.mention}")

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
        await interaction.response.send_message("❌ Khong co quyen!",ephemeral=True); return
    try:
        tien_v=parse_tien(tien)
        if tien_v=="ALL":
            await interaction.response.send_message("❌ Khong dung all!"); return
    except:
        await interaction.response.send_message("❌ Tien khong hop le!"); return
    tid=str(nguoi.id); balances[tid]=get_bal(tid)+tien_v; save()
    await interaction.response.send_message(f"✅ Da cong **{fmt(tien_v)} xu** cho {nguoi.mention}")

@bot.tree.command(name="bocam",description="Bo cam (Admin)")
async def bocam(interaction: discord.Interaction, nguoi: discord.Member):
    if str(interaction.user.id) not in ADMIN_IDS:
        await interaction.response.send_message("❌ Khong co quyen!",ephemeral=True); return
    tid=str(nguoi.id)
    if tid in banned_until:
        banned_until.pop(tid,None); save()
        await interaction.response.send_message(f"✅ Da bo cam cho {nguoi.mention}")
    else:
        await interaction.response.send_message(f"ℹ️ {nguoi.mention} khong bi cam")

@bot.tree.command(name="vayxu",description="Vay xu toi da 2M/ngay")
async def vayxu(interaction: discord.Interaction, tien: str):
    await interaction.response.defer()
    uid=str(interaction.user.id); now=int(time.time())
    try:
        tien_v=parse_tien(tien)
        if tien_v=="ALL":
            await interaction.followup.send("❌ Khong dung all!"); return
    except:
        await interaction.followup.send("❌ Tien khong hop le!"); return
    if tien_v<=0:
        await interaction.followup.send("❌ Tien > 0"); return
    logs=[x for x in vay_log.get(uid,[]) if now-x[0] < 86400]
    tong_ngay=sum(x[1] for x in logs)
    if tong_ngay+tien_v>VAY_LIMIT_NGAY:
        await interaction.followup.send(f"❌ Gioi han {fmt(VAY_LIMIT_NGAY)}/ngay! Da vay {fmt(tong_ngay)}/{fmt(VAY_LIMIT_NGAY)}"); return
    logs.append([now,tien_v]); vay_log[uid]=logs
    if int(debts.get(uid,0))==0:
        debts_time[uid]=now
    balances[uid]=get_bal(uid)+tien_v; debts[uid]=int(debts.get(uid,0))+tien_v; save()
    await interaction.followup.send(f"💸 Vay **{fmt(tien_v)} xu** thanh cong! Phai tra trong {VAY_HAN_GIO}h\n💸 No: **{fmt(debts[uid])} xu**")

@bot.tree.command(name="trano",description="Tra no xu")
async def trano(interaction: discord.Interaction, tien: str):
    await interaction.response.defer()
    uid=str(interaction.user.id); now=int(time.time())
    debt=int(debts.get(uid,0))
    if debt<=0:
        await interaction.followup.send("✅ Khong co no!"); return
    try:
        p=parse_tien(tien)
        tien_v=debt if p=="ALL" else p
    except:
        await interaction.followup.send("❌ Tien khong hop le!"); return
    if tien_v>debt: tien_v=debt
    bal=get_bal(uid)
    if bal < tien_v:
        banned_until[uid]=now+BAN_GIO*3600
        debts[uid]=0; debts_time.pop(uid,None); save()
        await interaction.followup.send(f"🚫 Khong du xu tra! Bi cam {BAN_GIO} tieng va xoa no **{fmt(debt)} xu**!"); return
    balances[uid]=bal-tien_v; debts[uid]=debt-tien_v
    if debts[uid]==0: debts_time.pop(uid,None)
    save()
    await interaction.followup.send(f"✅ Da tra **{fmt(tien_v)} xu**!\n💸 No con: **{fmt(debts[uid])} xu**")

@bot.tree.command(name="cau",description="Xem cau")
async def cau(interaction: discord.Interaction):
    if not cau_history:
        await interaction.response.send_message("Chua co cau"); return
    await interaction.response.send_message(f"📈 Cau: `{' '.join(cau_history[-20:])}`")

@bot.tree.command(name="bxh",description="Top 10 nguoi giau nhat")
async def bxh(interaction: discord.Interaction):
    await interaction.response.defer()
    await interaction.followup.send(build_bxh_text())

if __name__ == "__main__":
    if not TOKEN:
        print("LOI: Chua set DISCORD_TOKEN trong Variables cua Railway!", flush=True)
        sys.exit(1)
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"LOI khi chay bot: {e}", flush=True)
        sys.exit(1)
