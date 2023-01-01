import asyncio
import logging
import re

import velum

import sail

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


# Occasionally, the default string parser gets in your way.
# Say you want to do something with codeblocks, where you do not want the
# quotes inside to be consumed by the default parser. In situations like these,
# Sail provides you the ability to provide your own string parsers.

client = velum.GatewayClient()
manager = sail.CommandManager().with_prefix("!")
manager.bind_to_app(client)


# Oversimplified codeblock regex...

CODEBLOCK_RE = re.compile(
    r"\s*```(?P<lang>\S+)?\s*(?P<body>.*?)\s*```\s*",
    # Three backticks followed by an optional code language,
    # then the code body, and finally three closing backticks.
    re.DOTALL | re.IGNORECASE,
)


# A string parser function should
# - take a string as only argument -- this is the user input to parse,
# - return a tuple with:
#   - a sequence of positional arguments,
#   - a mapping of keyword arguments, mapping the name to a sequence of values.

# In this case, it is sufficient to simply pass the invocation string to the
# function unedited. Thus, we can simply return the whole string as if it were
# a positional arg, and return an empty dict for keyword args.


@manager.command(string_parser=lambda s: ([s], {}))
async def codeblock(ctx: sail.Context, codeblock: str) -> None:
    match = CODEBLOCK_RE.fullmatch(codeblock)
    if not match:
        return

    groupdict = match.groupdict()

    lang = groupdict["lang"]
    body = groupdict["body"]  # pyright: ignore  # noqa: F841

    await client.rest.send_message("Sail", f"Evaluating your `{lang}` code...")

    ...  # Actual code eval implementation...


# Finally, we can run the bot as per usual.

asyncio.run(client.start())
