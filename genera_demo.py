"""Genera tre layer sintetici nello stesso GeoPackage."""

import argparse
from pathlib import Path

import numpy as np
from pyogrio.raw import write
from shapely import to_wkb
from shapely.geometry import box


CRS = "EPSG:32632"


def generate(path):
    if path.exists():
        raise FileExistsError(path)
    origin_x, origin_y = 500_000, 5_000_000

    def rectangle(left, right):
        return box(origin_x + left, origin_y, origin_x + right, origin_y + 10)

    layers = {
        "particelle": [(0, 10), (20, 30), (40, 50), (60, 70), (80, 90)],
        "progetto_v1": [(0, 5), (40, 44), (60, 64), (75, 80)],
        "progetto_v2": [(20, 26), (40, 47), (66, 70), (70, 80)],
    }
    for name, bounds in layers.items():
        identifiers = [np.array(["P01", "P02", "P03", "P04", "P05"])] if name == "particelle" else []
        write(
            path, to_wkb([rectangle(*extent) for extent in bounds]),
            identifiers, ["id"] if identifiers else [],
            layer=name, driver="GPKG", geometry_type="Polygon", crs=CRS,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    generate(parser.parse_args().output)
