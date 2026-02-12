"""Playwright UI tests for the visual editor."""

import socket
import subprocess
import sys
import time

import pytest
import requests
from playwright.sync_api import sync_playwright


def _get_free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    _, port = sock.getsockname()
    sock.close()
    return port


def _wait_for_server(base_url: str, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            resp = requests.get(f"{base_url}/api/health", timeout=1)
            if resp.status_code == 200:
                return
        except Exception as exc:
            last_error = exc
        time.sleep(0.2)
    raise RuntimeError(f"Server did not start in time: {last_error}")


@pytest.fixture(scope="module")
def base_url():
    port = _get_free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "ypack_web.server",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    base = f"http://127.0.0.1:{port}"
    try:
        _wait_for_server(base)
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


def _wait_for_preview_contains(page, text: str, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    last_text = ""
    while time.time() < deadline:
        last_text = page.get_by_test_id("yaml-preview").inner_text()
        if text in last_text:
            return
        time.sleep(0.2)
    raise AssertionError(f"Expected YAML preview to contain '{text}'. Last preview: {last_text}")


def test_visual_editor_file_flow(base_url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(base_url, wait_until="domcontentloaded")

        page.get_by_role("tab", name="可视化").click()
        page.drag_and_drop("[data-testid='visual-palette-file']", "[data-testid='visual-canvas']")

        page.locator("[data-testid='visual-source'] input").fill("bin/MyApp.exe")
        page.get_by_test_id("visual-save").click()

        page.get_by_test_id("visual-apply").click()

        _wait_for_preview_contains(page, "visual:")
        _wait_for_preview_contains(page, "MyApp.exe")

        browser.close()
