# Test Stack Selection

Select the test stack from existing project evidence before adding dependencies.

## Audit Signals

Inspect:

- `settings.gradle*`, root `build.gradle*`, module `build.gradle*`
- `src/androidTest`, `src/test`
- dependencies containing `espresso`, `uiautomator`, `androidx.compose.ui:ui-test`, `androidx.test`
- Compose usage: `@Composable`, `setContent`, `Modifier`, Compose dependencies
- XML/View usage: layouts under `res/layout`, Activities, Fragments, DataBinding/ViewBinding
- existing custom test runners
- CI scripts or Gradle tasks

## Selection Rules

Use the smallest reliable stack:

1. If Compose UI is the primary UI and Compose test dependencies exist, use Compose UI Test.
2. If Compose UI is primary but dependencies are missing, add Compose UI Test dependencies matching the project's Compose setup.
3. If XML/View UI is primary and Espresso exists, use Espresso for in-app assertions.
4. If XML/View UI is primary and no test stack exists, add AndroidX Test + Espresso unless cross-app/system UI is required.
5. If the path crosses system permission dialogs, settings, notifications, external apps, or launcher boundaries, use UiAutomator for those steps.
6. Use a hybrid when needed: Compose/Espresso for app UI and UiAutomator for system UI.
7. Do not default to Appium or cloud testing for v1.
8. Maestro may be mentioned as an optional future or fallback route, but native Android test tooling is the default.

## Recommended Commands

Prefer module-scoped commands:

```bash
./gradlew :app:connectedDebugAndroidTest
./gradlew :app:connectedAndroidTest
./gradlew :app:assembleDebug :app:assembleDebugAndroidTest
```

When possible, run a single class or package to keep the repair loop small:

```bash
./gradlew :app:connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=com.example.P0LoginTest
```

Always pass the selected device through Gradle/adb-compatible configuration when the project supports it. Use `adb -s <serial>` for direct adb commands.

## Dependency Change Rules

When adding test dependencies:

- Match existing Android Gradle Plugin, Kotlin, Compose, and AndroidX versions.
- Prefer version catalogs if the project uses `libs.versions.toml`.
- Keep dependency changes scoped to androidTest unless app code needs testability hooks.
- Run a Gradle sync-equivalent command or test compile after editing Gradle files.
