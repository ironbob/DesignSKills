package com.x.order;

public final class OrderService {
  private final OrderRepository orderRepository;

  public OrderService(OrderRepository orderRepository) {
    this.orderRepository = orderRepository;
  }

  public Object find(String orderId) {
    return orderRepository.find(orderId);
  }
}
