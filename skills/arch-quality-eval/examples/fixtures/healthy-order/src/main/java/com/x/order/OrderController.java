package com.x.order;

public final class OrderController {
  private final OrderService orderService;

  public OrderController(OrderService orderService) {
    this.orderService = orderService;
  }

  public Object find(String orderId) {
    return orderService.find(orderId);
  }
}
