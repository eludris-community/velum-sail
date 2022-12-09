import logging

from velum import models
from velum.events import message_events

from sail.impl import command_manager

_LOGGER = logging.getLogger("velum.debug")


async def test_invoke(manager: command_manager.CommandManager, invocation: str) -> None:
    debug_message = models.Message(author="DEBUG", content=invocation)
    debug_event = message_events.MessageCreateEvent(message=debug_message)

    try:
        await manager.try_invoke(debug_event)

    except Exception as exc:
        exc_info = type(exc), exc, exc.__traceback__  #.tb_next if exc.__traceback__ else None

        _LOGGER.error(
            "Test invocation failed.",
            exc_info=exc_info,
        )

    else:
        _LOGGER.debug("Test invocation successful.")
