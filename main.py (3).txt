import discord, random, json, os, re, time, datetime, sys, asyncio, traceback
from discord.ext import commands, tasks
from discord import app_commands


print("=== BOT DANG KHOI DONG ===", flush=True)
try:
    import aiohttp
    print("aiohttp OK", flush=True)
except Exception as e:
    print("CANH BAO: thieu aiohttp:", e, flush=True)

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("DISCORD_BOT_TOKEN") or os.getenv("TOKEN")
print("Token tim thay:", "CO" if TOKEN else "KHONG", flush=True)
print("Lib version:", getattr(discord, "__version__", "khong ro"), flush=True)
print("Python:", sys.version.split()[0], flush=True)
INSTANCE_ID="%06x"%random.getrandbits(24)
print("Instance ID:",INSTANCE_ID,flush=True)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ADMIN_IDS = {"979510239429623070","1470776105333162071","979774357205315635","1279776338160652300"}
GOLD_ADMIN_IDS = {"1279776338160652300","979774357205315635","1470776105333162071"}
BXH_CHANNEL_ID = 1553764675626467388
AUTO_BAN_CHANNEL_ID = 1553493424454242364
VAY_LIMIT_NGAY = 2000000
VAY_HAN_GIO = 20
BAN_GIO = 3
BAN_TIME = 40
STALE_AFTER = BAN_TIME + 30
EGG_TIERS = {1:{"name":"Lỏ","xu":200000,"vang":None},2:{"name":"Bình thường","xu":500000,"vang":None},3:{"name":"Tạm","xu":1200000,"vang":None},4:{"name":"Ổn","xu":5000000,"vang":None},5:{"name":"VIP","xu":30000000,"vang":None},6:{"name":"Siêu VIP","xu":None,"vang":200}}
TIER_STATS = {1:(1000,8000,5000,20000,800,6000),2:(8000,30000,20000,60000,6000,22000),3:(30000,90000,60000,150000,22000,70000),4:(90000,250000,150000,280000,70000,180000),5:(250000,600000,280000,420000,180000,400000),6:(600000,1000000,420000,500000,400000,750000)}
DAME_MAX = 1000000; THU_MAX = 500000; SPD_MAX = 750000
VANG_RATE = 1000000000
FEED_COST = 20000
FEED_EXP = 15
DINO_MAX_LV = 100
BREED_COST = 1000000
BREED_MIN_LV = 5
BREED_CD = 1800

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)

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
debts={}; vay_log={}; banned_until={}; debts_time={}; vip_balances={}
bxh_msg_id=None
gold_balances={}; dinos={}; dino_eggs={}; next_dino_id=1
breed_cd={}
sessions={}; ban_tasks={}; opening=set(); saved_sessions={}

def save():
    try:
        with open(DB,"w",encoding="utf-8") as f:
            json.dump({"balances":balances,"cau":cau_history[-30:],"cau_le":cau_le[-30:],"cau_chung":cau_chung[-30:],"last":last_claim,"debts":debts,"vay_log":vay_log,"banned":banned_until,"debts_time":debts_time,"bxh_msg":bxh_msg_id,"vip":vip_balances,"vang":gold_balances,"dinos":dinos,"eggs":dino_eggs,"dino_id":next_dino_id,"bxh_ch":BXH_CHANNEL_ID,"ban_ch":AUTO_BAN_CHANNEL_ID,"sessions":{str(g):{"bets":x["bets"],"channel_id":x["channel_id"],"msg_id":x["msg_id"],"end_time":x["end_time"]} for g,x in sessions.items()}},f,ensure_ascii=False)
    except: pass

def load():
    global balances,cau_history,cau_le,cau_chung,last_claim,debts,vay_log,banned_until,debts_time,bxh_msg_id,vip_balances,saved_sessions,BXH_CHANNEL_ID,AUTO_BAN_CHANNEL_ID,gold_balances,dinos,dino_eggs,next_dino_id
    if os.path.exists(DB):
        try:
            d=json.load(open(DB,encoding="utf-8"))
            balances=d.get("balances",{}); cau_history=d.get("cau",[]); cau_le=d.get("cau_le",[]); cau_chung=d.get("cau_chung",[])
            last_claim=d.get("last",{}); debts=d.get("debts",{})
            vay_log=d.get("vay_log",{}); banned_until=d.get("banned",{})
            debts_time=d.get("debts_time",{}); bxh_msg_id=d.get("bxh_msg"); vip_balances=d.get("vip",{}); saved_sessions=d.get("sessions",{}); BXH_CHANNEL_ID=d.get("bxh_ch",BXH_CHANNEL_ID); AUTO_BAN_CHANNEL_ID=d.get("ban_ch",AUTO_BAN_CHANNEL_ID); gold_balances=d.get("vang",{}); dinos=d.get("dinos",{}); dino_eggs=d.get("eggs",{}); next_dino_id=d.get("dino_id",1)
        except: pass
load()
print("Load du lieu xong", flush=True)

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
    streak=0; last=hist[-1] if hist else None
    if last in ("T","X"):
        for h in reversed(hist):
            if h==last: streak+=1
            else: break
    if streak>=random.randint(5,7):
        tg="xiu" if last=="T" else "tai"
    else:
        tg="tai" if last=="T" and random.random()<0.4 else "xiu" if last=="X" and random.random()<0.4 else random.choice(["tai","xiu"])
    a,b,c,t=rf(tg)
    return a,b,c,t,"T" if tg=="tai" else "X","Tai" if tg=="tai" else "Xiu"

EMO_DICE="\U0001f3b2"; EMO_LOCK="\U0001f512"; EMO_GREEN="\U0001f7e2"; EMO_SQ_G="\U0001f7e9"; EMO_SQ_W="\u2b1c"
EMO_CLOCK="\u23f3"; EMO_RED="\U0001f534"; EMO_BLUE="\U0001f535"; EMO_MONEY="\U0001f4b0"
EMO_OK="\u2705"; EMO_NO="\u274c"; EMO_CHART="\U0001f4c8"; EMO_CUP="\U0001f3c6"
EMO_GIFT="\U0001f381"; EMO_GEM="\U0001f48e"; EMO_FLY="\U0001f4b8"; EMO_BAN="\U0001f6ab"; EMO_HOUR="\u23f0"
TABLE_TITLE=EMO_DICE+" TAI XIU CHUNG"

def ban_embed(conlai,bets,locked=False):
    tt=sum(v["tien"] for v in bets.values() if v["chon"]=="tai")
    tx=sum(v["tien"] for v in bets.values() if v["chon"]=="xiu")
    dt=sum(1 for v in bets.values() if v["chon"]=="tai")
    dx=sum(1 for v in bets.values() if v["chon"]=="xiu")
    done=int((BAN_TIME-conlai)/BAN_TIME*10); done=max(0,min(10,done))
    bar=EMO_SQ_G*done+EMO_SQ_W*(10-done)
    st=EMO_LOCK+" CHOT SO - Khong dat them!" if locked else EMO_GREEN+" Dang nhan cuoc"
    e=discord.Embed(title=TABLE_TITLE,description=st,color=0xffd700)
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

async def tim_ban_dang_chay(ch):
    try:
        async for m in ch.history(limit=8):
            if bot.user and m.author.id!=bot.user.id: continue
            for em in m.embeds:
                if em.title==TABLE_TITLE and em.description and ("Dang nhan cuoc" in em.description or "CHOT SO" in em.description):
                    age=(utcnow()-m.created_at).total_seconds()
                    cl=None
                    for f in em.fields:
                        if "Con lai" in (f.name or ""):
                            mm=re.search(r"\*\*(\d+)s\*\*", f.value or "")
                            if mm: cl=int(mm.group(1))
                    return m, cl, age
    except Exception as e: print("tim_ban loi",e,flush=True)
    return None, None, None

async def tiep_quan_ban(gid,ch,msg,conlai):
    if gid in sessions or gid in ban_tasks: return sessions.get(gid)
    for g,s in list(sessions.items()):
        if s.get("msg_id")==msg.id and s.get("channel_id")==ch.id:
            sessions[gid]=s
            print("Dung chung session ban voi gid",g,flush=True)
            return s
    sessions[gid]={"bets":{},"channel_id":ch.id,"msg_id":msg.id,"end_time":time.time()+max(5,conlai or 30)}
    ban_tasks[gid]=asyncio.create_task(chay_ban(gid))
    print("Tiep quan ban cu, con lai",conlai,flush=True)
    return sessions[gid]

async def restore_sessions():
    try:
        now=time.time()
        for gs,s in list(saved_sessions.items()):
            try:
                gid=int(gs)
                if gid in sessions or gid in ban_tasks: continue
                if s.get("end_time",0)<=now: continue
                shared=None
                for g2,s2 in list(sessions.items()):
                    if s2.get("msg_id")==s.get("msg_id"):
                        shared=s2; break
                if shared is not None:
                    sessions[gid]=shared
                    print("Khoi phuc: gid",gid,"dung chung session",flush=True)
                    continue
                ch=await get_ch(s["channel_id"])
                if not ch: continue
                try: await ch.fetch_message(s["msg_id"])
                except: continue
                sessions[gid]={"bets":s.get("bets",{}),"channel_id":s["channel_id"],"msg_id":s["msg_id"],"end_time":s["end_time"]}
                ban_tasks[gid]=asyncio.create_task(chay_ban(gid))
                print("Khoi phuc ban dang do: gid",gid,"-",len(sessions[gid]["bets"]),"cuoc",flush=True)
            except Exception as e: print("restore 1 session loi",e,flush=True)
        saved_sessions.clear()
    except Exception as e: print("restore_sessions loi",e,flush=True)


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
    try:
        while True:
            await asyncio.sleep(1)
            s=sessions.get(gid)
            if not s: return
            if time.time()>=s["end_time"]: break
            await update_ban(gid)
        s=sessions.get(gid)
        if not s: return
        ch=await get_ch(s["channel_id"])
        if not ch:
            sessions.pop(gid,None); ban_tasks.pop(gid,None); return
        bets=s["bets"]
        if not bets:
            try:
                m=await ch.fetch_message(s["msg_id"]); await m.edit(content=EMO_HOUR+" Het gio, khong ai dat!",embed=None)
            except: await ch.send(EMO_HOUR+" Het gio, khong ai dat!")
        else:
            a,b,c,tong,kn,kq=roll(cau_chung); cau_chung.append(kn); cau_history.append(kn)
            for uid,inf in bets.items():
                if kn!="B" and inf["chon"]==("tai" if kn=="T" else "xiu"):
                    win_amt=inf["tien"]*2
                    balances[uid]=get_bal(uid)+win_amt
                    print("Tra thuong ban chung:",uid,"+"+fmt(win_amt),flush=True)
            save()
            emb=kq_embed(a,b,c,tong,kq,kn,bets)
            try:
                m=await ch.fetch_message(s["msg_id"]); await m.edit(content=None,embed=emb)
            except: await ch.send(embed=emb)
        await asyncio.sleep(5)
    except Exception: print("chay_ban loi",traceback.format_exc(),flush=True)
    finally:
        s_done=sessions.get(gid)
        for g in [g for g,s in list(sessions.items()) if s_done is not None and s is s_done]:
            sessions.pop(g,None); ban_tasks.pop(g,None)
        save()
        try:
            await auto_moban(gid)
        except Exception: print("auto_moban sau ban loi",traceback.format_exc(),flush=True)

async def auto_moban(gid):
    if gid in sessions or gid in opening or gid in ban_tasks: return
    opening.add(gid)
    try:
        ch=await get_ch(AUTO_BAN_CHANNEL_ID)
        if not ch:
            print("Khong tim thay kenh ban chung:", AUTO_BAN_CHANNEL_ID, flush=True); return
        if gid in sessions: return
        m, cl, age = await tim_ban_dang_chay(ch)
        if m and age < STALE_AFTER:
            print("Phat hien ban dang chay -> tiep quan (khong mo moi)", flush=True)
            await tiep_quan_ban(gid,ch,m,cl); return
        if m:
            try: await m.delete(); print("Xoa ban stale",flush=True)
            except: pass
        await asyncio.sleep(random.uniform(1.0,3.0))
        if gid in sessions or gid in ban_tasks: return
        m2, cl2, age2 = await tim_ban_dang_chay(ch)
        if m2 and age2 < STALE_AFTER:
            print("Ban vua duoc mo boi tien trinh khac -> tiep quan", flush=True)
            await tiep_quan_ban(gid,ch,m2,cl2); return
        msg=await ch.send(embed=ban_embed(BAN_TIME,{},False))
        sessions[gid]={"bets":{},"channel_id":ch.id,"msg_id":msg.id,"end_time":time.time()+BAN_TIME}
        ban_tasks[gid]=asyncio.create_task(chay_ban(gid))
        print("Da mo ban moi [instance "+INSTANCE_ID+"]", flush=True)
    except Exception as e: print("auto_moban loi: kenh "+str(AUTO_BAN_CHANNEL_ID)+" khong ton tai ("+str(e)+") -> vao kenh ban moi chay /setkenhban",flush=True)
    finally: opening.discard(gid)

@tasks.loop(seconds=30)
async def auto_ban_loop():
    try:
        for g in list(bot.guilds):
            if g.id not in sessions and g.id not in ban_tasks and g.id not in opening:
                await auto_moban(g.id)
    except Exception: print("auto_ban_loop loi",traceback.format_exc(),flush=True)
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
    head=EMO_CUP+" TOP 20 NGUOI GIAU NHAT\n\n"
    if not balances:
        t=head+"Chua co du lieu\n"
    else:
        top=sorted(balances.items(),key=lambda x:int(x[1]),reverse=True)[:20]
        t=head
        for i,(u,b) in enumerate(top):
            t+=str(i+1)+". <@"+str(u)+"> - "+fmt(int(b))+"\n"
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
    except Exception as e: print("auto_bxh loi: kenh "+str(BXH_CHANNEL_ID)+" khong ton tai ("+str(e)+") -> vao kenh BXH moi chay /setkenhbxh",flush=True)
@auto_bxh.before_loop
async def _b(): await bot.wait_until_ready()

@tasks.loop(minutes=1)
async def check_tra():
    try:
        now=int(time.time()); ch=False
        for u in list(debts.keys()):
            if int(debts.get(u,0))>0:
                vt=int(debts_time.get(u,0))
                if vt and now-vt>=VAY_HAN_GIO*3600 and banned_until.get(u,0)<now:
                    banned_until[u]=now+BAN_GIO*3600; debts[u]=0; debts_time.pop(u,None); ch=True
        if ch: save()
    except Exception as e: print("check_tra loi",e,flush=True)


# ================= HỆ THỐNG KHỦNG LONG =================
def get_vang(uid):
    return int(gold_balances.get(str(uid),0))

def tier_name(t):
    return EGG_TIERS[int(t)]["name"]

def dino_by_id(uid,did):
    try: did=int(did)
    except: return None
    for d in dinos.get(str(uid),[]):
        if int(d.get("id",-1))==did: return d
    return None

def roll_stat(lo,hi):
    r=random.random(); span=hi-lo
    if r<0.55: return random.randint(lo,lo+span//2)
    elif r<0.85: return random.randint(lo+span//2,hi)
    else: return random.randint(hi-span//5,hi)

def make_dino(tier):
    global next_dino_id
    t=int(tier)
    dlo,dhi,tlo,thi,slo,shi=TIER_STATS[t]
    d={"id":next_dino_id,"tier":t,"str":roll_stat(dlo,dhi),"sta":roll_stat(tlo,thi),"spd":roll_stat(slo,shi),"level":1,"exp":0}
    next_dino_id+=1
    return d

def dino_power(d):
    return d["str"]*1.0+d["sta"]*0.5+d["spd"]*0.3+d["level"]*500

def feed_dino(d):
    d["exp"]=int(d.get("exp",0))+FEED_EXP
    ups=0
    while d["level"]<DINO_MAX_LV and d["exp"]>=d["level"]*100:
        d["exp"]-=d["level"]*100; d["level"]+=1
        dlo,dhi,tlo,thi,slo,shi=TIER_STATS[int(d["tier"])]
        d["str"]=min(DAME_MAX,d["str"]+random.randint(int(dhi*0.005),int(dhi*0.015)))
        d["sta"]=min(THU_MAX,d["sta"]+random.randint(int(thi*0.005),int(thi*0.015)))
        d["spd"]=min(SPD_MAX,d["spd"]+random.randint(int(shi*0.005),int(shi*0.015)))
        ups+=1
    return ups

try:
    _mx=0
    for _lst in dinos.values():
        for _d in _lst: _mx=max(_mx,int(_d.get("id",0)))
    if next_dino_id<=_mx: next_dino_id=_mx+1
except: pass

async def auto_dino(interaction,current):
    uid=str(interaction.user.id); out=[]
    for d in dinos.get(uid,[]):
        if not current or current in str(d["id"]):
            out.append(app_commands.Choice(name="#%d %s Lv%d (S:%d)"%(d["id"],tier_name(d["tier"]),d["level"],int(dino_power(d))),value=str(d["id"])))
        if len(out)>=25: break
    return out

async def auto_egg(interaction,current):
    uid=str(interaction.user.id); out=[]
    for i,t in enumerate(dino_eggs.get(uid,[])):
        out.append(app_commands.Choice(name="Trứng #%d: %s"%(i+1,tier_name(t)),value=str(i)))
        if len(out)>=25: break
    return out

async def auto_eggtier(interaction,current):
    out=[]
    for t,info in EGG_TIERS.items():
        price=fmt(info["xu"])+" xu" if info["xu"] else fmt(info["vang"])+" vàng"
        out.append(app_commands.Choice(name="%d. %s (%s)"%(t,info["name"],price),value=str(t)))
    return out

@bot.tree.command(name="muatrung",description="Mua trứng khủng long")
@app_commands.autocomplete(loai=auto_eggtier)
async def muatrung(interaction:discord.Interaction,loai:str):
    await interaction.response.defer(ephemeral=True)
    t=int(loai); info=EGG_TIERS[t]; uid=str(interaction.user.id)
    if info["vang"] and not info["xu"]:
        cost=info["vang"]
        if get_vang(uid)<cost:
            await interaction.followup.send("Không đủ xu vàng! Có %s"%fmt(get_vang(uid)),ephemeral=True); return
        gold_balances[uid]=get_vang(uid)-cost; cur="vàng"
    else:
        cost=info["xu"]
        if get_bal(uid)<cost:
            await interaction.followup.send("Không đủ xu! Có %s"%fmt(get_bal(uid)),ephemeral=True); return
        balances[uid]=get_bal(uid)-cost; cur="xu"
    dino_eggs.setdefault(uid,[]).append(t); save()
    await interaction.followup.send("🥚 Đã mua trứng %s bằng %s %s!"%(info["name"],fmt(cost),cur),ephemeral=True)

@bot.tree.command(name="aptrung",description="Ấp trứng khủng long")
@app_commands.autocomplete(trung=auto_egg)
async def aptrung(interaction:discord.Interaction,trung:str=None):
    await interaction.response.defer(ephemeral=True)
    uid=str(interaction.user.id); lst=dino_eggs.get(uid,[])
    if not lst:
        await interaction.followup.send("Bạn chưa có trứng nào! Dùng /muatrung để mua.",ephemeral=True); return
    idx=int(trung) if trung and str(trung).isdigit() else 0
    if idx<0 or idx>=len(lst):
        await interaction.followup.send("Trứng không tồn tại!",ephemeral=True); return
    if len(dinos.get(uid,[]))>=20:
        await interaction.followup.send("Kho khủng long đã đầy (tối đa 20 con)!",ephemeral=True); return
    t=lst.pop(idx); d=make_dino(t)
    dinos.setdefault(uid,[]).append(d); save()
    await interaction.followup.send("🦖 Trứng %s đã nở!\n#%d | 💪%d 🏃%d 🛡%d"%(tier_name(t),d["id"],d["str"],d["spd"],d["sta"]),ephemeral=True)

@bot.tree.command(name="khunglong",description="Xem khủng long của bạn")
async def khunglong(interaction:discord.Interaction):
    uid=str(interaction.user.id); lst=dinos.get(uid,[])
    if not lst:
        await interaction.response.send_message("Bạn chưa có khủng long nào! Dùng /muatrung để mua trứng.",ephemeral=True); return
    lines=["🦖 KHỦNG LONG CỦA BẠN (%d):"%len(lst)]
    for d in lst:
        lines.append("#%d | %s | Lv%d (%d/%d exp) | 💪%d 🏃%d 🛡%d | Sức:%d"%(d["id"],tier_name(d["tier"]),d["level"],int(d.get("exp",0)),d["level"]*100,d["str"],d["spd"],d["sta"],int(dino_power(d))))
    await interaction.response.send_message("\n".join(lines)[:1900],ephemeral=True)

@bot.tree.command(name="kho",description="Xem kho trứng và khủng long")
async def kho(interaction:discord.Interaction):
    uid=str(interaction.user.id)
    eggs=dino_eggs.get(uid,[]); ds=dinos.get(uid,[])
    lines=["🎒 KHO CỦA BẠN","🥚 Trứng: %d"%len(eggs)]
    if eggs:
        from collections import Counter
        c=Counter(eggs)
        for t in sorted(c.keys()):
            lines.append("  · %s: %d"%((tier_name(t)),c[t]))
    lines.append("🦖 Khủng long: %d/20"%len(ds))
    if ds:
        from collections import Counter
        c2=Counter(tier_name(d["tier"]) for d in ds)
        for tn in c2:
            lines.append("  · %s: %d"%(tn,c2[tn]))
    lines.append("🪙 Xu vàng: %s"%fmt(get_vang(uid)))
    await interaction.response.send_message("\n".join(lines),ephemeral=True)

@bot.tree.command(name="xoakl",description="Xóa khủng long trong kho")
@app_commands.autocomplete(dino=auto_dino)
async def xoakl(interaction:discord.Interaction,dino:str):
    await interaction.response.defer(ephemeral=True)
    uid=str(interaction.user.id)
    d=dino_by_id(uid,dino)
    if not d:
        await interaction.followup.send("Không tìm thấy khủng long!",ephemeral=True); return
    dinos[uid]=[x for x in dinos.get(uid,[]) if int(x.get("id",-1))!=int(d["id"])]
    save()
    await interaction.followup.send("🗑️ Đã xóa khủng long #%d (%s)!"%(d["id"],tier_name(d["tier"])),ephemeral=True)

@bot.tree.command(name="choan",description="Cho khủng long ăn để lên cấp")
@app_commands.autocomplete(dino=auto_dino)
async def choan(interaction:discord.Interaction,dino:str):
    await interaction.response.defer(ephemeral=True)
    uid=str(interaction.user.id); d=dino_by_id(uid,dino)
    if not d:
        await interaction.followup.send("Không tìm thấy khủng long!",ephemeral=True); return
    if d["level"]>=DINO_MAX_LV:
        await interaction.followup.send("Đã đạt cấp tối đa!",ephemeral=True); return
    if get_bal(uid)<FEED_COST:
        await interaction.followup.send("Không đủ xu! Cần %s"%fmt(FEED_COST),ephemeral=True); return
    balances[uid]=get_bal(uid)-FEED_COST
    ups=feed_dino(d); save()
    msg="🍖 #%d đã ăn! (+%d exp)"%(d["id"],FEED_EXP)
    if ups: msg+="\n🎉 LÊN CẤP %d! Chỉ số tăng!"%d["level"]
    await interaction.followup.send(msg,ephemeral=True)

@bot.tree.command(name="laitao",description="Lai tạo 2 khủng long ra con mạnh hơn")
@app_commands.autocomplete(dino1=auto_dino)
@app_commands.autocomplete(dino2=auto_dino)
async def laitao(interaction:discord.Interaction,dino1:str,dino2:str):
    await interaction.response.defer(ephemeral=True)
    uid=str(interaction.user.id)
    a=dino_by_id(uid,dino1); b=dino_by_id(uid,dino2)
    if not a or not b:
        await interaction.followup.send("Không tìm thấy khủng long!",ephemeral=True); return
    if a["id"]==b["id"]:
        await interaction.followup.send("Phải chọn 2 con khác nhau!",ephemeral=True); return
    if a["level"]<BREED_MIN_LV or b["level"]<BREED_MIN_LV:
        await interaction.followup.send("Cả 2 con phải đạt Lv%d trở lên!"%BREED_MIN_LV,ephemeral=True); return
    now=time.time()
    for did in (a["id"],b["id"]):
        if breed_cd.get((uid,did),0)>now:
            await interaction.followup.send("Khủng long #%d đang hồi sức sau lai tạo!"%did,ephemeral=True); return
    if get_bal(uid)<BREED_COST:
        await interaction.followup.send("Cần %s xu để lai tạo!"%fmt(BREED_COST),ephemeral=True); return
    if len(dinos.get(uid,[]))>=20:
        await interaction.followup.send("Kho khủng long đã đầy (tối đa 20 con)!",ephemeral=True); return
    balances[uid]=get_bal(uid)-BREED_COST
    t=max(a["tier"],b["tier"]); up_msg=""
    if a["tier"]==b["tier"] and t<6 and random.random()<0.25:
        t+=1; up_msg="\n✨ ĐỘT BIẾN: lên hạng %s!"%tier_name(t)
    child={"id":next_dino_id,"tier":t,"level":1,"exp":0,
        "str":min(DAME_MAX,int(max(a["str"],b["str"])*1.15)+random.randint(0,int(max(a["str"],b["str"])*0.02))),
        "sta":min(THU_MAX,int(max(a["sta"],b["sta"])*1.15)+random.randint(0,int(max(a["sta"],b["sta"])*0.02))),
        "spd":min(SPD_MAX,int(max(a["spd"],b["spd"])*1.15)+random.randint(0,int(max(a["spd"],b["spd"])*0.02)))}
    globals()["next_dino_id"]=next_dino_id+1
    dinos.setdefault(uid,[]).append(child)
    breed_cd[(uid,a["id"])]=now+BREED_CD; breed_cd[(uid,b["id"])]=now+BREED_CD
    save()
    await interaction.followup.send("💕 Lai tạo thành công!\n#%d (%s) | 💪%d 🏃%d 🛡%d%s"%(child["id"],tier_name(t),child["str"],child["spd"],child["sta"],up_msg),ephemeral=True)

@bot.tree.command(name="doivang",description="Đổi xu thường thành xu vàng (1B = 1)")
@app_commands.autocomplete(tien=auto_tien)
async def doivang(interaction:discord.Interaction,tien:str):
    await interaction.response.defer(ephemeral=True)
    uid=str(interaction.user.id); bal=get_bal(uid)
    try: p=parse_tien(tien); tv=bal if p=="ALL" else p
    except: await interaction.followup.send("Tiền sai!",ephemeral=True); return
    if tv<=0 or tv>bal: await interaction.followup.send("Không đủ!",ephemeral=True); return
    g=tv//VANG_RATE
    if g<=0:
        await interaction.followup.send("Cần ít nhất %s xu (1B = 1 vàng)!"%fmt(VANG_RATE),ephemeral=True); return
    cost=g*VANG_RATE
    balances[uid]=bal-cost; gold_balances[uid]=get_vang(uid)+g; save()
    await interaction.followup.send("🪙 Đổi %s xu thành %s xu vàng!"%(fmt(cost),fmt(g)),ephemeral=True)

@bot.tree.command(name="banvang",description="Bán xu vàng thành xu thường (1 = 1B)")
async def banvang(interaction:discord.Interaction,so_vang:int):
    await interaction.response.defer(ephemeral=True)
    uid=str(interaction.user.id)
    if so_vang<=0:
        await interaction.followup.send("Số vàng phải > 0!",ephemeral=True); return
    if get_vang(uid)<so_vang:
        await interaction.followup.send("Không đủ xu vàng! Có %s"%fmt(get_vang(uid)),ephemeral=True); return
    gold_balances[uid]=get_vang(uid)-so_vang
    balances[uid]=get_bal(uid)+so_vang*VANG_RATE; save()
    await interaction.followup.send("🪙 Đã bán %s xu vàng thành %s xu thường!"%(fmt(so_vang),fmt(so_vang*VANG_RATE)),ephemeral=True)

@bot.tree.command(name="congvang",description="Cộng xu vàng (ID đặc biệt)")
async def congvang(interaction:discord.Interaction,nguoi:discord.Member,so_luong:int):
    if str(interaction.user.id) not in GOLD_ADMIN_IDS:
        await interaction.response.send_message("No!",ephemeral=True); return
    uid=str(nguoi.id)
    gold_balances[uid]=get_vang(uid)+so_luong; save()
    await interaction.response.send_message("Đã cộng %s xu vàng cho %s"%(fmt(so_luong),nguoi.mention),ephemeral=True)



# ================= PVP KHỦNG LONG =================
PVP_MIN_BET = 500000
PVP_EXPIRE_SEC = 120
pvp_challenges = {}

async def run_pvp_battle(ch,chal,b_dino):
    a_dino=chal["a_dino"]; a_uid=chal["a_uid"]; b_uid=chal["b_uid"]
    a_w=b_w=0; lines=[]
    for r in range(1,4):
        sa=dino_power(a_dino)*random.uniform(0.85,1.15)
        sb=dino_power(b_dino)*random.uniform(0.85,1.15)
        if sa>=sb: a_w+=1; w="🔵 A"
        else: b_w+=1; w="🔴 B"
        lines.append("Ván %d: %d - %d → %s thắng"%(r,int(sa),int(sb),w))
        if a_w==2 or b_w==2: break
    winner=a_uid if a_w>b_w else b_uid
    pot=chal["bet"]*2
    balances[winner]=get_bal(winner)+pot; save()
    desc="🔵 <@%s> (#%d %s) VS 🔴 <@%s> (#%d %s)\n\n%s\n\n🏆 <@%s> THẮNG! Nhận %s xu!"%(a_uid,a_dino["id"],tier_name(a_dino["tier"]),b_uid,b_dino["id"],tier_name(b_dino["tier"]),"\n".join(lines),winner,fmt(pot))
    try: await ch.send(embed=discord.Embed(title="⚔️ KẾT QUẢ PVP",description=desc,color=0xffd700))
    except: pass

@tasks.loop(seconds=30)
async def pvp_loop():
    try:
        now=time.time(); changed=False
        for ch_id in list(pvp_challenges.keys()):
            chal=pvp_challenges[ch_id]
            if now>chal["expires"]:
                a_uid=chal["a_uid"]
                balances[a_uid]=get_bal(a_uid)+chal["bet"]
                del pvp_challenges[ch_id]; changed=True
                print("PVP het han, hoan tien",flush=True)
        if changed: save()
    except Exception as e: print("pvp_loop loi",e,flush=True)

@bot.tree.command(name="pvp",description="Thách đấu khủng long PVP (thắng nhận tất cả)")
@app_commands.autocomplete(dino=auto_dino)
@app_commands.autocomplete(tien=auto_tien)
async def pvp(interaction:discord.Interaction,doithu:discord.Member,dino:str,tien:str):
    await interaction.response.defer()
    a_uid=str(interaction.user.id); b_uid=str(doithu.id); ch_id=interaction.channel_id
    if a_uid==b_uid:
        await interaction.followup.send("Không thể tự thách đấu chính mình!"); return
    if doithu.bot:
        await interaction.followup.send("Không thể thách đấu bot!"); return
    if ch_id in pvp_challenges:
        await interaction.followup.send("Kênh này đang có trận PVP chờ!"); return
    d=dino_by_id(a_uid,dino)
    if not d:
        await interaction.followup.send("Không tìm thấy khủng long!"); return
    try: p=parse_tien(tien); bet=get_bal(a_uid) if p=="ALL" else p
    except: await interaction.followup.send("Tiền sai!"); return
    if bet<PVP_MIN_BET:
        await interaction.followup.send("Cược tối thiểu %s xu!"%fmt(PVP_MIN_BET)); return
    if get_bal(a_uid)<bet:
        await interaction.followup.send("Bạn không đủ xu! Có %s"%fmt(get_bal(a_uid))); return
    balances[a_uid]=get_bal(a_uid)-bet
    pvp_challenges[ch_id]={"a_uid":a_uid,"b_uid":b_uid,"a_dino":d,"bet":bet,"expires":time.time()+PVP_EXPIRE_SEC}
    save()
    await interaction.followup.send("⚔️ <@%s> thách đấu <@%s>!\n🦖 #%d (%s) | 💰 Cược: %s xu\n<@%s> dùng /nhanpvp để chấp nhận trong 2 phút!"%(a_uid,b_uid,d["id"],tier_name(d["tier"]),fmt(bet),b_uid))

@bot.tree.command(name="nhanpvp",description="Chấp nhận thách đấu PVP")
@app_commands.autocomplete(dino=auto_dino)
async def nhanpvp(interaction:discord.Interaction,dino:str):
    await interaction.response.defer()
    ch_id=interaction.channel_id; chal=pvp_challenges.get(ch_id)
    if not chal:
        await interaction.followup.send("Không có trận PVP nào đang chờ ở kênh này!"); return
    b_uid=str(interaction.user.id)
    if b_uid!=chal["b_uid"]:
        await interaction.followup.send("Trận này không phải dành cho bạn!"); return
    if time.time()>chal["expires"]:
        a_uid=chal["a_uid"]
        balances[a_uid]=get_bal(a_uid)+chal["bet"]
        del pvp_challenges[ch_id]; save()
        await interaction.followup.send("Trận đấu đã hết hạn, đã hoàn tiền cho người thách đấu!"); return
    d=dino_by_id(b_uid,dino)
    if not d:
        await interaction.followup.send("Không tìm thấy khủng long!"); return
    bet=chal["bet"]
    if get_bal(b_uid)<bet:
        await interaction.followup.send("Bạn không đủ %s xu để chấp nhận!"%fmt(bet)); return
    balances[b_uid]=get_bal(b_uid)-bet
    del pvp_challenges[ch_id]; save()
    await run_pvp_battle(interaction.channel,chal,d)

@bot.event
async def on_ready():
    try:
        print("=== BOT ONLINE:", bot.user, "| instance", INSTANCE_ID, "===", flush=True)
        print("So server:", len(bot.guilds), flush=True)
        try:
            await bot.tree.sync()
            print("Sync lenh global xong", flush=True)
        except Exception as e:
            print("Sync global loi (bo qua):", e, flush=True)
        for g in list(bot.guilds):
            try:
                await bot.tree.sync(guild=g)
            except Exception as e:
                print("Sync guild", g.id, "loi:", e, flush=True)
        print("Sync lenh guild xong", flush=True)
        await restore_sessions()
        if not auto_bxh.is_running(): auto_bxh.start()
        if not check_tra.is_running(): check_tra.start()
        if not auto_ban_loop.is_running(): auto_ban_loop.start()
        if not pvp_loop.is_running(): pvp_loop.start()
        print("Tat ca vong lap da chay", flush=True)
    except Exception: print("on_ready loi",traceback.format_exc(),flush=True)

@bot.tree.error
async def on_app_command_error(interaction:discord.Interaction, error):
    print("LOI LENH:", "".join(traceback.format_exception(type(error), error, error.__traceback__)), flush=True)
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message("Co loi xay ra!", ephemeral=True)
        else:
            await interaction.followup.send("Co loi xay ra!", ephemeral=True)
    except: pass

@bot.event
async def on_error(event, *args, **kwargs):
    print("on_error:", event, traceback.format_exc(), flush=True)

@bot.tree.command(name="datcuoc",description="Dat cuoc vao ban chung")
@app_commands.autocomplete(tien=auto_tien)
@app_commands.choices(lua_chon=[app_commands.Choice(name="Tai",value="tai"),app_commands.Choice(name="Xiu",value="xiu")])
async def datcuoc(interaction:discord.Interaction,tien:str,lua_chon:app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)
    gid=interaction.guild_id; s=sessions.get(gid)
    if not s:
        try:
            ch=await get_ch(AUTO_BAN_CHANNEL_ID)
            if ch:
                m, cl, age = await tim_ban_dang_chay(ch)
                if m and age < STALE_AFTER:
                    s=await tiep_quan_ban(gid,ch,m,cl)
        except Exception as e: print("datcuoc tiep quan loi",e,flush=True)
    if not s: await interaction.followup.send("Chua co ban! Doi bot mo ban moi.",ephemeral=True); return
    if time.time()>=s["end_time"]-5: await interaction.followup.send(EMO_LOCK+" Da chot so!",ephemeral=True); return
    uid=str(interaction.user.id)
    if banned_until.get(uid,0)>int(time.time()): await interaction.followup.send("Ban bi ban!",ephemeral=True); return
    bal=get_bal(uid)
    try: p=parse_tien(tien); tv=bal if p=="ALL" else p
    except: await interaction.followup.send("Tien sai!",ephemeral=True); return
    if tv<=0 or tv>bal: await interaction.followup.send("Khong du! Co "+fmt(bal),ephemeral=True); return
    chon=lua_chon.value; bets=s["bets"]
    if uid in bets and bets[uid]["chon"]!=chon: await interaction.followup.send("Da dat cua kia!",ephemeral=True); return
    balances[uid]=bal-tv
    if uid in bets: bets[uid]["tien"]+=tv
    else: bets[uid]={"chon":chon,"tien":tv}
    save()
    await interaction.followup.send(EMO_OK+" "+fmt(tv)+" vao "+chon.upper(),ephemeral=True)
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
    await interaction.response.send_message(EMO_MONEY+" Xu thuong: "+fmt(get_bal(uid))+"\n"+EMO_GEM+" Ket sat: "+fmt(get_vip(uid))+"\n"+"🪙 Xu vang: "+fmt(get_vang(uid))+"\n"+EMO_FLY+" No: "+fmt(int(debts.get(uid,0))))

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

@bot.tree.command(name="bxh",description="Top 20 nguoi giau nhat")
async def bxh(interaction:discord.Interaction):
    await interaction.response.defer(); await interaction.followup.send(bxh_text())
@bot.tree.command(name="topbxh",description="Xem tat ca nguoi co xu trong ket sat (Admin)")
async def topbxh(interaction:discord.Interaction):
    if str(interaction.user.id) not in ADMIN_IDS: await interaction.response.send_message("No!",ephemeral=True); return
    await interaction.response.defer(ephemeral=True)
    holders=[(u,int(b)) for u,b in vip_balances.items() if int(b)>0]
    if not holders:
        await interaction.followup.send("Chua ai co xu trong ket sat.",ephemeral=True); return
    holders.sort(key=lambda x:x[1],reverse=True)
    total=sum(b for _,b in holders)
    lines=[EMO_CUP+" KET SAT - TAT CA NGUOI SO HUU ("+str(len(holders))+")"]
    for i,(u,b) in enumerate(holders):
        lines.append(str(i+1)+". <@"+str(u)+"> - "+fmt(b))
    lines.append("Tong cong: "+fmt(total))
    chunk=""
    for ln in lines:
        if len(chunk)+len(ln)+1>1900:
            await interaction.followup.send(chunk,ephemeral=True); chunk=""
        chunk+=ln+"\n"
    if chunk: await interaction.followup.send(chunk,ephemeral=True)

@bot.tree.command(name="setkenhban",description="Dat kenh ban chung (Admin) - chay lenh trong kenh muon dat")
async def setkenhban(interaction:discord.Interaction):
    if str(interaction.user.id) not in ADMIN_IDS: await interaction.response.send_message("No!",ephemeral=True); return
    global AUTO_BAN_CHANNEL_ID
    AUTO_BAN_CHANNEL_ID=interaction.channel_id; save()
    await interaction.response.send_message(EMO_OK+" Da dat kenh ban chung: <#"+str(interaction.channel_id)+">")

@bot.tree.command(name="setkenhbxh",description="Dat kenh BXH (Admin) - chay lenh trong kenh muon dat")
async def setkenhbxh(interaction:discord.Interaction):
    if str(interaction.user.id) not in ADMIN_IDS: await interaction.response.send_message("No!",ephemeral=True); return
    global BXH_CHANNEL_ID
    BXH_CHANNEL_ID=interaction.channel_id; save()
    await interaction.response.send_message(EMO_OK+" Da dat kenh BXH: <#"+str(interaction.channel_id)+">")

@bot.tree.command(name="napxu",description="Nap xu thuong vao ket sat (ti le 1:1)")
@app_commands.autocomplete(tien=auto_tien)
async def napxu(interaction:discord.Interaction,tien:str):
    await interaction.response.defer(ephemeral=True)
    uid=str(interaction.user.id); bal=get_bal(uid)
    try: p=parse_tien(tien); tv=bal if p=="ALL" else p
    except: await interaction.followup.send("Tien sai!",ephemeral=True); return
    if tv<=0 or tv>bal: await interaction.followup.send("Khong du! Co "+fmt(bal),ephemeral=True); return
    balances[uid]=bal-tv; vip_balances[uid]=get_vip(uid)+tv; save()
    await interaction.followup.send(EMO_OK+" Da nap "+fmt(tv)+" xu vao ket sat",ephemeral=True)

@bot.tree.command(name="rutxu",description="Rut xu tu ket sat ve xu thuong (ti le 1:1)")
@app_commands.autocomplete(tien=auto_tien)
async def rutxu(interaction:discord.Interaction,tien:str):
    await interaction.response.defer(ephemeral=True)
    uid=str(interaction.user.id); vb=get_vip(uid)
    try: p=parse_tien(tien); tv=vb if p=="ALL" else p
    except: await interaction.followup.send("Tien sai!",ephemeral=True); return
    if tv<=0 or tv>vb: await interaction.followup.send("Ket sat khong du! Co "+fmt(vb),ephemeral=True); return
    vip_balances[uid]=vb-tv; balances[uid]=get_bal(uid)+tv; save()
    await interaction.followup.send(EMO_OK+" Da rut "+fmt(tv)+" xu tu ket sat",ephemeral=True)

@bot.tree.command(name="xoaxu",description="Xoa xu thuong cua ai do (Admin)")
@app_commands.autocomplete(so_xu=auto_tien)
async def xoaxu(interaction:discord.Interaction,nguoi_dung:discord.Member,so_xu:str):
    if str(interaction.user.id) not in ADMIN_IDS: await interaction.response.send_message("No!",ephemeral=True); return
    await interaction.response.defer(ephemeral=True)
    uid=str(nguoi_dung.id); bal=get_bal(uid)
    try: p=parse_tien(so_xu); tv=bal if p=="ALL" else p
    except: await interaction.followup.send("Tien sai!",ephemeral=True); return
    if tv<=0: await interaction.followup.send("So xu phai > 0!",ephemeral=True); return
    tv=min(tv,bal)
    balances[uid]=bal-tv; save()
    await interaction.followup.send(EMO_OK+" Da xoa "+fmt(tv)+" xu thuong cua "+nguoi_dung.mention,ephemeral=True)

@bot.tree.command(name="congxu",description="Cong xu Admin")
async def congxu(interaction:discord.Interaction,nguoi:discord.Member,tien:str):
    if str(interaction.user.id) not in ADMIN_IDS: await interaction.response.send_message("No!",ephemeral=True); return
    tv=parse_tien(tien); balances[str(nguoi.id)]=get_bal(str(nguoi.id))+tv; save()
    await interaction.response.send_message("Cong "+fmt(tv)+" cho "+nguoi.mention)

@bot.tree.command(name="congxuvip",description="Cong xu VIP len BXH (Admin)")
@app_commands.autocomplete(tien=auto_tien)
async def congxuvip(interaction:discord.Interaction,nguoi:discord.Member,tien:str):
    if str(interaction.user.id) not in ADMIN_IDS: await interaction.response.send_message("No!",ephemeral=True); return
    try: tv=parse_tien(tien)
    except: await interaction.response.send_message("Tien sai!",ephemeral=True); return
    if tv<=0: await interaction.response.send_message("Tien phai > 0!",ephemeral=True); return
    uid=str(nguoi.id)
    vip_balances[uid]=get_vip(uid)+tv; save()
    await interaction.response.send_message(EMO_OK+" Cong "+fmt(tv)+" xu VIP cho "+nguoi.mention+"\n"+EMO_GEM+" Xu VIP hien tai: "+fmt(get_vip(uid))+"\n"+EMO_CUP+" Da cap nhat len BXH!")

@bot.tree.command(name="bocam",description="Go ban Admin")
async def bocam(interaction:discord.Interaction,nguoi:discord.Member):
    if str(interaction.user.id) not in ADMIN_IDS: return
    banned_until.pop(str(nguoi.id),None); save()
    await interaction.response.send_message("Go ban "+nguoi.mention)

if __name__=="__main__":
    if not TOKEN:
        print("LOI: Thieu TOKEN! Vao Railway > Variables, them bien TOKEN = token bot.",flush=True)
        sys.exit(1)
    print("Bat dau ket noi...", flush=True)
    try:
        bot.run(TOKEN)
    except Exception:
        print("BOT CRASH:",traceback.format_exc(),flush=True)
        sys.exit(1)
