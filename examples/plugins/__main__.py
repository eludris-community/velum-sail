import asyncio

import velum

import sail

client = velum.GatewayClient()
manager = sail.CommandManager.with_prefix("!")
manager.bind_to_app(client)


async def main():
    await sail.load_extension(
        ".test_plugin", "examples.plugins", client=client, command_manager=manager
    )

    await client.start()


@manager.command()
async def reload(ctx: sail.Context):
    await sail.reload_extension(".test_plugin", client=client, command_manager=manager)
    await client.rest.send_message("Sail", "Done deal.")


asyncio.run(main())
