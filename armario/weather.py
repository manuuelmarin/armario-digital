"""Optional on-demand forecast; no request is made without an explicit form submission."""

import json
import math
from datetime import UTC, datetime
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from flask import Blueprint, flash, redirect, render_template, request, url_for

from .db import get_db
from .domain import text_value

bp = Blueprint("weather", __name__)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("El servicio meteorológico devolvió una redirección inesperada.")


def get_forecast(latitude, longitude):
    query = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": 5,
            "timezone": "auto",
        }
    )
    req = Request(
        "https://api.open-meteo.com/v1/forecast?" + query,
        headers={"User-Agent": "ArmarioDigital/0.2"},
    )
    try:
        with build_opener(NoRedirect()).open(req, timeout=5) as response:
            raw = response.read(200_001)
        if len(raw) > 200_000:
            raise ValueError("La respuesta meteorológica es demasiado grande.")
        payload = json.loads(raw)
        daily = payload["daily"]
        days = daily["time"]
        high, low, rain = (
            daily[key]
            for key in ("temperature_2m_max", "temperature_2m_min", "precipitation_probability_max")
        )
        if not (
            isinstance(days, list)
            and 1 <= len(days) <= 7
            and len(days) == len(high) == len(low) == len(rain)
        ):
            raise ValueError("La respuesta meteorológica tiene un formato inesperado.")
        rows = []
        for date, maximum, minimum, probability in zip(days, high, low, rain, strict=True):
            datetime.strptime(date, "%Y-%m-%d")
            if (
                any(
                    not isinstance(n, (int, float)) or isinstance(n, bool) or not math.isfinite(n)
                    for n in (maximum, minimum, probability)
                )
                or not 0 <= probability <= 100
            ):
                raise ValueError("La respuesta meteorológica tiene valores inesperados.")
            rows.append({"date": date, "max": maximum, "min": minimum, "rain": probability})
        return rows
    except (URLError, TimeoutError, KeyError, TypeError, json.JSONDecodeError, OSError) as exc:
        raise ValueError(
            "No se pudo actualizar el tiempo. Se conserva la última consulta disponible."
        ) from exc


@bp.get("/tiempo")
def index():
    row = get_db().execute("SELECT * FROM weather_cache WHERE id=1").fetchone()
    forecast = json.loads(row["payload"]) if row else []
    return render_template("weather.html", cache=row, forecast=forecast)


@bp.post("/tiempo/actualizar")
def update():
    label = text_value(request.form, "label", 80, True)
    try:
        lat, lon = float(request.form.get("latitude", "")), float(request.form.get("longitude", ""))
    except ValueError as exc:
        raise ValueError("Introduce coordenadas numéricas válidas.") from exc
    if (
        not math.isfinite(lat)
        or not math.isfinite(lon)
        or not -90 <= lat <= 90
        or not -180 <= lon <= 180
    ):
        raise ValueError("Las coordenadas no son válidas.")
    rows = get_forecast(lat, lon)
    db = get_db()
    with db:
        db.execute(
            "INSERT OR REPLACE INTO weather_cache VALUES (1,?,?,?,?,?)",
            (label, lat, lon, datetime.now(UTC).isoformat(timespec="seconds"), json.dumps(rows)),
        )
    flash("Previsión actualizada.", "success")
    return redirect(url_for("weather.index"))


@bp.post("/tiempo/borrar")
def clear():
    if request.form.get("confirm") != "1":
        raise ValueError("Confirma la eliminación de la consulta.")
    db = get_db()
    with db:
        db.execute("DELETE FROM weather_cache WHERE id=1")
    flash("Consulta meteorológica eliminada de los datos actuales.", "success")
    return redirect(url_for("weather.index"))
