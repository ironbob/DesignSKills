package com.x.order;

import java.util.HashMap;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public interface OrderRepository {
    void save(OrderAggregate order);

    final class InMemory implements OrderRepository {
        private static final Logger log = LoggerFactory.getLogger(InMemory.class);
        private final Map<String, OrderAggregate> orders = new HashMap<>();

        @Override
        public void save(OrderAggregate order) {
            log.info("repository save started orderId={}", order.id());
            orders.put(order.id(), order);
            log.info("repository save completed orderId={}", order.id());
        }
    }
}
