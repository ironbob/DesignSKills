package com.x.order;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * ROLE-L02 — 分层角色（service / 应用服务）。
 * 单一职责：用例编排（事务边界、协调领域对象与仓库），不含协议细节（SRP / DIP）。
 */
@Service
public class OrderService {
    private static final Logger log = LoggerFactory.getLogger(OrderService.class);
    private final OrderRepository orderRepository;

    public OrderService(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    public OrderResponse create(CreateOrderRequest request) {
        log.info("OrderService.create 编排下单 userId={}", request.getUserId());
        // 聚合根封装下单不变量（库存校验、金额一致性）—— aggregate / high_cohesion_low_coupling
        OrderAggregate order = OrderAggregate.create(request.getUserId(), request.getAmount());
        try {
            orderRepository.save(order); // 外部调用（DB）
            log.info("OrderService.create 下单完成 orderId={}", order.getOrderId());
            return new OrderResponse(order.getOrderId());
        } catch (InsufficientStockException e) {
            log.error("OrderService.create 库存不足 userId={} amount={}", request.getUserId(), request.getAmount(), e);
            throw e;
        }
    }
}
