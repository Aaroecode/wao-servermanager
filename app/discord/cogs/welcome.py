import discord, random
from discord.ext import commands


WELCOME_CHANNEL_ID = 123456789012345678  
WELCOME_IMAGE = ["https://themepack.me/i/c/749x467/media/g/207/sword-art-online-theme-17.jpg",
                 "https://themepack.me/i/c/749x467/media/g/207/sword-art-online-theme-19.jpg",
                 "https://themepack.me/i/c/749x467/media/g/207/sword-art-online-theme-1.jpg",
                 "https://themepack.me/i/c/749x467/media/g/207/sword-art-online-theme-4.jpg"] 
SAO_BLUE = 0x00AEEF  


welcome_messages = [ "{user} logged in! Remember: if you die here, you… actually just respawn. Have fun!",
                    "Welcome {user}! Please keep all swords sheathed while browsing the Discord."

                    "{user} has joined! Kirito is already jealous of your potential.",

                    "Welcome, {user}! Word is you’re stronger than Klein… but honestly that’s not hard.",

                    "A new challenger appears! {user}, don’t worry — nobody actually dies here."]

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Event listener for joining users
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        channel_id=1118932593979707452
        channel = member.guild.get_channel(channel_id)
        print(channel.id)
        if not channel:
            return


        embed = discord.Embed(
            title="◆ LINK START ◆",
            description=(random.choice(welcome_messages)).format(user=member.mention),
            color=SAO_BLUE
        )
        embed.set_image(url=random.choice(WELCOME_IMAGE))
        embed.set_footer(text="Sword Art Online — System Interface")

        await channel.send(embed=embed)
    

    @commands.command(name="test_welcome", help="Test the welcome message")
    async def test_welcome(self, ctx):
        await ctx.channel.send("Testing welcome message...")
        await self.on_member_join(ctx.author)



async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))
    print("WelcomeCog loaded.")
