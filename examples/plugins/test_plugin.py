import sail

plugin = sail.Plugin()


@plugin.command()
async def plugin_command(ctx: sail.Context):
    await plugin.rest.send_message("Sail", f"Sent from plugin {plugin.name!r}!")


load, unload = plugin.entrypoints
