import discord, random, json, os, re, time, datetime, sys, asyncio
from discord.ext import commands, tasks
from discord import app_commands

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ADMIN_IDS = {"1470776105333162071", "1279776338160652300"}
BXH_CHANNEL_ID = 1553764675626467388
AUTO_BAN_CHANNEL_ID = 1553493424454242364
REWARDS = {1:20000000,2:15000000,3:10000000,4:8000000,5:7000000,6:6000000,7:5000000,8:4000000,9:3000000,10:2000000}
VAY_LIMIT_NGAY = 2000000
VAY_HAN_GIO = 20
BAN_GIO = 3
BAN_TIME = 40

def parse_tien(s):
    s=str(s).lower().strip().replace(",","").replace(" ","")
    if s in ("all","allin","tatay"): return "ALL"
    m=re.match(r"^(\d+(\.\d+)?)(k|m|b|t)?$", s)
    if not m: raise ValueError()
    n=float(m.group(1)); u=m.group(3)
    if u=="k": n*=1000
    elif u=="m": n*=1000000
    elif u=="b": n*=1000000000
    elif u=="t": n*=1000000000000
    return int(n)

def fmt(n):
    n=int(n)
    if n>=10**12: return f"{n/10**12:.1f}".rstrip("0").rstrip(".")+"T"
    if n>=10**9: return f"{n/10**9:.1f}".rstrip("0").rstrip(".")+"B"
    if n>=10**6: return f"{n/10**6:.1f}".rstrip("0").rstrip(".")+"M"
    if n>=10**3: return f"{n/10**3:.1f}".rstrip("0").rstrip(".")+"k"
    return str(n)

DB="data.json"
balances={}; cau_history=[]; cau_le=[]; cau_chung=[]; last_claim={}
debts={}; vay_log={}; banned_until={}; debts_time={}; vip_balances={}; pending_rewards={}
bxh_msg_id=None; last_reset_date=""
sessions={}; ban_tasks={}

def save():
    try:
        with open(DB,"w",encoding="utf-8") as f:
            json.dump({"balances":balances,"cau":cau_history[-30:],"cau_le":cau_le[-30:],"cau_chung":cau_chung[-30:],"last":last_claim,"debts":debts,"vay_log":vay_log,"banned":banned_until,"debts_time":debts_time,"bxh_msg":bxh_msg_id,"reset":last_reset_date,"vip":vip_balances,"pending":pending_rewards},f,ensure_ascii=False)
    except: pass
def load():
    global balances,cau_history,cau_le,cau_chung,last_claim,debts,vay_log,banned_until,debts_time,bxh_msg_id,last_reset_date,vip_balances,pending_rewards
    if os.path.exists(DB):
        try:
            d=json.load(open(DB,encoding="utf-8"))
            balances=d.get("balances",{}); cau_history=d.get("cau",[]); cau_le=d.get("cau_le",[]); cau_chung=d.get("cau_chung",[])
            last_claim=d.get("last",{}); debts=d.get("debts",{})
            vay_log=d.get("vay_log",{}); banned_until=d.get("banned",{})
            debts_time=d.get("debts_time",{}); bxh_msg_id=d.get("bxh_msg"); last_reset_date=d.get("reset",""); vip_balances=d.get("vip",{}); pending_rewards=d.get("pending",{})
        except: pass
load()
def get_bal(uid): return int(balances.get(str(uid),10000))
def get_vip(uid): return int(vip_balances.get(str(uid),0))

def roll(hist):
    if random.random()<0.028:
        x=random.randint(1,6); return x,x,x,x*3,"B","Bao"
    def rf(tg):
        while True:
            a=random.randint(1,6); b=random.randint(1,6); c=random.randint(1,6)
            if a==b==c: continue
            t=a+b+c
            if tg=="xiu" and 4<=t<=10: return a,b,c,t
            if tg=="tai" and 11<=t<=17: return a,b,c,t
    last=hist[-1] if hist else None
    tg="tai" if last=="T" and random.random()<0.4 else "xiu" if last=="X" and random.random()<0.4 else random.choice(["tai","xiu"])
    a,b,c,t=rf(tg)
    return a,b,c,t,"T" if tg=="tai" else "X","Tai" if tg=="tai" else "Xiu"

EMO_DICE="🎲"; EMO_LOCK="🔒"; EMO_GREEN="🟢"; EMO_SQ_G="🟩"; EMO_SQ_W="⬜"
EMO_CLOCK="⏳"; EMO_RED="🔴"; EMO_BLUE="🔵"; EMO_MONEY="💰"
EMO_OK="✅"; EMO_NO="❌"; EMO_CHART="📈"; EMO_CUP="🏆"
EMO_GIFT="🎁"; EMO_GEM="💎"; EMO_FLY="💸"; EMO_BAN="🚫"; EMO_HOUR="⏰"

def ban_embed(conlai,bets,locked=False):
    tt=sum(v["tien"] for v in bets.values() if v["chon"]=="tai")
    tx=sum(v["tien"] for v in bets.values() if v["chon"]=="xiu")
    dt=sum(1 for v in bets.values() if v["chon"]=="tai")
    dx=sum(1 for v in bets.values() if v["chon"]=="xiu")
    done=int((BAN_TIME-conlai)/BAN_TIME*10); done=max(0,min(10,done))
    bar=EMO_SQ_G*done+EMO_SQ_W*(10-done)
    st=EMO_LOCK+" CHOT SO - Khong dat them!" if locked else EMO_GREEN+" Dang nhan cuoc"
    e=discord.Embed(title=EMO_DICE+" TAI XIU CHUNG",description=st,color=0xffd700)
    e.add_field(name=EMO_CLOCK+" Con lai",value="**"+str(max(0,conlai))+"s**\n"+bar,inline=False)
    e.add_field(name=EMO_RED+" TAI",value=str(dt)+" nguoi\n"+EMO_MONEY+" "+fmt(tt),inline=True)
    e.add_field(name=EMO_BLUE+" XIU",value=str(dx)+" nguoi\n"+EMO_MONEY+" "+fmt(tx),inline=True)
    return e

def kq_embed(a,b,c,tong,kq,kn,bets):
    col=0x00ff00 if kn=="T" else 0x0099ff if kn=="X" else 0xff0000
    e=discord.Embed(title=EMO_DICE+" KET QUA: "+str(a)+"-"+str(b)+"-"+str(c),description="### Tong "+str(tong)+" -> "+kq.upper(),color=col)
    th=[];thua=[]
    for uid,inf in bets.items():
        win=(kn!="B") and (inf["chon"]==("tai" if kn=="T" else "xiu"))
        if win: th.append(EMO_OK+" <@"+uid+"> +"+fmt(inf["tien"]))
        else: thua.append(EMO_NO+" <@"+uid+"> -"+fmt(inf["tien"]))
    if th: e.add_field(name="Thang ("+str(len(th))+")",value="\n".join(th[:20]),inline=False)
    if thua: e.add_field(name="Thua ("+str(len(thua))+")",value="\n".join(thua[:20]),inline=False)
    e.add_field(name=EMO_CHART+" Cau",value=" ".join(cau_chung[-10:]),inline=False)
    return e

async def get_ch(cid):
    c=bot.get_channel(cid)
    if c: return c
    try: return await bot.fetch_channel(cid)
    except: return None

async def update_ban(gid):
    s=sessions.get(gid)
    if not s: return
    try:
        ch=await get_ch(s["channel_id"])
        if not ch: return
        msg=await ch.fetch_message(s["msg_id"])
        cl=max(0,int(s["end_time"]-time.time()))
        await msg.edit(content=None,embed=ban_embed(cl,s["bets"],locked=cl<=5))
    except Exception as e: print("update loi",e,flush=True)

async def chay_ban(gid):
    while True:
        await asyncio.sleep(1)
        s=sessions.get(gid)
        if not s: return
        if time.time()>=s["end_time"]: break
        await update_ban(gid)
    s=sessions.pop(gid,None); ban_tasks.pop(gid,None)
    if not s: return
    ch=await get_ch(s["channel_id"])
    if not ch: return
    bets=s["bets"]
    if not bets:
        try:
            m=await ch.fetch_message(s["msg_id"]); await m.edit(content=EMO_HOUR+" Het gio, khong ai dat!",embed=None)
        except: await ch.send(EMO_HOUR+" Het gio, khong ai dat!")
        await asyncio.sleep(5)
        await auto_moban(gid)
        return
    a,b,c,tong,kn,kq=roll(cau_chung); cau_chung.append(kn); cau_history.append(kn)
    for uid,inf in bets.items():
        if kn!="B" and inf["chon"]==("tai" if kn=="T" else "xiu"):
            balances[uid]=get_bal(uid)+inf["tien"]*2
    save()
    emb=kq_embed(a,b,c,tong,kq,kn,bets)
    try:
        m=await ch.fetch_message(s["msg_id"]); await m.edit(content=None,embed=emb)
    except: await ch.send(embed=emb)
    await asyncio.sleep(5)
    await auto_moban(gid)

async def auto_moban(gid):
    try:
        ch=await get_ch(AUTO_BAN_CHANNEL_ID)
        if not ch: return
        if gid in sessions: return
        msg=await ch.send(embed=ban_embed(BAN_TIME,{},False))
        sessions[gid]={"bets":{},"channel_id":ch.id,"msg_id":msg.id,"end_time":time.time()+BAN_TIME}
        ban_tasks[gid]=asyncio.create_task(chay_ban(gid))
    except Exception as e: print("auto_moban loi",e,flush=True)

@tasks.loop(minutes=1)
async def auto_ban_loop():
    for g in list(bot.guilds):
        if g.id not in sessions and g.id not in ban_tasks:
            await auto_moban(g.id)
@auto_ban_loop.before_loop
async def _abl(): await bot.wait_until_ready()

GOI=["all","1k","10k","100k","1m","10m","100m","1b","10b","1t"]
async def auto_tien(i,cur):
    cur=cur.lower().strip(); out=[]
    for v in GOI:
        if cur in v or not cur: out.append(app_commands.Choice(name=v,value=v))
    if cur and cur not in GOI:
        try: parse_tien(cur); out.insert(0,app_commands.Choice(name=cur,value=cur))
        except: pass
    return out[:25]

def bxh_text():
    if not vip_balances: return EMO_CUP+" TOP 10 XU VIP\n\nChua co du lieu (doi xu thuong -> xu VIP bang /doixu de len BXH)"
    top=sorted(vip_balances.items(),key=lambda x:x[1],reverse=True)[:10]
    t=EMO_CUP+" TOP 10 XU VIP\n\n"
    for i,(u,b) in enumerate(top): t+=str(i+1)+". <@"+u+"> - "+fmt(b)+" VIP\n"
    return t

@tasks.loop(hours=2)
async def auto_bxh():
    global bxh_msg_id
    try:
        ch=bot.get_channel(BXH_CHANNEL_ID) or await bot.fetch_channel(BXH_CHANNEL_ID)
        t=bxh_text()
        if bxh_msg_id:
            try: await (await ch.fetch_message(bxh_msg_id)).edit(content=t); return
            except: pass
        m=await ch.send(t); bxh_msg_id=m.id; save()
    except Exception as e: print(e,flush=True)
@auto_bxh.before_loop
async def _b(): await bot.wait_until_ready()
@tasks.loop(minutes=1)
async def daily_rs():
    global last_reset_date
    vn=datetime.datetime.utcnow()+datetime.timedelta(hours=7)
    td=vn.strftime("%Y-%m-%d")
    if vn.hour==0 and vn.minute<2 and last_reset_date!=td:
        last_reset_date=td
        top=sorted(vip_balances.items(),key=lambda x:x[1],reverse=True)[:10]
        rewards_given={}
        for i,(u,b) in enumerate(top):
            rw=REWARDS.get(i+1,0)
            if rw>0: rewards_given[u]=rw
        vip_balances.clear()
        for u,rw in rewards_given.items():
            vip_balances[u]=rw
        pending_rewards.clear()
        save()
@tasks.loop(minutes=1)
async def check_tra():
    now=int(time.time()); ch=False
    for u in list(debts.keys()):
        if int(debts.get(u,0))>0:
            vt=int(debts_time.get(u,0))
            if vt and now-vt>=VAY_HAN_GIO*3600 and banned_until.get(u,0)<now:
                banned_until[u]=now+BAN_GIO*3600; debts[u]=0; debts_time.pop(u,None); ch=True
    if ch: save()

@bot.event
async def on_ready():
    print("Online",bot.user,flush=True); await bot.tree.sync()
    if not auto_bxh.is_running(): auto_bxh.start()
    if not daily_rs.is_running(): daily_rs.start()
    if not check_tra.is_running(): check_tra.start()
    if not auto_ban_loop.is_running(): auto_ban_loop.start()

@bot.tree.command(name="datcuoc",description="Dat cuoc vao ban chung")
@app_commands.autocomplete(tien=auto_tien)
@app_commands.choices(lua_chon=[app_commands.Choice(name="Tai",value="tai"),app_commands.Choice(name="Xiu",value="xiu")])
async def datcuoc(interaction:discord.Interaction,tien:str,lua_chon:app_commands.Choice[str]):
    gid=interaction.guild_id; s=sessions.get(gid)
    if not s: await interaction.response.send_message("Chua co ban! Doi bot mo ban moi.",ephemeral=True); return
    if time.time()>=s["end_time"]-5: await interaction.response.send_message(EMO_LOCK+" Da chot so!",ephemeral=True); return
    uid=str(interaction.user.id)
    if banned_until.get(uid,0)>int(time.time()): await interaction.response.send_message("Ban bi ban!",ephemeral=True); return
    bal=get_bal(uid)
    try: p=parse_tien(tien); tv=bal if p=="ALL" else p
    except: await interaction.response.send_message("Tien sai!",ephemeral=True); return
    if tv<=0 or tv>bal: await interaction.response.send_message("Khong du! Co "+fmt(bal),ephemeral=True); return
    chon=lua_chon.value; bets=s["bets"]
    if uid in bets and bets[uid]["chon"]!=chon: await interaction.response.send_message("Da dat cua kia!",ephemeral=True); return
    balances[uid]=bal-tv
    if uid in bets: bets[uid]["tien"]+=tv
    else: bets[uid]={"chon":chon,"tien":tv}
    save()
    await interaction.response.send_message(EMO_OK+" "+fmt(tv)+" vao "+chon.upper(),ephemeral=True)
    await update_ban(gid)

@bot.tree.command(name="taixiu",description="Choi le")
@app_commands.autocomplete(tien=auto_tien)
@app_commands.choices(lua_chon=[app_commands.Choice(name="Tai",value="tai"),app_commands.Choice(name="Xiu",value="xiu")])
async def taixiu(interaction:discord.Interaction,tien:str,lua_chon:app_commands.Choice[str]):
    await interaction.response.defer()
    uid=str(interaction.user.id)
    if banned_until.get(uid,0)>int(time.time()): await interaction.followup.send("Ban bi ban!"); return
    bal=get_bal(uid)
    try: p=parse_tien(tien); tv=bal if p=="ALL" else p
    except: await interaction.followup.send("Tien sai!"); return
    if tv>bal: await interaction.followup.send("Khong du! Co "+fmt(bal)); return
    chon=lua_chon.value
    a,b,c,tong,kn,kq=roll(cau_le)
    win=(kn!="B") and (chon==("tai" if kn=="T" else "xiu"))
    cau_le.append(kn); cau_history.append(kn); balances[uid]=bal+tv if win else bal-tv; save()
    icon=EMO_OK+" THANG" if win else EMO_NO+" THUA"
    await interaction.followup.send(EMO_DICE+" "+str(a)+"-"+str(b)+"-"+str(c)+" ("+str(tong)+") => "+kq+"\n"+icon+" "+fmt(tv)+"\n"+EMO_MONEY+" Con: "+fmt(balances[uid]))

@bot.tree.command(name="soxu",description="Xem xu + no")
async def soxu(interaction:discord.Interaction):
    uid=str(interaction.user.id)
    await interaction.response.send_message(EMO_MONEY+" Xu thuong: "+fmt(get_bal(uid))+"\n"+EMO_GEM+" Xu VIP: "+fmt(get_vip(uid))+"\n"+EMO_FLY+" No: "+fmt(int(debts.get(uid,0))))
@bot.tree.command(name="nhanxu",description="Nhan 50k/24h")
async def nhanxu(interaction:discord.Interaction):
    uid=str(interaction.user.id); now=int(time.time())
    if now-last_claim.get(uid,0)<86400: await interaction.response.send_message(EMO_CLOCK+" Chua du 24h!",ephemeral=True); return
    last_claim[uid]=now; balances[uid]=get_bal(uid)+50000; save()
    await interaction.response.send_message(EMO_GIFT+" +50k! Co "+fmt(balances[uid]))
@bot.tree.command(name="chuyentien",description="Chuyen xu")
async def chuyentien(interaction:discord.Interaction,nguoi:discord.Member,tien:str):
    await interaction.response.defer()
    try: tv=parse_tien(tien)
    except: await interaction.followup.send("Tien sai!"); return
    uid=str(interaction.user.id); bal=get_bal(uid)
    if tv<=0 or tv>bal: await interaction.followup.send("Khong du!"); return
    balances[uid]=bal-tv; balances[str(nguoi.id)]=get_bal(str(nguoi.id))+tv; save()
    await interaction.followup.send(EMO_OK+" Chuyen "+fmt(tv)+" cho "+nguoi.mention)
@bot.tree.command(name="vayxu",description="Vay toi da 2M/ngay")
async def vayxu(interaction:discord.Interaction,tien:str):
    await interaction.response.defer(); uid=str(interaction.user.id); now=int(time.time())
    try: tv=parse_tien(tien)
    except: await interaction.followup.send("Tien sai!"); return
    logs=[x for x in vay_log.get(uid,[]) if now-x[0]<86400]
    if sum(x[1] for x in logs)+tv>VAY_LIMIT_NGAY: await interaction.followup.send("Qua 2M/ngay!"); return
    logs.append([now,tv]); vay_log[uid]=logs
    if int(debts.get(uid,0))==0: debts_time[uid]=now
    balances[uid]=get_bal(uid)+tv; debts[uid]=int(debts.get(uid,0))+tv; save()
    await interaction.followup.send("Vay "+fmt(tv)+"! No: "+fmt(debts[uid]))
@bot.tree.command(name="trano",description="Tra no")
async def trano(interaction:discord.Interaction,tien:str):
    await interaction.response.defer(); uid=str(interaction.user.id); d=int(debts.get(uid,0))
    if d<=0: await interaction.followup.send("Khong no!"); return
    try: p=parse_tien(tien); tv=d if p=="ALL" else p
    except: await interaction.followup.send("Tien sai!"); return
    tv=min(tv,d)
    if get_bal(uid)<tv:
        banned_until[uid]=int(time.time())+BAN_GIO*3600; debts[uid]=0; debts_time.pop(uid,None); save()
        await interaction.followup.send(EMO_BAN+" Khong du! Ban "+str(BAN_GIO)+"h!"); return
    balances[uid]=get_bal(uid)-tv; debts[uid]=d-tv
    if debts[uid]==0: debts_time.pop(uid,None)
    save(); await interaction.followup.send("Tra "+fmt(tv)+"! Con "+fmt(debts[uid]))
@bot.tree.command(name="cau",description="Xem cau choi le")
async def cau(interaction:discord.Interaction):
    await interaction.response.send_message(" ".join(cau_le[-20:]) if cau_le else "Chua co")
@bot.tree.command(name="cauchung",description="Xem cau dat cuoc chung ca server")
async def cauchung(interaction:discord.Interaction):
    await interaction.response.send_message(" ".join(cau_chung[-20:]) if cau_chung else "Chua co")
@bot.tree.command(name="bxh",description="Top 10")
async def bxh(interaction:discord.Interaction):
    await interaction.response.defer(); await interaction.followup.send(bxh_text())
@bot.tree.command(name="doixu",description="Doi 10 xu thuong = 1 xu VIP (len BXH)")
@app_commands.autocomplete(tien=auto_tien)
async def doixu(interaction:discord.Interaction,tien:str):
    await interaction.response.defer(ephemeral=True)
    uid=str(interaction.user.id)
    bal=get_bal(uid)
    try: p=parse_tien(tien); tv=bal if p=="ALL" else p
    except: await interaction.followup.send("Tien sai!",ephemeral=True); return
    if tv<10: await interaction.followup.send(EMO_NO+" Toi thieu 10 xu thuong!",ephemeral=True); return
    if tv>bal: await interaction.followup.send("Khong du! Co "+fmt(bal),ephemeral=True); return
    vip_gain=tv//10
    if vip_gain<=0: await interaction.followup.send(EMO_NO+" So xu khong du doi!",ephemeral=True); return
    cost=vip_gain*10
    balances[uid]=bal-cost; vip_balances[uid]=get_vip(uid)+vip_gain; save()
    await interaction.followup.send(EMO_OK+" Doi "+fmt(cost)+" xu thuong -> "+fmt(vip_gain)+" xu VIP!\n"+EMO_GEM+" Xu VIP: "+fmt(get_vip(uid)),ephemeral=True)
@bot.tree.command(name="congxu",description="Cong xu Admin")
async def congxu(interaction:discord.Interaction,nguoi:discord.Member,tien:str):
    if str(interaction.user.id) not in ADMIN_IDS: await interaction.response.send_message("No!",ephemeral=True); return
    tv=parse_tien(tien); balances[str(nguoi.id)]=get_bal(str(nguoi.id))+tv; save()
    await interaction.response.send_message("Cong "+fmt(tv)+" cho "+nguoi.mention)
@bot.tree.command(name="bocam",description="Go ban Admin")
async def bocam(interaction:discord.Interaction,nguoi:discord.Member):
    if str(interaction.user.id) not in ADMIN_IDS: return
    banned_until.pop(str(nguoi.id),None); save()
    await interaction.response.send_message("Go ban "+nguoi.mention)

if __name__=="__main__":
    if not TOKEN: print("Thieu TOKEN",flush=True); sys.exit(1)
    bot.run(TOKEN)
