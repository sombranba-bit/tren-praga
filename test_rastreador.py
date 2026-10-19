"""Comprobación sin red: python3 test_rastreador.py"""
import json
import os
import stat
import tempfile
from pathlib import Path

import rastreador as r

tmp = Path(tempfile.mkdtemp())
r.HISTORICO = tmp / "data" / "historico.json"

# renfecli falso con la forma real de su --json
renfe_json = {"journeys": [
    {"departure": "16:05", "arrival": "17:26", "train_type": "AVLO", "from": "MADRID-PUERTA DE ATOCHA-ALMUDENA GRANDES",
     "price": 19.5, "available": True, "sold_out": False},
    {"departure": "17:00", "arrival": "18:21", "train_type": "AVE", "from": "MADRID-PUERTA DE ATOCHA-ALMUDENA GRANDES",
     "price": 0, "available": False, "sold_out": True},
]}
fake = tmp / "renfe"
fake.write_text(f"#!/bin/sh\ncat <<'EOF'\n{json.dumps(renfe_json)}\nEOF\n")
fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
r.RENFE_BIN = str(fake)


def falso_http(url, cuerpo, token=None):
    if url.endswith("/Token/login"):
        return {"token": "x"}
    assert cuerpo["destination"] == r.OUIGO_ZARAGOZA and token == "x"
    return {"outbound": [
        {"departure_station": {"departure_timestamp": "2027-01-05T15:40:00+01:00"},
         "arrival_station": {"arrival_timestamp": "2027-01-05T17:05:00+01:00"},
         "price": 15.0, "full": False, "remaining_seats": 3},
        {"departure_station": {"departure_timestamp": "2027-01-05T08:00:00+01:00"},  # fuera de franja
         "arrival_station": {"arrival_timestamp": "2027-01-05T09:20:00+01:00"}, "price": 9.0},
    ]}


r.http_json = falso_http
assert r.main(hoy="2026-10-19") == 0
d = json.loads(r.HISTORICO.read_text())
p = d["pasadas"][-1]
assert d["config"]["fecha"] == "2027-01-05"
assert p["estado"] == {"Renfe": "2 trenes", "Ouigo": "2 trenes"}, p["estado"]  # 1 Ouigo por cada estación de Madrid
avlo, ave = p["trenes"][0], p["trenes"][1]
assert avlo == {"op": "Avlo", "de": "Madrid Atocha", "sale": "16:05", "llega": "17:26", "precio": 19.5,
                "agotado": False, "plazas": None}, avlo
assert ave["agotado"] and ave["precio"] is None
assert p["trenes"][2]["sale"] == "15:40" and p["trenes"][2]["plazas"] == 3

# Renfe sin venta abierta: no es error
fake.write_text("#!/bin/sh\necho \"no trains for MADRID → ZARAGOZA — the date may be outside Renfe's sale window\" >&2\nexit 1\n")
assert r.main(hoy="2026-10-19") == 0
assert json.loads(r.HISTORICO.read_text())["pasadas"][-1]["estado"]["Renfe"] == "aún no está a la venta"

# Todo roto: código de salida 1 para que GitHub avise, y la pasada se guarda igual
fake.write_text("#!/bin/sh\necho boom >&2\nexit 1\n")
r.http_json = lambda *a, **k: (_ for _ in ()).throw(OSError("sin red"))
assert r.main(hoy="2026-10-19") == 1
assert len(json.loads(r.HISTORICO.read_text())["pasadas"]) == 3

# Pasada la fecha del viaje no hace nada
assert r.main(hoy="2027-01-06") == 0 and len(json.loads(r.HISTORICO.read_text())["pasadas"]) == 3
print("OK")
