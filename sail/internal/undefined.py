import typing

import typing_extensions

__all__: typing.Sequence[str] = (
    "UndefinedType",
    "UNDEFINED",
    "UndefinedOr",
)


class UndefinedType:
    """The type of the `UNDEFINED` singleton sentinel value."""

    __slots__: typing.Sequence[str] = ()

    def __bool__(self) -> typing.Literal[False]:
        return False

    def __copy__(self) -> typing_extensions.Self:
        # This is meant to be a singleton
        return self

    def __deepcopy__(self, memo: typing.MutableMapping[int, typing.Any]) -> typing_extensions.Self:
        memo[id(self)] = self

        # This is meant to be a singleton
        return self

    def __getstate__(self) -> typing.Any:
        # Returning False tells pickle to not call `__setstate__` on unpickling.
        return False

    def __repr__(self) -> str:
        return "UNDEFINED"

    def __reduce__(self) -> str:
        # Returning a string makes pickle fetch from the module namespace.
        return "UNDEFINED"

    def __str__(self) -> str:
        return "UNDEFINED"


UNDEFINED = UndefinedType()
"""A sentinel singleton that denotes a missing or omitted value."""


def __new__(cls: UndefinedType) -> typing.NoReturn:  # pragma: nocover
    raise TypeError("Cannot initialize multiple instances of singleton UNDEFINED")


UndefinedType.__new__ = __new__  # pyright: ignore
del __new__


_T = typing.TypeVar("_T")

UndefinedOr = typing.Union[_T, UndefinedType]
