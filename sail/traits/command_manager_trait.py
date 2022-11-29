from __future__ import annotations

import typing

from velum import MessageCreateEvent
from velum.traits import event_manager_trait

from sail.traits import command_trait

__all__: typing.Sequence[str] = ("CommandManager",)


CommandT = typing.TypeVar("CommandT", bound=command_trait.AnyCommand)


class EventAware(typing.Protocol):
    __slots__: typing.Sequence[str] = ()

    @property
    def event_manager(self) -> event_manager_trait.EventManager:
        ...


class CommandManager(typing.Protocol):
    @property
    def commands(self) -> typing.Sequence[command_trait.AnyCommand]:
        ...

    @staticmethod
    def prepare(content: str) -> typing.Tuple[str, str, str] | typing.Tuple[None, None, None]:
        ...

    async def try_invoke(self, event: MessageCreateEvent) -> None:
        ...

    def add_command(self, command: command_trait.AnyCommand) -> None:
        ...

    def remove_command(self, command: command_trait.AnyCommand) -> None:
        ...

    def command(
        self,
        **__kwargs: typing.Any,
    ) -> typing.Callable[
        [typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, typing.Any]]],
        command_trait.AnyCommand,
    ]:
        ...

    def bind_to_event_manager(self, event_manager: event_manager_trait.EventManager) -> None:
        ...

    def bind_to_app(self, app: EventAware) -> None:
        ...

    def set_prepare_callback(
        self,
        callback: typing.Callable[
            [str],
            typing.Tuple[typing.Optional[str], typing.Optional[str], typing.Optional[str]],
        ],
    ) -> None:
        ...
