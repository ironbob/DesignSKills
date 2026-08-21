package com.x.api;

public final class OrderApi {
  public int quote(int basePrice) {
    return basePrice;
  }

  public int recalculateDiscount(int basePrice) {
    return basePrice / 10;
  }
}
