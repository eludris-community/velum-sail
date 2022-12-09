import enum
import typing

__all__: typing.Sequence[str] = (
    "Greedy",
    "JoinedStr",
    "SpecialType",
    "unpack_typehint",
)


class SpecialType(enum.Enum):
    GREEDY = enum.auto()
    JOINEDSTR = enum.auto()


CollectionT = typing.TypeVar("CollectionT", bound=typing.Collection[typing.Any])
Greedy = typing.Annotated[CollectionT, SpecialType.GREEDY]
JoinedStr = typing.Annotated[str, SpecialType.JOINEDSTR]


def unpack_typehint(
    annotation: typing.Any,
) -> typing.Tuple[
    typing.Any,  # Innermost type
    typing.Optional[typing.Type[typing.Any]],  # Container type
    typing.Sequence[typing.Any],  # Annotated arguments, if any
]:
    if container := typing.get_origin(annotation):
        if container is typing.Annotated:
            annotation, *annotated_args = typing.get_args(annotation)

            inner, container, _ = unpack_typehint(annotation)
            return inner, container, annotated_args

        inner = typing.get_args(annotation)[0]
    else:
        inner = annotation

    return inner, container, ()
