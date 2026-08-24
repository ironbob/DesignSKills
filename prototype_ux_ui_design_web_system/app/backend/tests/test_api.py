"""products API 测试（内存临时数据目录）。"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WB_DATA_DIR", str(tmp_path))
    from backend.main import create_app

    with TestClient(create_app()) as c:
        yield c


def test_health(client: TestClient):
    body = client.get("/api/health").json()
    assert body["ok"] is True
    assert body["runner"] == "mock"


def test_create_product_with_project(client: TestClient):
    r = client.post(
        "/api/products",
        json={
            "name": "词汇课程练习",
            "requirement_doc": "# 词汇课程需求\n用户：中学生…",
            "doc_name": "vocab.md",
            "project": {"name": "手机App", "platform": "mobile_app"},
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "词汇课程练习"
    (proj,) = body["projects"]
    assert proj["canvas"] == {"width": 390, "height": 844}
    assert proj["stage_status"] == {"1": "ready"}


def test_create_product_rejects_unknown_platform(client: TestClient):
    r = client.post(
        "/api/products",
        json={
            "name": "X",
            "requirement_doc": "内容",
            "project": {"name": "腕表", "platform": "watch_os"},
        },
    )
    assert r.status_code == 422


def test_list_after_create(client: TestClient, tmp_path: Path):
    client.post(
        "/api/products",
        json={
            "name": "P1",
            "requirement_doc": "内容",
            "project": {"name": "Web系统", "platform": "web"},
        },
    )
    names = [p["name"] for p in client.get("/api/products").json()]
    assert names == ["P1"]
    # 工作区落盘：产品文档母本 + 项目内拷贝
    assert (tmp_path / "products" / "1" / "requirement.md").exists()
    proj_dir = next((tmp_path / "products" / "1" / "projects").iterdir())
    assert (proj_dir / "00-requirement.md").exists()
