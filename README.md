# Velum-Sail

Velum-Sail is a command handler for [Velum](https://github.com/eludris-community/velum), which in turn is a wrapper for the [Eludris](https://eludris.pages.dev/#/) API. It expands on velum by adding shell-like text-based commands, a command handler that can hook into a `velum.GatewayClient`, and extensions to keep your files organised (coming soon<sup>TM</sup>).

Please keep in mind that this library is still in its infancy, and some much needed features such as documentation are coming in the nearTM future.


# Installing

*Python 3.10 or higher is required.*

To install the library, currently the only option is to install it off of this very github page.
```
python3 -m pip install -U git+https://github.com/eludris-community/velum-sail
```


# Example

```py
import asyncio
import typing

import velum
import sail


bot = velum.GatewayClient()
manager = sail.CommandManager.with_prefix("!")
manager.bind_to_app(bot)


@manager.command()
async def my_command(ctx: sail.Context, x: typing.List[bool]) -> None:
    await bot.rest.send_message(f"{ctx.author} sent in {len(x)} bools, {sum(x)} of which were True!")


asyncio.run(bot.start())
```

For more in-depth examples, please see the [examples directory](https://github.com/eludris-community/velum-sail/tree/master/examples).
