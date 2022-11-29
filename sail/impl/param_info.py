import abc
import inspect
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
AnyCollectionT = typing.Type[typing.Collection[typing.Any]]


@attr.define()
class ParamInfo(typing.Generic[T]):
    name: str = attr.field()
    parser: argument_parser_trait.ArgumentParser[T] = attr.field()
    default: empty.EmptyOr[T] = attr.field(default=empty.EMPTY, kw_only=True)
    container: typing.Optional[AnyCollectionT] = attr.field(default=None, kw_only=True)
    short: typing.Optional[str] = attr.field(default=None, kw_only=True)
    greedy: bool = attr.field(default=False, kw_only=True)
    flag: bool = attr.field(default=False, kw_only=True)

    def __attrs_post_init__(self) -> None:
        if self.greedy and not self.container:
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

    @classmethod
    def from_parameter(cls, parameter: inspect.Parameter) -> typing_extensions.Self:
        inner, container, annotated_params = typing_utils.unpack_typehint(parameter.annotation)
        if isinstance(container, abc.ABCMeta):
            # If the container is some non-instantiable generic, default to list.
            container = list

        greedy = typing_utils.SpecialType.GREEDY in annotated_params
        flag = parameter.kind is inspect.Parameter.KEYWORD_ONLY and inner is bool and not container

        if greedy and (parameter.kind is inspect.Parameter.KEYWORD_ONLY):
            raise TypeError("Keyword-only arguments cannot be greedy.")

        if container and not issubclass(container, typing.Collection):
            raise TypeError("The container class must be a subclass of typing.Collection.")

        if greedy and not container:
            raise TypeError("Greedy parameters must be have a container of some sort.")

        if inner is empty or inner is typing.Any or issubclass(inner, str):
            parser = argument_parser.StringParser()
        elif issubclass(inner, bool):
            parser = argument_parser.BoolParser()
        elif issubclass(inner, int):
            parser = argument_parser.NumberParser(decimal=False)
        elif issubclass(inner, float):
            parser = argument_parser.NumberParser()
        else:
            raise TypeError(f"Unsupported type annotation for parameter {parameter.name}.")

        return cls(
            parameter.name,
            parser,
            default=parameter.default,
            container=container,
            greedy=greedy,
            flag=flag,
        )

    def override_typesafe(
        self,
        /,
        *,
        parser: undefined.UndefinedOr[
            argument_parser_trait.ArgumentParser[T]
        ] = undefined.UNDEFINED,
        default: undefined.UndefinedOr[T] = undefined.UNDEFINED,
        container: undefined.UndefinedOr[AnyCollectionT] = undefined.UNDEFINED,
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

        if container:
            if isinstance(container, abc.ABCMeta):
                # If the container is some non-instantiable generic, default to list.
                container = list

            if self.container is not None and not issubclass(container, self.container):
                raise TypeError(
                    "The override container type must be a subtype of the existing container type."
                )

            self.container = container

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
