package com.x.order;

public final class OrderAggregateTest {
    public static void main(String[] args) {
        OrderAggregate order = OrderAggregate.create("user-1", 10);
        if (order.amount() != 10) {
            throw new AssertionError("valid amount was not preserved");
        }

        try {
            OrderAggregate.create("user-1", 0);
            throw new AssertionError("non-positive amount should fail");
        } catch (OrderAggregate.InvalidOrderAmountException expected) {
            // Expected defensive boundary.
        }
    }
}
