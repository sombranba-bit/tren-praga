"""Rastreador de precios de tren Madrid -> Zaragoza para la vuelta de Praga.

Cada ejecución es una "pasada": consulta Renfe y Ouigo y la añade a
data/historico.json, que es lo que lee index.html. Lo lanza GitHub Actions
cada pocas horas; no necesita nada instalado más allá de Python.
"""
import json
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

# --- Lo único que hay que tocar para otro viaje --------------------------
FECHA = "2027-01-05"
ADULTOS = 4
DESDE, HASTA = "14:00", "19:30"  # franja de salida; el bus actual sale a las 16:45
# --------------------------------------------------------------------------

HISTORICO = Path(__file__).parent / "data" / "historico.json"
RENFE_BIN = str(Path(__file__).parent / "renfe")  # renfecli, lo descarga el workflow

# API JSON que usa la propia web de Ouigo; las credenciales son las públicas de su web.
OUIGO_API = "https://mdw02.api-es.ouigo.com/api"
OUIGO_LOGIN = {"username": "ouigo.web", "password": "SquirelWeb!2020"}
OUIGO_ORIGENES = {"7160000": "Madrid Atocha", "7117000": "Madrid Chamartín"}
OUIGO_ZARAGOZA = "7104040"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0 Safari/537.36"


def estacion(nombre):
    n = nombre.upper()
    if "ATOCHA" in n:
        return "Madrid Atocha"
    if "CHAMART" in n:
        return "Madrid Chamartín"
    return nombre.title()


def renfe():
    """AVE, Avlo y Alvia de Renfe. Precio por persona, buscando plazas para los 4."""
    r = subprocess.run(
        [RENFE_BIN, "search", "madrid", "zaragoza", "--date", FECHA, "--adults", str(ADULTOS),
         "--after", DESDE, "--before", HASTA, "--json"],
        capture_output=True, text=True, timeout=180,
    )
    if r.returncode != 0:
        # Renfe contesta lista vacía cuando el día aún no está a la venta.
        if "sale window" in r.stderr:
            return [], "aún no está a la venta"
        raise RuntimeError((r.stderr or r.stdout).strip()[-300:])
    trenes = [
        {
            "op": {"AVLO": "Avlo"}.get(j["train_type"].upper(), j["train_type"].upper()),
            "de": estacion(j["from"]),
            "sale": j["departure"],
            "llega": j["arrival"],
            "precio": j["price"] or None,
            "agotado": j["sold_out"] or not j["available"],
            "plazas": None,  # Renfe no lo dice; la búsqueda ya exige sitio para los 4
        }
        for j in json.loads(r.stdout)["journeys"]
    ]
    return trenes, None


def http_json(url, cuerpo, token=None):
    cab = {"Content-Type": "application/json", "User-Agent": UA}
    if token:
        cab["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, json.dumps(cuerpo).encode(), cab)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def ouigo():
    """Ouigo. Se pide para 1 pasajero (precio por persona) y se guardan las plazas libres."""
    token = http_json(f"{OUIGO_API}/Token/login", OUIGO_LOGIN)["token"]
    trenes = []
    for codigo, nombre in OUIGO_ORIGENES.items():
        datos = http_json(f"{OUIGO_API}/Sale/journeysearch", {
            "origin": codigo, "destination": OUIGO_ZARAGOZA, "outbound_date": FECHA,
            "passengers": [{"discount_cards": [], "disability_type": "NH", "type": "A"}],
        }, token) or {}
        if datos.get("error"):
            raise RuntimeError(str(datos["error"]))
        for v in datos.get("outbound") or []:
            sale = datetime.fromisoformat(v["departure_station"]["departure_timestamp"]).strftime("%H:%M")
            if not DESDE <= sale <= HASTA:
                continue
            trenes.append({
                "op": "Ouigo",
                "de": nombre,
                "sale": sale,
                "llega": datetime.fromisoformat(v["arrival_station"]["arrival_timestamp"]).strftime("%H:%M"),
                "precio": v.get("price"),
                "agotado": bool(v.get("full")) or v.get("price") is None,
                "plazas": v.get("remaining_seats"),
            })
    return trenes, None


def main(fuentes=(("Renfe", renfe), ("Ouigo", ouigo)), hoy=None):
    if (hoy or date.today().isoformat()) > FECHA:
        print("El viaje ya pasó: no se hace la pasada.")
        return 0
    pasada = {"t": datetime.now(timezone.utc).isoformat(timespec="minutes"), "trenes": [], "estado": {}}
    for nombre, fuente in fuentes:
        try:
            trenes, nota = fuente()
            pasada["trenes"] += trenes
            pasada["estado"][nombre] = nota or f"{len(trenes)} trenes"
        except Exception as e:  # una fuente rota no debe impedir guardar la otra
            pasada["estado"][nombre] = f"ERROR: {e}"
    datos = json.loads(HISTORICO.read_text()) if HISTORICO.exists() else {"pasadas": []}
    datos["config"] = {"fecha": FECHA, "adultos": ADULTOS, "desde": DESDE, "hasta": HASTA,
                       "ruta": "Madrid → Zaragoza"}
    datos["pasadas"].append(pasada)
    HISTORICO.parent.mkdir(exist_ok=True)
    HISTORICO.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")))
    print(json.dumps(pasada["estado"], ensure_ascii=False))
    # Si fallan todas, el workflow sale en rojo y GitHub avisa por correo.
    return 1 if all(e.startswith("ERROR") for e in pasada["estado"].values()) else 0


if __name__ == "__main__":
    sys.exit(main())
