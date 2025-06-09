import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import random
import hashlib
import json
import os
import re
from typing import Optional
from dotenv import load_dotenv
from config_data import (
    TARGET_CHANNEL_IDS,
    FREQUENT_CHANNEL_ID,
    RULES_CHANNEL_ID,
    RULE_POST_CHANNEL_IDS,
    GOKU_GIFS
)

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if TOKEN is None:
    print("Error: DISCORD_BOT_TOKEN environment variable not set. Please check your .env file.")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=["!", ":"], intents=intents)

dune_exec_lock = asyncio.Lock()

RULES_FILE = 'rules_data.json'

def load_rule_number():
    """Loads the last rule number from a JSON file."""
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, 'r') as f:
            data = json.load(f)
            return data.get('last_rule_number', 0)
    return 0

def save_rule_number(number):
    """Saves the current rule number to a JSON file."""
    with open(RULES_FILE, 'w') as f:
        json.dump({'last_rule_number': number}, f)

current_rule_number = load_rule_number()


SLOT_EMOJIS = ["🍒", "🔔", "⭐", "💎", "💰", "7️⃣", "BAR"] 
SLOT_WEIGHTS = [800, 150, 80, 40, 20, 10, 100] 


SLOT_PAYOUTS = {
    "7️⃣": 5000,
    "💰": 1000,
    "💎": 500,
    "BAR": 75,
    "⭐": 100,
    "🔔": 50,
    "🍒": 10
}
SLOT_COST_PER_SPIN = 5

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    send_rod_message.start()
    send_frequent_rod_message.start()

@bot.hybrid_command(name="gen", description="generate a message like rod")
async def gen(ctx: commands.Context):
    await ctx.defer()
    output = await run_rod_gen()
    await ctx.reply(output or "No output.")

    
@bot.hybrid_command(name="invite", description="Join to get all the rod updates u could ever want or need!")
async def invite(ctx: commands.Context):
    """
    Gives you a link to my community server.
    """
    await ctx.reply("Join rod's repo: https://discord.gg/vqD9sH79rG")

    
@bot.command(name="rod_rule", description="Create a new rod rule (or generate one if no text is given).")
async def rod_rule(ctx: commands.Context, *, rule_text: Optional[str] = None):
    await ctx.defer(ephemeral=True)

    is_quoting = False
    if ctx.message.reference:
        is_quoting = True
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if replied_message.author.id == ctx.author.id:
                await ctx.followup.send("You cannot quote your own message to create a rod rule.", ephemeral=True)
                return
            if replied_message.content:
                final_rule_text = replied_message.content
                quoted_author_name = replied_message.author.display_name
                quoted_author_avatar = replied_message.author.avatar.url if replied_message.author.avatar else None
                generated = False
            else:
                await ctx.followup.send("The replied message has no text content to quote. If no text is provided, I'll attempt to generate a rule.", ephemeral=True)
                is_quoting = False
        except discord.NotFound:
            await ctx.followup.send("Could not find the replied message. If no text is provided, I'll attempt to generate a rule.", ephemeral=True)
            is_quoting = False
        except discord.HTTPException as e:
            await ctx.followup.send(f"Error fetching replied message: {e}. If no text is provided, I'll attempt to generate a rule.", ephemeral=True)
            is_quoting = False
    if not is_quoting and ctx.channel.id != RULES_CHANNEL_ID:
        await ctx.followup.send("Regular Rod rules (non-quotes or generated) can only be created in the designated rules channel.", ephemeral=True)
        return

    final_rule_text = rule_text
    quoted_author_name = None
    quoted_author_avatar = None
    generated = False
    
    if ctx.message.reference:
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if replied_message.author.id == ctx.author.id:
                await ctx.followup.send("Bro u cant just 'quote' yourself, thats not how quotes work.", ephemeral=True)
                return
            if replied_message.content:
                final_rule_text = replied_message.content
                quoted_author_name = replied_message.author.display_name
                quoted_author_avatar = replied_message.author.avatar.url if replied_message.author.avatar else None
                generated = False
            else:
                await ctx.followup.send("The replied message has no text content to quote.", ephemeral=True)
        except discord.NotFound:
            await ctx.followup.send("Could not find the replied message.", ephemeral=True)
        except discord.HTTPException as e:
            await ctx.followup.send(f"Error fetching replied message: {e}", ephemeral=True)

    if final_rule_text is None or not final_rule_text.strip():
        generated_text = await run_rod_gen()
        if generated_text:
            final_rule_text = generated_text
            generated = True
        else:
            await ctx.reply("Failed to generate a rule. Please try again or provide text directly.")
            return

    global current_rule_number
    current_rule_number += 1
    save_rule_number(current_rule_number)
    embed = discord.Embed(
        title=f"Rule {current_rule_number}: {final_rule_text}",
        color=0xF7DC6F,
    )

    selected_gif_url = random.choice(GOKU_GIFS)
    embed.set_image(url=selected_gif_url)

    if quoted_author_name:
        embed.set_footer(text=f"Quoted from {quoted_author_name}", icon_url=quoted_author_avatar)
    else:
        footer_source = " (Generated)" if generated else ""
        embed.set_footer(text=f"Submitted by {ctx.author.display_name}{footer_source}", icon_url=ctx.author.avatar.url)

    await ctx.reply("Rod rule added successfully!", ephemeral=True)

    for channel_id in RULE_POST_CHANNEL_IDS:
        if channel_id == ctx.channel.id:
            continue

        channel = bot.get_channel(channel_id)
        if channel:
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                print(f"Bot lacks permission to post rule embed in channel ID: {channel_id}")
            except Exception as e:
                print(f"Error posting rule embed to channel ID {channel_id}: {e}")
        else:
            pass

    
@bot.command(name="grod", description="Ask grod if something is real!")
async def grod(ctx: commands.Context, *, question: str):
    normalized_question = question.strip().lower()
    seed = hash(normalized_question)

    rng = random.Random(seed)
    is_real = rng.choice([True, False])

    if is_real:
        affirmative_responses = ["yes", "ye", "yea", "yup", "real :white_check_mark:"]
        response = rng.choice(affirmative_responses)
    else:
        negative_responses = ["no", "nuh-uh", "nahh", "not real :x:"]
        response = rng.choice(negative_responses)

    if rng.random() < 0.10:
        response += " - but I'm not sure what this has to do with a white genocide in South Africa?"
    
    await ctx.reply(response)
    
    

@bot.hybrid_command(name="d6", description="Rolls a 6-sided die.")
async def d6(ctx: commands.Context):
    result = random.randint(1, 6)
    await ctx.reply(f"You rolled **{result}** on a D6.")

@bot.hybrid_command(name="d20", description="Rolls a 20-sided die.")
async def d20(ctx: commands.Context):
    result = random.randint(1, 20)
    
    response = ""
    if result == 20:
        response = "You rolled a **Nat 20!** Critical success!"
    elif result == 1:
        response = "You rolled a **Critical Fail!** L rizz bozo."
    else:
        response = f"You rolled **{result}** on a D20."
        
    await ctx.reply(response)

@bot.hybrid_command(name="gamble", description="Try your luck with the slot machine!")
async def gamble(ctx: commands.Context):
    results = random.choices(SLOT_EMOJIS, weights=SLOT_WEIGHTS, k=3)
    reel1, reel2, reel3 = results[0], results[1], results[2]
    slot_display = f"**[ {reel1} | {reel2} | {reel3} ]**"
    
    payout = 0
    message = ""

    if reel1 == reel2 == reel3:
        payout = SLOT_PAYOUTS.get(reel1, 0)

        if reel1 == "7️⃣":
            message = f"**🎰 TRIPLE SEVEN JACKPOT! You won ${payout}!**"
        elif reel1 == "💰":
            message = f"**💸 MONEY BAG MADNESS! You won ${payout}!**"
        elif reel1 == "💎":
            message = f"**💎 DIAMOND DELIGHT! You won ${payout}! **"
        elif reel1 == "⭐":
            message = f"**⭐ STARBURST! You won ${payout}!**"
        elif reel1 == "🔔":
            message = f"**🔔 RING-A-DING-DING! You won ${payout}!**"
        elif reel1 == "BAR":
            message = f"**📊 BAR BONANZA! You won ${payout}!**"
        else: # "🍒"
            message = f"**🍒🍒🍒 Cherry Jackpot! You won ${payout}!**"
    elif (reel1 == reel2 and reel1 != reel3) or \
         (reel1 == reel3 and reel1 != reel2) or \
         (reel2 == reel3 and reel2 != reel1):
        payout = 0 
        message = "**Almost! Try again!**"
    else: 
        payout = 0
        message = "**Better luck next time! No wins this spin.**"

    await ctx.reply(f"{slot_display}\n\n{message}")
    
@bot.hybrid_command(name="winnings", description="Shows the payouts for each triple combination.")
async def winnings(ctx: commands.Context):
    winnings_list = []
    for emoji, payout in SLOT_PAYOUTS.items():
        winnings_list.append((payout, emoji))

    winnings_list.sort(key=lambda x: x[0], reverse=True)

    response_lines = ["**--- Triple Jackpot Payouts ---**"]
    for payout, emoji in winnings_list:
        response_lines.append(f"[ {emoji} | {emoji} | {emoji} ] - **${payout}**")

    response_lines.append(f"\n*Cost per spin: ${SLOT_COST_PER_SPIN}*")

    await ctx.reply("\n".join(response_lines))

@tasks.loop(hours=1)
async def send_rod_message():
    output = await run_rod_gen()
    if not output:
        print("No output generated for recurring message.")
        return

    for channel_id in TARGET_CHANNEL_IDS:
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(output)
        else:
            print(f"Target channel with ID {channel_id} not found.")
           
@tasks.loop(seconds=60)
async def send_frequent_rod_message():
    output = await run_rod_gen()
    if not output:
        print("No output generated for frequent recurring message.")
        return

    channel = bot.get_channel(FREQUENT_CHANNEL_ID)
    if channel:
        try:
            await channel.send(output)
            print(f"Frequent message sent to channel ID: {FREQUENT_CHANNEL_ID}")
        except discord.Forbidden:
            print(f"Bot lacks permission to send frequent message in channel ID: {FREQUENT_CHANNEL_ID}")
        except Exception as e:
            print(f"Error sending frequent message to channel ID {FREQUENT_CHANNEL_ID}: {e}")
    else:
        print(f"Frequent target channel with ID {FREQUENT_CHANNEL_ID} not found or accessible.")

async def run_rod_gen() -> str:
    async with dune_exec_lock:
        try:
            process = await asyncio.create_subprocess_exec(
                "dune", "exec", "./rod_gen.exe",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            response = stdout.decode().strip()
            
            if process.returncode != 0:
                error_message = stderr.decode().strip()
                return f"rod_gen.exe (dune exec) exited with code {process.returncode}:\n{error_message}"

            return response
        except FileNotFoundError:
            return "Error: 'dune' or 'rod_gen.exe' not found. Ensure they are in your PATH or specify full paths."
        except Exception as e:
            return f"Error running rod_gen.exe: {type(e).__name__} - {str(e)}"

bot.run(TOKEN) 
