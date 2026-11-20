"""Confronta due impronte di progetto su una base particellare comune."""

import argparse
import csv
import math
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from pyogrio import raw
from pyogrio.errors import DataSourceError, DataLayerError
from pyproj import CRS, Transformer
from pyproj.exceptions import ProjError
from shapely import difference, from_wkb, intersection, to_wkb, union, union_all
from shapely.errors import GEOSException
from shapely.ops import transform
from shapely.strtree import STRtree


FIELDS = ("particella", "esito", "prima_m2", "dopo_m2", "delta_m2",
          "rimossa_m2", "aggiunta_m2")


def read_layer(path, layer, target, id_field=None):
    metadata, _, wkb, columns = raw.read(
        path, layer=layer, columns=[id_field] if id_field else [], force_2d=True
    )
    label = f"{path} ({layer})" if layer else str(path)
    if not metadata["crs"]:
        raise ValueError(f"{label}: CRS assente")
    source = CRS.from_user_input(metadata["crs"])
    reproject = Transformer.from_crs(
        source, target, always_xy=True, allow_ballpark=False, only_best=True
    )
    geometries = []
    for row, geometry in enumerate(from_wkb(wkb), start=1):
        if (geometry is None or geometry.is_empty or not geometry.is_valid
                or geometry.geom_type not in {"Polygon", "MultiPolygon"}):
            raise ValueError(f"{label}: geometria poligonale non valida alla riga {row}")
        if source != target:
            geometry = transform(reproject.transform, geometry)
            if not geometry.is_valid or not math.isfinite(geometry.area):
                raise ValueError(f"{label}: trasformazione non valida alla riga {row}")
        geometries.append(geometry)
    identifiers = []
    if id_field:
        if id_field not in metadata["fields"]:
            raise ValueError(f"{label}: campo identificativo assente: {id_field}")
        for value in columns[0]:
            if value is None or (isinstance(value, float) and not math.isfinite(value)):
                raise ValueError(f"{label}: identificativo mancante")
            identifiers.append(str(value).strip())
        if "" in identifiers or len(set(identifiers)) != len(identifiers):
            raise ValueError(f"{label}: identificativi vuoti o duplicati")
    return geometries, identifiers


def compare(parcels, identifiers, previous, current, tolerance):
    footprint = union(previous, current)
    candidates = STRtree(parcels).query(footprint, predicate="intersects")
    rows, geometries = [], []
    for index in sorted(candidates):
        parcel = parcels[index]
        before = intersection(parcel, previous)
        after = intersection(parcel, current)
        removed = difference(before, after).area
        added = difference(after, before).area
        if removed + added <= tolerance:
            continue
        if before.area == 0:
            status = "entrata"
        elif after.area == 0:
            status = "uscita"
        elif abs(after.area - before.area) <= tolerance:
            status = "spostamento"
        else:
            status = "variazione"
        rows.append((identifiers[index], status, before.area, after.area,
                     after.area - before.area, removed, added))
        geometries.append(parcel)
    return rows, geometries


def write_results(output, rows, geometries, crs):
    if output.exists():
        raise ValueError(f"La cartella di output esiste già: {output}")
    with TemporaryDirectory(dir=output.parent) as temporary:
        staging = Path(temporary) / "risultati"
        staging.mkdir()
        with (staging / "variazioni.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(FIELDS)
            writer.writerows(rows)
        columns = list(zip(*rows)) if rows else [()] * len(FIELDS)
        data = [np.asarray(column, dtype=object if index < 2 else float)
                for index, column in enumerate(columns)]
        raw.write(
            staging / "variazioni.gpkg", to_wkb(np.asarray(geometries, dtype=object)),
            data, FIELDS, layer="particelle_varianti", driver="GPKG",
            geometry_type="MultiPolygon", promote_to_multi=True, crs=crs.to_wkt(),
        )
        staging.rename(output)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("particelle", "prima", "dopo"):
        parser.add_argument(name, type=Path)
        parser.add_argument(f"--layer-{name}")
    parser.add_argument("--id", required=True, help="Campo con identificativi univoci")
    parser.add_argument("--crs", required=True, help="CRS proiettato locale con unità in metri")
    parser.add_argument("--tolleranza-m2", type=float, default=0.0,
                        help="Ignora cambiamenti con area totale <= alla soglia")
    parser.add_argument("--output", type=Path, required=True, help="Nuova cartella di output")
    args = parser.parse_args(argv)
    try:
        crs = CRS.from_user_input(args.crs)
        if (not crs.is_projected or len(crs.axis_info) != 2
                or any(axis.unit_conversion_factor != 1 for axis in crs.axis_info)
                or crs.to_epsg() == 3857):
            raise ValueError("Scegli un CRS proiettato locale con assi in metri")
        if not math.isfinite(args.tolleranza_m2) or args.tolleranza_m2 < 0:
            raise ValueError("La tolleranza deve essere finita e non negativa")
        parcels, identifiers = read_layer(args.particelle, args.layer_particelle, crs, args.id)
        previous, _ = read_layer(args.prima, args.layer_prima, crs)
        current, _ = read_layer(args.dopo, args.layer_dopo, crs)
        rows, geometries = compare(
            parcels, identifiers, union_all(previous), union_all(current), args.tolleranza_m2
        )
        write_results(args.output, rows, geometries, crs)
    except (ValueError, OSError, GEOSException, ProjError, DataSourceError, DataLayerError) as error:
        parser.exit(2, f"Errore: {error}\n")
    print(f"{len(rows)} particelle con variazioni. Risultati in {args.output}")


if __name__ == "__main__":
    main()
