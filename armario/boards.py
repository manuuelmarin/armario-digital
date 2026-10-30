"""Private inspiration boards backed by locally processed images."""

from urllib.parse import urlsplit

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from .db import get_db
from .domain import text_value
from .images import record_integrity, remove_files, store_image
from .queries import entity

bp = Blueprint("boards", __name__)


def safe_link(value):
    if not value:
        return ""
    parts = urlsplit(value)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username
        or parts.password
        or any(ord(c) < 32 or c.isspace() for c in value)
    ):
        raise ValueError("Introduce un enlace HTTP o HTTPS válido.")
    return value


@bp.get("/inspiracion")
def index():
    db = get_db()
    boards = db.execute(
        "SELECT b.*,count(i.id) total FROM boards b LEFT JOIN board_items i ON i.board_id=b.id GROUP BY b.id ORDER BY b.id DESC"
    ).fetchall()
    return render_template("boards.html", boards=boards)


@bp.post("/inspiracion/nuevo")
def create():
    db = get_db()
    with db:
        bid = db.execute(
            "INSERT INTO boards(name,notes) VALUES (?,?)",
            (text_value(request.form, "name", 100, True), text_value(request.form, "notes", 3000)),
        ).lastrowid
    return redirect(url_for("boards.detail", bid=bid))


@bp.get("/inspiracion/<int:bid>")
def detail(bid):
    board = entity("boards", bid)
    items = (
        get_db()
        .execute("SELECT * FROM board_items WHERE board_id=? ORDER BY id", (bid,))
        .fetchall()
    )
    return render_template("board_detail.html", board=board, items=items)


@bp.post("/inspiracion/<int:bid>/anadir")
def add(bid):
    entity("boards", bid)
    caption = text_value(request.form, "caption", 300)
    link = safe_link(text_value(request.form, "link", 2000))
    photo = request.files.get("photo")
    if not caption and not link and not (photo and photo.filename):
        raise ValueError("Añade una imagen, un enlace o una nota.")
    db = get_db()
    root = current_app.config["DATA_DIR"] / "images"
    created = []
    try:
        with db:
            image = store_image(photo, root) if photo and photo.filename else None
            if image:
                created = [image["filename"], image["thumbnail"], image["preview"]]
                record_integrity(db, root, created)
            count = db.execute(
                "SELECT count(*) FROM board_items WHERE board_id=?", (bid,)
            ).fetchone()[0]
            if count >= 100:
                raise ValueError("Cada tablero admite hasta 100 elementos.")
            db.execute(
                "INSERT INTO board_items(board_id,caption,link,filename,thumbnail,preview,x,y) VALUES (?,?,?,?,?,?,?,?)",
                (
                    bid,
                    caption,
                    link,
                    *(
                        (image[k] for k in ("filename", "thumbnail", "preview"))
                        if image
                        else (None, None, None)
                    ),
                    (count % 9) * 220,
                    (count // 9) * 170,
                ),
            )
    except Exception:
        remove_files(root, created)
        raise
    flash("Elemento añadido al tablero.", "success")
    return redirect(url_for("boards.detail", bid=bid))


@bp.post("/inspiracion/<int:bid>/elemento/<int:iid>/guardar")
def update_item(bid, iid):
    entity("boards", bid)
    db = get_db()
    if not db.execute("SELECT 1 FROM board_items WHERE id=? AND board_id=?", (iid, bid)).fetchone():
        abort(404)
    try:
        x, y, width = (int(request.form.get(key, "")) for key in ("x", "y", "width"))
    except ValueError as exc:
        raise ValueError("Las posiciones deben ser números enteros.") from exc
    if not (0 <= x <= 2000 and 0 <= y <= 2000 and 100 <= width <= 600):
        raise ValueError("Posición o anchura fuera de los límites del tablero.")
    with db:
        db.execute(
            "UPDATE board_items SET x=?,y=?,width=?,caption=?,link=? WHERE id=?",
            (
                x,
                y,
                width,
                text_value(request.form, "caption", 300),
                safe_link(text_value(request.form, "link", 2000)),
                iid,
            ),
        )
    return redirect(url_for("boards.detail", bid=bid))


@bp.post("/inspiracion/<int:bid>/elemento/<int:iid>/eliminar")
def delete_item(bid, iid):
    entity("boards", bid)
    db = get_db()
    item = db.execute("SELECT * FROM board_items WHERE board_id=? AND id=?", (bid, iid)).fetchone()
    if item is None:
        abort(404)
    if request.form.get("confirm") != "1":
        raise ValueError("Confirma la eliminación.")
    names = [item[key] for key in ("filename", "thumbnail", "preview") if item[key]]
    with db:
        db.execute("DELETE FROM board_items WHERE id=?", (iid,))
        db.executemany("DELETE FROM image_integrity WHERE name=?", [(name,) for name in names])
    remove_files(current_app.config["DATA_DIR"] / "images", names)
    return redirect(url_for("boards.detail", bid=bid))


@bp.get("/inspiracion/<int:bid>/lienzo.css")
def layout_css(bid):
    from flask import Response

    entity("boards", bid)
    items = (
        get_db().execute("SELECT id,x,y,width FROM board_items WHERE board_id=?", (bid,)).fetchall()
    )
    rules = [
        f".board-item-{r['id']}{{left:{r['x']}px;top:{r['y']}px;width:{r['width']}px}}"
        for r in items
    ]
    height = max((r["y"] + 350 for r in items), default=500)
    rules.append(f".board-canvas{{height:{height}px}}")
    return Response("\n".join(rules), mimetype="text/css", headers={"Cache-Control": "no-store"})


@bp.post("/inspiracion/<int:bid>/renombrar")
def rename(bid):
    entity("boards", bid)
    db = get_db()
    with db:
        db.execute(
            "UPDATE boards SET name=?, notes=? WHERE id=?",
            (
                text_value(request.form, "name", 100, True),
                text_value(request.form, "notes", 3000),
                bid,
            ),
        )
    return redirect(url_for("boards.detail", bid=bid))


@bp.post("/inspiracion/<int:bid>/eliminar")
def delete_board(bid):
    entity("boards", bid)
    if request.form.get("confirm") != "1":
        raise ValueError("Confirma la eliminación.")
    db = get_db()
    names = [
        name
        for row in db.execute(
            "SELECT filename,thumbnail,preview FROM board_items WHERE board_id=?", (bid,)
        )
        for name in row
        if name
    ]
    with db:
        db.execute("DELETE FROM boards WHERE id=?", (bid,))
        db.executemany("DELETE FROM image_integrity WHERE name=?", [(name,) for name in names])
    remove_files(current_app.config["DATA_DIR"] / "images", names)
    flash("Tablero eliminado.", "success")
    return redirect(url_for("boards.index"))
