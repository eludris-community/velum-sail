import typing

from sail.internal import empty

__all__: typing.Sequence[str] = ("ArgumentParser",)


T = typing.TypeVar("T")
ContainerT = typing.TypeVar("ContainerT", bound=typing.Container[typing.Any])


class ArgumentParser(typing.Protocol[T]):
    __slots__: typing.Sequence[str] = ()

    @property
    def __type__(self) -> typing.Type[T]:
        ...

    def parse(self, argument: str, default: T | empty.Empty = empty.EMPTY) -> T:
        ...


class ContainerParser(typing.Protocol[ContainerT]):
    __slots__: typing.Sequence[str] = ()

    @property
    def __type__(self) -> typing.Type[ContainerT]:
        ...

    def parse(
        self,
        argument: typing.Sequence[object],
        default: ContainerT | empty.Empty = empty.EMPTY,
    ) -> ContainerT:
        ...
