import asyncio
import typing

import velum

import sail

# Sail implements a bunch of parsers to convert your bot's users' string inputs
# to all kinds of types. In most cases, this should be enough to work with to
# make some very complex commands. However, it is possible to extend Sail's
# functionality with your own parsers, just in case your needs are not quite
# covered. We'll go over some examples here.

client = velum.GatewayClient()
manager = sail.CommandManager.with_prefix("!")
manager.bind_to_app(client)


# First, we'll make a simple float parser with some extra functionality.
# Existing parser implementations can be found under `sail.impl.argument_parser`,
# and prototypes to which your parsers should adhere can be found under
# `sail.traits.argument_parser_trait`.

# To create a new parser from scratch, we import the `ArgumentParser` trait,
# and inherit from it. This way we can make sure that we implement everything
# Sail needs from an argument parser. Note that this inheritance is not strictly
# required, because it's ultimately just a prototype.

# To support default values for parsing, we use a special sentinel type `EMPTY`.
# This is used to differentiate between using `None` as default, and not having
# a default at all. `EMPTY` and co. can be found under `sail.internal.empty`

# We now import the bits required to make our custom parser.

import math

from sail.internal import empty
from sail.traits import argument_parser_trait


class FloatParser(argument_parser_trait.ArgumentParser[float]):
    @property
    def __type__(self) -> typing.Type[float]:
        return float

    def parse(self, argument: str, default: float | empty.Empty = empty.EMPTY) -> float:
        # First, check for a couple special constants `float(str)` doesn't
        # innately handle...
        if argument == "pi":
            return math.pi

        if argument == "e":
            return math.e

        if argument == "tau":
            return math.tau

        # Not a special constant, try just casting to float...
        try:
            return float(argument)

        except Exception:
            # Failed to cast. Check if a default was provided...
            if empty.is_nonempty(default):
                return default

            raise  # No default provided, just re-raise the exception.


# Now we can use this custom parser as part of a command:


@sail.param("number", parser=FloatParser())
@manager.command()
async def cool_floats(ctx: sail.Context, number: float):
    await client.rest.send_message("Sail", f"You entered {number:.4f}!")


# With this, if the command is invoked with e.g. `"!cool_floats pi"`, its
# `number` argument will be parsed to 3.14159... as expected.

# Something similar can be done with containers. Sail exposes a `ContainerParser`
# trait, which is used in a similar fashion. The `parse` function of a container
# parser will receive a sequence containing individual parsed elements. It is
# then up to the container parser to finalize the sequence and cast it to the
# desired container type.

# Note that, in most situations, if you want to use a custom container type,
# just using it as typehint is enough. As long as your custom type properly
# implements the `typing.AbstractSet` or `typing.Sequence` traits, and
# initialises with an iterable of values (e.g. `MyType([1,2,3])`), Sail should
# be able to handle it without further trouble.

# Now, for sake of illustration, we will make a custom container parser for
# lists of strings, that filters out any strings that do not start with "@".


class MentionContainerParser(argument_parser_trait.ContainerParser[typing.List[str]]):
    @property
    def __type__(self) -> typing.Type[typing.List[str]]:
        return typing.List[str]

    def parse(
        self,
        argument: typing.Sequence[object],
        default: typing.List[str] | empty.Empty = empty.EMPTY,
    ) -> typing.List[str]:
        parsed = [  # fmt: skip
            arg for arg in argument if isinstance(arg, str) and arg.startswith("@")
        ]

        if parsed:
            return parsed

        if empty.is_nonempty(default):
            return default

        raise TypeError("Got 0 valid mentions!")


# And similarly, this can be passed to a command as follows:


@sail.param("mentions", container_parser=MentionContainerParser())
@manager.command()
async def mention(ctx: sail.Context, mentions: typing.List[str]):
    mention_str = "', '".join(mentions)
    await client.rest.send_message("Sail", f"You mentioned '{mention_str}'!")


# Which, when invoked with e.g. `"!mention @foo @bar bat @baz` would result in
# the `mentions` param having value `["@foo", "@bar", "@baz"]`.


asyncio.run(client.start())
