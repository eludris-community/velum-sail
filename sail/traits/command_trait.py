import typing

from velum.events import message_events

__all__: typing.Sequence[str] = ("Command",)


P = typing.ParamSpec("P")
T = typing.TypeVar("T")
T_co = typing.TypeVar("T_co", covariant=True)

AnyCollectionT = typing.Type[typing.Collection[typing.Any]]

AnyCommand: typing.TypeAlias = "Command[typing.Any, typing.Any]"
CommandT = typing.TypeVar("CommandT", bound=AnyCommand)


class _AnyCallable(typing.Protocol):
    """An extremely lenient callable type."""

    def __call__(self, *__args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        ...


class Command(typing.Protocol[P, T_co]):
    __slots__: typing.Sequence[str] = ("name", "description", "aliases", "callback")

    name: str
    description: str
    aliases: typing.Collection[str]
    callback: _AnyCallable

    async def invoke(
        self,
        event: message_events.MessageCreateEvent,
        /,
        **__kwargs: typing.Any,
    ) -> None:
        ...
