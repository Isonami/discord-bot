# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)


def setup(bot):
    config = bot.config('partyhard')
    role_id = int(config.get('role_id'))

    @bot.model()
    class Partyhard_Roles(bot.BaseModel):
        role_id = bot.m.BigIntegerField()
        guild_id = bot.m.BigIntegerField()

        class Meta:
            indexes = (
                (('role_id', 'guild_id'), True),
            )

    @bot.init()
    async def init():
        try:
            await bot.db.get(Partyhard_Roles, role_id=role_id)
        except Partyhard_Roles.DoesNotExist:
            for guild in bot.guilds:
                role = bot.utils.get(guild.roles, id=role_id)
                if role is not None:
                    await bot.db.create(Partyhard_Roles, role_id=role_id, guild_id=guild.id)

    @bot.group(invoke_without_command=True)
    async def partyhard(ctx: bot.Context):
        """Partyhard module"""
        await bot.show_help(ctx, 'partyhard')

    partyhard.error(bot.default_error)

    @partyhard.command()
    async def on(ctx: bot.Context):
        """Sign for partyhard role"""
        try:
            role_db = await bot.db.get(Partyhard_Roles, guild_id=ctx.guild.id)
        except Partyhard_Roles.DoesNotExist:
            return

        role = bot.utils.get(ctx.guild.roles, id=role_db.role_id)

        if role in ctx.author.roles:
            return

        await ctx.author.add_roles(role)

        await ctx.send('Woohoo!')

    on.error(bot.default_error)

    @partyhard.command()
    async def off(ctx: bot.Context):
        """Unsign from partyhard role"""
        try:
            role_db = await bot.db.get(Partyhard_Roles, guild_id=ctx.guild.id)
        except Partyhard_Roles.DoesNotExist:
            return

        role = bot.utils.get(ctx.guild.roles, id=role_db.role_id)

        if role not in ctx.author.roles:
            return

        await ctx.author.remove_roles(role)

        await ctx.send('We\'ll miss you. :cry:')

    off.error(bot.default_error)
