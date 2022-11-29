import asyncio
import re
import typing

import velum

import sail

# ...But what if standard prefixes aren't cool enough?
# sail allows you to set custom callbacks to split a message into
# (the "prefix", the command name, the invocation)
# For example:


def prepare(content: str) -> typing.Tuple[str | None, str | None, str | None]:
    match = re.fullmatch(r"::<(.+?)>\s*(.+)", content)
    if not match:
        return (None, None, None)

    return ("::<>", *match.groups())


# Note that the "prefix" does not necessarily actually need to be a prefix.
# It is solely passed to the invocation context as `ctx.prefix` such that it
# can be checked inside the command, in case there are multiple prefixes.

# If all three return something other than None, the command manager will try
# to invoke the command.

# Next, we create a bot and command manager.

bot = velum.GatewayBot()
manager = sail.CommandManager()
manager.bind_to_app(bot)


# We then bind our custom prepare callback to the manager:

manager.set_prepare_callback(prepare)


# With that, commands are now invoked with turbofish instead of a simple prefix.


@manager.command(aliases=["cool-alias", "not_so_cool_alias"])
async def my_command(ctx: sail.Context, x: typing.List[int], *, y: bool) -> None:
    await bot.rest.send_message(
        "sail",
        f"Got {len(x)} number(s): {x}. "
        f"Flag y was set to {y}. "
        f"Invoked as {ctx.invoked_with} with prefix {ctx.prefix}.",
    )


# Note that this is the same command as in the `prefix.py` example.
# This command is now invoked as
# ::<my_command> 1 2 3 -y
# ::<cool-alias> 1 2
# ::<not_so_cool_alias> 1 2 3 4
# ...

# Finally, we run the bot as per usual.

asyncio.run(bot.start())
