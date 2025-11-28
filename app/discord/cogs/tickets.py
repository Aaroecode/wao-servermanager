import discord
from discord.ext import commands
from discord import app_commands
import io
import html
import asyncio
import asyncpg
import os
from datetime import datetime


STAFF_ROLE_ID = 1118940908063293552
TICKET_CATEGORY_NAME = "🎇=-=-=-Tickets-=-=-=🎇"
STAFF_LOG_CHANNEL_ID = 1118973729150615654

TICKET_REASONS = [
    ("general", "General Support"),
    ("player", "Player Report"),
    ("billing", "Billing Issue"),
    ("appeal", "Punishment Appeal"),
    ("bug", "Bug Report"),
]




async def generate_transcript_html(channel: discord.TextChannel) -> str:
    messages = []
    async for msg in channel.history(limit=None, oldest_first=True):
        messages.append(msg)

    parts = []
    parts.append('<!doctype html><html><head><meta charset="utf-8"><title>Transcript</title>')
    parts.append('<style>body{background:#2b2d31;color:#ddd;font-family:Inter,Segoe UI,Arial;padding:20px} .msg{padding:8px;border-bottom:1px solid #3a3b3f} .author{font-weight:600} .time{color:#9aa0a6;font-size:0.9em}</style>')
    parts.append('</head><body>')
    parts.append(f'<h2>Transcript: {html.escape(channel.name)}</h2>')
    parts.append('<div>')

    for msg in messages:
        ts = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
        author = html.escape(f"{msg.author.name}")
        content = html.escape(msg.content)
        parts.append(f'<div class="msg"><div class="author">{author} <span class="time">[{ts}]</span></div><div class="content">{content}</div>')

       
        for at in msg.attachments:
            parts.append(f'<div class="attachment"><a href="{at.url}" target="_blank">Attachment: {html.escape(at.filename)}</a></div>')

        
        for e in msg.embeds:
            try:
                title = html.escape(e.title) if e.title else ''
                desc = html.escape(e.description) if e.description else ''
                if title or desc:
                    parts.append(f'<div class="embed">Embed: <strong>{title}</strong><div>{desc}</div></div>')
            except Exception:
                pass

        parts.append('</div>')

    parts.append('</div></body></html>')
    return ''.join(parts)


class TicketModal(discord.ui.Modal):
    # username = discord.ui.TextInput(
    #     label="What is your Minecraft Username?",
    #     placeholder="Please fill this in",
    #     required=True,
    #     max_length=64
    # )

    # issue = discord.ui.TextInput(
    #     label="How can we assist you today?",
    #     style=discord.TextStyle.long,
    #     placeholder="Please fill this in",
    #     required=True,
    #     max_length=4000
    # )
    def __init__(self, bot: commands.Bot, reason_label: str, fields: list[dict]):
        super().__init__(title="Ticket Form", timeout=None)
        self.bot = bot
        self.reason_label = reason_label
        self.fields = fields
        for field in fields:
            input_field = discord.ui.TextInput(
                label=field.get("label", "Field"),
                placeholder=field.get("placeholder", ""),
                required=field.get("required", True),
                max_length=field.get("max_length", 1024)
            )
            setattr(self, field["id"], input_field)  
            self.add_item(input_field)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        staff_role = discord.utils.get(guild.roles, id=STAFF_ROLE_ID)

  
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY_NAME)

   
        base_name = f"ticket-{interaction.user.name}".lower().replace(' ', '-')[:90]

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        channel = await guild.create_text_channel(name=base_name, category=category, overwrites=overwrites)


        embed = discord.Embed(
            title=f"🎫 Ticket — {self.reason_label}",
            description=f"**Opened by:** {interaction.user.mention} **Time:** {datetime.utcnow()}",
            color=discord.Color.blue(),
        )
        for item in self.fields:
            field_id = item["id"]               
            text_input = getattr(self, field_id)  
            value = text_input.value            

            embed.add_field(name=item["label"], value=value, inline=False)

        await channel.send(content=interaction.user.mention, embed=embed)
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)


class TicketSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        options = [discord.SelectOption(label=label, value=key) for key, label in TICKET_REASONS]
        super().__init__(placeholder="Select a ticket reason...", min_values=1, max_values=1, options=options)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        fields = [
                    {
                        "id": "username",
                        "label": "What is your Minecraft Username?",
                        "placeholder": "Please fill this in",
                        "required": True,
                        "max_length": 64,
                    },
                    {
                        "id": "issue",
                        "label": "How can we assist you today?",
                        "placeholder": "Describe your issue...",
                        "required": True,
                        "long": True,          
                        "max_length": 4000,
                    }
                ]
        try:
            label = dict(TICKET_REASONS)[key]
            modal = TicketModal(self.bot, label, fields)
            print("yes")
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(e)


class TicketPanel(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.add_item(TicketSelect(bot))


class TicketCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ticketpanel", description="Post ticket creation panel")
    @app_commands.guilds(discord.Object(id=1114580786176348231))
    @app_commands.checks.has_role(STAFF_ROLE_ID)
    async def ticketpanel(self, interaction: discord.Interaction):
        embed = discord.Embed(title="General Support", description="Select a reason to open a ticket.", color=0x2b2d31)
        embed.add_field(name="Note", value="This form will be submitted to server staff. Do not share passwords or other sensitive information.", inline=False)
        await interaction.response.send_message(embed=embed, view=TicketPanel(self.bot))


    @app_commands.guilds(discord.Object(id=1114580786176348231))
    @app_commands.command(name="add", description="Add a user to this ticket channel")
    async def add_user(self, interaction: discord.Interaction, user: discord.Member):
        
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("This command can only be used in ticket channels.", ephemeral=True)

      
        if not channel.name.startswith('ticket-'):
            return await interaction.response.send_message("This doesn't appear to be a ticket channel.", ephemeral=True)

  
        await channel.set_permissions(user, view_channel=True, send_messages=True, read_message_history=True)
        await interaction.response.send_message(f"✅ {user.mention} can now see this ticket.")


    @app_commands.guilds(discord.Object(id=1114580786176348231))
    @app_commands.command(name="remove", description="Remove a user's access to this ticket channel")
    async def remove_user(self, interaction: discord.Interaction, user: discord.Member):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("This command can only be used in ticket channels.", ephemeral=True)
        if not channel.name.startswith('ticket-'):
            return await interaction.response.send_message("This doesn't appear to be a ticket channel.", ephemeral=True)

        await channel.set_permissions(user, overwrite=None)
        await interaction.response.send_message(f"✅ {user.mention} no longer has access to this ticket.")


    @app_commands.guilds(discord.Object(id=1114580786176348231))
    @app_commands.command(name="close", description="Close this ticket and create a transcript")
    async def close_ticket(self, interaction: discord.Interaction):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not channel.name.startswith('ticket-'):
            return await interaction.response.send_message("This command can only be used in ticket channels.", ephemeral=True)

        await interaction.response.send_message("🔒 Closing ticket and generating transcript...", ephemeral=True)

      
        try:
            html_text = await generate_transcript_html(channel)
            b = io.BytesIO(html_text.encode('utf-8'))
            filename = f"{channel.name}-transcript.html"
            file = discord.File(fp=b, filename=filename)

         
            if STAFF_LOG_CHANNEL_ID and STAFF_LOG_CHANNEL_ID != 0:
                log_ch = self.bot.get_channel(STAFF_LOG_CHANNEL_ID)
                if log_ch:
                    embed = discord.Embed(title="Ticket Closed", 
                                          description=f"Channel: {channel.mention}"
                                                    f"Closed by: {interaction.user.mention}", 
                                                    color=0xff5555, timestamp=datetime.utcnow())
                    await log_ch.send(embed=embed, file=file)

        except Exception as e:
            print('Error generating transcript:', e)

 
        try:
            await channel.delete(reason=f"Ticket closed by {interaction.user}")
        except Exception:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketCog(bot))
