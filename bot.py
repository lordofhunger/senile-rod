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
    TARGET_CHANNEL_IDS,    #IDs where generated rod quotes are posted
    FREQUENT_CHANNEL_ID,   #ID of the channel where generated rod quotes get posted once a minute
    RULES_CHANNEL_ID,      #ID of the channel where rod_rules can be made
    RULE_POST_CHANNEL_IDS, #ID of the channels where rod_rules are posted
    RULE_GIFS              #GIFs utilised in rod_rules
)

load_dotenv() #loading of the .env file, which is where the bot token is stored

TOKEN = os.getenv("DISCORD_BOT_TOKEN") # getting the token
if TOKEN is None:
    print("Error: DISCORD_BOT_TOKEN environment variable not set. Please check your .env file.")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True                                  # we want to see the content of messages (e.g. for rod_rules)
bot = commands.Bot(command_prefix=["!", ":"], intents=intents)  # our prefixes are ! and :

dune_exec_lock = asyncio.Lock() # this is a 'lock', it ensures that certain procedures are used one at a time, e.g. you cant use a procedure before someone else is finished

RULES_FILE = 'json-files/rules_data.json'                   # amount of made rules are stored here
CURRENT_FLEET_FILE = 'text-files/fleet-members.txt'         # fleet members of shirobobs-fleet are stored here
FORMER_FLEET_FILE = 'text-files/former-fleet-members.txt'   # former fleet members are stored here

def load_rule_number():
    """Procedure to get the amount of existing rod_rules"""
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, 'r') as f:
            data = json.load(f)
            return data.get('last_rule_number', 0)
    return 0

def save_rule_number(number):
    """Procedure to set the new amount of existing rod_rules."""
    with open(RULES_FILE, 'w') as f:
        json.dump({'last_rule_number': number}, f)

current_rule_number = load_rule_number() # get the current rule nr


SLOT_EMOJIS = ["🍒", "🔔", "⭐", "💎", "💰", "7️⃣", "BAR"]  # emojis used as options in our slot machine
SLOT_WEIGHTS = [800, 150, 80, 40, 20, 10, 100]             # their weights, i.e. how likely are they to appear

# the slot payouts, necessary for showing what you won and for the winnings command
SLOT_PAYOUTS = { 
    "7️⃣": 5000,
    "💰": 1000,
    "💎": 500,
    "BAR": 75,
    "⭐": 100,
    "🔔": 50,
    "🍒": 10
}
SLOT_COST_PER_SPIN = 5 # 'price' for a spin of the slot machine

# decorations for showing the fleet members
TOP_BANNER = "-------------------[ShiroBob's fleet]--------------------"
MID_BANNER = "-------------------[Former Members]----------------------"
BOTTOM_BANNER = "---------------------------------------------------------"

# main loop
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


@bot.hybrid_command(name="gen", description="Generate a message like rod")
async def gen(ctx: commands.Context):
    """
    Generates a message from rod's discord messages.
    """
    await ctx.defer()
    output = await run_rod_gen()
    await ctx.reply(output or "No output.")

    
@bot.hybrid_command(name="invite", description="Join to get all the rod updates u could ever want or need!")
async def invite(ctx: commands.Context):
    """
    Gives you a link to the rod's repo community server.
    """
    await ctx.reply("Join rod's repo: https://discord.gg/vqD9sH79rG")
    
    
#patreon.com/user?u=20322607    
@bot.hybrid_command(name="patreon", description="Sponsor rod, he'll probably buy posters with this money?")
async def invite(ctx: commands.Context):
    """
    Gives you a link to my Patreon, I don't know why you would want that.
    """
    await ctx.reply("Really? Okay: https://patreon.com/user?u=20322607")
    
@bot.hybrid_command(name="patreon-features", description="What features does rod's patreon come with?")
async def patreon_features(ctx: commands.Context):
    """
    Lists the "features" of rod's Patreon.
    """
    output_message = (
        "Purchasing rod's patreon comes with many fun features, including but not limited to:\n"
        "- loss of money\n"
        "- regret"
    )
    await ctx.reply(output_message)
    
@bot.command(name="rod_rule", description="Create a new rod rule (or generate one if no text is given).")
async def rod_rule(ctx: commands.Context, *, rule_text: Optional[str] = None):
    """
    Meant to add a new "rod rule", this is a feature based on one by discord user umbra_unbound, or Hephy, called 'Goku rules'.
    Goku rules contain a gif of Goku and a text stating Rule <nr>: <text of rule>, which is meant as a humorous take on 'Discord server rules'.
    In contrast, rod rules either contain an auto-generated message, a given message or a quoted one, and a gif defined in RULE_GIFS.
    As a nod to Hephy, 'real' rod rules can only be made in the #general channel of his Discord server.
    """
    await ctx.defer(ephemeral=True)

    is_quoting = False
    if ctx.message.reference:
        is_quoting = True
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if replied_message.author.id == ctx.author.id:
                await ctx.followup.send("'You cannot quote your own message, thats not how quotes work.' -rod", ephemeral=True)
                return
            if replied_message.content:
                final_rule_text = replied_message.content
                quoted_author_name = replied_message.author.display_name
                quoted_author_avatar = replied_message.author.avatar.url if replied_message.author.avatar else None
                generated = False
            else:
                await ctx.followup.send("I can't quote this messages content, and will provide my own.", ephemeral=True)
                is_quoting = False
        except discord.NotFound:
            await ctx.followup.send("I can't find the replied message.", ephemeral=True)
            is_quoting = False
        except discord.HTTPException as e:
            await ctx.followup.send(f"Error fetching replied message: {e}.", ephemeral=True)
            is_quoting = False
    if not is_quoting and ctx.channel.id != RULES_CHANNEL_ID:
        await ctx.followup.send("Regular rod rules (non-quotes or generated) can only be created in Hephy's general.", ephemeral=True)
        return

    final_rule_text = rule_text
    quoted_author_name = None
    quoted_author_avatar = None
    generated = False
    
    if ctx.message.reference:
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if replied_message.author.id == ctx.author.id:
                await ctx.followup.send("'You cannot quote your own message, thats not how quotes work.' -rod", ephemeral=True)
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

    selected_gif_url = random.choice(RULE_GIFS)
    embed.set_image(url=selected_gif_url)

    if quoted_author_name:
        embed.set_footer(text=f"Quoted from {quoted_author_name}", icon_url=quoted_author_avatar)
    else:
        footer_source = " (Generated)" if generated else ""
        embed.set_footer(text=f"Submitted by {ctx.author.display_name}{footer_source}", icon_url=ctx.author.avatar.url)

    await ctx.reply("New rod rule added!", ephemeral=True)

    for channel_id in RULE_POST_CHANNEL_IDS:
        if channel_id == ctx.channel.id:
            continue

        channel = bot.get_channel(channel_id)
        if channel:
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                print(f"Uhm, senile rod lacks permission to post rule embed in channel ID: {channel_id}")
            except Exception as e:
                print(f"Error posting rule embed to channel ID {channel_id}: {e}")
        else:
            pass

    
@bot.command(name="grod", description="Ask grod if something is real!")
async def grod(ctx: commands.Context, *, question: str):
    """
    A play on Elon Musks 'Grok' twitter bot, where users can ask Grok if something is 'real' or not.
    Grod (Grok-rod), will reply randomly, but deterministic, on whether the question is true or not.
    As an added realism bonus for Grok, Grod now has a one in ten chance of being confused about what
    the question has to do with a 'white genocide' in South Africa. 
    (https://www.theguardian.com/technology/2025/may/14/elon-musk-grok-white-genocide)
    """
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
    """
    This procedure simulates rolling a six-sided die.
    """
    result = random.randint(1, 6)
    await ctx.reply(f"You rolled **{result}** on a D6.")

@bot.hybrid_command(name="d20", description="Rolls a 20-sided die.")
async def d20(ctx: commands.Context):
    """
    This procedure simulates rolling a twenty-sided die.
    """
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
    """
    This procedure simulates a slot machine, rod enterprises does not endorse gambling.
    """
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
    """
    This procedure shows the 'winnings' that can be made from the slot machine.
    """
    winnings_list = []
    for emoji, payout in SLOT_PAYOUTS.items():
        winnings_list.append((payout, emoji))

    winnings_list.sort(key=lambda x: x[0], reverse=True)

    response_lines = ["**--- Triple Jackpot Payouts ---**"]
    for payout, emoji in winnings_list:
        response_lines.append(f"[ {emoji} | {emoji} | {emoji} ] - **${payout}**")

    response_lines.append(f"\n*Cost per spin: ${SLOT_COST_PER_SPIN}*")

    await ctx.reply("\n".join(response_lines))
    
    
RPS_CHOICES = {
    "rock": "🪨",
    "paper": "📄",
    "scissors": "✂️"
}

@bot.hybrid_command(name="rps", description="Rod̶ck, Paper, Scissors!")
@app_commands.describe(choice="Rock, paper, or scissors - choose wisely! :grinning:")
async def rps(ctx: commands.Context, choice: str):
    """
    This procedure simulates playing rock, paper, scissors with senile rod.
    """
    user_choice = choice.lower()

    if user_choice not in RPS_CHOICES:
        await ctx.reply("Huh? Pick `rock`, `paper`, or `scissors`.")
        return
        
    if ctx.author.display_name == "Gon Freeccs":
        result_message = "Wha!? Ya broke my damn tool!"
        bot_choice_emoji = "💥"
        await ctx.reply(
            f"You chose: {RPS_CHOICES[user_choice]} ({user_choice.capitalize()})\n"
            f"senile rod's choice exploded! {bot_choice_emoji}\n\n"
            f"**{result_message}**"
        )
        return


    bot_choice_name = random.choice(list(RPS_CHOICES.keys()))
    bot_choice_emoji = RPS_CHOICES[bot_choice_name]
    user_choice_emoji = RPS_CHOICES[user_choice]

    result_message = ""

    if user_choice == bot_choice_name:
        result_message = "A tie, guess you cant beat this old man ehehe :relieved:"
    elif (user_choice == "rock" and bot_choice_name == "scissors") or \
         (user_choice == "paper" and bot_choice_name == "rock") or \
         (user_choice == "scissors" and bot_choice_name == "paper"):
        result_message = "Wha? Damn youngsters playing tricks on an old man :unamused:"
    else:
        result_message = "L bozo :weary:"

    await ctx.reply(
        f"You chose: {user_choice_emoji} ({user_choice.capitalize()})\n"
        f"I chose: {bot_choice_emoji} ({bot_choice_name.capitalize()})\n\n"
        f"**{result_message}**"
    )
    


OP_RPS_CHOICES = {
    "ishi": {"emoji": "🪨", "full_name": "Ishi Ishi no Mi"},
    "mori": {"emoji": "🌳", "full_name": "Mori Mori no Mi"},
    "supa": {"emoji": "🔪", "full_name": "Supa Supa no Mi"}
}

@bot.hybrid_command(name="op_rps", description="One Piece Rock, Paper, Scissors!")
@app_commands.describe(choice="Ishi (Rock), Mori ('Paper'), or Supa ('Scissors') - choose wisely!")
async def op_rps(ctx: commands.Context, choice: str):
    """
    This procedure simulates playing a one-piece themed rock, paper, scissors game with senile rod.
    """
    user_choice = choice.lower()

    if user_choice not in OP_RPS_CHOICES:
        await ctx.reply("Yeah yeah real pirates don't follow rules! But for this game, pick `ishi`, `mori`, or `supa`.")
        return

    bot_choice_name = random.choice(list(OP_RPS_CHOICES.keys()))

    user_choice_info = OP_RPS_CHOICES[user_choice]
    bot_choice_info = OP_RPS_CHOICES[bot_choice_name]

    user_choice_emoji = user_choice_info["emoji"]
    user_choice_full_name = user_choice_info["full_name"]
    bot_choice_emoji = bot_choice_info["emoji"]
    bot_choice_full_name = bot_choice_info["full_name"]

    result_message = ""

    if user_choice == bot_choice_name:
        result_message = "A tie! Looks like you can't beat this old man, wahwahwahwah :laughing:"
    elif (user_choice == "ishi" and bot_choice_name == "supa") or \
         (user_choice == "mori" and bot_choice_name == "ishi") or \
         (user_choice == "supa" and bot_choice_name == "mori"):
        result_message = "Wha? You younguns playing tricks on an old man, when I was in my prime roger was still a rookie! :unamused:"
    else:
        result_message = "L bozo! My Devil Fruit power is superior! wahwahwahwah :laughing:"

    await ctx.reply(
        f"You chose: {user_choice_emoji} ({user_choice_full_name})\n"
        f"I chose: {bot_choice_emoji} ({bot_choice_full_name})\n\n"
        f"**{result_message}**"
    )
    
@bot.hybrid_command(name="shirobobs-fleet", description="Shows the current and former members of ShiroBob's fleet.")
async def shirobobs_fleet(ctx: commands.Context):
    """
    Displays the combined crew of current and former fleet members.
    """
    if ctx.interaction:
        await ctx.interaction.response.defer()

    try:
        with open(CURRENT_FLEET_FILE, 'r', encoding='utf-8') as f:
            current_members_content = f.read()

        with open(FORMER_FLEET_FILE, 'r', encoding='utf-8') as f:
            former_members_content = f.read()

        full_fleet_content = (
            f"{TOP_BANNER}\n"
            f"{current_members_content.strip()}\n"
            f"{MID_BANNER}\n"
            f"{former_members_content.strip()}\n"
            f"{BOTTOM_BANNER}"
        )

        response_text = f"```\n{full_fleet_content}\n```"

        if ctx.interaction:
            await ctx.interaction.followup.send(response_text)
        else:
            await ctx.send(response_text)

    except FileNotFoundError as e:
        error_message = f"Uhh I can't find one of the fleet roster files! ({e.filename})"
        if ctx.interaction:
            await ctx.interaction.followup.send(error_message)
        else:
            await ctx.send(error_message)

    except Exception as e:
        error_message = f"An unexpected error occurred while reading the fleet roster: {e}"
        if ctx.interaction:
            await ctx.interaction.followup.send(error_message)
        else:
            await ctx.send(error_message)
        
def _count_fleet_members() -> int:
    """
    Counts the number of current fleet members.
    """
    num_members = 0
    try:
        with open(CURRENT_FLEET_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                stripped_line = line.strip()
                if stripped_line and not stripped_line.startswith('-'):
                    num_members += 1
    except FileNotFoundError:
        print(f"Fleet members file not found at {CURRENT_FLEET_FILE}.")
        return 0
    except Exception as e:
        print(f"ERROR: An error occurred while counting fleet members: {e}")
        return 0
    return num_members
    
@bot.hybrid_command(name="crew_size", description="Reports the current number of members in ShiroBob's fleet.")
async def crew_size(ctx: commands.Context):
    """
    Counts and reports the number of current fleet members.
    """
    if ctx.interaction:
        await ctx.interaction.response.defer()

    try:
        num_members = _count_fleet_members()

        response_message = f"ShiroBob's fleet currently has **{num_members}** members."

        if ctx.interaction:
            await ctx.interaction.followup.send(response_message)
        else:
            await ctx.send(response_message)

    except Exception as e:
        error_message = f"An error occurred while getting the crew size: {e}"
        if ctx.interaction:
            await ctx.interaction.followup.send(error_message)
        else:
            await ctx.send(error_message)
    
   
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
