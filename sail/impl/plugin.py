import asyncio
import importlib.abc
import importlib.util
import inspect
import logging
import os
import pathlib
import sys
import types
import typing

import velum
from velum.events import base_events
from velum.internal import class_utils
from velum.traits import event_manager_trait
from velum.traits import rest_trait

from sail.impl import command as command_impl
from sail.internal import parser
from sail.traits import command_manager_trait
from sail.traits import command_trait
from sail.traits import plugin_trait

__all__: typing.Sequence[str] = ("Plugin", "load_extension", "unload_extension", "reload_extension")


P = typing.ParamSpec("P")
T = typing.TypeVar("T")

_CommandMapping = typing.Dict[str, command_trait.Command[typing.Any, typing.Any]]
_ListenerMapping = typing.Dict[
    typing.Type[base_events.Event],
    typing.List[base_events.EventCallbackT[base_events.Event]],
]
_EntrypointCallback = typing.Callable[
    [velum.GatewayClient, command_manager_trait.CommandManager],
    typing.Coroutine[typing.Any, typing.Any, None],
]


_LOGGER = logging.getLogger("sail.plugin")
_UNIONS = frozenset((typing.Union, types.UnionType))


def _get_source_module_name() -> str:
    module_name = pathlib.Path(logging.currentframe().f_code.co_filename).stem
    _LOGGER.debug("Module name resolved to %r", module_name)
    return module_name


class Plugin(plugin_trait.Plugin):

    name: str
    logger: logging.Logger

    _client: typing.Optional[velum.GatewayClient]
    _command_manager: typing.Optional[command_manager_trait.CommandManager]
    _commands: _CommandMapping
    _listeners: _ListenerMapping

    def __init__(
        self, name: typing.Optional[str] = None, logger: typing.Optional[logging.Logger] = None
    ) -> None:
        self.name = name or _get_source_module_name()
        self.logger = _LOGGER if logger is None else logger

        self._client = None
        self._command_manager = None
        self._commands = {}
        self._listeners = {}

    @property
    def client(self) -> velum.GatewayClient:
        if self._client is None:
            raise RuntimeError("Cannot access the client of an inactive plugin.")

        return self._client

    @property
    def rest(self) -> rest_trait.RESTClient:
        return self.client.rest

    @property
    def event_manager(self) -> event_manager_trait.EventManager:
        return self.client.event_manager

    @property
    def command_manager(self) -> command_manager_trait.CommandManager:
        if self._command_manager is None:
            raise RuntimeError("Cannot access the command manager of an inactive plugin.")

        return self._command_manager

    @property
    def commands(self) -> typing.Sequence[command_trait.Command[typing.Any, typing.Any]]:
        return tuple(self._commands.values())

    @property
    def listeners(
        self,
    ) -> typing.Mapping[
        typing.Type[base_events.Event],
        typing.Sequence[base_events.EventCallbackT[base_events.Event]],
    ]:
        return {event: tuple(listeners) for event, listeners in self._listeners.items()}

    def add_command(self, command: command_trait.Command[typing.Any, typing.Any]) -> None:
        if command.name in self._commands:
            raise RuntimeError(f"Plugin {self.name} already has a command named {command.name!r}.")

        self._commands[command.name] = command

    def remove_command(self, command: command_trait.Command[typing.Any, typing.Any] | str) -> None:
        name = command.name if isinstance(command, command_trait.Command) else command
        if name not in self._commands:
            raise RuntimeError(f"Plugin {self.name!r} does not have a command named {name!r}.")

        self._commands.pop(name)

    def command(
        self,
        name: typing.Optional[str] = None,
        /,
        *,
        description: typing.Optional[str] = None,
        aliases: typing.Optional[typing.Collection[str]] = None,
        string_parser: typing.Optional[parser.StringParserCallback] = None,
    ) -> typing.Callable[[command_impl.CommandCallback[P, T]], command_impl.Command[P, T]]:
        def wrapper(callback: command_impl.CommandCallback[P, T]) -> command_impl.Command[P, T]:
            command = command_impl.Command(
                callback,
                name=name,
                description=description,
                aliases=aliases,
                string_parser=string_parser,
            )

            self.add_command(command)
            return command

        return wrapper

    def subscribe(
        self,
        event_type: typing.Type[base_events.EventT],
        callback: base_events.EventCallbackT[base_events.EventT],
    ) -> None:
        if not asyncio.iscoroutinefunction(callback):
            raise TypeError(f"Cannot subscribe to non-coroutine function '{callback.__name__}'.")

        self.logger.debug(
            "Subscribing callback '%s%s' to event-type '%s.%s'.",
            callback.__name__,
            inspect.signature(callback),
            event_type.__module__,
            event_type.__qualname__,
        )

        self._listeners.setdefault(event_type, []).append(callback)  # type: ignore

    def unsubscribe(
        self,
        event_type: typing.Type[base_events.EventT],
        callback: base_events.EventCallbackT[base_events.EventT],
    ) -> None:
        listeners = self._listeners.get(event_type)
        if not listeners:
            return

        _LOGGER.debug(
            "Unsubscribing callback '%s%s' from event-type '%s.%s'.",
            callback.__name__,
            inspect.signature(callback),
            event_type.__module__,
            event_type.__qualname__,
        )

        listeners.remove(callback)  # type: ignore

    def listen(
        self, *event_types: typing.Type[base_events.EventT]
    ) -> typing.Callable[
        [base_events.EventCallbackT[base_events.EventT]],
        base_events.EventCallbackT[base_events.EventT],
    ]:
        def wrapper(
            callback: base_events.EventCallbackT[base_events.EventT],
        ) -> base_events.EventCallbackT[base_events.EventT]:
            signature = inspect.signature(callback)
            parameters = signature.parameters.values()
            event_param = next(iter(parameters))
            annotation = event_param.annotation

            if annotation is inspect.Parameter.empty:
                if event_types:
                    resolved_types = event_types

                else:
                    raise TypeError(
                        "Please provide the event type either as an argument to the decorator "
                        "or as a type hint."
                    )

            else:
                if typing.get_origin(annotation) in _UNIONS:
                    resolved_types = {
                        class_utils.strip_generic(ann) for ann in typing.get_args(annotation)
                    }
                else:
                    resolved_types = {class_utils.strip_generic(annotation)}

                if event_types and resolved_types != set(event_types):
                    raise TypeError(
                        "Please make sure the event types provided to the decorator match those "
                        "provided as a typehint."
                    )

            for event_type in resolved_types:
                self.subscribe(event_type, callback)

            return callback

        return wrapper

    async def load(
        self,
        client: velum.GatewayClient,
        command_manager: command_manager_trait.CommandManager,
    ) -> None:

        self.logger.info("Attempting to load plugin %r...", self.name)

        # Set state...
        self._client = client
        self._command_manager = command_manager

        # Load commands...
        for command in self._commands.values():
            command_manager.add_command(command)

        # Load listeners...
        for event, listeners in self._listeners.items():
            for listener in listeners:
                client.subscribe(event, listener)

        self.logger.info("Successfully loaded plugin %r!", self.name)

    async def unload(
        self,
        client: velum.GatewayClient,
        command_manager: command_manager_trait.CommandManager,
    ) -> None:

        # Should realistically always be the case.
        assert self._client is client
        assert self._command_manager is command_manager

        self.logger.info("Attempting to unload plugin %r", self.name)

        # Unload commands...
        for command in self._commands.values():
            self.command_manager.remove_command(command)

        # Unload listeners...
        for event, listeners in self._listeners.items():
            for listener in listeners:
                self.client.unsubscribe(event, listener)

        # Remove state
        self._client = None
        self._command_manager = None

        self.logger.info("Successfully unloaded plugin %s", self.name)

    @property
    def entrypoints(self) -> typing.Tuple[_EntrypointCallback, _EntrypointCallback]:
        """Returns the plugin's most basic entrypoints. For use in an extension
        such that the plugin can be loaded as part of an extension.

        .. code-block:: python3

            plugin = Plugin()

            ...

            load, unload = plugin.entrypoints

        Note that you can always provide custom implementations for ``load``
        and ``unload`` on the extension (module/file), in case you need to
        do some extra work at extension load time; such as creating an
        ``aiohttp.ClientSession`` to make requests in that plugin.
        """
        return self.load, self.unload


def _assert_get_package() -> str:
    cwd = os.getcwd()

    package = sys.modules["__main__"].__file__
    if not package:
        raise ValueError("Failed to find the name of the main module.")

    return ".".join(
        pathlib.Path(package)
        .relative_to(cwd)
        .parts[:-1]
    )  # fmt: skip


def _assert_extension(module: types.ModuleType) -> plugin_trait.Extension:
    if not isinstance(module, plugin_trait.Extension):
        raise TypeError(
            f"Module {module.__name__!r} is not a valid extension. "
            "Please ensure it has the required 'load' and 'unload' entrypoints."
        )

    return module


async def load_extension(
    ext_name: str,
    /,
    package: typing.Optional[str] = None,
    *,
    client: velum.GatewayClient,
    command_manager: command_manager_trait.CommandManager,
) -> types.ModuleType:
    if not package and ext_name.startswith("."):
        try:
            package = _assert_get_package()
        except Exception as exc:
            raise LookupError(
                "No package provided for relative import, could not automatically determine one."
            ) from exc

        _LOGGER.info(
            "No package provided for relative import, attempting with {package} as package."
        )

    spec = importlib.util.find_spec(ext_name, package)
    if not spec:
        raise LookupError(f"Could not find a module named {ext_name!r}.")

    module = importlib.util.module_from_spec(spec)
    assert module  # Should be safe since the spec exists.

    # Apparently this must be done before putting the module in sys.modules
    # because of an optimisation in import.c; courtesy of importlib.
    module.__initializing__ = True  # type: ignore

    try:
        # Execute the module without overwriting the instance in sys.modules.
        # This is reliant on 'newer' python versions, but since we only support
        # 3.10+, I think this should be fine.
        loader = typing.cast(importlib.abc.Loader, module.__loader__)
        loader.exec_module(module)

        # At this point module holds the new state. Now we ensure the module we
        # just loaded actually is a Sail extension and load it.
        await _assert_extension(module).load(client, command_manager)

        # Finally, we update sys.modules to reflect the new module.
        # This actually works for both loading and reloading.
        sys.modules[ext_name] = module
        return module

    finally:
        module.__initializing__ = False  # type: ignore


async def _unload_extension(
    ext_name: str,
    /,
    *,
    client: velum.GatewayClient,
    command_manager: command_manager_trait.CommandManager,
    is_reload: bool = False,
) -> types.ModuleType:
    module = sys.modules[ext_name]

    await _assert_extension(module).unload(client, command_manager)

    if not is_reload:
        sys.modules.pop(ext_name)

    return module


async def unload_extension(
    ext_name: str,
    /,
    *,
    client: velum.GatewayClient,
    command_manager: command_manager_trait.CommandManager,
) -> None:
    module = await _unload_extension(ext_name, client=client, command_manager=command_manager)
    del module


async def reload_extension(
    ext_name: str,
    /,
    *,
    client: velum.GatewayClient,
    command_manager: command_manager_trait.CommandManager,
) -> types.ModuleType:
    unloaded = await _unload_extension(
        ext_name,
        client=client,
        command_manager=command_manager,
        is_reload=True,
    )

    package = unloaded.__package__
    del unloaded

    return await load_extension(
        ext_name,
        package,
        client=client,
        command_manager=command_manager,
    )
