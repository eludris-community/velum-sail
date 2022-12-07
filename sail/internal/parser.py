import typing

__all__: typing.Sequence[str] = ("parse_content",)


_QUOTES: typing.Mapping[str, str] = {
    '"': '"',
    "'": "'",
    "‘": "’",
    "‚": "‛",
    "“": "”",
    "„": "‟",
    "«": "»",
    "‹": "›",
    "《": "》",
    "〈": "〉",
    "「": "」",
    "『": "』",
    "﹁": "﹂",
    "﹃": "﹄",
    "＂": "＂",
    "｢": "｣",
    "〝": "〞",
    "⹂": "⹂",
}


def parse_content(
    content: str,
) -> typing.Tuple[typing.Sequence[str], typing.Mapping[str, typing.Sequence[str]]]:
    content_iter = iter(content)

    name: typing.List[str] = []
    value: typing.List[str] = []
    args: typing.List[str] = []
    kwargs: typing.Dict[str, typing.List[str]] = {}

    def finalise_argument():
        if name:
            kwargs.setdefault("".join(name), []).append("".join(value))
        else:
            args.append("".join(value))

        name.clear()
        value.clear()

    for char in content_iter:
        if char == "\\":
            # Escape, immediately consume next char.
            value.append(next(content_iter, ""))

        elif char in _QUOTES:
            # Quoted arg, figure out closing delimiter and consume until we find it.
            closing_quote = _QUOTES[char]
            while (char := next(content_iter)) != closing_quote:
                if char == "\\":
                    # Immediately consume the next character so as to not exit
                    # the loop on an escaped closing delimiter.
                    value.append(next(content_iter, ""))

                else:
                    value.append(char)

            finalise_argument()

        elif char == "-":
            if name:
                # Still have a name set from a previous dash, close it first.
                finalise_argument()

            if (char := next(content_iter)) == "-":
                # Double dash, set flag and consume until next space.
                dashes = 2
                while (char := next(content_iter, " ")) != " ":
                    name.append(char)

            else:
                # Single dash, set flag and consume next char.
                dashes = 1
                if char != " ":
                    name.append(char)

            if not name:
                # No name after the dashes, add it as a positional.
                args.append("-" * dashes)

        elif char == " ":
            if value:
                # New word and we have a value set, parse arg/kwarg.
                finalise_argument()

        else:
            # Standard character, positional arg or the value of a dashed arg.
            value.append(char)

    if name or value:
        # Finished loop, finalise leftover data, if any.
        finalise_argument()

    return args, kwargs
