package com.x.order;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * ROLE-D01 — 领域角色（aggregate / 聚合根）。
 * 封装订单聚合根，维护下单不变量（库存校验、金额一致性），对外唯一入口。
 * 依据：DDD 聚合根（一致性边界）+ 高内聚低耦合。
 */
public class OrderAggregate {
    private static final Logger log = LoggerFactory.getLogger(OrderAggregate.class);
    private final String orderId;
    private final String userId;
    private final int amount;

    private OrderAggregate(String orderId, String userId, int amount) {
        this.orderId = orderId;
        this.userId = userId;
        this.amount = amount;
    }

    // 工厂方法封装不变量校验——行为归对象（Tell-Don't-Ask），不贫血。
    public static OrderAggregate create(String userId, int amount) {
        if (amount <= 0) {
            log.warn("OrderAggregate.create 金额非法 userId={} amount={}", userId, amount); // 业务规则违反告警
            throw new InsufficientStockException("amount must be positive");
        }
        return new OrderAggregate("ORD-" + System.nanoTime(), userId, amount);
    }

    public String getOrderId() { return orderId; }
    public String getUserId() { return userId; }
    public int getAmount() { return amount; }
}
