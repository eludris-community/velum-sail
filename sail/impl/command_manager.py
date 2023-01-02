from __future__ import annotations

import logging
import typing

import attr
import typing_extensions
import velum
from velum.traits import event_manager_trait

from sail.impl import command as command_impl
from sail.internal import parser
from sail.traits import command_manager_trait
from sail.traits import command_trait

__all__: typing.Sequence[str] = ("CommandManager",)


_LOGGER = logging.getLogger("sail.command_manager")

P = typing.ParamSpec("P")
T = typing.TypeVar("T")

CommandMetadata = typing.Tuple[typing.Optional[str], typing.Optional[str], typing.Optional[str]]


@attr.define()
class CommandManager(command_manager_trait.CommandManager):

    _commands: typing.Dict[str, command_trait.AnyCommand] = attr.field(factory=dict)

    @property
    def commands(self) -> typing.Sequence[command_trait.AnyCommand]:
        return tuple(self._commands.values())

    async def try_invoke(self, event: velum.MessageCreateEvent) -> None:
        prefix, invoked_with, invocation = self.prepare(event.content)
        if invoked_with is None or prefix is None or invocation is None:
            return

        command = self._commands.get(invoked_with)
        if not command:
            return

        _LOGGER.debug(
            f"Invoking command {command} as '{invoked_with}' with invocation '{invocation}'."
        )

        await command.invoke(
            event,
            prefix=prefix,
            invoked_with=invoked_with,
            invocation=invocation,
        )

    def _add_command(self, name: str, command: command_trait.AnyCommand) -> None:
        if name in self._commands:
            raise RuntimeError(f"A command with name {name} has already been registered.")

        self._commands[name] = command

    def add_command(self, command: command_trait.AnyCommand) -> None:
        self._add_command(command.name, command)

        for alias in command.aliases:
            self._add_command(alias, command)

        if _LOGGER.isEnabledFor(logging.DEBUG):
            names = "', '".join([command.name, *command.aliases])
            _LOGGER.debug(f"Registered command with name(s): '{names}'.")

    def remove_command(self, command: command_trait.AnyCommand) -> None:
        self._commands.pop(command.name)

        for alias in command.aliases:
            self._commands.pop(alias)

        if _LOGGER.isEnabledFor(logging.DEBUG):
            names = "', '".join([command.name, *command.aliases])
            _LOGGER.debug(f"Deregistered command with name(s): '{names}'.")

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

    def get_command(self, name: str) -> typing.Optional[command_trait.AnyCommand]:
        return self._commands.get(name)

    def bind_to_event_manager(self, event_manager: event_manager_trait.EventManager) -> None:
        event_manager.subscribe(velum.MessageCreateEvent, self.try_invoke)

    def bind_to_app(self, app: command_manager_trait.EventAware) -> None:
        self.bind_to_event_manager(app.event_manager)

    def set_prepare_callback(self, callback: typing.Callable[[str], CommandMetadata]) -> None:
        self.prepare = callback  # pyright: ignore[reportGeneralTypeIssues]

    @classmethod
    def with_prefix(cls, *prefixes: str) -> typing_extensions.Self:
        manager = cls()
        manager.set_prepare_callback(generate_prefix_prepare(*prefixes))

        return manager


def generate_prefix_prepare(*prefixes: str) -> typing.Callable[[str], CommandMetadata]:
    def _prepare(
        content: str,
    ) -> typing.Tuple[typing.Optional[str], typing.Optional[str], typing.Optional[str]]:
        content = content.strip()
        for prefix in prefixes:
            if content.startswith(prefix):
                break

        else:
            return (None, None, None)

        split = content[len(prefix) :].lstrip().split(maxsplit=1)
        try:
            command, invocation = split

        except ValueError:
            return (prefix, split[0].strip(), "")

        else:
            return (prefix, command.strip(), invocation.strip())

    return _prepare
