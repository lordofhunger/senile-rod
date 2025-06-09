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

load_dotenv() 

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if TOKEN is None:
    print("Error: DISCORD_BOT_TOKEN environment variable not set. Please check your .env file.")
    exit(1)

TARGET_CHANNEL_IDS = [1381165170998378638, 1365712408710086737]
FREQUENT_CHANNEL_ID = 1381210044279820318
RULES_CHANNEL_ID = 1365712408710086737
RULE_POST_CHANNEL_IDS = [1381295413423771740, 1164969184158044220, 1381300617984872498]

intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix=["!", ":"], intents=intents)


GOKU_GIFS = [
    "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExbXhkaTRrN3ZyMGptbTBibnl2ZWFjajNhZnR6eG5nd250cGswNHU3ZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/XKZxVL0ZdTlf1Detsh/giphy.gif",
    "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExYzBjZDJ4cG10MHN4dXN6OGRqbm9vNHYwdXd0Ym82aWtuNjBhZXY3MCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/YHRllqcns1yI0rtJyx/giphy.gif",
    "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExY282aHdvcm01dTVxdDNhNWxmcXlwMXVuYmI2dnk4dGoxaTdpY3U5eiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/nLa6JbJ0F8mzaVVBwF/giphy.gif",
    "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExM2Rqd3U2djFhZTQ3M3Y4azVkZ3gxcmt4ajdyY3Y0N3hqdzNnOTBiaiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/nKeq599EKJOolyCtPk/giphy.gif",
    "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExZ25oNWFlaml3YXp5cnA1NWVnaDY2cnp2a2hyazFiZnl5OGtwcXg0NiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/p7QeOqVc1U6X025Ql6/giphy.gif",
    "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExMmg3d2dteGh2a3pwcG0xeWptYXNjNWU2cWZ4c21sZHQ3cjZtZjF1YSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/vMGG0UloaTGnDodQ7z/giphy.gif",
    "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExYzdpaWoxY2wxZGg0dnVnZDRmcDB4a2w0NnRhZzRxdjFoYnRkMmxuOSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/eZ35MrjDyOqGSUaFFz/giphy.gif",
    "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWRkdGx4bXJvamR0d2d2M2MzbjZvYTdvbGxoN3Q5YmFmNnp2d2x1dSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/A0ZEUfAWDpqiryHM6h/giphy.gif",
    "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExcGdiYmZ6amY2NTUycHRmZm5mN3N2cTQ4dmRtb2VoYmxoMDljOWt3ciZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/EyDYdGCCZBnGskjnIB/giphy.gif",
    "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExcWRnbDZzeWpianA5YWVkZWR4NG9qdmxreXpiZ2J6M2FzYWx3ZHplZiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/PHFczETRKfPropxkka/giphy.gif",
    "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExZDh4aHM1dnBjYWJvZ3g5Y3c0OWl1MXkzcGg2c3ZibDM2bnA4bDZ1YiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Z1cmg6ojCJIY9WMqso/giphy.gif",
    "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExMnI5ODQ5ZzJlZzhqOGk4cmtiYm4yczloNHg0eWZyM3ZmdmN6aXdlNiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/ZdwwQ8UwVxm5K5VgWU/giphy.gif",
    "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExajdxbHlrdTYweDRtZ2Z1MzUybDhjY3F0NGVuNGllMmM4dGU3NndobCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Lzd0wFp65M9HkVrP2a/giphy.gif",
    "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExajdxbHlrdTYweDRtZ2Z1MzUybDhjY3F0NGVuNGllMmM4dGU3NndobCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Lzd0wFp65M9HkVrP2a/giphy.gif",
    "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExajdxbHlrdTYweDRtZ2Z1MzUybDhjY3F0NGVuNGllMmM4dGU3NndobCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Lzd0wFp65M9HkVrP2a/giphy.gif",
]

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
    
@bot.command(name="rod_rule", description="Create a new rod rule (or generate one if no text is given).")
async def rod_rule(ctx: commands.Context, *, rule_text: Optional[str] = None):
    await ctx.defer(ephemeral=True)

    is_quoting = False
    if ctx.message.reference:
        is_quoting = True
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
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
    
    await ctx.reply(response)

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
