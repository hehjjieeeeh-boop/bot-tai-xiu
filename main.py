import discord, random, json, os, re, time, datetime, sys, asyncio
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
BAN_TIME = 45

def parse_tien(s):
    s=str(s).lower().strip().replace(",","").replace(" ","")
    if s in ("all","allin","tatay"): return "ALL"
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
    if n>=1_000_000_000_000: return f"{n/1_000_000_000_000:.1f}".rstrip('0').rstrip('.')+"T"
    if n>=1_000_000_000: return f"{n/1_000_000_000:.1f}".rstrip('0').rstrip('.')+"B"
    if n>=1_000_000: return f"{n/1_000_000:.1f}".rstrip('0').rstrip('.')+"M"
    if n>=1_000: return f"{n/1_000:.1f}".rstrip('0').rstrip('.')+"k"
    return str(n)

DB="data.json"
balances={}; cau_history=[]; last_claim={}
debts={}; vay_log={}; banned_until={}
debts_time={}
bxh_msg_id=None; last_reset_date=""
sessions={}

def save():
    try:
        with open(DB,"w",encoding="utf-8") as f:
            json.dump({"balances":balances,"cau":cau_history[-30:],"last":last_claim,"debts":debts,"vay_log":vay_log,"banned":banned_until,"debts_time":debts_time,"bxh_msg":bxh_msg_id,"reset":last_reset_date},f)
    except: pass

def load():
    global balances,cau_history,last_claim,debts,vay_log,banned_until,debts_time,bxh_msg_id,last_reset_date
    if os.path.exists(DB):
        try:
            d=json.load(open(DB,encoding="utf-8"))
            balances=d.get("balances",{}); cau_history=d.get("cau",[])
            last_claim=d.get("last",{}); debts=d.get("debts",{})
            vay_log=d.get("vay_log",{}); banned_until=d.get("banned",{})
            debts_time=d.get("debts_time",{}); bxh_msg_id=d.get("bxh_msg"); last_reset_date=d.get("reset","")
        except: pass
load()
def get_bal(uid): return balances.get(str(uid),10000)

def roll_chung():
    if random.random() < 0.028:
        x=random.randint(1,6); return x,x,x,x*3,"B","Bão 🏠"
    def roll_for(target):
        while True:
            x1=random.randint(1,6); x2=random.randint(1,6); x3=random.randint(1,6)
            if x1==x2==x3: continue
            t=x1+x2+x3
            if target=="xiu" and 4<=t<=10: return x1,x2,x3,t
            if target=="tai" and 11<=t<=17: return x1,x2,x3,t
    last = cau_history[-1] if cau_history else None
    if last in ("T","X") and random.random()<0.40:
        target = "tai" if last=="T" else "xiu"
    else:
        target = random.choice(["tai","xiu"])
    x1,x2,x3,t = roll_for(target)
    return x1,x2,x3,t,("T" if target=="tai" else "X"),("Tài" if target=="tai" else "Xỉu")

def get_ban_embed(conlai, bets):
    tong_tai=sum(v["tien"] for v in bets.values() if v["chon"]=="tai")
    tong_xiu=sum(v["tien"] for v in bets.values() if v["chon"]=="xiu")
    dem_tai=sum(1 for v in bets.values() if v["chon"]=="tai")
    dem_xiu=sum(1 for v in bets.values() if v["chon"]=="xiu")
    done = int((BAN_TIME-conlai)/BAN_TIME*10)
    if done<0: done=0
    if done>10: done=10
    bar = "🟩"*done + "⬜"*(10-done)
    e = discord.Embed(title="🎲 TÀI XỈU CHUNG - ĐANG ĐẶT CƯỢC", color=0xffd700)
    e.add_field(name="⏳ Thời gian", value=f"**{max(0,conlai)}s**\n{bar}", inline=False)
    e.add_field(name="🔴 TÀI", value=f"💰 {fmt(tong_tai)}\n👥 {dem_tai} người", inline=True)
    e.add_field(name="🔵 XỈU", value=f"💰 {fmt(tong_xiu)}\n👥 {dem_xiu} người", inline=True)
    e.add_field(name="📈 Cầu", value=' '.join(cau_history[-10:]) if cau_history else "Chưa có", inline=False)
    e.set_footer(text="Dùng /datcuoc để tham gia • all = tất tay")
    return e

def get_ketqua_embed(x1,x2,x3,tong,kq,kn,bets):
    mau = 0x00ff00 if kn=="T" else 0x0099ff if kn=="X" else 0xff0000
    e = discord.Embed(title=f"🎲 KẾT QUẢ: {x1} - {x2} - {x3}", description=f"### Tổng **{tong}** → **{kq.upper()}**", color=mau)
    thang=[]; thua=[]
    for uid,info in bets.items():
        chon=info["chon"]; tien_v=info["tien"]
        win=(kn!="B") and (chon==("tai" if kn=="T" else "xiu"))
        if win: thang.append(f"✅ <@{uid}> `+{fmt(tien_v)}` ({chon.upper()})")
        else: thua.append(f"❌ <@{uid}> `-{fmt(tien_v)}` ({chon.upper()})")
    if thang: e.add_field(name=f"🏆 Thắng ({len(thang)})", value="\n".join(thang[:15]), inline=False)
    if thua: e.add_field(name=f"💸 Thua ({len(thua)})", value="\n".join(thua[:15]), inline=False)
    e.add_field(name="📈 Cầu", value=' '.join(cau_history[-10:]), inline=False)
    e.set_footer(text=f"Tổng {len(bets)} người chơi")
    return e

async def update_ban_embed(guild_id):
    s = sessions.get(guild_id)
    if not s: return
    try:
        ch = bot.get_channel(s["channel_id"])
        if not ch: return
        msg = await ch.fetch_message(s["msg_id"])
        conlai = max(0, int(s["end_time"] - time.time()))
        await msg.edit(embed=get_ban_embed(conlai, s["bets"]), content=None)
    except Exception as e:
        print(f"[update_ban] loi: {e}", flush=True)

async def chay_ban(guild_id):
    s = sessions.get(guild_id)
    if not s: return
    print(f"[chay_ban] bat dau {guild_id}", flush=True)
    while True:
        await asyncio.sleep(5)
        s = sessions.get(guild_id)
        if not s:
            print("[chay_ban] session mat", flush=True); return
        conlai = int(s["end_time"] - time.time())
        if conlai <= 0: break
        await update_ban_embed(guild_id)
        print(f"[chay_ban] update {conlai}s", flush=True)
    s = sessions.pop(guild_id, None)
    if not s: return
    print("[chay_ban] het gio roll", flush=True)
    bets = s["bets"]
    ch = bot.get_channel(s["channel_id"])
    if not bets:
        try:
            msg = await ch.fetch_message(s["msg_id"])
            await msg.edit(content="⏰ Hết giờ mà không ai đặt cược!", embed=None)
        except:
            if ch: await ch.send("⏰ Hết giờ mà không ai đặt cược!")
        return
    x1,x2,x3,tong,kn,kq = roll_chung()
    cau_history.append(kn)
    is_bao = (kn=="B")
    for uid,info in bets.items():
        chon=info["chon"]; tien_v=info["tien"]
        win=(not is_bao) and (chon==("tai" if kn=="T" else "xiu"))
        if win: balances[uid]=get_bal(uid)+tien_v*2
    save()
    emb = get_ketqua_embed(x1,x2,x3,tong,kq,kn,bets)
    try:
        msg = await ch.fetch_message(s["msg_id"])
        await msg.edit(embed=emb, content=None)
        print("[chay_ban] da edit kq", flush=True)
    except Exception as e:
        print(f"[chay_ban] edit fail gui moi: {e}", flush=True)
        if ch: await ch.send(embed=emb)

TIEN_GOISAN=["all","1k","10k","100k","1m","10m","100m","1b","10b","1t"]
async def tien_autocomplete(interaction: discord.Interaction, current: str):
    cur=current.lower().strip(); out=[]
    for v in TIEN_GOISAN:
        if cur in v.lower() or not cur: out.append(app_commands.Choice(name=v,value=v))
    if cur and cur not in TIEN_GOISAN:
        try: parse_tien(cur); out.insert(0,app_commands.Choice(name=cur,value=cur))
        except: pass
    return out[:25]

def build_bxh_text():
    if not balances: return "Chua co du lieu!"
    top=sorted(balances.items(),key=lambda x:x[1],reverse=True)[:10]
    msg="🏆 **BANG XEP HANG - TOP 10**\n\n"
    medals=["🥇","🥈","🥉","4.","5.","6.","7.","8.","9.","10."]
    for i,(uid,bal) in enumerate(top):
        msg+=f"{medals[i]} <@{uid}> - **{fmt(bal)}** (thuong {fmt(REWARDS.get(i+1,0))})\n"
    return msg

@tasks.loop(hours=2)
async def auto_bxh_update():
    global bxh_msg_id
    try:
        ch=bot.get_channel(BXH_CHANNEL_ID) or await bot.fetch_channel(BXH_CHANNEL_ID)
        text=build_bxh_text()
        if bxh_msg_id:
            try: await (await ch.fetch_message(bxh_msg_id)).edit(content=text); return
            except: pass
        m=await ch.send(text); bxh_msg_id=m.id; save()
    except Exception as e: print(e,flush=True)
@auto_bxh_update.before_loop
async def before_bxh(): await bot.wait_until_ready()
@tasks.loop(minutes=1)
async def daily_reset_check():
    global last_reset_date
    now_vn=datetime.datetime.utcnow()+datetime.timedelta(hours=7)
    today=now_vn.strftime("%Y-%m-%d")
    if now_vn.hour==0 and now_vn.minute<2 and last_reset_date!=today:
        last_reset_date=today
        top=sorted(balances.items(),key=lambda x:x[1],reverse=True)[:10]
        for i,(uid,bal) in enumerate(top): balances[uid]=get_bal(uid)+REWARDS.get(i+1,0)
        save()
@tasks.loop(minutes=1)
async def check_no_tra():
    now=int(time.time()); changed=False
    for uid in list(debts.keys()):
        debt=int(debts.get(uid,0))
        if debt>0:
            vt=int(debts_time.get(uid,0))
            if vt and now-vt>=VAY_HAN_GIO*3600 and banned_until.get(uid,0)<now:
                banned_until[uid]=now+BAN_GIO*3600; debts[uid]=0; debts_time.pop(uid,None); changed=True
    if changed: save()

@bot.event
async def on_ready():
    print(f"Online {bot.user}",flush=True); await bot.tree.sync()
    if not auto_bxh_update.is_running(): auto_bxh_update.start()
    if not daily_reset_check.is_running(): daily_reset_check.start()
    if not check_no_tra.is_running(): check_no_tra.start()

@bot.tree.command(name="moban",description="Mở bàn tài xỉu chung 45s")
async def moban(interaction: discord.Interaction):
    gid=interaction.guild_id
    if not gid: await interaction.response.send_message("❌ Chỉ dùng trong server!"); return
    if gid in sessions: await interaction.response.send_message("⏳ Đang có bàn rồi!",ephemeral=True); return
    await interaction.response.defer()
    end_time=time.time()+BAN_TIME
    msg=await interaction.followup.send(embed=get_ban_embed(BAN_TIME, {}))
    sessions[gid]={"bets":{},"channel_id":interaction.channel_id,"msg_id":msg.id,"end_time":end_time}
    print(f"[moban] mo ban {gid} msg {msg.id}",flush=True)
    asyncio.create_task(chay_ban(gid))

@bot.tree.command(name="datcuoc",description="Đặt cược vào bàn chung")
@app_commands.autocomplete(tien=tien_autocomplete)
@app_commands.choices(lua_chon=[app_commands.Choice(name="Tài",value="tai"),app_commands.Choice(name="Xỉu",value="xiu")])
async def datcuoc(interaction: discord.Interaction, lua_chon: app_commands.Choice[str], tien: str):
    gid=interaction.guild_id
    s=sessions.get(gid)
    if not s: await interaction.response.send_message("❌ Chưa có bàn, dùng /moban!",ephemeral=True); return
    if time.time() >= s["end_time"]-2:
        await interaction.response.send_message("⏰ Hết giờ đặt rồi!",ephemeral=True); return
    uid=str(interaction.user.id); now=int(time.time())
    if banned_until.get(uid,0)>now: await interaction.response.send_message("🚫 Bạn đang bị cấm!",ephemeral=True); return
    bal=get_bal(uid)
    try: p=parse_tien(tien); tien_v=bal if p=="ALL" else p
    except: await interaction.response.send_message("❌ Tiền không hợp lệ!",ephemeral=True); return
    if tien_v<=0 or tien_v>bal: await interaction.response.send_message(f"❌ Không đủ xu! Có {fmt(bal)}",ephemeral=True); return
    chon=lua_chon.value; bets=s["bets"]
    if uid in bets and bets[uid]["chon"]!=chon:
        await interaction.response.send_message("❌ Đã đặt cửa kia rồi!",ephemeral=True); return
    balances[uid]=bal-tien_v
    if uid in bets: bets[uid]["tien"]+=tien_v
    else: bets[uid]={"chon":chon,"tien":tien_v}
    save()
    await interaction.response.send_message(f"✅ Đã đặt **{fmt(tien_v)}** vào **{chon.upper()}**",ephemeral=True)
    await update_ban_embed(gid)

@bot.tree.command(name="taixiu",description="Chơi lẻ")
@app_commands.autocomplete(tien=tien_autocomplete)
@app_commands.choices(lua_chon=[app_commands.Choice(name="Tài",value="tai"),app_commands.Choice(name="Xỉu",value="xiu")])
async def taixiu(interaction: discord.Interaction, tien: str, lua_chon: app_commands.Choice[str]):
    await interaction.response.defer()
    uid=str(interaction.user.id); bal=get_bal(uid)
    try: p=parse_tien(tien); tien_v=bal if p=="ALL" else p
    except: await interaction.followup.send("❌ Tiền không hợp lệ!"); return
    chon=lua_chon.value
    if tien_v<=0 or tien_v>bal: await interaction.followup.send("❌ Không đủ xu!"); return
    x1,x2,x3,tong,kn,kq=roll_chung()
    win=(kn!="B") and (chon==("tai" if kn=="T" else "xiu"))
    cau_history.append(kn); balances[uid]=bal+tien_v if win else bal-tien_v; save()
    await interaction.followup.send(f"🎲 {x1}-{x2}-{x3} ({tong}) => **{kq}**\n{'✅ THẮNG' if win else '❌ THUA'} {fmt(tien_v)}\n💰 Còn: {fmt(balances[uid])}")

@bot.tree.command(name="soxu",description="Xem xu")
async def soxu(interaction: discord.Interaction):
    await interaction.response.send_message(f"💰 Bạn có **{fmt(get_bal(str(interaction.user.id)))} xu**")
@bot.tree.command(name="cau",description="Xem cầu")
async def cau(interaction: discord.Interaction):
    await interaction.response.send_message(f"📈 Cầu: `{' '.join(cau_history[-20:])}`" if cau_history else "Chưa có")
@bot.tree.command(name="bxh",description="Top 10")
async def bxh(interaction: discord.Interaction):
    await interaction.response.defer(); await interaction.followup.send(build_bxh_text())
@bot.tree.command(name="nhanxu",description="Nhận 50k/24h")
async def nhanxu(interaction: discord.Interaction):
    uid=str(interaction.user.id); now=int(time.time()); last=last_claim.get(uid,0)
    if 86400-(now-last)>0: await interaction.response.send_message("⏳ Chờ đã!",ephemeral=True); return
    last_claim[uid]=now; balances[uid]=get_bal(uid)+50000; save()
    await interaction.response.send_message(f"🎁 +50k! Có {fmt(balances[uid])}")
@bot.tree.command(name="vayxu",description="Vay 2M/ngày")
async def vayxu(interaction: discord.Interaction, tien: str):
    await interaction.response.defer()
    uid=str(interaction.user.id); now=int(time.time())
    try: tien_v=parse_tien(tien)
    except: await interaction.followup.send("❌ Tiền không hợp lệ!"); return
    logs=[x for x in vay_log.get(uid,[]) if now-x[0]<86400]
    if sum(x[1] for x in logs)+tien_v>VAY_LIMIT_NGAY: await interaction.followup.send("❌ Quá 2M/ngày!"); return
    logs.append([now,tien_v]); vay_log[uid]=logs
    if int(debts.get(uid,0))==0: debts_time[uid]=now
    balances[uid]=get_bal(uid)+tien_v; debts[uid]=int(debts.get(uid,0))+tien_v; save()
    await interaction.followup.send(f"💸 Vay {fmt(tien_v)}! Nợ: {fmt(debts[uid])}")
@bot.tree.command(name="trano",description="Trả nợ")
async def trano(interaction: discord.Interaction, tien: str):
    await interaction.response.defer()
    uid=str(interaction.user.id); debt=int(debts.get(uid,0))
    if debt<=0: await interaction.followup.send("✅ Không nợ!"); return
    try: p=parse_tien(tien); tien_v=debt if p=="ALL" else p
    except: await interaction.followup.send("❌ Tiền không hợp lệ!"); return
    if tien_v>debt: tien_v=debt
    if get_bal(uid)<tien_v:
        banned_until[uid]=int(time.time())+BAN_GIO*3600; debts[uid]=0; debts_time.pop(uid,None); save()
        await interaction.followup.send(f"🚫 Không đủ xu! Ban {BAN_GIO}h + xoá nợ!"); return
    balances[uid]=get_bal(uid)-tien_v; debts[uid]=debt-tien_v
    if debts[uid]==0: debts_time.pop(uid,None)
    save(); await interaction.followup.send(f"✅ Trả {fmt(tien_v)}! Còn nợ {fmt(debts[uid])}")
@bot.tree.command(name="chuyentien",description="Chuyển xu")
async def chuyentien(interaction: discord.Interaction, nguoi: discord.Member, tien: str):
    await interaction.response.defer()
    try: tien_v=parse_tien(tien)
    except: await interaction.followup.send("❌ Tiền không hợp lệ!"); return
    uid=str(interaction.user.id); bal=get_bal(uid)
    if tien_v<=0 or tien_v>bal: await interaction.followup.send("❌ Không đủ!"); return
    balances[uid]=bal-tien_v; balances[str(nguoi.id)]=get_bal(str(nguoi.id))+tien_v; save()
    await interaction.followup.send(f"✅ Chuyển {fmt(tien_v)} cho {nguoi.mention}")
@bot.tree.command(name="congxu",description="Cộng xu (Admin)")
async def congxu(interaction: discord.Interaction, nguoi: discord.Member, tien: str):
    if str(interaction.user.id) not in ADMIN_IDS: await interaction.response.send_message("❌!",ephemeral=True); return
    tien_v=parse_tien(tien); balances[str(nguoi.id)]=get_bal(str(nguoi.id))+tien_v; save()
    await interaction.response.send_message(f"✅ Cộng {fmt(tien_v)} cho {nguoi.mention}")
@bot.tree.command(name="bocam",description="Bỏ cấm (Admin)")
async def bocam(interaction: discord.Interaction, nguoi: discord.Member):
    if str(interaction.user.id) not in ADMIN_IDS: return
    banned_until.pop(str(nguoi.id),None); save()
    await interaction.response.send_message(f"✅ Đã bỏ cấm {nguoi.mention}")

if __name__=="__main__":
    if not TOKEN: print("Thiếu DISCORD_TOKEN",flush=True); sys.exit(1)
    bot.run(TOKEN)
