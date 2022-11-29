import asyncio
import typing

import velum

import sail

# To create commands, we first create a bot as per usual.
# Next, we create a CommandManager. To set a prefix for the command manager,
# simply use the classmethod `with_prefix(<prefix>)`.

bot = velum.GatewayBot()
manager = sail.CommandManager.with_prefix("!")


# We then bind the command manager to the bot. This creates a listener for
# `velum.MessageCreateEvent`s, that will automatically try to dispatch commands
# if a message with correct prefix and command name was found.

manager.bind_to_app(bot)


# Now, we can add commands to the command manager.
# With this, we can set a name for the command, a description, and aliases.
# The command can then be invoked through either its name or aliases.
# For ease of use, the command name defaults to that of the wrapped function,
# and the description defaults to the docstring of said function.

# The first parameter of a command must always be the invocation context.
# (Subject to change? maybe a @skip_context deco?)
# This contains information such as the event with which the command was invoked,
# the name or alias with which it was invoked, the parsed args/kwargs, etc.


@manager.command(aliases=["cool-alias", "not_so_cool_alias"])
async def my_command(ctx: sail.Context, x: typing.List[int], *, y: bool) -> None:
    await bot.rest.send_message(
        "sail",
        f"Got {len(x)} number(s): {x}. "
        f"Flag y was set to {y}. "
        f"Invoked as {ctx.invoked_with} with prefix {ctx.prefix}.",
    )


# Finally, we run the bot as per usual.
# The command can now be invoked as e.g.
# "!my_command 1 2 3 4 -y"
# "!cool-alias 5 6"
# "!not_so_cool_alias 7 8 9"
# ...

asyncio.run(bot.start())
