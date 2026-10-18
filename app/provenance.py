"""Nombres de entradas conocidas según evidence/input_manifest.json.

Solo procedencia pública; no contiene hojas, filas ni etiquetas del ejercicio.
Las cargas del kit usan estos basenames (scripts/final_rehearsal.py y app.cli).
No deducir un nombre por el split: únicamente una coincidencia exacta de contenido.
"""

KNOWN_INPUT_FILENAMES = {
    "41e992fb46afb742c3dd54b79eb14c9e75863d71be563851f20d62ebd3798007": "supplier_training.xlsx",
    "709c6b3a1988350ed84b344aab191153381c071b10ff89a3d8374c80845c2318": "supplier_validation.xlsx",
    "f3c758c96de441ed8c9e228dd1e26b619b0969793d8c7ca0ccbadec24858411f": "supplier_test.xlsx",
    "be36ea08220842c8f3a12f823fbce9eaf39f0b879c172bebba27a4c41d232044": "supplier_liveday.xlsx",
}
