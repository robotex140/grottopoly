import discord
from discord.ext import commands, tasks
import random
import asyncio
import os
import json
from dotenv import load_dotenv
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging
from functools import wraps

# Load environment variables from .env file
load_dotenv()

# Existing command cooldown and spam control
user_cooldowns = defaultdict(dict)

team_sabotaged = defaultdict(lambda: False)

# Get paths and IDs from environment variables
GIF_PATHS = os.getenv('GIF_PATHS').split(',')
GAME_CHANNEL_ID = int(os.getenv('GAME_CHANNEL_ID'))
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
CATEGORY_ID = int(os.getenv('CATEGORY_ID'))
CAPTAIN_COMMANDS_CHANNEL_ID = int(os.getenv('CAPTAIN_COMMANDS_CHANNEL_ID'))

TAUNT_INTERVAL_SECONDS = 14400  # 4 hours
NUMBER_OF_TEAMS = 8

logging.basicConfig(level=logging.DEBUG)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Enable the members intent

# Print GIF paths for debugging
print("GIF paths loaded from .env:")
for path in GIF_PATHS:
    print(path, "exists:", os.path.isfile(path))

# Initialize bot with command prefix and intents
bot = commands.Bot(command_prefix='!', intents=intents)

team_sabotages = defaultdict(int)  # Track the number of sabotages per team

# Variables to track teams and game state
number_of_teams = 0
teams_set = False
game_started = False  # Track if the game has started

# Initialize bot with command prefix and intents, set case_insensitive to True
bot = commands.Bot(command_prefix='!', intents=intents, case_insensitive=True)

# Data storage (consider using a database for persistence)
team_data = {}
captains = {}
team_positions = defaultdict(lambda: 1)
completed_tiles = defaultdict(set)
tile_completions = defaultdict(list)
player_completions = defaultdict(int)
team_members = defaultdict(set)
hard_stop_tiles = [1, 5, 15, 23, 32, 40, 46, 52, 59, 63, 64, 65, 66, 67, 68, 69]
team_has_rolled = defaultdict(lambda: False)
bonus_tile_completions = defaultdict(dict)
team_advantages = defaultdict(lambda: None)
bonus_choices = defaultdict(dict)
rolls_count = defaultdict(int)
tile_completion_times = defaultdict(list)
tile_start_times = {}
teams_needing_bonus_choice = defaultdict(lambda: None)

team_gp_bonus = defaultdict(int)

# List of hard stop messages
hard_stop_messages = [
    "You go to move {roll} tiles but a magical force stops you at tile {tile}. Complete this tile to roll again.",
    "You move {roll} tiles but soup's guide did not prepare you for tile {tile}. Complete this tile to proceed.",
    "Your progress is halted at tile {tile}. Complete this tile before continuing your journey.",
    "You attempt to move {roll} tiles but must stop at tile {tile} and finish its task to move on.",
    "You are stopped at tile {tile}. You have a funny feeling you must complete this tile before continuing.",
]


# Dictionary for team roles
team_roles = {
    'team1': 1192366243324366891,  # Replace with actual role ID for Team 1
    'team2': 1192366338186940527,  # Replace with actual role ID for Team 2
    'team3': 1192366365965815848,  # Replace with actual role ID for Team 3
    'team4': 1192366394155745291,  # Replace with actual role ID for Team 4
    'team5': 1251364935053738074,  # Replace with actual role ID for Team 5
    'team6': 1251720714050998273,  # Replace with actual role ID for Team 6
    'team7': 1251720752235937802,  # Replace with actual role ID for Team 7
    'team8': 1251720795152060497  # Replace with actual role ID for Team 8
}

# Tasks for Monkey's Paw
monkey_paw_tasks = {
    1: "    .",
    2: "    .",
    3: "    .",
    4: "    .",
    5: "    .",
    6: "    .",
    7: "    .",
    8: "    .",
    9: "    .",
    10: "    .",
    11: "    .",
    12: "    .",
    13: "    .",
    14: "    .",
    15: "    .",
    16: "    .",
    17: "    .",
    18: "    .",
    19: "    .",
    20: "    ."
}

# Dictionary for tile tasks
tile_tasks = {
  1: 'task',
  2: 'task',
  3: 'task',
  4: 'task',
  5: 'task',
  6: 'task',
  7: 'task',
  8: 'task',
  9: 'task',
  10: 'task',
  11: 'task',
  12: 'task',
  13: 'task',
  14: 'task',
  15: 'task',
  16: 'task',
  17: 'task',
  18: 'task',
  19: 'task',
  20: 'task',
  21: 'task',
  22: 'task',
  23: 'task',
  24: 'task',
  25: 'task',
  26: 'task',
  27: 'task',
  28: 'task',
  29: 'task',
  30: 'task',
  31: 'task',
  32: 'task',
  33: 'task',
  34: 'task',
  35: 'task',
  36: 'task',
  37: 'task',
  38: 'task',
  39: 'task',
  40: 'task',
  41: 'task',
  42: 'task',
  43: 'task',
  44: 'task',
  45: 'task',
  46: 'task',
  47: 'task',
  48: 'task',
  49: 'task',
  50: 'task',
  51: 'task',
  52: 'task',
  53: 'task',
  54: 'task',
  55: 'task',
  56: 'task',
  57: 'task',
  58: 'task',
  59: 'task',
  60: 'task',
  61: 'task',
  62: 'task',
  63: 'task',
  64: 'task',
  65: 'task',
  66: 'task',
  67: 'task',
  68: 'task',
  69: 'task',
}

# Tasks for bonus tiles
bonus_tasks = {
    "1": "Obtain a Pet",
    "2": "Obtain a Jar",
    "3": "Obtain a Cox or Tob Kit",
    "4": "Obtain a Cox or Tob Dust"
}

# Default message for undefined tasks
default_task_message = "No task defined for this tile yet."

# Predefined taunts
taunts = [
    "Hey {team}, are you taking a nap? Complete your tile already!",
    "The game's waiting on you, {team}! Finish up and let's move!",
    "Are you still with us, {team}? Your tile is calling!",
    "Come on, {team}, it's not rocket science! Complete your tile!",
    "Earth to {team}! Complete your tile!",
    "Tick-tock, {team}! Time's wasting, get it done!",
    "Don't keep us in suspense, {team}! Complete your tile!",
    "Have you forgotten your tile, {team}? Get your act together!",
    "Move it, {team}! We're all waiting, hurry up!",
    "What's the hold-up, {team}? The game won't play itself, get moving!",
    "Speed it up, {team}! We haven't got all day!",
    "Get your head in the game, {team}! Complete your tile!",
    "Did you fall asleep, {team}? Your tile's not gonna complete itself!",
    "Quit stalling, {team}! The game awaits, hurry up!",
    "Let's go, {team}! Time to complete that tile!",
    # More taunts...
]

# Predefined responses for trying to roll before finishing the tile
incomplete_tile_responses = [
    "Nice try, {team}, but you need to complete your tile before rolling! Get with it!",
    "Patience, {team}! Finish your task before rolling the dice. Seriously.",
    "You can't roll yet, {team}. Complete the tile first! Don't get ahead of yourself.",
    "Hold up, {team}! You haven't finished your task yet. What's the rush?",
    "Not so fast, {team}! Complete your tile before rolling! We're all waiting!",
    "No shortcuts, {team}! Finish your tile task first. We see you trying!",
    "Did you forget something, {team}? Complete your tile first! It's not that hard.",
    "Whoa there, {team}! You need to finish your tile before rolling. Keep up!",
    "Complete your task, {team}, then you can roll! Don't jump the gun.",
    "Oops, {team}! Finish the tile before rolling the dice. What's the holdup?",
    # More responses...
]

# New responses for no tiles completed
no_tiles_completed_responses = [
    "We have a slacker here. Get back to work and help your team!",
    "Zero tiles completed? Seriously? Get your act together!",
    "Hey, what are you waiting for? Finish a tile already!",
    "Not a single tile? Stop messing around and do something!",
    "Do you even know how to play? Get to work!",
    "Are you kidding me? Zero tiles? Quit slacking off!",
    "What's the holdup? Get off your butt and complete a tile!",
    "No tiles done? Pathetic. Get to work!",
    "This isn't a vacation! Start completing tiles!",
    "Wow, zero tiles? Move and help your team!",
    "Not even one tile? Get it together and do your part!",
    "Stop being useless and complete a tile!",
    "What's wrong? Can't complete a single tile? Get to it!",
    "No tiles completed? Embarrassing. Get to work!",
    "Zero tiles? Quit being a dead weight and help your team!",
    # More responses...
]

# Responses for landing on a hard stop tile
hard_stop_responses = [
    "You cannot move past tile {stop_tile} until you complete its task.",
    "You have a funny feeling that you must complete tile {stop_tile} before continuing.",
    "Roses are red, your hit-splats are blue, finish tile {stop_tile} and then you can continue.",
    "You feel drawn to stop on tile {stop_tile}. Finish its task before rolling again.",
    "You cannot proceed beyond tile {stop_tile} until its task is done.",
    "A mystical force compels you to finish tile {stop_tile} before moving on.",
    "Tile {stop_tile} is your current quest. Complete it before advancing.",
    "The path ahead is blocked by tile {stop_tile}'s challenge. Overcome it to proceed.",
    "Your journey halts at tile {stop_tile}. Complete its task to continue your adventure.",
    "Tile {stop_tile} holds you captive. Conquer its challenge to roll again."
]

# Track user messages for spam control
user_messages = defaultdict(deque)
user_timeouts = {}

SPAM_LIMIT = 5  # Number of messages
SPAM_TIME = 10  # Time window in seconds
TIMEOUT_DURATION = 300  # Timeout duration in seconds (5 minutes)

async def handle_spam(ctx):
    user_id = ctx.author.id
    now = datetime.utcnow()
    if user_id in user_cooldowns:
        if "spam" in user_cooldowns[user_id]:
            user_cooldowns[user_id]["spam"].append(now)
            user_cooldowns[user_id]["spam"] = [t for t in user_cooldowns[user_id]["spam"] if now - t < timedelta(seconds=10)]
            if len(user_cooldowns[user_id]["spam"]) > 5:
                user_cooldowns[user_id]["global"] = now + timedelta(minutes=5)
                return True
        else:
            user_cooldowns[user_id]["spam"] = [now]
    else:
        user_cooldowns[user_id]["spam"] = [now]
    return False

async def check_timeout(ctx):
    user_id = ctx.author.id
    if user_id in user_cooldowns:
        if "global" in user_cooldowns[user_id]:
            timeout = user_cooldowns[user_id]["global"]
            if datetime.utcnow() < timeout:
                return True
    return False

async def sync_team_members():
    """Synchronize team members based on existing roles in the guild."""
    await bot.wait_until_ready()
    guild = bot.get_guild(GAME_CHANNEL_ID)
    if not guild:
        logging.error(f"Guild with ID {GAME_CHANNEL_ID} not found.")
        return

    for team, role_id in team_roles.items():
        role = discord.utils.get(guild.roles, id=role_id)
        if role:
            team_members[team] = set(member.id for member in role.members)
        else:
            logging.warning(f"Role with ID {role_id} not found in guild.")
    logging.debug("Team members synchronized based on existing roles.")

def is_captain(ctx):
    """Check if the user has the Team Captain role."""
    captain_role = discord.utils.get(ctx.guild.roles, name="Team Captain")
    return captain_role in ctx.author.roles

def resolve_team_identifier(identifier):
    """Resolve the team identifier to the actual team key used in the data structures."""
    identifier = identifier.lower().strip()
    if identifier in team_data:
        return identifier
    for team, name in team_data.items():
        if name.lower().strip() == identifier:
            return team
    return None

def in_game_channel(ctx):
    """Check if the command was issued in the game channel."""
    return ctx.channel.id == CHANNEL_ID

def in_designated_category(ctx):
    """Check if the command was issued in the designated category."""
    return ctx.channel.category_id == CATEGORY_ID

def in_captain_commands_channel(ctx):
    """Check if the command was issued in the captain command channel."""
    return ctx.channel.id == CAPTAIN_COMMANDS_CHANNEL_ID


def save_state():
    logging.debug("Entered save_state function")

    state = {
        "team_data": team_data,
        "captains": captains,
        "team_positions": {k: v for k, v in team_positions.items()},
        "completed_tiles": {k: list(v) for k, v in completed_tiles.items()},
        "tile_completions": {k: v for k, v in tile_completions.items()},
        "player_completions": player_completions,
        "team_members": {k: list(v) for k, v in team_members.items()},
        "team_has_rolled": {k: v for k, v in team_has_rolled.items()},
        "bonus_tile_completions": {k: {str(kk): vv for kk, vv in v.items()} for k, v in bonus_tile_completions.items()},
        "team_advantages": {k: v for k, v in team_advantages.items()},
        "bonus_choices": {k: {str(kk): vv for kk, vv in v.items()} for k, v in bonus_choices.items()},
        "rolls_count": {k: v for k, v in rolls_count.items()},
        "tile_completion_times": {k: [(tile, time.total_seconds()) for tile, time in v] for k, v in tile_completion_times.items()},
        "teams_set": teams_set,
        "game_started": game_started,
        "tile_start_times": {k: v.isoformat() for k, v in tile_start_times.items()},
        "teams_needing_bonus_choice": {k: v for k, v in teams_needing_bonus_choice.items()},
        "team_gp_bonus": dict(team_gp_bonus),
        "team_sabotaged": dict(team_sabotaged)
    }

    logging.debug(f"State to be saved: {state}")
    logging.debug(f"Bonus Tile Completions to be saved: {bonus_tile_completions}")

    with open("state.json", "w") as f:
        json.dump(state, f)

    logging.debug("Exited save_state function")

def load_state():
    global team_data, captains, team_positions, completed_tiles, tile_completions, player_completions, team_members
    global team_has_rolled, bonus_tile_completions, team_advantages, bonus_choices, rolls_count, tile_completion_times
    global teams_set, number_of_teams, game_started, tile_start_times, teams_needing_bonus_choice, team_gp_bonus, team_sabotaged

    try:
        with open("state.json", "r") as f:
            state = json.load(f)
            team_data = state.get("team_data", {})
            captains = state.get("captains", {})
            team_positions = defaultdict(lambda: 1, state.get("team_positions", {}))
            completed_tiles = defaultdict(set, {k: set(v) for k, v in state.get("completed_tiles", {}).items()})
            tile_completions = defaultdict(list, {k: v for k, v in state.get("tile_completions", {}).items()})
            player_completions = state.get("player_completions", {})
            team_members = defaultdict(set, {k: set(v) for k, v in state.get("team_members", {}).items()})
            team_has_rolled = defaultdict(lambda: False, state.get("team_has_rolled", {}))
            bonus_tile_completions = defaultdict(dict, {k: v for k, v in state.get("bonus_tile_completions", {}).items()})
            team_advantages = defaultdict(lambda: None, state.get("team_advantages", {}))
            bonus_choices = defaultdict(dict, {k: v for k, v in state.get("bonus_choices", {}).items()})
            rolls_count = defaultdict(int, state.get("rolls_count", {}))
            tile_completion_times = defaultdict(list, {k: [(tile, timedelta(seconds=time)) for tile, time in v] for k, v in state.get("tile_completion_times", {}).items()})
            tile_start_times = {k: datetime.fromisoformat(v) for k, v in state.get("tile_start_times", {}).items()}
            teams_set = state.get("teams_set", False)
            game_started = state.get("game_started", False)
            teams_needing_bonus_choice = defaultdict(lambda: None, state.get("teams_needing_bonus_choice", {}))
            team_gp_bonus = defaultdict(int, state.get("team_gp_bonus", {}))
            team_sabotaged = defaultdict(lambda: False, state.get("team_sabotaged", {}))
            number_of_teams = len(team_data)
            logging.debug("Loaded state from state.json.")
            logging.debug(f"Loaded Bonus Tile Completions: {bonus_tile_completions}")
    except FileNotFoundError:
        logging.debug("No saved state found, starting fresh.")
    except Exception as e:
        logging.error(f"Error loading state: {e}")


async def initialize_team_members():
    """Initialize team members based on existing roles in the guild."""
    await bot.wait_until_ready()
    guild = bot.get_guild(GAME_CHANNEL_ID)
    if not guild:
        logging.error(f"Guild with ID {GAME_CHANNEL_ID} not found.")
        return

    for team, role_id in team_roles.items():
        role = discord.utils.get(guild.roles, id=role_id)
        if role:
            for member in role.members:
                team_members[team].add(member.id)
    logging.debug("Team members initialized based on existing roles.")

@bot.event
async def on_ready():
    """Start the taunt loop when the bot is ready."""
    await initialize_team_members()
    if teams_set and game_started:
        taunt_teams.start()
    logging.debug(f"Logged in as {bot.user}")
    logging.debug(f"Loaded Bonus Tile Completions on startup: {bonus_tile_completions}")
    logging.debug(f"Loaded Team Positions on startup: {team_positions}")
    logging.debug(f"Loaded Team Data on startup: {team_data}")

async def prompt_confirmation(ctx, number):
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['y', 'n']

    await ctx.send(f"Confirm {number} of teams, Y or N.")
    try:
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        return msg.content.lower() == 'y'
    except asyncio.TimeoutError:
        await ctx.send("Confirmation timed out.")
        return False

async def prompt_bonus_choice(ctx):
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['1', '2', '3']

    bonus_message = (
        "**Choose your bonus option:**\n"
        "1 - Monkey's Paw 🐾\n"
        "2 - GP 💰\n"
        "3 - Sabotage 😈"
    )

    await ctx.send(bonus_message)
    try:
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        return msg.content.lower()
    except asyncio.TimeoutError:
        return None

def command_cooldown(func):
    @wraps(func)
    async def wrapper(ctx, *args, **kwargs):
        user_id = ctx.author.id

        if await check_timeout(ctx):
            await ctx.send(f"You are currently in a timeout, {ctx.author.mention}.")
            return

        if await handle_spam(ctx):
            await ctx.send(f"To prevent spam, you are on a 5 minute timeout, {ctx.author.mention}.")
            return

        await func(ctx, *args, **kwargs)
    return wrapper

# Specific cooldown for !pester command
def specific_cooldown(rate, per):
    def decorator(func):
        @wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            user_id = ctx.author.id
            if user_id in user_cooldowns:
                if "pester" in user_cooldowns[user_id]:
                    last_used = user_cooldowns[user_id]["pester"]
                    now = datetime.utcnow()
                    if now < last_used + timedelta(seconds=per):
                        remaining_time = (last_used + timedelta(seconds=per) - now).total_seconds()
                        await ctx.send(f"You're using !pester too frequently. Try again in {remaining_time:.0f} seconds.")
                        return
            user_cooldowns[user_id]["pester"] = datetime.utcnow()
            return await func(ctx, *args, **kwargs)
        return wrapper
    return decorator

def category_check():
    def predicate(ctx):
        return in_designated_category(ctx)
    return commands.check(predicate)

def captain_command_check():
    def predicate(ctx):
        return in_captain_commands_channel(ctx)
    return commands.check(predicate)

@bot.command()
@commands.has_permissions(administrator=True)
@category_check()
@command_cooldown
async def set_teams(ctx, number: int):
    """Set the number of teams for the game, if the user is an administrator."""
    global number_of_teams, teams_set

    if teams_set:
        await ctx.send("Teams have already been set and cannot be changed.")
        return

    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Only administrators can set the number of teams.")
        return

    if number < 1 or number > 8:
        await ctx.send("Please choose a number of teams between 1 and 8.")
        return

    if await prompt_confirmation(ctx, number):
        number_of_teams = number
        teams_set = True
        for i in range(1, number_of_teams + 1):
            team_name = f"team{i}"
            team_data[team_name] = ""
            team_positions[team_name] = 1
            team_has_rolled[team_name] = False
            team_advantages[team_name] = None
            tile_completion_times[team_name] = []
        await ctx.send(f"The game will be played with {number_of_teams} teams.")
        save_state()
    else:
        await ctx.send("Number of teams setting canceled.")

@bot.command()
@commands.has_permissions(administrator=True)
@category_check()
@command_cooldown
async def start(ctx):
    """Start the game, if the user is an administrator."""
    global game_started

    if not teams_set:
        await ctx.send("Teams have not been set yet. Please use !set_teams to set the number of teams.")
        return

    if game_started:
        await ctx.send("The game has already started.")
        return

    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Only administrators can start the game.")
        return

    game_started = True

    for team in list(team_data.keys())[:number_of_teams]:
        team_positions[team] = 1  # Ensure all teams are at tile 1
        team_has_rolled[team] = False  # Reset the roll status for all teams
        # Initialize tile_completion_times for each team
        tile_completion_times[team] = []
        # Start the timer for the first tile
        tile_start_times[team] = datetime.now()

    await ctx.send("The game has started! All teams are on tile 1.")

    # Notify each team about their starting tile and task
    for team in list(team_data.keys())[:number_of_teams]:
        role_id = team_roles.get(team)
        if role_id:
            role = ctx.guild.get_role(role_id)
            if role:
                task = tile_tasks.get(1, default_task_message)
                await ctx.send(f"{role.mention} You are beginning on tile 1. Your task is: {task}. Good luck!")

    save_state()

@bot.command()
@commands.check(is_captain)
@captain_command_check()
@command_cooldown
async def set_name(ctx, team: str, *team_name):
    """Set the team name, if the user is a captain."""
    if not teams_set:
        await ctx.send("Teams have not been set yet. Please use !set_teams to set the number of teams.")
        return

    team = resolve_team_identifier(team)
    if team is None:
        await ctx.send(f"Invalid team. Please choose from {', '.join(team_data.keys())}.")
        return

    team_name = " ".join(team_name)  # Join the team_name tuple into a single string with spaces
    team_data[team] = team_name

    await ctx.send(f"Team {team} is now called {team_name}.")
    save_state()

@bot.command()
@commands.has_permissions(administrator=True)
@captain_command_check()
@command_cooldown
async def set_captain(ctx, member: discord.Member, team: str):
    """Assign a captain, if the user is an administrator."""
    if not teams_set:
        await ctx.send("Teams have not been set yet. Please use !set_teams to set the number of teams.")
        return

    team = resolve_team_identifier(team)
    if team is None:
        await ctx.send(f"The team {team} does not exist.")
        return

    captains[member.id] = team
    captain_role = discord.utils.get(ctx.guild.roles, name="Team Captain")
    if captain_role:
        await member.add_roles(captain_role)
    await ctx.send(f"{member.display_name} has been assigned as captain of {team} and given the Team Captain role.")
    save_state()

@bot.command()
@commands.check(is_captain)
@captain_command_check()
@command_cooldown
async def assign_members(ctx, team: str, *members: discord.Member):
    """Assign members to a team."""
    if not teams_set:
        await ctx.send("Teams have not been set yet. Please use !set_teams to set the number of teams.")
        return

    team = resolve_team_identifier(team)
    if team is None:
        await ctx.send(f"Invalid team. Please choose from {', '.join(team_data.keys())}.")
        return

    team_role = discord.utils.get(ctx.guild.roles, id=team_roles.get(team))
    if not team_role:
        await ctx.send(f"Role for {team} not found. Please ensure the role exists.")
        return

    for member in members:
        try:
            team_members[team].add(member.id)
            await member.add_roles(team_role)
            await ctx.send(f"{member.display_name} has been assigned to {team} and given the role {team_role.name}.")
        except discord.Forbidden:
            await ctx.send(
                f"Failed to assign role to {member.display_name}. Check the bot's role hierarchy and permissions.")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
    save_state()

dice_emojis = {
    1: "1️⃣",
    2: "2️⃣",
    3: "3️⃣",
    4: "4️⃣",
    5: "5️⃣",
    6: "6️⃣"
}

async def handle_roll(team):
    roll = random.randint(1, 6)
    roll_message = f"You rolled a {dice_emojis[roll]}"

    # Apply advantage or sabotage if present
    if team_advantages[team] == "advantage":
        roll += 1
        roll_message += f". With your advantage, you move {roll} tiles."
    elif team_advantages[team] == "sabotage":
        roll -= 2
        roll_message += f". But you are subject to sabotage, so your roll is reduced by 2 and only move {roll} tiles."
        team_advantages[team] = None  # Reset sabotage after it's been applied

    # Apply multiple sabotages
    if team_sabotages[team] > 0:
        roll -= 2 * team_sabotages[team]
        roll_message += f" Due to {team_sabotages[team]} sabotages, you move {roll} tiles."
        team_sabotages[team] = 0  # Reset sabotage counter after applying

    return roll, roll_message



import random

async def update_team_position(team, roll):
    current_position = team_positions[team]
    new_position = current_position + roll
    hard_stop_message = ""

    # Ensure the new position is within the bounds of the game board
    if new_position < 1:
        new_position = 1
    elif new_position > 69:
        new_position = 69

    if roll > 0:
        for stop_tile in hard_stop_tiles:
            if current_position < stop_tile <= new_position:
                new_position = stop_tile
                hard_stop_message = random.choice(hard_stop_messages).format(roll=roll, tile=new_position)
                break
    else:
        for stop_tile in reversed(hard_stop_tiles):
            if new_position <= stop_tile < current_position and stop_tile not in completed_tiles[team]:
                new_position = stop_tile
                hard_stop_message = random.choice(hard_stop_messages).format(roll=roll, tile=new_position)
                break

    team_positions[team] = new_position
    return new_position, hard_stop_message



@bot.command()
@commands.check(is_captain)
@captain_command_check()
@command_cooldown
async def roll(ctx, *, team: str):
    """Roll the dice to move the team forward, if the user is a captain or administrator."""
    if not teams_set:
        await ctx.send("Teams have not been set yet. Please use !set_teams to set the number of teams.")
        return

    if not game_started:
        await ctx.send("The game has not started yet. Please use !start to start the game.")
        return

    team = resolve_team_identifier(team)
    if team is None:
        await ctx.send(f"The team {team} does not exist.")
        return

    if team_data[team] == "":
        await ctx.send(f"Team {team} must set a name using !set_name before rolling.")
        return

    try:
        current_position = team_positions[team]
        logging.debug(f"Team {team} current position: {current_position}")
        if current_position not in completed_tiles[team]:
            response = random.choice(incomplete_tile_responses).format(team=team_data[team])
            await ctx.send(response)
            return

        roll, roll_message = await handle_roll(team)
        new_position, hard_stop_message = await update_team_position(team, roll)

        # Send a random GIF from the list
        random_gif = random.choice(GIF_PATHS)
        if random_gif and os.path.isfile(random_gif):
            await ctx.send(file=discord.File(random_gif))
        else:
            await ctx.send("Error: Could not find the GIF file.")

        if new_position == current_position:
            # Team did not move, they must complete the current tile again
            await ctx.send(f"{roll_message} Due to sabotage, Team {team_data[team]} did not move and must re-complete tile {current_position}.")
            if current_position in completed_tiles[team]:
                completed_tiles[team].remove(current_position)  # Reset the task completion status
            team_has_rolled[team] = False
            return
        else:
            team_positions[team] = new_position
            team_has_rolled[team] = True  # Mark the team as having rolled

            move_message = f" You moved to tile {new_position}."
            await ctx.send(f"🫳 🎲\n\n{roll_message}{move_message}")

            if new_position == 69:
                task = tile_tasks.get(new_position, default_task_message)
                await ctx.send("You've landed on tile 69, nice! Good luck on the last task - may the odds be ever in your favor.")
            else:
                task = tile_tasks.get(new_position, default_task_message)
                await ctx.send(f"Your new task is to complete tile {new_position}: {task}")

            if hard_stop_message:
                await ctx.send(hard_stop_message)

            rolls_count[team] += 1
            # Start the timer for the new tile
            tile_start_times[team] = datetime.now()
            save_state()  # Save state after a successful roll

        # Reset sabotage counter and flag after roll
        team_sabotages[team] = 0
        team_sabotaged[team] = False

    except KeyError as e:
        logging.error(f"KeyError in roll command for team {team}: {e}")
        await ctx.send(f"An error occurred while processing the command: Missing key {e}")
    except Exception as e:
        logging.error(f"Error in roll command: {e}")
        await ctx.send(f"An error occurred while processing the command: {str(e)}")


@bot.command()
@commands.check(is_captain)
@captain_command_check()
@command_cooldown
async def complete(ctx, *, input: str):
    """Mark a tile task as complete, if the user is a captain or administrator."""
    if not teams_set:
        await ctx.send("Teams have not been set yet. Please use !set_teams to set the number of teams.")
        return

    if not game_started:
        await ctx.send("The game has not started yet. Please use !start to start the game.")
        return

    await sync_team_members()  # Sync team members before processing the command

    try:
        team, tile_str, member_str = input.rsplit(' ', 2)
        team = resolve_team_identifier(team)
        if team is None:
            await ctx.send(f"The team {team} does not exist.")
            return

        try:
            tile = int(tile_str)
        except ValueError:
            await ctx.send(
                f"Invalid tile number '{tile_str}'. Please provide a valid number for the tile number. For example: !complete <team name> <tile_number> <@member>")
            return

        member = await commands.MemberConverter().convert(ctx, member_str)

        if member.id not in team_members[team]:
            await ctx.send(f"{member.display_name} is not a member of team {team_data[team]}.")
            return

        current_position = team_positions.get(team)
        if current_position is None:
            await ctx.send(f"Team {team_data.get(team, 'Unknown')} does not have a valid position.")
            return

        if tile != current_position:
            await ctx.send(f"Team {team_data[team]} is not on tile {tile}. Current position is {current_position}.")
            return

        if tile in completed_tiles[team]:
            await ctx.send(f"Tile {tile} has already been marked as complete for team {team_data[team]}.")
            return

        completed_tiles[team].add(tile)
        tile_completions[team].append((tile, member.id))
        player_completions[member.id] = player_completions.get(member.id, 0) + 1
        await ctx.send(f"Tile {tile} marked as complete for team {team_data[team]} by {member.display_name}.")

        # Record the completion time
        completion_time = datetime.now()
        if team in tile_start_times:
            start_time = tile_start_times.pop(team)
            tile_completion_times[team].append((tile, completion_time - start_time))

        # Handle completion of tile 69
        if tile == 69:
            await ctx.send(f"Tile 69 marked as complete for team {team_data[team]} by {member.display_name}.")
            await ctx.send(
                f"**🎉 CUMGRADULATIONS {team_data[team]}! You've completed the final tile and won the game! 🎉**")

            gif_path = os.getenv('GIF11_PATH')  # Ensure this environment variable is set with the correct path to gif11
            if gif_path and os.path.isfile(gif_path):
                await ctx.send(file=discord.File(gif_path))
            else:
                await ctx.send("Error: Could not find the GIF file for the congratulatory message.")

        save_state()  # Save state after marking a tile as complete
    except Exception as e:
        logging.error(f"Error in complete command: {e}")
        await ctx.send(f"An error occurred while processing the command: {str(e)}")


@bot.command()
@category_check()
@command_cooldown
async def board(ctx):
    """Secret command to display all tiles on the board."""
    taylor2ya_id = 472000479476580362

    if ctx.author.id == taylor2ya_id:
        response = "**All Tiles on the Board**\n\n"
        for tile, task in tile_tasks.items():
            response += f"Tile {tile}: {task}\n"
        await ctx.send(response)
    else:
        await ctx.send(f"Hey everyone, @{ctx.author.display_name} just tried to do something very silly!")


@bot.command()
@commands.check(is_captain)
@captain_command_check()
@command_cooldown
async def complete_bonus(ctx, *, input: str):
    """Mark a bonus tile task as complete, if the user is a captain."""
    if not teams_set:
        await ctx.send("Teams have not been set yet. Please use !set_teams to set the number of teams.")
        return

    if not game_started:
        await ctx.send("The game has not started yet. Please use !start to start the game.")
        return

    try:
        # Parsing input
        team, tile_str, member_str = input.rsplit(' ', 2)
        tile = str(int(tile_str))  # Ensure tile is a string
        member = await commands.MemberConverter().convert(ctx, member_str)

        # Resolve team
        team = resolve_team_identifier(team)
        if team is None:
            await ctx.send(f"The team {team} does not exist.")
            return

        # Check if member is part of the team
        if member.id not in team_members[team]:
            await ctx.send(f"{member.display_name} is not a member of team {team_data[team]}.")
            return

        # Check if the tile is a valid bonus tile
        if tile not in bonus_tasks:
            await ctx.send("Invalid bonus tile. Please choose a valid bonus tile.")
            return

        # Check if the bonus tile has already been completed by the team
        if tile in bonus_tile_completions[team]:
            await ctx.send(f"Bonus tile {tile} has already been completed by team {team_data[team]}.")
            return

        # Mark the bonus tile as complete
        bonus_tile_completions[team][tile] = member.id
        logging.debug(f"Marked bonus tile {tile} as complete for team {team_data[team]}")
        await ctx.send(f"Bonus tile {tile} marked as complete for team {team_data[team]} by {member.display_name}.")

        # Choose a reward
        while True:
            choice = await prompt_bonus_choice(ctx)
            if choice == '1':
                team_advantages[team] = "monkey_paw"
                bonus_choices[team][tile] = "Monkey's Paw"
                await ctx.send(f"Team {team_data[team]} has chosen Monkey's Paw and can use the !redeem command to get a new task.")
                break
            elif choice == '2':
                bonus_choices[team][tile] = "GP"
                gp_amount = 3000000  # Example: 3 million GP per bonus
                team_gp_bonus[team] += gp_amount
                await ctx.send(f"Each member of your team has been awarded 3m GP 💰.")
                break
            elif choice == '3':
                while True:
                    await ctx.send("Which team would you like to sabotage? (Type 'cancel' to abort)")

                    def check_team(m):
                        return m.author == ctx.author and m.channel == ctx.channel

                    try:
                        msg = await bot.wait_for('message', check=check_team, timeout=60.0)
                        if msg.content.lower() == 'cancel':
                            await ctx.send("Sabotage selection canceled.")
                            break
                        target_team = resolve_team_identifier(msg.content.lower())
                        if target_team is None:
                            await ctx.send(f"The team {msg.content.lower()} does not exist. Please try again.")
                            continue
                        if team_sabotaged[target_team]:
                            await ctx.send(f"Team {team_data[target_team]} has already been sabotaged and must roll before being sabotaged again.")
                            continue
                        team_advantages[target_team] = "sabotage"
                        team_sabotaged[target_team] = True
                        bonus_choices[team][tile] = "Sabotage"
                        await ctx.send(f"Team {team_data[target_team]} has been sabotaged and their next roll will be -2.")
                        break
                    except asyncio.TimeoutError:
                        await ctx.send("Sabotage selection timed out.")
                        break
                if msg.content.lower() == 'cancel':
                    continue
                else:
                    break

        # Save the state after marking a bonus tile as complete
        save_state()
    except Exception as e:
        logging.error(f"Error in complete_bonus command: {e}")
        await ctx.send(f"An error occurred while processing the command: {str(e)}")


@bot.command()
@commands.check(is_captain)
@captain_command_check()
@command_cooldown
async def redeem(ctx, *, team: str):
    """Redeem the Monkey's Paw to get a new task for the current tile."""
    if not teams_set:
        await ctx.send("Teams have not been set yet. Please use !set_teams to set the number of teams.")
        return

    if not game_started:
        await ctx.send("The game has not started yet. Please use !start to start the game.")
        return

    team = resolve_team_identifier(team)
    if team is None:
        await ctx.send(f"The team {team} does not exist.")
        return

    if team_advantages[team] != "monkey_paw":
        await ctx.send(f"Team {team_data[team]} does not have a Monkey's Paw to redeem.")
        return

    current_position = team_positions[team]
    new_task = random.choice(list(monkey_paw_tasks.values()))
    tile_tasks[current_position] = new_task
    team_advantages[team] = None  # Consume the Monkey's Paw

    await ctx.send(f"Team {team_data[team]} has redeemed the Monkey's Paw! The new task for tile {current_position} is: {new_task}")
    save_state()

@bot.command()
@commands.check(is_captain)
@captain_command_check()
@command_cooldown
async def choose_bonus(ctx, team: str, choice: str):
    """Allow a team to choose their bonus option if they timed out."""
    team = resolve_team_identifier(team)
    if team is None:
        await ctx.send(f"The team {team} does not exist.")
        return

    if team not in teams_needing_bonus_choice:
        await ctx.send(f"Team {team_data[team]} does not need to make a bonus choice or has already chosen.")
        return

    tile = teams_needing_bonus_choice[team]
    if choice == '1':
        team_advantages[team] = "monkey_paw"
        bonus_choices[team][tile] = "Monkey's Paw"
        await ctx.send(f"Team {team_data[team]} has chosen Monkey's Paw and can use the !redeem command to get a new task.")
    elif choice == '2':
        bonus_choices[team][tile] = "GP"
        await ctx.send("Each member of your team has been awarded 3m GP 💰.")
    elif choice == '3':
        await ctx.send("Which team would you like to sabotage? (Type 'cancel' to abort)")

        def check_team(m):
            return m.author == ctx.author and m.channel == ctx.channel

        while True:
            try:
                msg = await bot.wait_for('message', check=check_team, timeout=60.0)
                if msg.content.lower() == 'cancel':
                    await ctx.send("Sabotage selection canceled.")
                    return
                target_team = resolve_team_identifier(msg.content.lower())
                if target_team is None:
                    await ctx.send(f"The team {msg.content.lower()} does not exist. Please try again.")
                    continue
                team_advantages[target_team] = "sabotage"
                bonus_choices[team][tile] = "Sabotage"
                await ctx.send(f"Team {team_data[target_team]} has been sabotaged and their next roll will be -2.")
                break
            except asyncio.TimeoutError:
                await ctx.send("Sabotage selection timed out.")
                return
    else:
        await ctx.send("Invalid choice. Please select 1, 2, or 3.")

    del teams_needing_bonus_choice[team]
    save_state()

@bot.command()
@category_check()
@command_cooldown
async def completed(ctx, *, team: str):
    """List completed tiles for the team, including bonus tiles."""
    if not teams_set:
        await ctx.send("Teams have not been set yet. Please use !set_teams to set the number of teams.")
        return

    if not game_started:
        await ctx.send("The game has not started yet. Please use !start to start the game.")
        return

    team = resolve_team_identifier(team)
    if team is None:
        await ctx.send(f"The team {team} does not exist.")
        return

    try:
        team_name = team_data.get(team, team.capitalize())
        completed = "\n".join([
            f"**Tile {tile}** ({tile_tasks.get(tile, default_task_message)}) - "
            f"**{(user.display_name if (user := bot.get_user(member_id)) else 'Unknown')}**"
            for tile, member_id in tile_completions[team]
        ])
        bonus_completed = "\n".join([
            f"**Bonus Tile {tile}** ({bonus_tasks.get(tile, default_task_message)}) - "
            f"**{(user.display_name if (user := bot.get_user(member_id)) else 'Unknown')}**"
            for tile, member_id in bonus_tile_completions[team].items()
        ])

        response = f"**{team_name} ({team})**\n"
        if completed:
            response += f"\n**Completed Tiles:**\n\n{completed}"
        else:
            response += "\nNo regular tiles completed."

        if bonus_completed:
            response += f"\n\n**Bonus Tiles:**\n\n{bonus_completed}"
        else:
            response += "\n\nNo bonus tiles completed."

        await ctx.send(response)
    except Exception as e:
        logging.error(f"Error in completed command: {e}")
        await ctx.send(f"An error occurred while processing the command: {str(e)}")



@bot.command()
@category_check()
@command_cooldown
async def completed_tasks(ctx, *, member: discord.Member):
    """Display how many tiles a player has completed, including bonus tiles, along with the tasks."""
    if not teams_set:
        await ctx.send("Teams have not been set yet. Please use !set_teams to set the number of teams.")
        return

    if not game_started:
        await ctx.send("The game has not started yet. Please use !start to start the game.")
        return

    try:
        # Regular tiles completed by the member
        regular_tiles = [
            f"**Tile {tile}**: {tile_tasks.get(tile, default_task_message)} (Team {team_data[team]})"
            for team, completions in tile_completions.items()
            for tile, member_id in completions
            if member_id == member.id
        ]

        # Bonus tiles completed by the member
        bonus_tiles = [
            f"**Tile {tile}**: {bonus_tasks.get(tile, default_task_message)} (Team {team_data[team]})"
            for team, completions in bonus_tile_completions.items()
            for tile, member_id in completions.items()
            if member_id == member.id
        ]

        if not regular_tiles and not bonus_tiles:
            response = random.choice(no_tiles_completed_responses).format(team=member.display_name)
            await ctx.send(response)
        else:
            response = f"**{member.display_name}** has completed the following regular tiles:\n" + "\n".join(regular_tiles)
            if bonus_tiles:
                response += f"\n\n**{member.display_name}** has completed the following bonus tiles:\n" + "\n".join(bonus_tiles)
            await ctx.send(response)
    except Exception as e:
        logging.error(f"Error in completed_tasks command: {e}")
        await ctx.send(f"An error occurred while processing the command: {str(e)}")


@bot.command()
@category_check()
@command_cooldown
async def current(ctx):
    """List all teams, their current tiles, and tasks."""
    if not teams_set:
        await ctx.send("Teams have not been set yet. Please use !set_teams to set the number of teams.")
        return

    if not game_started:
        await ctx.send("The game has not started yet. Please use !start to start the game.")
        return

    try:
        current_list = []
        for team, position in team_positions.items():
            team_name = team_data[team] if team_data[team] else team.capitalize()
            task = tile_tasks.get(position, default_task_message)
            task_status = " - **Task completed, pending next roll**" if position in completed_tiles[team] else ""
            current_list.append(f"**{team_name}** (Team {team[-1]}) is on **tile {position}**\n"
                                f"**Task:** {task}{task_status}\n")

        formatted_output = "\n".join(current_list)
        await ctx.send(f"**Current Teams, Tiles, and Tasks**:\n\n{formatted_output}")
    except Exception as e:
        logging.error(f"Error in current command: {e}")
        await ctx.send(f"An error occurred while processing the command: {str(e)}")

@bot.command()
@category_check()
@command_cooldown
async def commandlist(ctx):
    """List all available bot commands."""
    captain_role = discord.utils.get(ctx.guild.roles, name="Team Captain")
    is_captain = captain_role in ctx.author.roles if captain_role else False
    is_admin = ctx.author.guild_permissions.administrator

    general_commands = [
        ("!completed <team>", "List all completed tiles for a team"),
        ("!completed_all", "Show all teams and the tiles they have completed"),
        ("!current", "List all teams, their current tiles, and tasks"),
        ("!completed_tasks <@member>", "Display how many tiles a player has completed"),
        ("!mvp", "Show the top 3 players who have completed the most tiles"),
        ("!commandlist", "List all available bot commands"),
        ("!bonus_tiles <team>", "View the bonus tiles completed by a specific team"),
        ("!description", "Provide a brief description of the Grottopoly game"),
        ("!pester", "The only command you can spam"),
        ("!yellow_tiles", "Explains what yellow tiles are"),
        ("!monkeys_paw", "Explain how the Monkey's Paw bonus works"),
        ("!sabotage", "Explain what the sabotage bonus does"),
        ("!gp", "Explain what the GP bonus does")  # Adding the new command here
    ]

    captain_commands = [
        ("!set_name <team> <team_name>", "Set your team's custom name"),
        ("!assign_members <team> <@members...>", "Assign members to a team and give them the team role"),
        ("!roll <team>", "Roll the dice to move your team forward"),
        ("!complete <team> <tile_number> <@member>", "Mark a tile task as complete by a specific member"),
        ("!complete_bonus <team> <tile_number> <@member>", "Mark a bonus tile task as complete by a specific member"),
        ("!redeem <team>", "Redeem the Monkey's Paw to get a new task for the current tile"),
        ("!statistics", "Show statistics for each team")
    ]

    admin_commands = [
        ("!set_teams <number>", "Set the number of teams"),
        ("!start", "Start the game (administrators only)"),
        ("!set_captain <@member> <team>", "Assign a captain to a team and give them the Team Captain role"),
        ("!members", "List all members assigned to each team")
    ]

    response = "**Basic Commands**\n"
    for command, description in general_commands:
        response += f"`{command}` - {description}\n"

    if is_captain or is_admin:
        response += "\n**Captain Commands**\n"
        for command, description in captain_commands:
            response += f"`{command}` - {description}\n"

    if is_admin:
        response += "\n**Admin Commands**\n"
        for command, description in admin_commands:
            response += f"`{command}` - {description}\n"

    await ctx.send(response)


@bot.command()
@category_check()
@command_cooldown
async def description(ctx):
    """Provide a brief description of the Grottopoly game."""
    description_text = (
        "**🎲 Grottopoly Game Overview 🎲**\n"
        "\n"
        "Welcome to **Grottopoly**, a unique and engaging twist on the traditional bingo competition, brought to life within a Discord server. "
        "Combining elements of classic board games and Old School RuneScape challenges, Grottopoly creates a dynamic and competitive experience for players.\n"
        "\n"
        "**Game Objective**:\n"
        "Teams compete to advance across a virtual game board by completing specific skilling, bossing, and collection log-related tasks on each tile. "
        "The ultimate goal is to be the first team to reach and complete the final tile, overcoming various challenges and leveraging strategic advantages along the way.\n"
        "\n"
        "**Key Features**:\n"
        "• **Teamwork**: Collaborate with your team to strategize and complete tasks efficiently.\n"
        "• **Challenges**: Encounter a variety of tasks that test your skills in different aspects of Old School RuneScape.\n"
        "• **Bonuses**: Land on special tiles that offer rewards or opportunities to hinder your opponents.\n"
        "• **Competition**: Race against other teams to see who can navigate the board and complete all tasks first.\n"
        "\n"
        "Are you ready to roll the dice and lead your team to victory? Let the games begin!"
    )
    await ctx.send(description_text)


@bot.command()
@category_check()
@command_cooldown
async def completed_all(ctx):
    """Show all teams and the tiles they have completed, along with who completed each tile."""
    if not teams_set:
        await ctx.send("Teams have not been set yet. Please use !set_teams to set the number of teams.")
        return

    if not game_started:
        await ctx.send("The game has not started yet. Please use !start to start the game.")
        return

    try:
        completed_list = []
        for team in team_data.keys():
            team_name = team_data[team] if team_data[team] else team.capitalize()
            completed_tiles_list = []
            for tile, member_id in tile_completions[team]:
                member = ctx.guild.get_member(member_id)
                if member:
                    display_name = member.display_name
                else:
                    display_name = "Unknown"
                completed_tiles_list.append(
                    f"**Tile {tile}** ({tile_tasks.get(tile, default_task_message)}) - **{display_name}**")

            if completed_tiles_list:
                completed_list.append(f"**{team_name} ({team})**:\n" + "\n".join(completed_tiles_list))
            else:
                completed_list.append(f"**{team_name} ({team})**:\n*No tiles completed.*")

        response = "\n\n".join(completed_list)
        await ctx.send(response)
    except Exception as e:
        logging.error(f"Error in completed_all command: {e}")
        await ctx.send(f"An error occurred while processing the command: {str(e)}")


@bot.command()
@category_check()
@command_cooldown
async def mvp(ctx):
    """Show the top 3 players who have completed the most tiles."""
    if not teams_set:
        await ctx.send("Teams have not been set yet. Please use !set_teams to set the number of teams.")
        return

    if not game_started:
        await ctx.send("The game has not started yet. Please use !start to start the game.")
        return

    if not player_completions:
        await ctx.send("No tiles have been completed yet.")
        return

    try:
        # Calculate regular tile completions for each player
        regular_completions = defaultdict(int)
        for completions in tile_completions.values():
            for tile, member_id in completions:
                regular_completions[member_id] += 1

        # Find the top players based on regular completions only
        top_players = sorted(regular_completions.items(), key=lambda x: x[1], reverse=True)[:3]

        if not top_players:
            await ctx.send("No players have completed any regular tiles yet.")
            return

        # Prepare response
        response = "🏆🌟 **Top 3 MVPs of the Game** 🌟🏆\n\n"

        medals = ["🥇", "🥈", "🥉"]
        previous_tiles = None
        medal_index = 0
        lines = []
        tied_players = []

        for i, (player_id, tiles) in enumerate(top_players):
            player = await bot.fetch_user(player_id)
            display_name = ctx.guild.get_member(player_id).display_name

            if previous_tiles is not None and tiles == previous_tiles:
                tied_players.append(display_name)
            else:
                if tied_players:
                    if len(tied_players) > 1:
                        lines.append(f"{current_medal} **{'** and **'.join(tied_players)}** have all completed {previous_tiles} tiles and are tied!")
                    else:
                        lines.append(f"{current_medal} **{tied_players[0]}**: {previous_tiles} completed tiles")
                    tied_players = []

                if medal_index >= len(medals):
                    break

                current_medal = medals[medal_index]
                tied_players.append(display_name)
                previous_tiles = tiles
                medal_index += 1

        if tied_players:
            if len(tied_players) > 1:
                lines.append(f"{current_medal} **{'** and **'.join(tied_players)}** have all completed {previous_tiles} tiles and are tied!")
            else:
                lines.append(f"{current_medal} **{tied_players[0]}**: {previous_tiles} completed tiles")

        response += "\n\n".join(lines)
        await ctx.send(response)
    except Exception as e:
        logging.error(f"Error in mvp command: {e}")
        await ctx.send(f"An error occurred while processing the command: {str(e)}")


def format_duration(seconds):
    """
    Convert seconds to a human-readable format of days, hours, minutes, and seconds.
    """
    duration = timedelta(seconds=seconds)
    days = duration.days
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

    return ", ".join(parts)

@bot.command()
@commands.has_permissions(administrator=True)
@captain_command_check()
@command_cooldown
async def statistics(ctx):
    """Show statistics for each team."""
    if not teams_set:
        await ctx.send("Teams have not been set yet. Please use !set_teams to set the number of teams.")
        return

    if not game_started:
        await ctx.send("The game has not started yet. Please use !start to start the game.")
        return

    try:
        stats = []
        for team, position in team_positions.items():
            team_name = team_data[team] if team_data[team] else team.capitalize()

            if team not in rolls_count:
                stats.append(
                    f"**{team_name}** (Team {team[-1]}) has not rolled yet. They are currently on **tile {position}**.\n"
                )
                continue

            if not tile_completion_times[team]:
                stats.append(
                    f"**{team_name}** (Team {team[-1]}) has not finished their start tile and cannot roll past **tile {position}**.\n"
                )
                continue

            # Collect unique completed tiles and times
            unique_completions = {tile: time for tile, time in tile_completion_times[team]}
            completed_times = list(unique_completions.values())

            if len(completed_times) > 1:
                total_time = sum(time.total_seconds() for time in completed_times)
                avg_time = total_time / len(completed_times)
                slowest_tile = max(completed_times, key=lambda x: x.total_seconds()).total_seconds()
                fastest_tile = min(completed_times, key=lambda x: x.total_seconds()).total_seconds()
            else:
                avg_time = None
                slowest_tile = None
                fastest_tile = None

            stats.append(
                f"**{team_name}** (Team {team[-1]})\n"
                f"- **Rolls:** {rolls_count[team]}\n"
                f"- **Tiles completed:** {len(unique_completions)}\n"
                f"- **Bonus tiles completed:** {len(bonus_tile_completions[team])}\n"
                f"- **Longest tile to complete:** {format_duration(slowest_tile) if slowest_tile is not None else 'N/A'}\n"
                f"- **Fastest tile to complete:** {format_duration(fastest_tile) if fastest_tile is not None else 'N/A'}\n"
                f"- **Average tile completion time:** {format_duration(avg_time) if avg_time is not None else 'N/A'}\n"
                f"- **Completed tiles:** {', '.join(str(tile) for tile in sorted(unique_completions.keys()))}"
                f"{' - **Task completed, pending next roll**' if team not in tile_start_times else ''}\n"
            )

        formatted_output = "\n\n".join(stats)
        await ctx.send(f"**Team Statistics**:\n\n{formatted_output}")
    except Exception as e:
        logging.error(f"Error in statistics command: {e}")
        await ctx.send(f"An error occurred while processing the command: {str(e)}")


@bot.command()
@commands.has_permissions(administrator=True)
@category_check()
@command_cooldown
async def members(ctx):
    """List all members assigned to each team."""
    if not teams_set:
        await ctx.send("Teams have not been set yet. Please use !set_teams to set the number of teams.")
        return

    if not game_started:
        await ctx.send("The game has not started yet. Please use !start to start the game.")
        return

    try:
        response = []
        for i in range(1, number_of_teams + 1):
            team_key = f"team{i}"
            role_id = team_roles.get(team_key)
            team_role = discord.utils.get(ctx.guild.roles, id=role_id)
            if not team_role:
                response.append(f"**Team {i}**: Role not found.")
                continue

            custom_team_name = team_data.get(team_key, "")
            team_display_name = f"Team {i} ({custom_team_name})" if custom_team_name else f"Team {i}"

            members = [member.display_name for member in team_role.members]
            if not members:
                response.append(f"**{team_display_name}**: No members assigned.")
            else:
                response.append(f"**{team_display_name}**:\n" + "\n".join(members))

        await ctx.send("\n\n".join(response))
    except Exception as e:
        logging.error(f"Error in members command: {e}")
        await ctx.send(f"An error occurred while processing the command: {str(e)}")

@bot.command()
@category_check()
@command_cooldown
async def bonus_tiles(ctx):
    """Provide a general description of bonus tiles and the choices available upon their completion."""
    response = (
        "**:bangbang: Bonus Tiles :bangbang:**\n\n"
        "Bonus tiles are special tiles that can be completed at any time, but only once per team. "
        "Upon completing a bonus tile, your team can choose one of the following bonuses:\n"
        "- **Monkey's Paw**: Grants a special task with unique rewards. Use `!monkeys_paw` to learn more.\n"
        "- **GP (Gold Pieces)**: Awards a certain amount of GP to each team member. Use `!gp` to learn more.\n"
        "- **Sabotage**: Allows you to hinder another team's progress. Use `!sabotage` to learn more.\n\n"
        "To mark a bonus tile as complete, use the command `!complete_bonus` command."
    )
    await ctx.send(response)


@bot.command(name="completed_bonus")
@category_check()
@command_cooldown
async def completed_bonus(ctx, *, team: str):
    """Show the bonus tiles completed by a specific team and the members who completed them."""
    if not game_started:
        await ctx.send("The game has not started yet. Please wait until the game starts to use this command.")
        return

    team = resolve_team_identifier(team)
    if team is None:
        await ctx.send(f"The team {team} does not exist.")
        return

    bonuses = bonus_tile_completions[team]
    logging.debug(f"Bonus tiles for team {team}: {bonuses}")  # Log the bonus tiles
    response = f"**Bonus Tiles Completed by {team_data[team]}:**\n"

    for tile, task in bonus_tasks.items():
        if tile in bonuses:
            member_id = bonuses[tile]
            member = ctx.guild.get_member(member_id)
            member_name = member.display_name if member else str(member_id)
            response += f"Bonus Tile {tile} ({task}) - {member_name}\n"
            logging.debug(f"Bonus tile {tile} for team {team_data[team]} completed by {member_name}")  # Log each completion
        else:
            response += f"Bonus Tile {tile} ({task}) - Not completed\n"

    await ctx.send(response)


@bot.command()
@category_check()
@command_cooldown
async def bonus_tiles_list(ctx):
    """List all available bonus tiles."""
    response = f"**:boom: Available Bonus Tiles :boom:**\n\n"
    for tile, task in bonus_tasks.items():
        response += f"{tile} - {task}\n"
    await ctx.send(response)


@bot.command()
@commands.has_permissions(administrator=True)
@category_check()
@command_cooldown
async def rules(ctx):
    """Display the game rules."""
    images = [
        os.getenv("IMAGE1_PATH"),  # First image
        os.getenv("IMAGE2_PATH"),  # Second image
        os.getenv("IMAGE3_PATH"),  # Third image
        os.getenv("IMAGE4_PATH"),  # Fourth image
        os.getenv("IMAGE5_PATH")  # Fifth image
    ]

    # Part 1: Drop Verification and images 1-3
    part1 = (
        "**🎲 Grottopoly Bingo Rules 🎲**\n\n"
        "**1. Drop Verification**\n"
        "In order for a drop to count towards any tile, you must provide a screenshot with the 'Clan Events' plugin visible on your screen. "
        "Please make sure this is set up and is showing for any drops received during the bingo - as drops will not count if this is not showing.\n"
        "This is essentially an overlay, which provides the event name, date, and time.\n\n"
        "**1.1 Setting up 'Clan Events'**\n"
        "Search 'Clan Events' on the plugin hub & download:\n"
    )
    await ctx.send(part1, file=discord.File(images[0]))

    part1_continued = (
        "**1.2 Enabling the Overlay**\n"
        "Make sure it is turned on, at the top right.\n"
        "Click the 'Display the overlay'.\n"
        "Set the event password to 'Grotto Bingo'.\n"
        "Click 'include date & time'.\n"
        "Password color can be whatever you choose.\n"
    )
    await ctx.send(part1_continued, file=discord.File(images[1]))

    part1_continued_2 = (
        "**1.3 Example of the Overlay**\n"
        "This is how the overlay should look in-game. Feel free to move this overlay around anywhere on your screen. "
        "It just needs to be visible for verification purposes.\n"
    )
    await ctx.send(part1_continued_2, file=discord.File(images[2]))

    part1_continued_3 = (
        "**1.4 For Mobile/Steam Users**\n"
        "For those of you who may play on mobile or Steam, please have the clan chat open for screenshots and the drop visible in the clan box.\n\n"
    )
    await ctx.send(part1_continued_3)

    # Part 2: Posting screenshots and image 4
    part2 = (
        "**2. Posting Screenshots**\n"
        "Screenshots of drops must be posted in the relevant 'drops' channel within your own team's chat channels. We do not want to be sifting through loads of Barrows drops in your general drops channel. "
        "See attached photo for where drops should go, whether that is in: drops, barrows-drops, or wilderness-shield.\n"
        "We encourage you to share your drops over in the main <#697877518513864793> channel as well - let's keep the Discord looking alive and well.\n\n"
    )
    await ctx.send(part2, file=discord.File(images[3]))

    # Part 3: Account Usage
    part3 = (
        "**3. Account Usage**\n"
        "The use of an alt/main account is generally not allowed as you should be playing with your team.\n\n"
    )
    await ctx.send(part3)

    # Part 4: Tile Submission Decisions
    part4 = (
        "**4. Tile Submission Decisions**\n"
        "The final decision for the submissions of tiles is with the mods. If you fail to include the event overlay, for instance, please let us know ASAP and we will try to be as lenient as possible, whilst ensuring that it is fair on other teams.\n\n"
    )
    await ctx.send(part4)

    # Part 5: Prizes
    part5 = (
        "**5. Prizes**\n"
        "The prizes will be divided as follows:\n"
        "• 1st place team - 60%\n"
        "• 2nd place team - 30%\n"
        "• The MVP of the overall bingo will receive 10% of the total prize pool!\n"
        "**5.1 MVP Selection**\n"
        "The MVP will be decided based upon total points earned for their team. In the result of a tie, both players will split the prize pool.\n\n"
    )
    await ctx.send(part5)

    # Part 6: Using TempleOSRS and image 5
    part6 = (
        "**6. Using TempleOSRS**\n"
        "We will be using TempleOSRS to track exp gains and boss KCs during the bingo. Please install the XP updater plugin from the hub and make sure 'TempleOSRS' is selected. "
        "This will auto-update your information every time you log out.\n"
    )
    await ctx.send(part6, file=discord.File(images[4]))

    # Part 6.1: Unranked boss KC
    part6_1 = (
        "**6.1 Unranked Boss KC**\n"
        "If you are unranked in a boss, TempleOSRS will not count your KC until you're ranked. In this scenario, you will need to upload a picture of your starting KC to your team's relevant 'starting KC' channel."
    )
    await ctx.send(part6_1)


@bot.command()
@category_check()
@command_cooldown
@specific_cooldown(rate=1, per=180)  # 3-minute cooldown for !pester command
async def pester(ctx):
    """Send a taunt to a random team that hasn't completed their tile."""
    if not teams_set:
        await ctx.send("Teams have not been set yet. Please use !set_teams to set the number of teams.")
        return

    if not game_started:
        await ctx.send("The game has not started yet. Please use !start to start the game.")
        return

    try:
        # List of teams that haven't completed their tile
        incomplete_teams = [team for team, position in team_positions.items() if position not in completed_tiles[team]]

        if not incomplete_teams:
            await ctx.send("All teams have completed their current tiles. No one to pester!")
            return

        # Choose a random team from the incomplete teams
        team_to_pester = random.choice(incomplete_teams)
        team_role_id = team_roles[team_to_pester]
        team_role = ctx.guild.get_role(team_role_id)

        if team_role:
            response = random.choice(taunts).format(team=team_role.mention)
            await ctx.send(response)
        else:
            await ctx.send(f"Could not find the role for team {team_to_pester}.")

    except Exception as e:
        logging.error(f"Error in pester command: {e}")
        await ctx.send(f"An error occurred while processing the command: {str(e)}")

@bot.command()
@category_check()
@command_cooldown
async def yellow_tiles(ctx):
    """Explain the hard stop tiles and their significance."""
    explanation = (
        "🚧 **Yellow Tiles** 🚧\n\n"
        "In **Grottopoly**, certain tiles are designated as 'Yellow Tiles'. These tiles represent team-focused tasks "
        "that must be completed before your team can roll the dice and move forward.\n\n"
        "**Key Points:**\n"
        "After completing the yellow tile, your team will be allowed to **!roll** again and continue progressing."
    )
    await ctx.send(explanation)


@tasks.loop(seconds=TAUNT_INTERVAL_SECONDS)
async def taunt_teams():
    """Send a taunt to the teams that haven't completed their tile every 4 hours."""
    if not game_started:
        return

    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        logging.error(f"Channel with ID {CHANNEL_ID} not found.")
        return

    try:
        for team, position in team_positions.items():
            if position not in completed_tiles[team]:
                role_id = team_roles.get(team)
                if role_id:
                    role_mention = f"<@&{role_id}>"
                    response = random.choice(taunts).format(team=f"{team_data[team]} {role_mention}")
                    await channel.send(response)
    except Exception as e:
        logging.error(f"Error in taunt_teams task: {e}")

@bot.command()
@category_check()
@command_cooldown
async def monkeys_paw(ctx):
    """Explain how the Monkey's Paw bonus works."""
    explanation = (
        "**🐾 Monkey's Paw Bonus 🐾**\n\n"
        "The Monkey's Paw bonus is a special advantage that can be obtained by completing a bonus tile. When your team redeems the Monkey's Paw, you are randomly granted a new task for the current tile you are on, which could be easier or more challenging than the original task.\n\n"
        "**How to Use the Monkey's Paw Bonus**\n"
        "1. Complete a bonus tile.\n"
        "2. Choose the Monkey's Paw as a reward.\n"
        "3. Use the command `!redeem <team>` to redeem the Monkey's Paw bonus for your team.\n"
        "4. The bot will assign a new task to the current tile your team is on.\n\n"
    )
    await ctx.send(explanation)

@bot.command()
@category_check()
@command_cooldown
async def sabotage(ctx):
    """Explain what the sabotage bonus does."""
    explanation = (
        "**😈 Sabotage Bonus 😈**\n\n"
        "The Sabotage bonus is a special disadvantage that you can inflict on another team by completing a bonus tile. When you sabotage another team, their next roll will be reduced by 2, slowing their progress significantly.\n\n"
        "**How to Use the Sabotage Bonus**\n"
        "1. Complete a bonus tile.\n"
        "2. Choose Sabotage as a reward.\n"
        "3. Select the target team you want to sabotage.\n"
        "4. The bot will apply the sabotage to the chosen team, reducing their next roll by 2.\n\n"
        "Use the Sabotage bonus strategically to hinder the progress of strong competitors and increase your chances of winning!"
    )
    await ctx.send(explanation)

@bot.command()
@category_check()
@command_cooldown
async def gp(ctx):
    """Explain what the GP choice does."""
    explanation = (
        "**💰 GP Bonus 💰**\n\n"
        "The GP (Gold Pieces) bonus is a reward that you can choose by completing a bonus tile. When you select the GP bonus, each member of your team will be awarded a certain amount of GP upon conpletion of this Bingo.\n\n"
        "**How to Use the GP Bonus**\n"
        "1. Complete a bonus tile.\n"
        "2. Choose the GP Bonus option.\n"
        "3. Profit.\n"
        "Use the GP bonus to maybe afford a Bond! But in this economy, think again!"
    )
    await ctx.send(explanation)

@bot.command()
@category_check()
@command_cooldown
async def gold(ctx):
    """Display the amount of gold each team has received from the bonus tiles."""
    if not game_started:
        await ctx.send("The game has not started yet. Please wait until the game starts to use this command.")
        return

    if not team_gp_bonus:
        await ctx.send("No teams have received GP bonuses yet.")
        return

    response = "**:money_mouth: Gold Distribution from Bonus Tiles :money_mouth: **\n\n"
    for team, gp in team_gp_bonus.items():
        response += f"{team_data[team]}: {gp} GP per team member!\n"

    await ctx.send(response)


@bot.command()
@commands.has_permissions(administrator=True)
@captain_command_check()
@command_cooldown
async def give(ctx, team: str, tile: int):
    """Admin command to place a team on a specific tile."""
    if not teams_set:
        await ctx.send("Teams have not been set yet. Please use !set_teams to set the number of teams.")
        return

    team = resolve_team_identifier(team)
    if team is None:
        await ctx.send(f"The team {team} does not exist.")
        return

    if tile < 1 or tile > 69:
        await ctx.send("Please provide a valid tile number between 1 and 69.")
        return

    team_positions[team] = tile
    team_has_rolled[team] = True  # Mark the team as having rolled to avoid immediate reroll

    # Reset the completion status for the new tile
    if tile in completed_tiles[team]:
        completed_tiles[team].remove(tile)

    await ctx.send(f"Team {team_data[team]} has been placed on tile {tile}.")
    save_state()  # Save state after moving the team to the specific tile


@bot.command()
@commands.has_permissions(administrator=True)
@captain_command_check()
@command_cooldown
async def assign(ctx, team: str, tile: int):
    """Admin command to mark a task as complete for a team."""
    if not teams_set:
        await ctx.send("Teams have not been set yet. Please use !set_teams to set the number of teams.")
        return

    team = resolve_team_identifier(team)
    if team is None:
        await ctx.send(f"The team {team} does not exist.")
        return

    if tile < 1 or tile > 69:
        await ctx.send("Please provide a valid tile number between 1 and 69.")
        return

    completed_tiles[team].add(tile)
    tile_completions[team].append((tile, None))  # No specific member assigned
    player_completions[None] = player_completions.get(None, 0) + 1

    await ctx.send(f"Tile {tile} marked as complete for team {team_data[team]}.")
    save_state()  # Save state after marking the task as complete

@bot.command()
@category_check()
@command_cooldown
async def howto(ctx):
    """Provide a detailed explanation on how to play the game."""
    howto_text = (
        "**🎲 How to Play Grottopoly 🎲**\n\n"
        "Each team begins on Tile 1 and must complete the task prior to being able to roll. "
        "Captains are allowed to roll for any team and can do so by using the `!roll <team>` command in the <#1269067795874713733>. "
        "If you complete a tile, captains can use the `!complete <team> <tile> <member>` command to mark a tile as complete. "
        "We will use this command to track the overall `!mvp` of the bingo.\n\n"
        "The board is hidden until tiles are rolled on. `!yellow_tiles` are 'hard stop' tiles that have a team-incentivized task to complete. "
        "Once a yellow tile is completed, your team can roll again to continue progressing.\n\n"
        "While playing this bingo, there are `!bonus_tiles` available to passively complete! "
        "By using `!complete_bonus <team> <tile> <member>`, your team will be able to pick a secret reward: Sabotage, GP, or Advantage.\n\n"
        "You can see real-time progress of various teams by using the `!current` command, `!completed_all` command, or `!completed <team>` command.\n\n"
        "For detailed rules, please visit <#1146853066990157894>.\n\n"
        "If you have any questions, please ask a staff member!"
    )
    await ctx.send(howto_text)


# Start the bot
load_state()  # Load the saved state before starting the bot
bot.run(DISCORD_BOT_TOKEN)
