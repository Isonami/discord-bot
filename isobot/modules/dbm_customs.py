# -*- coding: utf-8 -*-
import logging
import re

logger = logging.getLogger(__name__)


def setup(bot):
    config = bot.config('customs')
    role_id = int(config.get('role_id'))
    battle_net_tag_match = re.compile(r'^\S+#[0-9]+$')
    timeout = 300

    @bot.model()
    class Customs_Roles(bot.BaseModel):
        role_id = bot.m.BigIntegerField()
        guild_id = bot.m.BigIntegerField()

        class Meta:
            indexes = (
                (('role_id', 'guild_id'), True),
            )

    @bot.model()
    class Customs_Users_List(bot.BaseModel):
        role = bot.m.ForeignKeyField(Customs_Roles, related_name='members')
        member_id = bot.m.BigIntegerField()
        battle_net_tag = bot.m.CharField(null=True)

    @bot.init()
    async def init():
        try:
            await bot.db.get(Customs_Roles, role_id=role_id)
        except Customs_Roles.DoesNotExist:
            for guild in bot.guilds:
                role = bot.utils.get(guild.roles, id=role_id)
                if role is not None:
                    await bot.db.create(Customs_Roles, role_id=role_id, guild_id=guild.id)

    @bot.group(invoke_without_command=True)
    async def custom(ctx: bot.Context):
        """Custom games module"""
        await bot.show_help(ctx, 'custom')

    custom.error(bot.default_error)

    @custom.command()
    async def sign(ctx: bot.Context):
        """Sign for custom games role"""
        try:
            print(ctx.guild.id)
            role_db = await bot.db.get(Customs_Roles, guild_id=ctx.guild.id)
        except Customs_Roles.DoesNotExist:
            return

        role = bot.utils.get(ctx.guild.roles, id=role_db.role_id)

        if role in ctx.author.roles:
            return

        member, create = await bot.db.get_or_create(Customs_Users_List, {"role": role_db, "member_id": ctx.author.id},
                                                    role=role_db, member_id=ctx.author.id)

        await ctx.author.add_roles(role)

        if not member.battle_net_tag:
            num_tries = 3

            await ctx.author.send('Please send me your battle.net tag.')

            for count in range(num_tries):
                def pred(m):
                    return m.author == ctx.author and m.channel == ctx.author.dm_channel

                msg = await bot.wait_for('message', check=pred, timeout=timeout)
                battle_net_tag = msg.content.strip()

                match = battle_net_tag_match.match(battle_net_tag)

                if match:
                    member.battle_net_tag = battle_net_tag
                    await bot.db.update(member)

                    await ctx.author.send('Thank you!')
                    return

                if count == num_tries - 1:
                    await ctx.author.send('Invalid tag format.')
                else:
                    await ctx.author.send('Invalid tag format (Example: Tag#1234). Try again.')

    @custom.command()
    async def unsign(ctx: bot.Context):
        """Unsign from custom games role"""
        try:
            print(ctx.guild.id)
            role_db = await bot.db.get(Customs_Roles, guild_id=ctx.guild.id)
        except Customs_Roles.DoesNotExist:
            return

        role = bot.utils.get(ctx.guild.roles, id=role_db.role_id)

        if role not in ctx.author.roles:
            return

        await ctx.author.remove_roles(role)
