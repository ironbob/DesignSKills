package com.x.order;

import java.util.Objects;
import java.util.UUID;

public record OrderAggregate(String id, String userId, long amount) {
    public OrderAggregate {
        Objects.requireNonNull(id, "id");
        Objects.requireNonNull(userId, "userId");
        if (amount <= 0) {
            throw new InvalidOrderAmountException(amount);
        }
    }

    public static OrderAggregate create(String userId, long amount) {
        return new OrderAggregate(UUID.randomUUID().toString(), userId, amount);
    }

    public static final class InvalidOrderAmountException extends IllegalArgumentException {
        public InvalidOrderAmountException(long amount) {
            super("order amount must be positive: " + amount);
        }
    }
}
