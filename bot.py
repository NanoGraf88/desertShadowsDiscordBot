import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
from threading import Thread
from flask import Flask

# Load environment variables
load_dotenv()

# Create Flask app for health checks (for Render.com)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!", 200

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))

# Configuration
class Config:
    log_channel_id = 1446405582356746382  # LOG CHANNEL ID
    auto_roles = [1343398705965043734]
    
config = Config()

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Server whitelist
ALLOWED_GUILD_ID = 1343366735478132838

# ===== PERSISTENT DROPDOWN VIEW FOR REACTION ROLES =====
class PersistentRoleSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # This makes it persistent!
    
    @discord.ui.select(
        placeholder="Choose your timezone",
        min_values=0,
        max_values=1,
        custom_id="timezone_select",  # Important: custom_id makes it persistent across restarts
        options=[
            discord.SelectOption(label="GMT-8 (PST)", description="Pacific Standard Time", value="role_gmt8", emoji="🌊"),
            discord.SelectOption(label="GMT-5 (EST)", description="Eastern Standard Time", value="role_gmt5", emoji="🌆"),
            discord.SelectOption(label="GMT±0 (GMT)", description="Greenwich Mean Time", value="role_gmt0", emoji="🌧️"),
            discord.SelectOption(label="GMT+1 (CET)", description="Central European Time", value="role_gmt1", emoji="🏰"),
            discord.SelectOption(label="GMT+2 (EET)", description="Eastern European Time", value="role_gmt2", emoji="🌲"),
            discord.SelectOption(label="GMT+3 (ARAT)", description="Arabia Standard Time", value="role_gmt3", emoji="🏜️"),
            discord.SelectOption(label="GMT+8 (CST)", description="China Standard Time", value="role_gmt8_cst", emoji="🏯"),
            discord.SelectOption(label="GMT+9 (JST)", description="Japan Standard Time", value="role_gmt9", emoji="🎌"),
            discord.SelectOption(label="GMT+10 (AEST)", description="Australian Eastern Time", value="role_gmt10", emoji="🐨")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        # Map selection values to actual role IDs
        role_map = {
            'role_gmt8': 1446396768223887361,      # GMT-8 (PST)
            'role_gmt5': 1446396812264210483,      # GMT-5 (EST)
            'role_gmt0': 1446396816626024478,      # GMT±0 (GMT)
            'role_gmt1': 1446396816797990943,      # GMT+1 (CET)
            'role_gmt2': 1446396817372872764,      # GMT+2 (EET)
            'role_gmt3': 1446396818127585381,      # GMT+3 (ARAT)
            'role_gmt8_cst': 1446396818589094009,  # GMT+8 (CST)
            'role_gmt9': 1446396819134222490,      # GMT+9 (JST)
            'role_gmt10': 1446396975367847939      # GMT+10 (AEST)
        }
        
        selected_roles = [role_map[value] for value in select.values]
        member = interaction.user
        
        try:
            # Remove all mapped roles first
            all_mapped_roles = [interaction.guild.get_role(role_id) for role_id in role_map.values()]
            all_mapped_roles = [r for r in all_mapped_roles if r and r in member.roles]
            
            if all_mapped_roles:
                await member.remove_roles(*all_mapped_roles)
            
            # Add selected roles
            roles_to_add = [interaction.guild.get_role(role_id) for role_id in selected_roles]
            roles_to_add = [r for r in roles_to_add if r]
            
            if roles_to_add:
                await member.add_roles(*roles_to_add)
                await interaction.response.send_message('✅ Your roles have been updated!', ephemeral=True)
            else:
                await interaction.response.send_message('✅ Your timezone roles have been removed!', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                f'❌ Failed to update roles. Make sure the bot has permission and its role is above the roles being assigned.\nError: {e}',
                ephemeral=True
            )

# ===== BOT READY EVENT =====
@bot.event
async def on_ready():
    print(f'✅ Bot is online as {bot.user}')
    
    # Register the persistent view so it works after bot restarts
    bot.add_view(PersistentRoleSelectView())
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} slash commands')
    except Exception as e:
        print(f'Error syncing commands: {e}')

# ===== AUTO-ASSIGN ROLES ON MEMBER JOIN =====
@bot.event
async def on_member_join(member):
    print(f'New member joined: {member.name}')
    
    try:
        for role_id in config.auto_roles:
            role = member.guild.get_role(role_id)
            if role:
                await member.add_roles(role)
                print(f'✅ Assigned role {role.name} to {member.name}')
    except Exception as e:
        print(f'Error assigning auto-roles: {e}')

# ===== MESSAGE DELETE LOGGING =====
@bot.event
async def on_message_delete(message):
    print(f'🗑️ Message deleted: "{message.content}" by {message.author}')
    
    if message.author.bot:
        print('  ↳ Ignoring bot message')
        return
    
    if config.log_channel_id is None:
        print('  ↳ No log channel set')
        return
    
    log_channel = message.guild.get_channel(config.log_channel_id)
    if not log_channel:
        print(f'  ↳ Could not find log channel with ID {config.log_channel_id}')
        return

    embed = discord.Embed(
        color=discord.Color.red(),
        description=f"**Content**\n{message.content or '*No content (might be embed/attachment)*'}",
        timestamp=discord.utils.utcnow()
    )
    embed.set_author(name=f"@{message.author.name}", icon_url=message.author.display_avatar.url)
    embed.add_field(
        name="Message deleted in",
        value=f"{message.channel.mention}",
        inline=False
    )
    embed.set_footer(text=f"User ID: {message.author.id}")

    try:
        await log_channel.send(embed=embed)
        print('  ✅ Logged to channel')
    except Exception as e:
        print(f'  ❌ Error logging deleted message: {e}')

# ===== MESSAGE EDIT LOGGING =====
@bot.event
async def on_message_edit(before, after):
    print(f'✏️ Message edited by {after.author}')
    
    if after.author.bot:
        print('  ↳ Ignoring bot message')
        return
    
    if before.content == after.content:
        print('  ↳ Content unchanged (might be embed update)')
        return
    
    if config.log_channel_id is None:
        print('  ↳ No log channel set')
        return
    
    log_channel = after.guild.get_channel(config.log_channel_id)
    if not log_channel:
        print(f'  ↳ Could not find log channel with ID {config.log_channel_id}')
        return

    embed = discord.Embed(
        color=discord.Color.gold(),
        description=f"**Old**\n{before.content or '*No content*'}\n\n**New**\n{after.content or '*No content*'}",
        timestamp=discord.utils.utcnow()
    )
    embed.set_author(name=f"@{after.author.name}", icon_url=after.author.display_avatar.url)
    embed.add_field(
        name=f"Message edited in",
        value=f"{after.channel.mention} - [Jump to message]({after.jump_url})",
        inline=False
    )
    embed.set_footer(text=f"User ID: {after.author.id}")

    try:
        await log_channel.send(embed=embed)
        print('  ✅ Logged to channel')
    except Exception as e:
        print(f'  ❌ Error logging edited message: {e}')

# ===== VOICE CHANNEL LOGGING =====
@bot.event
async def on_voice_state_update(member, before, after):
    print(f'🔊 Voice state update for {member}')
    
    if member.bot:
        print('  ↳ Ignoring bot')
        return
    
    if config.log_channel_id is None:
        print('  ↳ No log channel set')
        return
    
    log_channel = member.guild.get_channel(config.log_channel_id)
    if not log_channel:
        print(f'  ↳ Could not find log channel with ID {config.log_channel_id}')
        return

    # Member joined a voice channel
    if before.channel is None and after.channel is not None:
        print(f'  ↳ Joined voice channel: {after.channel.name}')
        embed = discord.Embed(
            color=discord.Color.blue(),
            title="Member joined voice channel",
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=f"@{member.name}", icon_url=member.display_avatar.url)
        embed.add_field(
            name="Channel",
            value=f"🔊 • {after.channel.mention}",
            inline=False
        )
        embed.set_footer(text=f"User ID: {member.id}")
        
        try:
            await log_channel.send(embed=embed)
            print('  ✅ Logged to channel')
        except Exception as e:
            print(f'  ❌ Error logging voice join: {e}')
    
    # Member left a voice channel
    elif before.channel is not None and after.channel is None:
        print(f'  ↳ Left voice channel: {before.channel.name}')
        embed = discord.Embed(
            color=discord.Color.red(),
            title="Member left voice channel",
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=f"@{member.name}", icon_url=member.display_avatar.url)
        embed.add_field(
            name="Channel",
            value=f"🔊 • {before.channel.mention}",
            inline=False
        )
        embed.set_footer(text=f"User ID: {member.id}")
        
        try:
            await log_channel.send(embed=embed)
            print('  ✅ Logged to channel')
        except Exception as e:
            print(f'  ❌ Error logging voice leave: {e}')
    
    # Member switched voice channels
    elif before.channel is not None and after.channel is not None and before.channel != after.channel:
        print(f'  ↳ Switched from {before.channel.name} to {after.channel.name}')
        embed = discord.Embed(
            color=discord.Color.blue(),
            title="Member changed voice channel",
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=f"@{member.name}", icon_url=member.display_avatar.url)
        embed.add_field(
            name="Before",
            value=f"🔊 • {before.channel.mention}",
            inline=True
        )
        embed.add_field(
            name="After",
            value=f"🔊 • {after.channel.mention}",
            inline=True
        )
        embed.set_footer(text=f"User ID: {member.id}")
        
        try:
            await log_channel.send(embed=embed)
            print('  ✅ Logged to channel')
        except Exception as e:
            print(f'  ❌ Error logging voice switch: {e}')
    else:
        print('  ↳ Other voice state change (mute/deafen/etc), not logging')

# ===== ROLE CHANGE LOGGING =====
@bot.event
async def on_member_update(before, after):
    print(f'👥 Member update for {after}')
    
    # Check if member is a bot
    if before.bot or after.bot:
        print('  ↳ Ignoring bot')
        return
    
    # Check if roles changed
    if before.roles == after.roles:
        print('  ↳ Roles unchanged (might be nickname/avatar update)')
        return
    
    if config.log_channel_id is None:
        print('  ↳ No log channel set')
        return
    
    log_channel = after.guild.get_channel(config.log_channel_id)
    if not log_channel:
        print(f'  ↳ Could not find log channel with ID {config.log_channel_id}')
        return

    # Find added roles
    added_roles = [role for role in after.roles if role not in before.roles]
    # Find removed roles
    removed_roles = [role for role in before.roles if role not in after.roles]
    
    print(f'  ↳ Added: {[r.name for r in added_roles]}, Removed: {[r.name for r in removed_roles]}')
    
    # Send separate embeds for added and removed roles
    if added_roles:
        for role in added_roles:
            embed = discord.Embed(
                color=discord.Color.green(),
                title="Role added",
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(name=f"@{after.name}", icon_url=after.display_avatar.url)
            embed.description = role.mention
            embed.set_footer(text=f"User ID: {after.id}")
            
            try:
                await log_channel.send(embed=embed)
                print(f'  ✅ Logged role add: {role.name}')
            except Exception as e:
                print(f'  ❌ Error logging role add: {e}')
    
    if removed_roles:
        for role in removed_roles:
            embed = discord.Embed(
                color=discord.Color.red(),
                title="Role removed",
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(name=f"@{after.name}", icon_url=after.display_avatar.url)
            embed.description = role.mention
            embed.set_footer(text=f"User ID: {after.id}")
            
            try:
                await log_channel.send(embed=embed)
                print(f'  ✅ Logged role remove: {role.name}')
            except Exception as e:
                print(f'  ❌ Error logging role remove: {e}')

# ===== SLASH COMMAND: CREATE EMBED =====
@bot.tree.command(name="embed", description="Create a custom embed")
@app_commands.describe(
    title="Embed title",
    description="Embed description",
    color="Embed color (hex code like #FF0000)"
)
@app_commands.default_permissions(administrator=True)
async def embed_command(interaction: discord.Interaction, title: str, description: str, color: str = "#0099ff"):
    try:
        # Convert hex color to discord.Color
        color_int = int(color.replace("#", ""), 16)
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color(color_int),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f'Created by {interaction.user}')
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f'❌ Error creating embed: {e}', ephemeral=True)

# ===== SLASH COMMAND: REACTION ROLES (NOW PERSISTENT) =====
@bot.tree.command(name="reactionroles", description="Create a persistent reaction role menu")
@app_commands.describe(title="Menu title")
@app_commands.default_permissions(administrator=True)
async def reactionroles_command(interaction: discord.Interaction, title: str):
    embed = discord.Embed(
        title=title,
        description='Select your roles from the dropdown below!\n\n**This menu will stay active even after bot restarts.**',
        color=discord.Color.green()
    )
    
    # Create persistent dropdown menu
    view = PersistentRoleSelectView()
    
    await interaction.response.send_message(embed=embed, view=view)

# ===== SLASH COMMAND: SET LOG CHANNEL =====
@bot.tree.command(name="setlogchannel", description="Set the channel for message logs")
@app_commands.describe(channel="The log channel")
@app_commands.default_permissions(administrator=True)
async def setlogchannel_command(interaction: discord.Interaction, channel: discord.TextChannel):
    config.log_channel_id = channel.id
    await interaction.response.send_message(f'✅ Log channel set to {channel.mention}', ephemeral=True)

# ===== SLASH COMMAND: SET AUTO ROLES =====
@bot.tree.command(name="setautoroles", description="Set roles to auto-assign on member join")
@app_commands.describe(
    role1="First role",
    role2="Second role (optional)",
    role3="Third role (optional)"
)
@app_commands.default_permissions(administrator=True)
async def setautoroles_command(
    interaction: discord.Interaction, 
    role1: discord.Role, 
    role2: discord.Role = None, 
    role3: discord.Role = None
):
    roles = [role1]
    if role2:
        roles.append(role2)
    if role3:
        roles.append(role3)
    
    config.auto_roles = [role.id for role in roles]
    
    role_mentions = ', '.join([role.mention for role in roles])
    await interaction.response.send_message(
        f'✅ Auto-roles updated! New members will receive: {role_mentions}',
        ephemeral=True
    )

# Login to Discord
if __name__ == '__main__':
    # Start Flask server in a separate thread
    Thread(target=run_flask, daemon=True).start()
    
    bot.run(os.getenv('DISCORD_TOKEN'))