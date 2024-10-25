import discord
from discord.ext import commands
import json
import sqlite3
import random
import asyncio
import datetime
import string

# Bot-Einstellungen
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# SQLite Datenbank Verbindung
conn = sqlite3.connect('premium.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS premium_servers (
                server_id INTEGER PRIMARY KEY, 
                expiry_date TEXT)''')

# Tabelle für Tickets erstellen
c.execute('''CREATE TABLE IF NOT EXISTS tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER,
                user_id INTEGER,
                channel_id INTEGER,
                status TEXT)''')
conn.commit()

# Laden der Codes aus der JSON-Datei
codes = {}
try:
    with open('codes.json', 'r') as f:
        codes = json.load(f)
except FileNotFoundError:
    with open('codes.json', 'w') as f:
        json.dump(codes, f)

# -----------------------------------
# Ticket-System (Simple)
# -----------------------------------
@bot.command()
async def ticket(ctx):
    """Erstelle ein Ticket."""
    # Erstelle einen neuen Ticket-Channel
    ticket_channel = await ctx.guild.create_text_channel(f'ticket-{ctx.author.name}')

    # Speichere Ticket-Informationen in der Datenbank
    c.execute("INSERT INTO tickets (server_id, user_id, channel_id, status) VALUES (?, ?, ?, ?)",
              (ctx.guild.id, ctx.author.id, ticket_channel.id, 'open'))
    conn.commit()

    await ticket_channel.send(f"Ticket eröffnet von {ctx.author.mention}. Bitte beschreibe dein Anliegen!")
    await ctx.send(f"Dein Ticket wurde erstellt: {ticket_channel.mention}")

@bot.command()
async def close(ctx):
    """Schließe ein Ticket."""
    if ctx.channel.name.startswith('ticket-'):
        ticket_id = ctx.channel.id
        c.execute("UPDATE tickets SET status = ? WHERE channel_id = ?", ('closed', ticket_id))
        conn.commit()
        await ctx.send("Das Ticket wurde geschlossen. Der Channel wird nun gelöscht.")
        await ctx.channel.delete()
    else:
        await ctx.send("Dieses Kommando kann nur in einem Ticket-Channel verwendet werden.")

@bot.command()
async def view_tickets(ctx):
    """Zeige alle offenen Tickets."""
    c.execute("SELECT * FROM tickets WHERE server_id = ? AND status = ?", (ctx.guild.id, 'open'))
    tickets = c.fetchall()

    if not tickets:
        await ctx.send("Es gibt derzeit keine offenen Tickets.")
        return

    embed = discord.Embed(title="Offene Tickets", description="", color=0x00ff00)
    for ticket in tickets:
        ticket_channel = bot.get_channel(ticket[3])
        user = bot.get_user(ticket[2])
        embed.add_field(name=f"Ticket #{ticket[0]}", value=f"Benutzer: {user.mention} | Kanal: {ticket_channel.mention}", inline=False)

    await ctx.send(embed=embed)

# -----------------------------------
# Music-Features
# -----------------------------------
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
    else:
        await ctx.send("Du musst in einem Sprachkanal sein, um diesen Befehl zu verwenden.")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
    else:
        await ctx.send("Ich bin in keinem Sprachkanal.")

@bot.command()
async def play(ctx):
    await ctx.send("Dieses Feature ist Deaktiviert. Weil YTDL zurzeit probleme verursacht.")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("Musik gestoppt.")
    else:
        await ctx.send("Ich bin in keinem Sprachkanal.")

# -----------------------------------
# Moderation-Features
# -----------------------------------
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f'{member.name} wurde gebannt.')

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f'{member.name} wurde gekickt.')

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount=10):
    await ctx.channel.purge(limit=amount)
    await ctx.send(f'{amount} Nachrichten wurden gelöscht.', delete_after=5)

# -----------------------------------
# Mini-Spiele
# -----------------------------------
@bot.command()
async def rps(ctx, choice):
    choices = ["rock", "paper", "scissors"]
    bot_choice = random.choice(choices)
    if choice == bot_choice:
        await ctx.send(f"Unentschieden! Ich habe auch {bot_choice} gewählt.")
    elif (choice == "rock" and bot_choice == "scissors") or \
         (choice == "paper" and bot_choice == "rock") or \
         (choice == "scissors" and bot_choice == "paper"):
        await ctx.send(f"Du gewinnst! Ich habe {bot_choice} gewählt.")
    else:
        await ctx.send(f"Du verlierst! Ich habe {bot_choice} gewählt.")

@bot.command()
async def counter(ctx):
    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel and msg.content.isdigit()

    current_number = 0
    await ctx.send("Zähle hoch, ohne die Zahl zu wiederholen! Beginne bei 1.")
    while True:
        msg = await bot.wait_for('message', check=check)
        number = int(msg.content)
        if number == current_number + 1:
            current_number = number
        else:
            await ctx.send(f"Du hast verloren! Die korrekte Zahl wäre {current_number + 1} gewesen.")
            break

@bot.command()
async def quiz(ctx):
    questions = {
        "Hauptstadt von Deutschland?": "Berlin",
        "Größter Ozean?": "Pazifik",
        "Höchster Berg der Welt?": "Mount Everest",
    }
    question = random.choice(list(questions.keys()))
    answer = questions[question]

    await ctx.send(f"Frage: {question}")

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        msg = await bot.wait_for('message', check=check, timeout=15.0)
        if msg.content.lower() == answer.lower():
            await ctx.send("Richtig!")
        else:
            await ctx.send(f"Falsch! Die richtige Antwort wäre '{answer}' gewesen.")
    except asyncio.TimeoutError:
        await ctx.send(f"Zeit abgelaufen! Die richtige Antwort wäre '{answer}' gewesen.")

# -----------------------------------
# Mediathek & Premium-Features
# -----------------------------------
@bot.command()
async def mediathek(ctx):
    with open('mediathek.json', 'r') as f:
        mediathek = json.load(f)

    embed = discord.Embed(title="Mediathek", description="Wähle einen Film oder Serie", color=0x00ff00)

    for item in mediathek:
        embed.add_field(name=item['Title'], value=item['Description'], inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def getpremium(ctx):
    await ctx.send("Hier kannst du Premium erwerben: https://rickbot.justinsanjp.de/premium.html")

@bot.command()
async def redeemcode(ctx):
    await ctx.send("Bitte gib deinen Aktivierungscode ein:")

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        code = msg.content.strip()

        if code in codes:
            server_id = ctx.guild.id
            expiry_date = codes[code]
            c.execute("INSERT OR REPLACE INTO premium_servers (server_id, expiry_date) VALUES (?, ?)",
                      (server_id, expiry_date))
            conn.commit()
            await ctx.send("Premium wurde erfolgreich aktiviert!")
            del codes[code]
            with open('codes.json', 'w') as f:
                json.dump(codes, f)
        else:
            await ctx.send("Ungültiger Code.")
    except asyncio.TimeoutError:
        await ctx.send("Zeit abgelaufen! Bitte versuche es erneut.")

@bot.command()
async def testpremium(ctx):
    server_id = ctx.guild.id
    expiry_date = (datetime.datetime.now() + datetime.timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT OR REPLACE INTO premium_servers (server_id, expiry_date) VALUES (?, ?)",
              (server_id, expiry_date))
    conn.commit()
    await ctx.send("Premium wurde für 30 Minuten aktiviert!")

# Bot-Start // get your token here: https://discord.com/developers/applications
bot.run('insert your bot token here')
