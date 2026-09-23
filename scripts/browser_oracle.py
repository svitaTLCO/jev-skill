#!/usr/bin/env python3
"""Run a manifest-defined browser oracle against one local HTML artifact."""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> int:
    work = Path("/work")
    oracle = json.loads((work / "oracle.json").read_text(encoding="utf-8"))
    external_requests: list[str] = []
    page_errors: list[str] = []
    console_errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
        page = browser.new_page()
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)

        def block_external(route):
            external_requests.append(route.request.url)
            route.abort()

        page.route("http://**/*", block_external)
        page.route("https://**/*", block_external)
        page.goto((work / "index.html").resolve().as_uri(), wait_until="load")
        if page.title() != oracle["title"]:
            raise AssertionError(f"title mismatch: expected {oracle['title']!r}, got {page.title()!r}")
        page.get_by_text(oracle["initial_text"], exact=True).first.wait_for(state="visible")
        for step in oracle["steps"]:
            button = page.get_by_role("button", name=step["button"], exact=True)
            button.wait_for(state="visible")
            for _ in range(step.get("clicks", 1)):
                if step.get("activation") == "keyboard":
                    button.focus()
                    page.keyboard.press(step.get("key", "Enter"))
                else:
                    button.click()
            page.get_by_text(step["expected_text"], exact=True).first.wait_for(state="visible")
        if oracle.get("no_external_requests") and external_requests:
            raise AssertionError(f"external requests attempted: {external_requests!r}")
        if page_errors:
            raise AssertionError(f"uncaught browser errors: {page_errors!r}")
        if console_errors:
            raise AssertionError(f"browser console errors: {console_errors!r}")
        browser.close()
    print(json.dumps({"passed": True, "title": oracle["title"], "steps": len(oracle["steps"]),
                      "external_requests": external_requests, "page_errors": page_errors,
                      "console_errors": console_errors}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
