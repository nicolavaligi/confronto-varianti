import csv
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from pyogrio import read_info

from genera_demo import generate


SCRIPT = Path(__file__).resolve().parents[1] / "confronto_varianti.py"


class ComparisonTest(unittest.TestCase):
    def test_demo_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "demo.gpkg"
            output = root / "risultati"
            generate(source)
            command = [
                sys.executable, str(SCRIPT), *([str(source)] * 3),
                "--layer-particelle", "particelle", "--layer-prima", "progetto_v1",
                "--layer-dopo", "progetto_v2", "--id", "id", "--crs", "EPSG:32632",
                "--output", str(output),
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)
            with (output / "variazioni.csv").open(newline="", encoding="utf-8") as stream:
                rows = [
                    (row["particella"], row["esito"], float(row["prima_m2"]),
                     float(row["dopo_m2"]), float(row["delta_m2"]),
                     float(row["rimossa_m2"]), float(row["aggiunta_m2"]))
                    for row in csv.DictReader(stream)
                ]
            self.assertEqual(rows, [
                ("P01", "uscita", 50, 0, -50, 50, 0),
                ("P02", "entrata", 0, 60, 60, 0, 60),
                ("P03", "variazione", 40, 70, 30, 0, 30),
                ("P04", "spostamento", 40, 40, 0, 40, 40),
            ])
            info = read_info(output / "variazioni.gpkg", layer="particelle_varianti")
            self.assertEqual(info["features"], 4)
            self.assertEqual(info["crs"], "EPSG:32632")
            repeated = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(repeated.returncode, 2)
            self.assertIn("esiste già", repeated.stderr)

            empty = root / "vuoto"
            subprocess.run(
                [*command[:-1], str(empty), "--tolleranza-m2", "80"],
                check=True, capture_output=True, text=True,
            )
            self.assertEqual(read_info(empty / "variazioni.gpkg")["features"], 0)
