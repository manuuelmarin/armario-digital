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
            page.get_by_role("button", name="Revisar traslado").click()
            assert page.get_by_text("Destino:").is_visible()
            page.get_by_role("button", name="Confirmar traslado").click()
            page.wait_for_url(base + "/")
            assert "Espacio B" in page.locator(".card-caption").inner_text()
            page.goto(base + "/outfits/nuevo")
            page.get_by_label("Nombre *", exact=True).fill("Oficina de prueba")
            page.locator('input[name="garment_ids"]').check()
            page.get_by_role("button", name="Guardar outfit").click()
            page.wait_for_url("**/outfits")
            assert page.get_by_role("heading", name="Oficina de prueba").is_visible()
            page.get_by_role("link", name="Ver combinación Oficina de prueba").click()
            assert page.get_by_role("heading", name="Oficina de prueba").is_visible()
            assert page.get_by_role("heading", name="Camisa de prueba").is_visible()
            assert page.locator(".outfit-preview img").evaluate("img => img.naturalWidth > 0")
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
                    "/outfits/1",
                    "/outfits/1/editar",
                    "/maletas",
                    "/maletas/1",
                    "/maletas/1/imprimir",
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


def test_organization_board_and_import_in_browser(app, tmp_path):
    from playwright.sync_api import sync_playwright

    from .conftest import post

    client = app.test_client()
    post(client, "/inspiracion/nuevo", {"name": "Ideas"})
    post(client, "/inspiracion/1/anadir", {"caption": "Una idea", "photo": photograph()})
    with running_app(app) as base, sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_options())
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.set_default_timeout(5000)
        for width in (1440, 390):
            page.set_viewport_size({"width": width, "height": 900})
            for route in (
                "/",
                "/prendas/importar",
                "/colecciones",
                "/inspiracion",
                "/inspiracion/1",
                "/tiempo",
                "/ajustes",
            ):
                page.goto(base + route)
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
                    route,
                    width,
                )
                if route == "/inspiracion/1":
                    assert page.locator(".board-item img").evaluate(
                        "i => i.complete && i.naturalWidth > 0"
                    )
                    assert page.locator(".board-item").evaluate(
                        "i => getComputedStyle(i).position === 'absolute'"
                    )
                    page.screenshot(path=str(tmp_path / f"board-{width}.png"), full_page=True)
        page.set_viewport_size({"width": 1440, "height": 900})
        photo = tmp_path / "imagen.jpg"
        photo.write_bytes(photograph()[0].getvalue())
        page.goto(base + "/prendas/importar")
        page.locator('input[name="photos"]').set_input_files(photo)
        assert page.locator('input[name="photo_names"]').input_value() == "imagen"
        page.locator('input[name="photo_names"]').fill("Prenda revisada")
        page.get_by_role("button", name="Importar prendas").click()
        assert page.get_by_text("Prenda revisada").first.is_visible()
        page.goto(base + "/outfits/nuevo")
        page.locator('input[name="garment_ids"]').first.check()
        assert page.locator("[data-picker-selected]").inner_text() == "1 seleccionadas"
        page.goto(base + "/inspiracion/1")
        handle = page.locator(".board-drag")
        box = handle.bounding_box()
        page.mouse.move(box["x"] + 5, box["y"] + 5)
        page.mouse.down()
        page.mouse.move(box["x"] + 80, box["y"] + 25, steps=4)
        page.mouse.up()
        page.wait_for_load_state("load")
        assert int(page.locator('#board-form-1 input[name="x"]').input_value()) > 0
        browser.close()


def test_picker_pagination_retains_selected_items_and_preview(app, tmp_path):
    from playwright.sync_api import sync_playwright

    from armario.db import connect

    db = connect(app.config["DATA_DIR"] / "wardrobe.sqlite")
    with db:
        db.executemany(
            "INSERT INTO garments(name,category_id,location_id) VALUES (?,1,1)",
            [(f"Prenda {n:02d}",) for n in range(30)],
        )
    db.close()
    photo = tmp_path / "ejemplo.jpg"
    photo.write_bytes(photograph()[0].getvalue())
    with running_app(app) as base, sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_options())
        page = browser.new_page(viewport={"width": 390, "height": 900})
        page.goto(base + "/prendas/importar")
        page.locator('input[name="photos"]').set_input_files(photo)
        assert page.locator("[data-import-preview] img").evaluate(
            "img => img.complete && img.naturalWidth > 0"
        )
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.goto(base + "/outfits/nuevo")
        cards = page.locator("[data-picker-card]")
        assert page.locator("[data-picker-card]:visible").count() == 24
        cards.nth(0).locator("input").check()
        page.locator("[data-picker-next]").click()
        cards.nth(24).locator("input").check()
        assert page.locator("[data-picker-selected]").inner_text() == "2 seleccionadas"
        page.locator("[data-picker-prev]").click()
        assert cards.nth(0).locator("input").is_checked()
        page.get_by_label("Nombre *", exact=True).fill("Selección paginada")
        page.get_by_role("button", name="Guardar outfit").click()
        page.get_by_role("link", name="Ver combinación Selección paginada").click()
        assert page.locator(".outfit-preview").count() == 2
        browser.close()


def test_optional_assistant_review_generation_and_mobile(app, tmp_path):
    from playwright.sync_api import sync_playwright

    from armario.db import connect
    from armario.profiles import save_profile

    from .conftest import post
    from .test_local_ai import FakeOllama, profile_data, worker

    client = app.test_client()
    post(client, "/ajustes/ia", {"enabled": "1"})
    for kind, length in (
        ("camisa", "no_visible"),
        ("pantalon", "largo"),
        ("calzado", "no_visible"),
    ):
        response = post(
            client,
            "/prendas/nueva",
            {
                "name": f"Ejemplo {kind}",
                "category_id": "1",
                "location_id": "1",
                "photos": photograph(),
            },
        )
        gid = int(response.location.rsplit("/", 1)[1])
        db = connect(app.config["DATA_DIR"] / "wardrobe.sqlite")
        try:
            with db:
                save_profile(db, gid, profile_data(kind, length), 0, {"origin": "synthetic_test"})
        finally:
            db.close()
    runner = worker(app, FakeOllama())
    with running_app(app) as base, sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_options())
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(5000)
        for width in (1440, 390):
            page.set_viewport_size({"width": width, "height": 950})
            for route in (
                "/ajustes/ia",
                "/ia/tareas",
                "/ia/analizar",
                "/outfits/generar",
                "/prendas/1/descripcion",
            ):
                page.goto(base + route)
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
                    width,
                    route,
                )
                for image in page.locator("main img").all():
                    image.scroll_into_view_if_needed()
                    page.wait_for_function(
                        "img => img.complete && img.naturalWidth > 0", arg=image.element_handle()
                    )
                    assert image.evaluate("img => img.complete && img.naturalWidth > 0")
        page.goto(base + "/prendas/1/descripcion")
        assert page.locator("fieldset").count() == 7
        page.get_by_label("Descripción completa", exact=True).fill(
            "Camisa revisada en el navegador."
        )
        page.get_by_role("checkbox", name="He revisado la descripción").check()
        page.get_by_role("button", name="Guardar descripción revisada").click()
        page.get_by_role("link", name="Completar con esta prenda").click()
        assert page.locator('input[name="garment_ids"][value="1"]').is_checked()
        page.get_by_label("Chaqueta o abrigo", exact=True).select_option("no")
        page.get_by_label("Pantalón", exact=True).select_option("largo")
        page.get_by_role("button", name="Generar propuestas").click()
        assert page.get_by_role("button", name="Cancelar tarea").is_visible()
        assert runner.run_once()
        page.get_by_role("link", name="Actualizar estado", exact=True).click()
        assert page.get_by_role("heading", name="Propuesta 1", exact=True).is_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(tmp_path / "assistant-mobile.png"), full_page=True)
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.screenshot(path=str(tmp_path / "assistant-desktop.png"), full_page=True)
        page.get_by_label("Nombre para guardar").fill("Outfit asistido de prueba")
        page.get_by_role("button", name="Guardar propuesta 1", exact=True).click()
        assert page.get_by_role("heading", name="Outfit asistido de prueba").is_visible()
        assert page.locator(".outfit-preview").count() == 3
        # Core review and generation controls also work with JavaScript disabled.
        context = browser.new_context(java_script_enabled=False)
        no_js = context.new_page()
        no_js.goto(base + "/prendas/1/descripcion")
        assert no_js.locator("fieldset").count() == 7
        no_js.get_by_label("Descripción completa", exact=True).fill("Revisión sin JavaScript.")
        no_js.get_by_role("checkbox", name="He revisado la descripción").check()
        no_js.get_by_role("button", name="Guardar descripción revisada").click()
        assert no_js.get_by_text("Revisión sin JavaScript.", exact=True).is_visible()
        context.close()
        browser.close()


def test_replace_saved_outfit_keeps_optional_layers_without_javascript(app, tmp_path):
    from playwright.sync_api import sync_playwright

    from armario.db import connect
    from armario.profiles import save_profile

    from .conftest import post
    from .test_local_ai import FakeOllama, profile_data, worker

    client = app.test_client()
    post(client, "/ajustes/ia", {"enabled": "1"})
    for index, (kind, length) in enumerate(
        (
            ("camisa", "no_visible"),
            ("pantalon", "largo"),
            ("calzado", "no_visible"),
            ("chaqueta", "no_visible"),
            ("accesorio", "no_visible"),
            ("chaqueta", "no_visible"),
        ),
        1,
    ):
        response = post(
            client,
            "/prendas/nueva",
            {
                "name": f"Pieza {index}",
                "category_id": "1",
                "location_id": "1",
                "photos": photograph(),
            },
        )
        gid = int(response.location.rsplit("/", 1)[1])
        db = connect(app.config["DATA_DIR"] / "wardrobe.sqlite")
        try:
            with db:
                save_profile(db, gid, profile_data(kind, length), 0, {"origin": "synthetic_test"})
        finally:
            db.close()
    post(
        client,
        "/outfits/nuevo",
        {"name": "Cinco piezas", "occasion": "Cena", "garment_ids": [str(n) for n in range(1, 6)]},
    )
    runner = worker(app, FakeOllama())
    with running_app(app) as base, sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_options())
        context = browser.new_context(
            java_script_enabled=False, viewport={"width": 390, "height": 950}
        )
        page = context.new_page()
        page.goto(base + "/outfits/generar?outfit_id=1&replace=4")
        assert page.locator('input[name="replacement_role"]').input_value() == "outer"
        assert page.get_by_label("Chaqueta o abrigo", exact=True).input_value() == "yes"
        assert page.get_by_label("Permitir un accesorio", exact=True).is_checked()
        assert page.get_by_label("Pantalón", exact=True).input_value() == "largo"
        assert page.get_by_label("Ocasión (opcional)", exact=True).input_value() == "Cena"
        assert page.locator('input[name="garment_ids"]:checked').count() == 4
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.get_by_role("button", name="Generar propuestas").click()
        assert runner.run_once()
        page.get_by_role("link", name="Actualizar estado", exact=True).click()
        assert page.locator(".ai-pieces strong").all_text_contents() == [
            "Pieza 1",
            "Pieza 2",
            "Pieza 3",
            "Pieza 5",
            "Pieza 6",
        ]
        for image in page.locator(".ai-pieces img").all():
            image.scroll_into_view_if_needed()
            page.wait_for_function(
                "img => img.complete && img.naturalWidth > 0", arg=image.element_handle()
            )
        page.screenshot(path=str(tmp_path / "audit-replacement-mobile.png"), full_page=True)
        page.set_viewport_size({"width": 1440, "height": 1000})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(tmp_path / "audit-replacement-desktop.png"), full_page=True)
        context.close()
        browser.close()


def test_mobile_theme_and_trip_picker_across_pages(app, db):
    from playwright.sync_api import expect, sync_playwright

    with db:
        db.executemany(
            "INSERT INTO garments(name,category_id,location_id) VALUES (?,1,1)",
            [(f"Camisa {i:02d}",) for i in range(30)],
        )
        db.execute("INSERT INTO trips(name,origin_id,destination_id) VALUES ('Viaje',1,2)")
    with running_app(app) as base, sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_options())
        page = browser.new_page(viewport={"width": 390, "height": 844}, color_scheme="light")
        page.goto(base)
        page.locator(".mobile-more summary").click()
        page.get_by_role("link", name="Ajustes", exact=True).click()
        page.get_by_label("Apariencia").select_option("dark")
        page.reload()
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        page.goto(base + "/maletas/1")
        expect(page.get_by_role("checkbox")).to_have_count(0)
        page.get_by_role("link", name="Añadir prendas del armario").click()
        expect(page.get_by_role("checkbox")).to_have_count(24)
        page.get_by_role("checkbox").first.check()
        page.get_by_role("link", name="Siguiente").click()
        expect(page.get_by_role("checkbox")).to_have_count(6)
        page.get_by_role("checkbox").first.check()
        page.get_by_label("Buscar prendas").fill("Camisa 29")
        page.get_by_role("button", name="Buscar", exact=True).click()
        expect(page.get_by_role("checkbox")).to_have_count(1)
        page.get_by_role("button", name="Añadir selección").click()
        expect(page.locator(".checklist-row")).to_have_count(2)
        browser.close()
