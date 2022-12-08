from __future__ import annotations

import attr
import typing

from sail import errors
from sail.internal import empty
from sail.traits import argument_parser_trait

__all__: typing.Sequence[str] = ("NumberParser", "BoolParser", "StringParser")


NumberT = typing.TypeVar("NumberT", bound=int | float)
ContainerT = typing.TypeVar("ContainerT", bound=typing.Container[typing.Any])
SequenceT = typing.TypeVar("SequenceT", bound=typing.Sequence[typing.Any])
SetT = typing.TypeVar("SetT", bound=typing.AbstractSet[typing.Any])


@attr.define()
class NumberParser(argument_parser_trait.ArgumentParser[NumberT]):

    signed: bool = attr.field(default=True)
    decimal: bool = attr.field(default=True)

    if typing.TYPE_CHECKING:

        @typing.overload
        def __init__(
            self: NumberParser[int],
            *,
            signed: bool = True,
            decimal: typing.Literal[False],
        ):
            ...

        @typing.overload
        def __init__(
            self: NumberParser[float],
            *,
            signed: bool = True,
            decimal: typing.Literal[True] = True,
        ):
            ...

        def __init__(self, *, signed: bool = True, decimal: bool = True):
            ...

    @property
    def __type__(self) -> typing.Type[NumberT]:
        return typing.cast(typing.Type[NumberT], float if self.decimal else int)

    def parse(
        self,
        argument: str,
        default: empty.EmptyOr[NumberT] = empty.EMPTY,
    ) -> NumberT:
        type_ = float if self.decimal else int

        try:
            result = typing.cast(NumberT, type_(argument))

        except Exception as exc:
            raise errors.ConversionError(argument, type_, exc) from None

        else:
            if empty.is_nonempty(default):
                return default

            if not self.signed and result < 0:
                raise errors.ConversionError(
                    argument,
                    type_,
                    ValueError(f"'{result}' is not a valid unsigned number."),
                )

            return result


class BoolParser(argument_parser_trait.ArgumentParser[bool]):
    @property
    def __type__(self) -> typing.Type[bool]:
        return bool

    def parse(
        self,
        argument: str,
        default: empty.EmptyOr[bool] = empty.EMPTY,
    ) -> bool:
        if argument.lower() in ["yes", "y", "true", "t", "1", ""]:
            return True
        elif argument.lower() in ["no", "n", "false", "f", "0"]:
            return False
        else:
            if empty.is_nonempty(default):
                return default

            raise errors.ConversionError(
                argument,
                bool,
                ValueError(f"'{argument}' is not a valid boolean."),
            )


class StringParser(argument_parser_trait.ArgumentParser[str]):
    @property
    def __type__(self) -> typing.Type[str]:
        return str

    def parse(
        self,
        argument: str,
        default: empty.EmptyOr[str] = empty.EMPTY,
    ) -> str:
        if argument:
            return argument
        if empty.is_nonempty(default):
            return default
        return ""


@attr.define()
class _ContainerParser(argument_parser_trait.ContainerParser[ContainerT]):
    # NOTE: This class is private because a container would also allow
    # mappings to be used. Instead, we make two subclasses for sequences
    # and sets, as a mapping parser would require different logic.

    collection_type: typing.Type[ContainerT] = attr.field()

    @property
    def __type__(self) -> typing.Type[ContainerT]:
        return self.collection_type

    def parse(
        self,
        argument: typing.Iterable[str],
        default: ContainerT | empty.Empty = empty.EMPTY
    ) -> ContainerT:
        try:
            return self.collection_type.__call__(argument)
        except Exception as exc:
            if empty.is_nonempty(default):
                return default

            raise errors.ConversionError(argument, self.collection_type, exc) from None


class SequenceParser(_ContainerParser[SequenceT]):
    __slots__: typing.Sequence[str] = ()


class SetParser(_ContainerParser[SetT]):
    __slots__: typing.Sequence[str] = ()
