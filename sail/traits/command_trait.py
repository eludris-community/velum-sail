import typing

from velum.events import message_events

__all__: typing.Sequence[str] = ("Command",)


P = typing.ParamSpec("P")
T = typing.TypeVar("T")
T_co = typing.TypeVar("T_co", covariant=True)

AnyCollectionT = typing.Type[typing.Collection[typing.Any]]

AnyCommand: typing.TypeAlias = "Command[typing.Any, typing.Any]"
CommandT = typing.TypeVar("CommandT", bound=AnyCommand)


class Command(typing.Protocol[P, T_co]):
    __slots__: typing.Sequence[str] = ("name",)

    name: str
    aliases: typing.Collection[str]

    async def invoke(
        self,
        event: message_events.MessageCreateEvent,
        /,
        **__kwargs: typing.Any,
    ):
        ...
