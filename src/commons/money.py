from dataclasses import dataclass



@dataclass(frozen=True)
class Money:
    currency: str
    value: int

    def __add__(self, other):
        if other.currency != self.currency:
            raise ValueError(f"Cannot add {self.currency} to {other.currency}")
        return Money(self.currency, self.value + other.value)

    def __sub__(self, other):
        if other.currency != self.currency:
            raise ValueError(f"Cannot subtract {self.currency} to {other.currency}")
        if other.value > self.value:
            raise ValueError(f"Subtract operation cannot result in negative values")
        return Money(self.currency, self.value - other.value)

    def __mul__(self, other):
        return Money(self.currency, self.value*other)
