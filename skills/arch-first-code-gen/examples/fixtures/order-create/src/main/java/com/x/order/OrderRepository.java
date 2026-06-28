package com.x.order;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Repository;

/**
 * ROLE-L03 — 分层角色（repository / 持久化抽象）。
 * 单一职责：聚合的存取；接口属领域层、实现属基础设施层（DIP / dependency_direction）。
 */
@Repository
public class OrderRepository {
    private static final Logger log = LoggerFactory.getLogger(OrderRepository.class);

    public void save(OrderAggregate order) {
        log.info("OrderRepository.save 外部调用(DB) orderId={}", order.getOrderId()); // 外部调用打点
        // 实际持久化省略
    }
}
