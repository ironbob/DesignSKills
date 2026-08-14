package com.x.order;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public final class OrderController {
    private static final Logger log = LoggerFactory.getLogger(OrderController.class);
    private final OrderService service;

    public OrderController(OrderService service) {
        this.service = service;
    }

    public OrderAggregate createOrder(String userId, long amount) {
        log.info("createOrder started userId={} amount={}", userId, amount);
        try {
            OrderAggregate order = service.create(userId, amount);
            log.info("createOrder completed orderId={}", order.id());
            return order;
        } catch (RuntimeException error) {
            log.error("createOrder failed userId={} amount={}", userId, amount, error);
            throw error;
        }
    }
}
