import inspect
import types
import typing

import attr
import typing_extensions

from sail.impl import argument_parser
from sail.internal import empty
from sail.internal import typing_utils
from sail.internal import undefined
from sail.traits import argument_parser_trait

__all__: typing.Sequence[str] = ("ParamInfo",)


T = typing.TypeVar("T")
AnyContainer = typing.Container[typing.Any]


def _determine_type_parser(
    type_: typing.Type[typing.Any],
    parameter_name: str,
    annotated_params: typing.Sequence[typing.Any],
) -> argument_parser_trait.ArgumentParser[typing.Any]:
    if type_ is empty or type_ is typing.Any or issubclass(type_, str):
        return argument_parser.StringParser()
    elif issubclass(type_, bool):
        return argument_parser.BoolParser()
    elif issubclass(type_, int):
        return argument_parser.NumberParser(decimal=False)
    elif issubclass(type_, float):
        return argument_parser.NumberParser()

    raise TypeError(f"Unsupported type annotation for parameter {parameter_name}.")


def _determine_container_parser(
    type_: typing.Optional[typing.Type[AnyContainer]],
    parameter_name: str,
    annotated_params: typing.Sequence[typing.Any],
) -> argument_parser_trait.ContainerParser[typing.Any]:
    if typing_utils.SpecialType.JOINEDSTR in annotated_params:
        return argument_parser.JoinedStringParser()
    elif type_ is None:
        return argument_parser.UnpackParser()
    elif issubclass(type_, typing.Sequence):
        return argument_parser.SequenceParser(type_)
    elif issubclass(type_, typing.AbstractSet):
        return argument_parser.SetParser(type_)

    raise TypeError(f"Unsupported container type annotation for parameter {parameter_name}.")


@attr.define()
class ParamInfo(typing.Generic[T]):
    name: str = attr.field()
    parser: argument_parser_trait.ArgumentParser[T] = attr.field()
    container_parser: argument_parser_trait.ContainerParser[typing.Any] = attr.field(default=None)
    default: empty.EmptyOr[T] = attr.field(default=empty.EMPTY, kw_only=True)
    short: typing.Optional[str] = attr.field(default=None, kw_only=True)
    greedy: bool = attr.field(default=False, kw_only=True)
    flag: bool = attr.field(default=False, kw_only=True)

    def __attrs_post_init__(self) -> None:
        if self.container_parser is None:
            self.container_parser = argument_parser.UnpackParser()

        if self.greedy and isinstance(self.container_parser, argument_parser.UnpackParser):
            raise TypeError("Greedy parameters must be have a container of some sort.")

        if self.is_flag and self.greedy:
            raise TypeError("Flags cannot be greedy.")

    @property
    def type(self) -> typing.Type[T]:
        return self.parser.__type__

    @property
    def is_optional(self) -> bool:
        return self.default is empty

    @property
    def is_flag(self) -> bool:
        return self.flag or self.short is not None

    @property
    def has_container(self) -> bool:
        return self.container_parser.__type__ is not types.NoneType  # noqa: E721

    @classmethod
    def from_parameter(cls, parameter: inspect.Parameter) -> typing_extensions.Self:
        inner, container, annotated_params = typing_utils.unpack_typehint(parameter.annotation)

        greedy = typing_utils.SpecialType.GREEDY in annotated_params
        flag = parameter.kind is inspect.Parameter.KEYWORD_ONLY and inner is bool and not container

        if greedy and (parameter.kind is inspect.Parameter.KEYWORD_ONLY):
            raise TypeError("Keyword-only arguments cannot be greedy.")

        if container and not issubclass(container, typing.Collection):
            raise TypeError("The container class must be a subclass of typing.Collection.")

        if greedy and not container:
            raise TypeError("Greedy parameters must be have a container of some sort.")


        return cls(
            parameter.name,
            _determine_type_parser(inner, parameter.name, annotated_params),
            _determine_container_parser(container, parameter.name, annotated_params),
            default=parameter.default,
            greedy=greedy,
            flag=flag,
        )

    def override_typesafe(  # noqa: C901
        self,
        /,
        *,
        parser: undefined.UndefinedOr[
            argument_parser_trait.ArgumentParser[T]
        ] = undefined.UNDEFINED,
        container_parser: undefined.UndefinedOr[
            argument_parser_trait.ContainerParser[AnyContainer],
        ] = undefined.UNDEFINED,
        default: undefined.UndefinedOr[T] = undefined.UNDEFINED,
        short: undefined.UndefinedOr[str] = undefined.UNDEFINED,
        greedy: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        flag: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
    ) -> None:
        if parser:
            if not issubclass(parser.__type__, self.parser.__type__):
                raise TypeError(
                    "The override parser's type must be a subtype of that of the existing parser. "
                    f"Got: '{parser.__type__}', expected '{self.parser.__type__}'."
                )

            self.parser = parser

        if default:
            if self.default is not empty:  # TODO: maybe warn instead?
                raise ValueError("A default was already provided as part of the signature.")

            self.default = default

        if container_parser:
            _, container, _ = typing_utils.unpack_typehint(container_parser.__type__)

            if container and not issubclass(container, self.container_parser.__type__):
                raise TypeError(
                    "The override container parser's type must be a subtype of"
                    " the existing container parser's type."
                )

            self.container_parser = container_parser

        if short:
            self.short = short

        if isinstance(greedy, bool):
            if self.is_flag:
                raise TypeError("Flags cannot be greedy.")

            if self.greedy and not greedy:
                raise TypeError(
                    "Cannot override a parameter typehinted as greedy to be non-greedy."
                )

            self.greedy = greedy

        if isinstance(flag, bool):
            if self.is_flag and not flag:
                raise TypeError(
                    "Cannot override a flag parameter to no longer be a flag. "
                    "Note: callback parameter denoted as keyword-only are automatically made flags."
                )
