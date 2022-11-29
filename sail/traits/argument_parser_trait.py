import inspect
import typing

__all__: typing.Sequence[str] = ("ArgumentParser",)


T = typing.TypeVar("T")

empty = inspect.Parameter.empty


class ArgumentParser(typing.Protocol[T]):
    __slots__: typing.Sequence[str] = ()

    @property
    def __type__(self) -> typing.Type[T]:
        ...

    def parse(self, argument: str, default: T | typing.Type[empty] = empty) -> T:
        ...
