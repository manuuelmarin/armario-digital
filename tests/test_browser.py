"""Opt-in browser flow: RUN_BROWSER_TESTS=1 python -m pytest tests/test_browser.py."""

import io
import os
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest
from PIL import Image
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
    second_photo = tmp_path / "second.jpg"
    second_photo.write_bytes(photograph(color="ivory")[0].getvalue())
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
            page.get_by_role("textbox", name="Nombre", exact=True).fill("Camisa de prueba")
            page.locator('select[name="category_id"]').select_option("2")
            page.locator('input[name="photos"]').set_input_files([photo, second_photo])
            page.get_by_label("Verano", exact=True).check()
            invalid_fields = page.locator("form.editor").evaluate(
                "form => Array.from(form.elements).filter(el => el.validity && !el.validity.valid).map(el => ({name:el.name,value:el.value,message:el.validationMessage}))"
            )
            assert invalid_fields == []
            page.get_by_role("button", name="Guardar prenda").click()
            page.wait_for_url("**/prendas/1")
            assert page.get_by_role("heading", name="Camisa de prueba").is_visible()
            assert page.locator(".detail-photo img").evaluate("img => img.naturalWidth > 0")
            first_source = page.locator("[data-main-photo]").get_attribute("src")
            page.get_by_role("button", name="Ver foto 2 de Camisa de prueba", exact=True).click()
            assert page.locator("[data-main-photo]").get_attribute("src") != first_source
            page.goto(base)
            page.get_by_role("checkbox", name="Seleccionar Camisa de prueba").check()
            assert page.locator("[data-selection-count]").inner_text() == "1"
            page.locator("#bulk-destination").select_option("2")
            page.get_by_role("button", name="Mover selección").click()
            page.wait_for_url(base + "/")
            assert "Espacio B" in page.locator(".card-caption").inner_text()
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
                "checkbox", name="Confirmo que estas prendas han llegado a Espacio C"
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


@contextmanager
def running_app(application):
    server = make_server("127.0.0.1", 0, application, threaded=True)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        worker.join(timeout=5)


def browser_options():
    options = {"headless": True}
    if executable := os.environ.get("BROWSER_EXECUTABLE"):
        options.update(executable_path=executable, args=["--no-sandbox", "--disable-dev-shm-usage"])
    return options


def test_first_run_creates_only_the_space_entered_in_browser(tmp_path):
    from playwright.sync_api import sync_playwright

    from armario import create_app
    from armario.db import connect

    root = tmp_path / "empty"
    application = create_app({"TESTING": True, "DATA_DIR": root})
    with running_app(application) as base, sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_options())
        page = browser.new_page(viewport={"width": 390, "height": 900})
        page.set_default_timeout(5000)
        page.goto(base)
        page.get_by_role("link", name="Crear mi primer espacio", exact=True).click()
        page.get_by_label("Nombre del espacio", exact=True).fill("Espacio de prueba")
        page.get_by_role("button", name="Crear espacio y continuar").click()
        page.wait_for_url("**/prendas/nueva")
        page.get_by_role("textbox", name="Nombre", exact=True).fill("Primera prenda")
        page.get_by_role("button", name="Guardar prenda").click()
        page.wait_for_url("**/prendas/1")
        assert page.get_by_role("heading", name="Primera prenda").is_visible()
        assert not page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        browser.close()
    connection = connect(root / "wardrobe.sqlite")
    try:
        assert [row[0] for row in connection.execute("SELECT name FROM locations")] == [
            "Espacio de prueba"
        ]
    finally:
        connection.close()


def test_demo_retina_images_searchable_picker_and_mobile_filters(tmp_path):
    from playwright.sync_api import sync_playwright

    from armario import create_app
    from armario.demo import seed_demo

    root = tmp_path / "showcase"
    application = create_app({"TESTING": True, "DATA_DIR": root, "DEMO_MODE": True})
    seed_demo(root)
    with running_app(application) as base, sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_options())
        page = browser.new_page(viewport={"width": 1600, "height": 1050}, device_scale_factor=2)
        page.set_default_timeout(5000)
        page.goto(base)
        page.wait_for_load_state("networkidle")
        assert page.locator(".garment-card").count() == 12
        selection = page.locator(".garment-card img").first.evaluate(
            "img => ({source:img.currentSrc, display:img.clientWidth})"
        )
        encoded = page.request.get(selection["source"]).body()
        with Image.open(io.BytesIO(encoded)) as picture:
            assert picture.width >= min(selection["display"] * 2, 1000)
        screenshots = Path(os.environ.get("ARMARIO_SCREENSHOTS", "test-results"))
        screenshots.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshots / "demo-desktop.png"))
        page.goto(base + "/outfits/nuevo")
        search = page.get_by_role("searchbox", name="Buscar en el selector de prendas", exact=True)
        search.fill("gabardina")
        assert page.locator("[data-picker-card]:visible").count() == 1
        page.locator('[data-picker-card]:visible input[type="checkbox"]').check()
        search.fill("sin coincidencias")
        assert page.locator("[data-picker-card] input:checked").count() == 1
        assert page.locator("[data-picker-empty]").is_visible()
        page.set_viewport_size({"width": 390, "height": 950})
        page.goto(base)
        assert not page.locator('select[name="category_id"]').is_visible()
        page.get_by_role("button", name="Filtros", exact=True).click()
        assert page.locator('select[name="category_id"]').is_visible()
        page.locator('select[name="category_id"]').select_option("1")
        page.get_by_role("button", name="Aplicar", exact=True).click()
        page.wait_for_url("**/*category_id=1*")
        assert page.locator(".garment-card").count() == 2
        assert not page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        page.goto(base)
        page.screenshot(path=str(screenshots / "demo-mobile.png"))
        browser.close()
