import typing

import velum
from velum.events import base_events

from sail.traits import command_manager_trait
from sail.traits import command_trait


@typing.runtime_checkable
class Extension(typing.Protocol):
    async def load(
        self,
        __client: velum.GatewayClient,
        __command_manager: command_manager_trait.CommandManager,
    ) -> None:
        ...

    async def unload(
        self,
        __client: velum.GatewayClient,
        __command_manager: command_manager_trait.CommandManager,
    ) -> None:
        ...


@typing.runtime_checkable
class Plugin(Extension, typing.Protocol):
    def add_command(self, __command: command_trait.Command[typing.Any, typing.Any]) -> None:
        ...

    def remove_command(self, __command: command_trait.Command[typing.Any, typing.Any]) -> None:
        ...

    def subscribe(
        self,
        __event_type: typing.Type[base_events.EventT],
        __callback: base_events.EventCallbackT[base_events.EventT],
    ) -> None:
        ...

    def unsubscribe(
        self,
        __event_type: typing.Type[base_events.EventT],
        __callback: base_events.EventCallbackT[base_events.EventT],
    ) -> None:
        ...
