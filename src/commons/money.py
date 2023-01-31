from dataclasses import dataclass


@dataclass(frozen=True)
class Money:
    currency: str
    value: int
