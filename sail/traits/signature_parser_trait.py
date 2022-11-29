import typing

__all__: typing.Sequence[str] = ("SignatureParser",)


T = typing.TypeVar("T")
AnyCollectionT = typing.Type[typing.Collection[typing.Any]]


class SignatureParser(typing.Protocol):
    __slots__: typing.Sequence[str] = ()

    def parse(
        self,
        invocation: str,
    ) -> typing.Tuple[typing.Sequence[typing.Any], typing.Mapping[str, typing.Any]]:
        ...
