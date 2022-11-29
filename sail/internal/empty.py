import inspect
import typing

__all__: typing.Sequence[str] = (
    "EMPTY",
    "Empty",
    "EmptyOr",
    "is_nonempty",
)

_T = typing.TypeVar("_T")

EMPTY = inspect.Parameter.empty
Empty = typing.Type[EMPTY]
EmptyOr = Empty | _T


def is_nonempty(arg: EmptyOr[_T]) -> typing.TypeGuard[_T]:
    return arg is not EMPTY
