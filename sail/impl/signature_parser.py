import typing

import attr

from sail import errors
from sail.impl import param_info
from sail.internal import parser
from sail.internal import undefined
from sail.traits import argument_parser_trait
from sail.traits import signature_parser_trait

__all__: typing.Sequence[str] = ("SignatureParser",)


T = typing.TypeVar("T")
AnyCollectionT = typing.Type[typing.Collection[typing.Any]]


@attr.define()
class SignatureParser(signature_parser_trait.SignatureParser):

    pos_params: typing.Sequence[param_info.ParamInfo[typing.Any]] = attr.field()
    kw_params: typing.Mapping[str, param_info.ParamInfo[typing.Any]] = attr.field()

    def update_param_typesafe(
        self,
        name: str,
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
        if name in self.kw_params:
            existing = self.kw_params[name]
        else:
            for existing in self.pos_params:
                if existing.name == name:
                    break

            else:
                raise NameError("Could not find a param with name '{name}'.")

        should_move = (existing.is_flag is False) and (flag is True)

        existing.override_typesafe(
            parser=parser,
            default=default,
            container=container,
            short=short,
            greedy=greedy,
            flag=flag,
        )

        if should_move:
            self.pos_params = [param for param in self.pos_params if param is not existing]
            self.kw_params = {**self.kw_params, existing.name: existing}

    def _consume_greedy_pos(
        self,
        arg_iter: typing.Iterator[str],
        param: param_info.ParamInfo[typing.Any],
        next_param: param_info.ParamInfo[typing.Any],
        carry: typing.List[typing.Any],
    ) -> typing.Collection[typing.Any]:
        assert param.container

        for arg in arg_iter:
            try:
                carry.append(param.parser.parse(arg))

            except errors.ConversionError:
                result: typing.Collection[typing.Any] = param.container.__call__(carry)

                # Add the most recent param to the carry list for the
                # next iteration.
                carry.clear()
                carry.append(next_param.parser.parse(arg))

                return result

        result: typing.Collection[typing.Any] = param.container.__call__(carry)
        carry.clear()

        return result

    def _consume_nongreedy_pos(
        self,
        arg_iter: typing.Iterator[str],
        param: param_info.ParamInfo[typing.Any],
        next_param: param_info.ParamInfo[typing.Any],
        carry: typing.List[typing.Any],
    ) -> typing.Collection[typing.Any]:
        assert param.container

        # We ensure the first arg always belongs to the param.
        # TODO: Do we really?
        carry.append(param.parser.parse(next(arg_iter)))

        for arg in arg_iter:
            try:
                next_param.parser.parse(arg)

            except errors.ConversionError:
                carry.append(param.parser.parse(arg))

            else:
                result = param.container.__call__(carry)

                # Add the most recent param to the carry list for the
                # next iteration.
                carry.clear()
                carry.append(next_param.parser.parse(arg))

                return result

        result = param.container.__call__(carry)
        carry.clear()

        return result

    def _consume_remaining_pos(
        self,
        arg_iter: typing.Iterator[str],
        param: param_info.ParamInfo[typing.Any],
        carry: typing.List[typing.Any],
    ) -> typing.Collection[typing.Any]:
        assert param.container

        for arg in arg_iter:
            carry.append(param.parser.parse(arg))

        return param.container.__call__(carry)

    def _try_default_pos(
        self,
        param: param_info.ParamInfo[typing.Any],
    ) -> typing.Any:
        if not param.default:
            raise RuntimeError(f"Required parameter {param.name} was not supplied a value.")
        if param.container:
            return param.container.__call__([param.default])

        return param.default

    def _parse_pos(self, args: typing.Sequence[str]) -> typing.Sequence[typing.Any]:
        n_pos = len(self.pos_params)
        pos_iter = enumerate(self.pos_params, 1)
        arg_iter = iter(args)

        # Temporary storage for parsed args, also used to carry args between iterations.
        carry: typing.List[typing.Any] = []

        # Storage for final results.
        arg_results: typing.List[typing.Any] = []
        for next_idx, param in pos_iter:

            if param.greedy:
                if next_idx >= n_pos:
                    # No remaining params, parse all remaining args
                    arg_results.append(self._consume_remaining_pos(arg_iter, param, carry))
                    break

                # Keep parsing args until we fail, only then continue to next param.
                arg_results.append(
                    self._consume_greedy_pos(arg_iter, param, self.pos_params[next_idx], carry)
                )

            elif param.container:
                if next_idx >= n_pos:
                    # No remaining params, parse all remaining args
                    arg_results.append(self._consume_remaining_pos(arg_iter, param, carry))
                    break

                # Non-greedily parse args, stop as soon as the next parser succeeds.
                arg_results.append(
                    self._consume_nongreedy_pos(arg_iter, param, self.pos_params[next_idx], carry)
                )

            elif carry:
                # If we already have a result, and this param does not return a
                # collection, that result should be assigned to this param.
                arg_results.append(carry[0])
                carry.clear()

            else:
                # If we don't have results yet, consume the next arg.
                try:
                    arg_results.append(param.parser.parse(next(arg_iter)))

                except StopIteration:
                    # If there is no next arg, try to get the default instead.
                    arg_results.append(self._try_default_pos(param))
                    break

        for _, param in pos_iter:
            # Try to supply any remaining parameters with their defaults, if any.
            # Error if any of these params does not have a default.
            arg_results.append(self._try_default_pos(param))

        remaining = "', '".join(arg for arg in arg_iter)
        if remaining:
            # Any remaining args should raise.
            raise RuntimeError(f"Supplied too many arguments: '{remaining}' remain unused.")

        return arg_results

    def _parse_kw(
        self, kwargs: typing.Mapping[str, typing.Sequence[str]]
    ) -> typing.Mapping[str, typing.Any]:
        carry: typing.Sequence[typing.Any] = []
        kwarg_results: typing.Mapping[str, typing.Any] = {}
        for name, param in self.kw_params.items():
            if param.type is bool:
                kwarg_results[name] = param.short in kwargs or param.name in kwargs
                continue

            for arg in kwargs[name]:
                carry.append(param.parser.parse(arg))

            if param.container:
                kwarg_results[name] = param.container.__call__(carry)
                carry.clear()

            elif len(carry) > 1:
                raise RuntimeError(
                    f"Got more than 1 argument for parameter {param.name} of type "
                    f"{param.parser.__type__.__name__}: {kwargs[name]!r}."
                )

            else:
                kwarg_results[name] = carry
                carry.clear()

        return kwarg_results

    def parse(
        self,
        invocation: str,
    ) -> typing.Tuple[typing.Sequence[typing.Any], typing.Mapping[str, typing.Any]]:
        args, kwargs = parser.parse_content(invocation)
        return (self._parse_pos(args), self._parse_kw(kwargs))
