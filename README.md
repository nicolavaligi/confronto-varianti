# Confronto varianti

Uno script Python che indica quali particelle riesaminare dopo una modifica al tracciato o al perimetro di un'opera. Usa la stessa base particellare per entrambe le revisioni e misura separatamente la superficie aggiunta e quella rimossa, anche quando il saldo è zero.

## Prova con dati sintetici

Dalla radice del repository, con Python 3.11 o successivo e un ambiente virtuale attivo:

```sh
python -m pip install .
mkdir -p demo
python genera_demo.py demo/input.gpkg
confronto-varianti demo/input.gpkg demo/input.gpkg demo/input.gpkg \
  --layer-particelle particelle --layer-prima progetto_v1 --layer-dopo progetto_v2 \
  --id id --crs EPSG:32632 --output demo/risultati
```

Apri `demo/risultati/variazioni.gpkg` in QGIS. Il layer contiene le geometrie delle particelle con gli stessi campi del CSV.

| Particella | Esito | Prima m² | Dopo m² | Rimossa m² | Aggiunta m² |
|---|---|---:|---:|---:|---:|
| P01 | uscita | 50 | 0 | 50 | 0 |
| P02 | entrata | 0 | 60 | 0 | 60 |
| P03 | variazione | 40 | 70 | 0 | 30 |
| P04 | spostamento | 40 | 40 | 40 | 40 |

P05 tocca il perimetro sul bordo e ha intersezione di area zero. Il report restituisce quattro righe.

## Uso con i propri dati

Passa tre sorgenti vettoriali leggibili da GDAL, nell'ordine particelle, progetto precedente e progetto aggiornato. Per ogni file con più layer, indica quello rilevante con l'opzione `--layer-*`. Le sorgenti richiedono poligoni o multipoligoni validi e un CRS dichiarato. Il campo scelto con `--id` deve avere valori univoci. Scegli con `--crs` un sistema proiettato in metri adatto alla zona di studio, come una zona UTM locale. Crea la cartella padre di `--output` prima di eseguire il comando.

Lo script unisce i poligoni di ogni revisione prima dell'overlay. Le aree sono planari. Il campo `delta_m2` contiene l'area dopo meno l'area prima. Con `--tolleranza-m2` puoi escludere particelle per cui la somma delle superfici aggiunte e rimosse è pari o inferiore alla soglia. Per le particelle interessate in entrambe le versioni, la stessa soglia definisce quando un saldo è abbastanza vicino a zero da classificare il cambiamento come spostamento. Il valore predefinito è zero. L'elaborazione usa la memoria locale per i tre layer.

## Verifica

```sh
python -m unittest discover -s tests -v
```
