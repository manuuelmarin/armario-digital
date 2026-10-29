"""Opt-in browser flow: RUN_BROWSER_TESTS=1 python -m pytest tests/test_browser.py."""

import os
import threading
from pathlib import Path

import pytest
from werkzeug.serving import make_server

from armario.backups import verify_backup

from .conftest import photograph

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_BROWSER_TESTS") != "1", reason="Prueba de navegador optativa"
)


def test_full_browser_workflow_and_responsive_layout(app, tmp_path):
    from playwright.sync_api import sync_playwright

    server = make_server("127.0.0.1", 0, app, threaded=True)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(photograph()[0].getvalue())
    screenshots = Path(os.environ.get("ARMARIO_SCREENSHOTS", "test-results"))
    screenshots.mkdir(parents=True, exist_ok=True)
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as playwright:
            launch = {"headless": True}
            if executable := os.environ.get("BROWSER_EXECUTABLE"):
                launch["executable_path"] = executable
                launch["args"] = ["--no-sandbox", "--disable-dev-shm-usage"]
            browser = playwright.chromium.launch(**launch)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.set_default_timeout(5000)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base)
            page.get_by_role("link", name="Añadir prenda", exact=True).click()
            page.get_by_label("Nombre *", exact=True).fill("Camisa de prueba")
            page.locator('select[name="category_id"]').select_option("2")
            page.locator('input[name="photos"]').set_input_files(photo)
            page.get_by_label("Verano", exact=True).check()
            invalid_fields = page.locator("form.editor").evaluate(
                "form => Array.from(form.elements).filter(el => el.validity && !el.validity.valid).map(el => ({name:el.name,value:el.value,message:el.validationMessage}))"
            )
            assert invalid_fields == []
            page.get_by_role("button", name="Guardar prenda").click()
            page.wait_for_url("**/prendas/1")
            assert page.get_by_role("heading", name="Camisa de prueba").is_visible()
            assert page.locator(".detail-photo img").evaluate("img => img.naturalWidth > 0")
            page.goto(base)
            page.get_by_role("checkbox", name="Seleccionar Camisa de prueba").check()
            assert page.locator("[data-selection-count]").inner_text() == "1"
            page.locator("#bulk-destination").select_option("2")
            page.get_by_role("button", name="Mover selección").click()
            page.wait_for_url(base + "/")
            assert "Madrid" in page.locator(".card-caption").inner_text()
            page.goto(base + "/outfits/nuevo")
            page.get_by_label("Nombre *", exact=True).fill("Oficina de prueba")
            page.locator('input[name="garment_ids"]').check()
            page.get_by_role("button", name="Guardar outfit").click()
            page.wait_for_url("**/outfits")
            assert page.get_by_role("heading", name="Oficina de prueba").is_visible()
            page.goto(base + "/maletas/nueva")
            page.get_by_label("Nombre *", exact=True).fill("Viaje de prueba")
            page.get_by_label("Origen *").select_option("2")
            page.get_by_label("Destino *").select_option("3")
            page.get_by_role("button", name="Guardar viaje").click()
            page.wait_for_url("**/maletas/1")
            page.get_by_label("Combinación").select_option("1")
            page.get_by_role("button", name="Añadir sus prendas").click()
            page.get_by_role(
                "button", name="Marcar preparada: Camisa de prueba", exact=True
            ).click()
            page.get_by_role("link", name="Revisar traslado a destino").click()
            page.get_by_role(
                "checkbox", name="Confirmo que estas prendas han llegado a La Manga"
            ).check()
            page.get_by_role("button", name="Confirmar cambio de ubicación").click()
            assert "Ya en destino" in page.locator(".checklist-row").inner_text()
            page.goto(base + "/ajustes")
            with page.expect_download() as download:
                page.get_by_role("button", name="Crear y descargar copia").click()
            saved = tmp_path / "download.zip"
            download.value.save_as(saved)
            assert verify_backup(saved)["garments"] == 1
            page.goto(base)
            page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
            for width in (1440, 850, 390):
                page.set_viewport_size({"width": width, "height": 900})
                for route in (
                    "/",
                    "/prendas/nueva",
                    "/prendas/1",
                    "/outfits",
                    "/outfits/1/editar",
                    "/maletas",
                    "/maletas/1",
                    "/ubicaciones",
                    "/ajustes",
                ):
                    page.goto(base + route)
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= window.innerWidth"
                    ), (route, width)
            page.goto(base)
            page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
            assert errors == []
            browser.close()
    finally:
        server.shutdown()
        worker.join(timeout=5)
