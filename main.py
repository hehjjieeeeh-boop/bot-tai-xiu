import discord
from discord.ext import commands
import random, json, os
from datetime import datetime, timedelta

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
DATA_FILE = "data.json"
balances = {}
daily_cd = {}

def load():
    global balances, daily_cd
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE,"r",encoding="utf-8") as f:
                d=json.load(f)
                balances=d.get("balances",{})
                daily_cd=d.get("daily",{})
        except: pass
def save():
    try:
        with open(DATA_FILE,"w",encoding="utf-8") as f:
            json.dump({"balances":balances,"daily":daily_cd},f)
    except Exception as e: print("save err",e)

load()
intents=discord.Intents.default()
bot=commands.Bot(command_prefix="!",intents=intents)

@bot.event
async def on_ready():
    print(f"Online {bot.user}")
    try:
        s=await bot.tree.sync()
        print(f"Synced {len(s)}")
    except Exception as e: print("sync err",e)

@bot.tree.command(name="daily",description="Nhan 50000 xu moi ngay")
async def daily(interaction:discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    try:
        uid=str(interaction.user.id)
        now=datetime.now()
        last=daily_cd.get(uid)
        if last:
            lt=datetime.fromisoformat(last)
            if now-lt<timedelta(hours=24):
                rem=timedelta(hours=24)-(now-lt)
                h=int(rem.total_seconds()//3600); m=int((rem.total_seconds()%3600)//60)
                await interaction.followup.send(f"⏰ Đã nhận rồi! Quay lại sau {h}h {m}p")
                return
        balances[uid]=balances.get(uid,0)+50000
        daily_cd[uid]=now.isoformat()
        save()
        await interaction.followup.send(f"🎉 +50.000 xu\n💰 Số dư: {balances[uid]:,} xu")
    except Exception as e:
        print("daily err",e)
        await interaction.followup.send("❌ Lỗi hệ thống, thử lại sau.")

@bot.tree.command(name="sodu",description="Xem so du")
async def sodu(interaction:discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    try:
        uid=str(interaction.user.id)
        await interaction.followup.send(f"💰 Số dư: {balances.get(uid,0):,} xu")
    except Exception as e:
        print(e)
        await interaction.followup.send("❌ Lỗi")
cau_history = []
@bot.tree.command(name="taixiu",description="Cuoc tai xiu")
@discord.app_commands.describe(tien="So tien cuoc",lua_chon="tai hoac xiu")
@discord.app_commands.choices(lua_chon=[discord.app_commands.Choice(name="Tài",value="tai"),discord.app_commands.Choice(name="Xỉu",value="xiu")])
async def taixiu(interaction:discord.Interaction,tien:int,lua_chon:str):
    await interaction.response.defer(ephemeral=False)
    try:
        uid=str(interaction.user.id)
        bal=balances.get(uid,0)
        if tien<=0:
            await interaction.followup.send("❌ Tiền phải >0"); return
        if bal<tien:
            await interaction.followup.send(f"❌ Không đủ tiền! Dư: {bal:,}"); return
        x1,x2,x3=random.randint(1,6),random.randint(1,6),random.randint(1,6)
        tong=x1+x2+x3
        if x1==x2==x3:
            win=False; kq="Bão 🏠"
        else:
            real="xiu" if 4<=tong<=10 else "tai"
            win=(real==lua_chon)
            kq="Xỉu" if real=="xiu" else "Tài"
        cau_history.append(kq)
        if win: balances[uid]=bal+tien
        else: balances[uid]=bal-tien
        save()
        icon="✅" if win else "❌"
        await interaction.followup.send(f"🎲 {x1}-{x2}-{x3} (Tổng {tong}) => {kq}\n{icon} {'Thắng' if win else 'Thua'} {tien:,} xu\n💰 Dư: {balances[uid]:,} xu")
    except Exception as e:
        print("tx err",e)
        await interaction.followup.send("❌ Lỗi, thử lại")


@bot.tree.command(name="chuyentien",description="Chuyen tien cho nguoi khac")
async def chuyentien(interaction:discord.Interaction, nguoi_nhan:discord.Member, so_tien:int):
    await interaction.response.defer(ephemeral=False)
    try:
        uid=str(interaction.user.id); tid=str(nguoi_nhan.id)
        if uid==tid:
            await interaction.followup.send("❌ Không tự chuyển cho mình"); return
        if so_tien<=0:
            await interaction.followup.send("❌ Số tiền phải >0"); return
        bal=balances.get(uid,0)
        if bal<so_tien:
            await interaction.followup.send(f"❌ Không đủ tiền! Dư: {bal:,}"); return
        balances[uid]=bal-so_tien
        balances[tid]=balances.get(tid,0)+so_tien
        save()
        await interaction.followup.send(f"✅ {interaction.user.mention} đã chuyển {so_tien:,} xu cho {nguoi_nhan.mention}\n💰 Dư mới: {balances[uid]:,} xu")
    except Exception as e:
        print("ct err",e); await interaction.followup.send("❌ Lỗi, thử lại")

ADMIN_ID="1279776338160652300"
@bot.tree.command(name="addxu",description="Admin cong xu")
async def addxu(interaction:discord.Interaction, nguoi_nhan:discord.Member, so_tien:int):
    await interaction.response.defer(ephemeral=False)
    try:
        if str(interaction.user.id)!=ADMIN_ID:
            await interaction.followup.send("⛔ Bạn không có quyền dùng lệnh này"); return
        if so_tien<=0:
            await interaction.followup.send("❌ Số tiền phải >0"); return
        tid=str(nguoi_nhan.id)
        balances[tid]=balances.get(tid,0)+so_tien
        save()
        await interaction.followup.send(f"✅ Đã cộng {so_tien:,} xu cho {nguoi_nhan.mention}\n💰 Dư: {balances[tid]:,} xu")
    except Exception as e:
        print("addxu err",e); await interaction.followup.send("❌ Lỗi")



@bot.tree.command(name="cautaixiu",description="Xem 10 cau tai xiu gan nhat")
async def cautaixiu(interaction:discord.Interaction):
    await interaction.response.defer()
    if not cau_history:
        await interaction.followup.send("Chua co cau nao.")
        return
    last_10=cau_history[-10:][::-1]
    msg="**10 cau gan nhat:**\n"
    for i,c in enumerate(last_10,1):
        msg+=f"{i}. {c}\n"
    await interaction.followup.send(msg)
bot.run(TOKEN)

