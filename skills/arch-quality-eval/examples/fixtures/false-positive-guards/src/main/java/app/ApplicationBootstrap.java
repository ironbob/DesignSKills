package app;

public final class ApplicationBootstrap {
  private final OrderService orders;
  private final PaymentService payments;
  private final InventoryService inventory;
  private final NotificationService notifications;
  private final CountryCatalog countries;

  public ApplicationBootstrap() {
    this.orders = new OrderService();
    this.payments = new PaymentService();
    this.inventory = new InventoryService();
    this.notifications = new NotificationService();
    this.countries = new CountryCatalog();
  }

  public void start() {
    orders.start();
    payments.start();
    inventory.start();
    notifications.start();
    countries.load();
  }
}
