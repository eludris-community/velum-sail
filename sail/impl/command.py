from __future__ import annotations

import inspect
import typing

import attr
from velum.events import message_events

from sail.impl import param_info
from sail.impl import signature_parser
from sail.internal import empty
from sail.internal import undefined
from sail.traits import argument_parser_trait
from sail.traits import command_trait

__all__: typing.Sequence[str] = (
    "Command",
    "Context",
)


_DEFAULT_DESC = "No description provided."

P = typing.ParamSpec("P")
T = typing.TypeVar("T")

AnyCollectionT = typing.Type[typing.Collection[typing.Any]]
CommandCallback = typing.Callable[
    typing.Concatenate["Context", P],
    typing.Coroutine[typing.Any, typing.Any, T],
]


@attr.define()
class Context:

    command: Command[typing.Any, typing.Any] = attr.field()
    prefix: str = attr.field()
    invoked_with: str = attr.field()
    event: message_events.MessageCreateEvent = attr.field()
    args: typing.Sequence[typing.Any] = attr.field()
    kwargs: typing.Mapping[str, typing.Any] = attr.field()

    @property
    def author(self) -> str:
        return self.event.author

    @property
    def content(self) -> str:
        return self.event.content


@attr.define(init=False)
class Command(command_trait.Command[P, T]):

    callback: CommandCallback[P, T] = attr.field(repr=False)
    name: str = attr.field()
    description: str = attr.field()
    aliases: typing.Collection[str] = attr.field()

    _signature: inspect.Signature = attr.field(repr=False)
    _signature_parser: signature_parser.SignatureParser = attr.field(repr=False)

    def __init__(
        self,
        callback: CommandCallback[P, T],
        /,
        *,
        name: typing.Optional[str] = None,
        description: typing.Optional[str] = None,
        aliases: typing.Optional[typing.Collection[str]] = None,
    ):
        self.callback = callback
        self.name = name or callback.__name__
        self.description = description or callback.__doc__ or _DEFAULT_DESC

        if not aliases:
            self.aliases = []
        elif isinstance(aliases, str):
            self.aliases = [aliases]
        else:
            self.aliases = aliases

        self._signature = inspect.signature(self.callback, eval_str=True)
        self.validate_params()

    def update_param_typesafe(
        self,
        name: str,
        /,
        *,
        parser: undefined.UndefinedOr[
            argument_parser_trait.ArgumentParser[T]
        ] = undefined.UNDEFINED,
        default: undefined.UndefinedOr[T] = undefined.UNDEFINED,
        container: undefined.UndefinedOr[AnyCollectionT] = undefined.UNDEFINED,
        short: undefined.UndefinedOr[str] = undefined.UNDEFINED,
        greedy: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        flag: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
    ) -> None:
        self._signature_parser.update_param_typesafe(
            name,
            parser=parser,
            default=default,
            container=container,
            short=short,
            greedy=greedy,
            flag=flag,
        )

    def validate_params(self) -> None:
        paraminfo: typing.Optional[param_info.ParamInfo[typing.Any]]
        pos_params: typing.List[param_info.ParamInfo[typing.Any]] = []
        kw_params: typing.Dict[str, param_info.ParamInfo[typing.Any]] = {}

        params_iter = iter(self._signature.parameters.items())

        # Ensure the first argument is the context.
        _, parameter = next(params_iter)
        if parameter.annotation is not empty and not issubclass(parameter.annotation, Context):
            raise TypeError("The first parameter of a command must be its context.")

        for name, parameter in params_iter:
            paraminfo = param_info.ParamInfo.from_parameter(parameter)

            if parameter.kind is inspect.Parameter.KEYWORD_ONLY:
                kw_params[name] = paraminfo
            else:
                pos_params.append(paraminfo)

        self._signature_parser = signature_parser.SignatureParser(pos_params, kw_params)

    async def invoke(
        self,
        event: message_events.MessageCreateEvent,
        /,
        *,
        prefix: str,
        invoked_with: str,
        invocation: str,
    ) -> None:
        args, kwargs = self._signature_parser.parse(invocation)
        ctx = Context(self, prefix, invoked_with, event, args, kwargs)

        await self.callback(ctx, *args, **kwargs)  # pyright: ignore[reportGeneralTypeIssues]
