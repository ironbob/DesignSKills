"""三端画布预设（与 06-tokens.json 的 target_canvas_presets 一致；R8 锁定）。"""

from __future__ import annotations

PLATFORMS: dict[str, dict] = {
    "mobile_app": {"label": "手机App", "width": 390, "height": 844},
    "desktop_app": {"label": "桌面App", "width": 1280, "height": 800},
    "web": {"label": "Web系统", "width": 1440, "height": 900},
}


def is_platform(key: str) -> bool:
    return key in PLATFORMS
