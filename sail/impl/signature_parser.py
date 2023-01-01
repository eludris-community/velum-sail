import types
import typing

import attr

from sail import errors
from sail.impl import param_info
from sail.internal import empty
from sail.internal import parser
from sail.internal import undefined
from sail.traits import argument_parser_trait
from sail.traits import signature_parser_trait

__all__: typing.Sequence[str] = ("SignatureParser",)


T = typing.TypeVar("T")
AnyCollectionT = typing.Type[typing.Collection[typing.Any]]


@attr.define()
class SignatureParser(signature_parser_trait.SignatureParser):

    _pos_params: typing.List[param_info.ParamInfo[typing.Any]] = attr.field()
    _kw_params: typing.Dict[str, param_info.ParamInfo[typing.Any]] = attr.field()
    string_parser: parser.StringParserCallback = attr.field(default=parser.parse_content)

    @property
    def pos_params(self) -> typing.Sequence[param_info.ParamInfo[typing.Any]]:
        return tuple(self._pos_params)

    @property
    def kw_params(self) -> typing.Mapping[str, param_info.ParamInfo[typing.Any]]:
        return types.MappingProxyType(self._kw_params)

    @property
    def alias_map(self) -> typing.Mapping[str, str]:
        aliases: typing.Dict[str, str] = {}
        for param in self._kw_params.values():
            aliases[param.name] = param.name
            if param.short:
                aliases[param.short] = param.name

        return aliases

    def update_param_typesafe(
        self,
        name: str,
        /,
        *,
        parser: undefined.UndefinedOr[
            argument_parser_trait.ArgumentParser[T]
        ] = undefined.UNDEFINED,
        container_parser: undefined.UndefinedOr[
            argument_parser_trait.ContainerParser[typing.Any]
        ] = undefined.UNDEFINED,
        default: undefined.UndefinedOr[T] = undefined.UNDEFINED,
        short: undefined.UndefinedOr[str] = undefined.UNDEFINED,
        greedy: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        flag: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
    ) -> None:
        if name in self._kw_params:
            existing = self._kw_params[name]
        else:
            for existing in self._pos_params:
                if existing.name == name:
                    break

            else:
                raise NameError("Could not find a param with name '{name}'.")

        # If the param used to be positional and is now a flag, it should
        # be moved from pos_params to kw_params.
        if not existing.is_flag and (flag or short):
            self._pos_params.remove(existing)
            self._kw_params[existing.name] = existing

        # Finally, we update in-place.
        existing.override_typesafe(
            parser=parser,
            container_parser=container_parser,
            default=default,
            short=short,
            greedy=greedy,
            flag=flag,
        )

    def _consume_greedy_pos(
        self,
        arg_iter: typing.Iterator[str],
        param: param_info.ParamInfo[typing.Any],
        next_param: param_info.ParamInfo[typing.Any],
        carry: typing.List[typing.Any],
    ) -> typing.Collection[typing.Any]:
        for arg in arg_iter:
            try:
                carry.append(param.parser.parse(arg))

            except errors.ConversionError:
                result: typing.Collection[typing.Any] = param.container_parser.parse(carry)

                # Add the most recent param to the carry list for the
                # next iteration.
                carry.clear()
                carry.append(next_param.parser.parse(arg))

                return result

        result: typing.Collection[typing.Any] = param.container_parser.parse(carry)
        carry.clear()

        return result

    def _consume_nongreedy_pos(
        self,
        arg_iter: typing.Iterator[str],
        param: param_info.ParamInfo[typing.Any],
        next_param: param_info.ParamInfo[typing.Any],
        carry: typing.List[typing.Any],
    ) -> typing.Collection[typing.Any]:
        # We ensure the first arg always belongs to the param.
        # TODO: Do we really?
        carry.append(param.parser.parse(next(arg_iter)))

        for arg in arg_iter:
            try:
                next_value = next_param.parser.parse(arg)

            except errors.ConversionError:
                carry.append(param.parser.parse(arg))

            else:
                result = param.container_parser.parse(carry)

                # Add the most recent param to the carry list for the
                # next iteration.
                carry.clear()
                carry.append(next_value)

                return result

        result = param.container_parser.parse(carry)
        carry.clear()

        return result

    def _consume_remaining_pos(
        self,
        arg_iter: typing.Iterator[str],
        param: param_info.ParamInfo[typing.Any],
        carry: typing.List[typing.Any],
    ) -> typing.Collection[typing.Any]:
        for arg in arg_iter:
            carry.append(param.parser.parse(arg))

        return param.container_parser.parse(carry)

    def _try_default_pos(
        self,
        param: param_info.ParamInfo[typing.Any],
    ) -> typing.Any:
        if not empty.is_nonempty(param.default):
            raise RuntimeError(f"Required parameter {param.name} was not supplied a value.")

        return param.container_parser.parse([param.default])

    def _parse_pos(  # noqa: C901
        self,
        args: typing.Sequence[str],
        results_store: typing.List[typing.Any],
    ) -> typing.Sequence[typing.Any]:
        n_pos = len(self._pos_params)
        pos_iter = enumerate(self._pos_params, 1)
        arg_iter = iter(args)

        # Temporary storage for parsed args, also used to carry args between iterations.
        carry: typing.List[typing.Any] = []

        for next_idx, param in pos_iter:

            if param.greedy:
                if next_idx >= n_pos:
                    # No remaining params, parse all remaining args
                    results_store.append(self._consume_remaining_pos(arg_iter, param, carry))
                    break

                # Keep parsing args until we fail, only then continue to next param.
                results_store.append(
                    self._consume_greedy_pos(arg_iter, param, self._pos_params[next_idx], carry)
                )

            elif param.has_container:
                if next_idx >= n_pos:
                    # No remaining params, parse all remaining args
                    results_store.append(self._consume_remaining_pos(arg_iter, param, carry))
                    break

                # Non-greedily parse args, stop as soon as the next parser succeeds.
                results_store.append(
                    self._consume_nongreedy_pos(arg_iter, param, self._pos_params[next_idx], carry)
                )

            elif carry:
                # If we already have a result, and this param does not return a
                # collection, that result should be assigned to this param.
                results_store.append(carry[0])
                carry.clear()

            else:
                # If we don't have results yet, consume the next arg.
                try:
                    results_store.append(param.parser.parse(next(arg_iter)))

                except StopIteration:
                    # If there is no next arg, try to get the default instead.
                    results_store.append(self._try_default_pos(param))
                    break

        for _, param in pos_iter:
            # Try to supply any remaining parameters with their defaults, if any.
            # Error if any of these params does not have a default.
            results_store.append(self._try_default_pos(param))

        remaining = "', '".join(arg for arg in arg_iter)
        if remaining:
            # Any remaining args should raise.
            raise RuntimeError(f"Got too many positional arguments: '{remaining}' remain unused.")

        return results_store

    def _preprocess_kw(
        self,
        kwargs: typing.Mapping[str, typing.Sequence[str]],
        alias_map: typing.Mapping[str, str],
    ) -> typing.Mapping[str, typing.Sequence[str]]:
        unaliased: typing.Dict[str, typing.Sequence[str]] = {}
        for key, value in kwargs.items():
            unaliased[alias_map[key]] = value

        return unaliased

    def _parse_kw(
        self,
        kwargs: typing.Mapping[str, typing.Sequence[str]],
        results_store: typing.Dict[str, typing.Any],
    ) -> typing.Mapping[str, typing.Any]:

        alias_map = self.alias_map
        provided = set(kwargs)
        if not provided.issubset(alias_map):
            remainder = "', '".join(provided.difference(alias_map))
            raise RuntimeError(f"Got one or more unexpected keyword arguments: '{remainder}'")

        # Unwrap aliases...
        kwargs = self._preprocess_kw(kwargs, alias_map)

        carry: typing.Sequence[typing.Any] = []
        for name, param in self._kw_params.items():
            if param.type is bool:
                results_store[name] = param.short in kwargs or param.name in kwargs
                continue

            for arg in kwargs[name]:
                carry.append(param.parser.parse(arg))

            if param.has_container:
                results_store[name] = param.container_parser.parse(carry)
                carry.clear()

            elif len(carry) > 1:
                raise RuntimeError(
                    f"Got more than 1 argument for parameter {param.name} of type "
                    f"{param.parser.__type__.__name__}: {kwargs[name]!r}."
                )

            else:
                results_store[name] = carry[0]
                carry.clear()

        return results_store

    def _parse(
        self,
        args: typing.Sequence[str],
        kwargs: typing.Mapping[str, typing.Sequence[str]],
    ):
        pos_results: typing.List[typing.Any] = []
        try:
            parsed_args = self._parse_pos(args, pos_results)

        except errors.ConversionError as exc:
            # Add whatever we did manage to convert to the exception for debugging
            exc.converted = pos_results
            raise exc

        kw_results: typing.Dict[str, typing.Any] = {}
        try:
            parsed_kwargs = self._parse_kw(kwargs, kw_results)

        except errors.ConversionError as exc:
            exc.converted = kw_results
            raise exc

        return parsed_args, parsed_kwargs

    def parse(
        self,
        invocation: str,
    ) -> typing.Tuple[typing.Sequence[typing.Any], typing.Mapping[str, typing.Any]]:
        args, kwargs = self.string_parser(invocation)
        return self._parse(args, kwargs)
