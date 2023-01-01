import typing

from sail.internal import undefined
from sail.traits import argument_parser_trait

__all__: typing.Sequence[str] = ("SignatureParser",)


T = typing.TypeVar("T")
AnyCollectionT = typing.Type[typing.Collection[typing.Any]]


class SignatureParser(typing.Protocol):
    __slots__: typing.Sequence[str] = ()

    # TODO: clean this up?
    def update_param_typesafe(
        self,
        name: str,
        /,
        *,
        parser: undefined.UndefinedOr[
            argument_parser_trait.ArgumentParser[T]
        ] = undefined.UNDEFINED,
        container_parser: undefined.UndefinedOr[
            argument_parser_trait.ContainerParser[typing.Any]
        ] = undefined.UNDEFINED,
        default: undefined.UndefinedOr[T] = undefined.UNDEFINED,
        short: undefined.UndefinedOr[str] = undefined.UNDEFINED,
        greedy: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        flag: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
    ) -> None:
        ...

    def parse(
        self,
        invocation: str,
    ) -> typing.Tuple[typing.Sequence[typing.Any], typing.Mapping[str, typing.Any]]:
        ...
