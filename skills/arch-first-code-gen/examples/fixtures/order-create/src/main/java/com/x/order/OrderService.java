package com.x.order;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public final class OrderService {
    private static final Logger log = LoggerFactory.getLogger(OrderService.class);
    private final OrderRepository repository;

    public OrderService(OrderRepository repository) {
        this.repository = repository;
    }

    public OrderAggregate create(String userId, long amount) {
        log.info("order use case started userId={}", userId);
        OrderAggregate order = OrderAggregate.create(userId, amount);
        repository.save(order);
        log.info("order use case completed orderId={}", order.id());
        return order;
    }
}
