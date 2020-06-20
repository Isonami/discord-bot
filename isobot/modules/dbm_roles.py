# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)


def build_role(bot, role, role_name):
    @role.group(invoke_without_command=True, name=role_name)
    async def role_manage(ctx: bot.Context):
        """{} role""".format(role_name.capitalize())
        await ctx.send_help(role_manage)

    @role_manage.command()
    async def add(ctx: bot.Context, user: str):
        """Add member to {} role""".format(role_name)
        await ctx.send('Hi')

    @role_manage.command()
    async def remove(ctx: bot.Context, user: str):
        """Remove member of {} role""".format(role_name)
        await ctx.send('Hi')

    @role_manage.command()
    async def link(ctx: bot.Context, discord_role: str):
        """Link discord role to {} role""".format(role_name)
        await ctx.send('Hi')

    @role_manage.command()
    async def unlink(ctx: bot.Context, discord_role: str):
        """Unlink discord role from {} role""".format(role_name)
        await ctx.send('Hi')


def setup(bot):

    @bot.group(invoke_without_command=True)
    async def role(ctx: bot.Context):
        """Bot roles managment"""
        await bot.show_help(ctx, 'role')

    role.error(bot.default_error)

    @role.group(invoke_without_command=True, name='test')
    async def role_manage(ctx: bot.Context):
        """Test role"""
        await bot.show_help(ctx, 'role', 'test')

    @role_manage.command()
    async def add(ctx: bot.Context):
        """Add member to test role"""
        await ctx.send('Hi')

    @bot.unload()
    def unload():
        bot.roles = None
