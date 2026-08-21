package app;

import java.util.Set;

public final class CountryCatalog {
  private static final Set<String> SUPPORTED = Set.of(
      "AR", "AU", "BR", "CA", "CN", "DE", "ES", "FR", "GB", "IN",
      "IT", "JP", "KR", "MX", "NL", "NO", "NZ", "PL", "SE", "SG",
      "TR", "US", "ZA"
  );

  public void load() {}

  public boolean supports(String countryCode) {
    return SUPPORTED.contains(countryCode);
  }
}
