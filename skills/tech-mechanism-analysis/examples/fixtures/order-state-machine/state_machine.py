from __future__ import annotations

from enum import Enum
import json


class OrderState(str, Enum):
    CREATED = "created"
    PAID = "paid"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"


ALLOWED_TRANSITIONS: dict[OrderState, set[OrderState]] = {
    OrderState.CREATED: {OrderState.PAID, OrderState.CANCELLED},
    OrderState.PAID: {OrderState.SHIPPED, OrderState.CANCELLED},
    OrderState.SHIPPED: set(),
    OrderState.CANCELLED: set(),
}


class OrderMachine:
    def __init__(self) -> None:
        self.state = OrderState.CREATED
        self.history = [self.state]

    def transition(self, target: OrderState) -> None:
        if target not in ALLOWED_TRANSITIONS[self.state]:
            raise ValueError(f"invalid transition: {self.state} -> {target}")
        self.state = target
        self.history.append(target)


def run_order() -> list[str]:
    machine = OrderMachine()
    machine.transition(OrderState.PAID)
    machine.transition(OrderState.SHIPPED)
    return [state.value for state in machine.history]


if __name__ == "__main__":
    print(json.dumps(run_order()))
