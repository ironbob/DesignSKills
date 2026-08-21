# Layout Check Catalog

Load only the sections relevant to the inspected UI. These are diagnostic prompts, not a reason to impose a new visual style or rewrite unrelated structure.

## 1. Text flow and overflow

Check whether realistic long labels, user-entered names, localized strings, metadata, and descriptions:

- push primary actions off-screen or beneath unrelated content;
- overlap neighboring regions, clip without an intentional disclosure path, or create unintended horizontal scrolling;
- wrap in a way that changes row alignment or makes repeated items visually unstable;
- make a reading column so wide or narrow that comprehension suffers;
- turn secondary description text into an undifferentiated wall of copy.

Preserve required information. Prefer a deliberate content rule—wrapping, truncation with a way to reveal, progressive disclosure, or an appropriate flexible parent constraint—over deleting text or hard-coding a one-language width.

## 2. Geometry, alignment, and spacing

Check whether elements that form one group share a meaningful edge, baseline, rhythm, or control height. Trace the layout in this order:

1. Parent sizing and available space.
2. Column/row allocation and flexible versus fixed children.
3. Child minimum sizes, intrinsic content, and overflow behavior.
4. Local offsets only when the first three cannot explain the issue.

Flag inconsistent geometry only when it creates a visible break in grouping, scanning, or operation. Do not normalize intentional asymmetry without evidence.

## 3. Responsive and resize behavior

Exercise or reason about a narrow but supported viewport/window/device. Check that:

- primary content and required actions remain reachable;
- columns collapse, wrap, scroll, or reprioritize intentionally rather than compressing into overlap;
- fixed side regions, toolbars, dialogs, and floating controls do not obscure the target;
- text scaling or platform window resizing does not convert a usable row into clipped controls.

Do not declare responsive behavior verified without an applicable render, test, or other direct evidence.

## 4. Hierarchy and density

Check that the user can distinguish primary content, secondary context, and available actions without reading every word. Flag only concrete problems such as:

- repeated cards or rows whose different content types have no stable visual hierarchy;
- dense metadata competing with the primary decision or action;
- long adjacent prose with no meaningful grouping or disclosure;
- an empty or error state that visually resembles normal content and obscures the next available action.

Do not convert this into a color, typography, branding, or aesthetic review.

## 5. State layout

For states that exist and affect the target, inspect default plus applicable empty, loading, and error states. Check that each state:

- uses the same relevant container boundaries or intentionally explains the change;
- does not collapse nearby actions or make recovery content unreachable;
- handles absent, delayed, or unusually long content without leaving broken gaps or overlap.

Mark inaccessible states `unverified`, not passed.

## 6. Platform selection

### Web

Focus on viewport changes, content-driven flex/grid sizing, scroll containment, dialogs/popovers, and overflow that creates horizontal page scrolling or hides actions. Inspect the actual parent/child sizing chain before adding local width or margin fixes.

### Desktop

Focus on window resize, minimum usable window size, sidebars/inspectors, toolbar height, panel split behavior, desktop scale settings, and scroll-container boundaries. Do not assume a desktop window has a fixed size.

### Mobile

Focus on small width, orientation, safe-area-adjacent controls, dynamic text growth, keyboard-adjacent content, and required actions that can be pushed beneath navigation or overlays. Do not treat a desktop row layout as the default mobile answer.
