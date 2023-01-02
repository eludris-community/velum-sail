from __future__ import annotations

import abc
import types
import typing

import attr

from sail import errors
from sail.internal import empty
from sail.internal import typing_utils
from sail.traits import argument_parser_trait

__all__: typing.Sequence[str] = (
    "NumberParser",
    "BoolParser",
    "StringParser",
    "UnionParser",
    "SequenceParser",
    "SetParser",
    "UnpackParser",
    "JoinedStringParser",
    "determine_type_parser",
    "determine_container_parser",
)


T = typing.TypeVar("T")
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
        argument = argument.lower()

        if argument in ["yes", "y", "true", "t", "1"]:
            return True
        elif argument in ["no", "n", "false", "f", "0"]:
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


class UnionParser(argument_parser_trait.ArgumentParser[T]):

    _type: typing.Type[T]

    def __init__(
        self,
        type_: typing.Type[T],
    ) -> None:
        self._type = type_
        self.is_optional = False

        self.parsers: typing.List[argument_parser_trait.ArgumentParser[typing.Any]] = []
        for subtype in typing.get_args(type_):
            if subtype in typing_utils.NONES:
                self.is_optional = True

            else:
                inner, _, parameter_annotations = typing_utils.unpack_typehint(subtype)
                self.parsers.append(determine_type_parser(inner, parameter_annotations))

    @property
    def __type__(self) -> typing.Type[T]:
        return self._type

    def parse(self, argument: str, default: T | empty.Empty = empty.EMPTY) -> T:
        for parser in self.parsers:
            try:
                return parser.parse(argument)

            except Exception:
                pass

        if empty.is_nonempty(default):
            return default

        types_repr = ", ".join(repr(parser.__type__.__name__) for parser in self.parsers)
        raise RuntimeError(f"Argument {argument!r} could not be converted to any of {types_repr}.")


# Container Parsers...


@attr.define()
class _ContainerParser(argument_parser_trait.ContainerParser[ContainerT]):
    # NOTE: This class is private because a container would also allow
    # mappings to be used. Instead, we make subclasses for sequences
    # and sets, as a mapping parser would require different logic.

    collection_type: typing.Type[ContainerT] = attr.field()

    @property
    def __type__(self) -> typing.Type[ContainerT]:
        return self.collection_type

    def parse(
        self, argument: typing.Iterable[object], default: ContainerT | empty.Empty = empty.EMPTY
    ) -> ContainerT:
        try:
            return self.collection_type.__call__(argument)
        except Exception as exc:
            if empty.is_nonempty(default):
                return default

            raise errors.ConversionError(argument, self.collection_type, exc) from None


@attr.define()
class SequenceParser(_ContainerParser[SequenceT]):
    def __attrs_post_init__(self) -> None:
        # In case some non-instantiable generic was passed, default to list.
        if isinstance(self.collection_type, abc.ABCMeta):
            self.collection_type = typing.cast(typing.Type[SequenceT], list)


@attr.define()
class SetParser(_ContainerParser[SetT]):
    def __attrs_post_init__(self) -> None:
        # In case some non-instantiable generic was passed, default to set.
        if isinstance(self.collection_type, abc.ABCMeta):
            self.collection_type = typing.cast(typing.Type[SetT], set)


@attr.define()
class UnpackParser(argument_parser_trait.ContainerParser[typing.Any]):
    # NOTE: Intentionally somewhat hacky with typing.Any, as this parser
    #       will be used to unpack a container to its first argument,
    #       and a container parser normally expects to return a container.

    @property
    def __type__(self) -> typing.Type[None]:
        return types.NoneType

    def parse(
        self, argument: typing.Sequence[object], default: typing.Any | empty.Empty = empty.EMPTY
    ) -> typing.Any:
        if len(argument) == 1:
            return argument[0]

        elif len(argument) > 1:
            raise errors.ConversionError(
                argument,
                self.__type__,
                TypeError("Got more than 1 argument for a parameter without a container type."),
            )

        elif empty.is_nonempty(default):
            return default

        raise errors.ConversionError(
            argument, self.__type__, TypeError("Got 0 arguments for required parameter.")
        ) from None


@attr.define()
class JoinedStringParser(argument_parser_trait.ContainerParser[str]):

    separator: str = attr.field(default=" ")

    @property
    def __type__(self) -> typing.Type[str]:
        return str

    def parse(
        self, argument: typing.Sequence[object], default: str | empty.Empty = empty.EMPTY
    ) -> str:
        if not argument:
            if empty.is_nonempty(default):
                return default

            raise TypeError("Got 0 arguments for required parameter.")

        assert all(isinstance(arg, str) for arg in argument)

        return self.separator.join(typing.cast(typing.Sequence[str], argument))


# TODO: Perhaps make a dict for this for slightly faster lookup.
#       Should not matter too much anyways as commands are only created when
#       the client is first started or when plugins are (re)loaded.
def determine_type_parser(
    type_: typing.Type[typing.Any],
    annotated_params: typing.Sequence[typing.Any],
) -> argument_parser_trait.ArgumentParser[typing.Any]:
    if typing.get_origin(type_) in typing_utils.UNIONS:
        return UnionParser(type_)
    elif type_ is empty or type_ is typing.Any or issubclass(type_, str):
        return StringParser()
    elif issubclass(type_, bool):
        return BoolParser()
    elif issubclass(type_, int):
        return NumberParser(decimal=False)
    elif issubclass(type_, float):
        return NumberParser()

    raise TypeError(f"Unsupported type annotation: {type_!r}.")


def determine_container_parser(
    type_: typing.Optional[typing.Type[typing.Container[typing.Any]]],
    annotated_params: typing.Sequence[typing.Any],
) -> argument_parser_trait.ContainerParser[typing.Any]:
    if typing_utils.SpecialType.JOINEDSTR in annotated_params:
        return JoinedStringParser()
    elif type_ is None:
        return UnpackParser()
    elif issubclass(type_, typing.Sequence):
        return SequenceParser(type_)
    elif issubclass(type_, typing.AbstractSet):
        return SetParser(type_)

    raise TypeError(f"Unsupported container type annotation: {type_!r}.")
