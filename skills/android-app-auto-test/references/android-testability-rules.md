# Android Testability Rules

Improve testability without damaging accessibility, product behavior, or code style.

## Locator Priority

Prefer stable locators in this order:

1. Compose `Modifier.testTag("screen.element.action")`
2. XML/View `android:id="@+id/..."`
3. resource names already exposed through binding
4. stable visible text only when it is product copy, not dynamic content
5. `contentDescription` only when it is correct accessibility semantics

Do not use coordinates, screenshots, sleep-only waits, or translated copy as primary locators.

## Compose

Use `Modifier.testTag(...)` for screens, important containers, input fields, primary actions, tabs, and result states. Keep tags stable, lowercase-ish, and domain meaningful:

```kotlin
Modifier.testTag("login.email_input")
Modifier.testTag("login.submit_button")
Modifier.testTag("home.loaded_state")
```

Avoid test tags on every tiny child. Add state tags for important success/error outcomes when visual text is dynamic.

## XML/View

Prefer ids for actionable or asserted views:

```xml
android:id="@+id/login_submit_button"
```

Use `contentDescription` only for meaningful image buttons, icon-only actions, or custom controls where accessibility needs it. Do not add fake descriptions to decorative images or layout containers just for tests.

## Logging

Use the project's existing logger. If there is no logger, add the lightest local mechanism consistent with the codebase.

Logs should support path verification and failure triage:

- `path_start`
- `step_enter`
- `action_submit`
- `result_success`
- `result_error`
- `navigation_blocked`
- `validation_error`
- `permission_denied`
- `api_request`
- `api_response`

Do not log secrets, passwords, full tokens, personal data, or raw request bodies. Prefer stable path ids and outcome codes.

## Waits And Synchronization

Prefer framework synchronization:

- Compose testing idle synchronization and semantics matchers
- Espresso idling resources where the app already supports them
- UiAutomator `Until` waits for system UI and cross-app surfaces

Use timeouts as a guard, not as primary synchronization.

## High-Risk Paths

Exclude destructive or externally visible actions by default:

- payment
- delete
- publish
- send message
- modify real profile data
- invite users
- trigger irreversible backend jobs

If the user allowed high-risk paths, still require test-environment evidence and safe test data.
