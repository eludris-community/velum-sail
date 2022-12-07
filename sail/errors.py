import typing

import attr
from velum import errors

__all__: typing.Sequence[str] = ("SailError", "ConversionError")


@attr.define(auto_exc=True, repr=False, init=False, slots=False)
class SailError(errors.VelumError):
    pass


@attr.define(auto_exc=True, repr=False, init=False, slots=False)
class ConversionError(SailError):

    argument: str
    type: typing.Type[typing.Any]
    exception: Exception
