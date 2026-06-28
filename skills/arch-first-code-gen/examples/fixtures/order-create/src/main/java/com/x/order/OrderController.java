package com.x.order;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * ROLE-L01 — 分层角色（controller）。
 * 单一职责：HTTP 协议适配 + 用例编排，不含业务逻辑（SRP / separation_of_concerns）。
 */
@RestController
@RequestMapping("/orders")
public class OrderController {
    private static final Logger log = LoggerFactory.getLogger(OrderController.class);
    private final OrderService orderService;

    // DIP：依赖 OrderService 抽象/接口，构造注入，不直接 new 实现。
    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @PostMapping
    public OrderResponse createOrder(@RequestBody CreateOrderRequest request) {
        log.info("createOrder 入口 userId={} amount={}", request.getUserId(), request.getAmount()); // 入口打点
        try {
            OrderResponse resp = orderService.create(request);
            log.info("createOrder 出口 orderId={} ", resp.getOrderId()); // 出口打点
            return resp;
        } catch (RuntimeException e) {
            log.error("createOrder 失败 userId={} amount={}", request.getUserId(), request.getAmount(), e); // 异常带上下文+堆栈
            throw e;
        }
    }
}
