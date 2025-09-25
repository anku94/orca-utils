from __future__ import annotations

from typing import Iterable

COMMAND_PREFIX = "COMMAND"


def _tokenize(command: str) -> list[str]:
    # Split on spaces and drop empty chunks.
    tokens = [part for part in command.strip().split(" ") if part]

    if not tokens:
        raise ValueError("command cannot be empty")

    return tokens


def _normalize_domains(domains: Iterable[str] | str) -> str:
    # Flatten domain tokens into the wire format.
    if isinstance(domains, str):
        domain_field = domains.strip()

        if not domain_field:
            raise ValueError("domains cannot be empty")

        return domain_field

    domain_tokens = [token.strip() for token in domains if token and token.strip()]

    if not domain_tokens:
        raise ValueError("domains cannot be empty")

    return "+".join(domain_tokens)


def serialize_commands(domains: Iterable[str] | str, commands: Iterable[str]) -> str:
    # Build a COMMAND payload for the transport.
    domain_field = _normalize_domains(domains)

    command_list = list(commands)

    if not command_list:
        raise ValueError("commands cannot be empty")

    fields: list[str] = [COMMAND_PREFIX, domain_field, str(len(command_list))]

    for command in command_list:
        tokens = _tokenize(command)
        fields.append(str(len(tokens)))
        fields.extend(tokens)

    return "|".join(fields)
