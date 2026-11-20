"""Demo HTTP del confronto particellare con dati sintetici."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from pyproj import CRS
from shapely import union_all

from confronto_varianti import FIELDS, compare, read_layer
from genera_demo import CRS as DEMO_CRS, generate


def demo():
    crs = CRS.from_user_input(DEMO_CRS)
    with TemporaryDirectory() as directory:
        source = Path(directory) / "demo.gpkg"
        generate(source)
        parcels, identifiers = read_layer(source, "particelle", crs, "id")
        previous, _ = read_layer(source, "progetto_v1", crs)
        current, _ = read_layer(source, "progetto_v2", crs)
        rows, _ = compare(parcels, identifiers, union_all(previous), union_all(current), 0)
    return {
        "crs": DEMO_CRS,
        "dati": "sintetici",
        "variazioni": [dict(zip(FIELDS, row)) for row in rows],
    }


def app(environ, start_response):
    method = environ["REQUEST_METHOD"]
    headers = [("Content-Type", "application/json; charset=utf-8")]
    if environ["PATH_INFO"] != "/":
        status, payload = "404 Not Found", {"errore": "Percorso inesistente"}
    elif method not in ("GET", "HEAD"):
        status, payload = "405 Method Not Allowed", {"errore": "Metodo non consentito"}
        headers.append(("Allow", "GET, HEAD"))
    else:
        status, payload = "200 OK", demo()
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers.append(("Content-Length", str(len(body))))
    start_response(status, headers)
    return [] if method == "HEAD" else [body]
