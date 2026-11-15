#!/usr/bin/env bash

RACINE="$(cd "$(dirname "$0")" && pwd)"
DENSITE="${1:-3}"

if [[ "$DENSITE" == "--clients-only" ]]; then
    exec bash "$RACINE/client/lancer_simulation.sh" "${2:-3}" "${3:-0.4}" "${4:-TOUS}"
fi

bash "$RACINE/server/lancer_serveur.sh" &
SERVEUR_PID=$!

arreter() {
    kill "$SERVEUR_PID" 2>/dev/null
    kill "${CLIENTS_PID:-}" 2>/dev/null
}
trap arreter EXIT INT TERM

cd "$RACINE" || exit 1
python3 - "$SERVEUR_PID" <<'PY' || exit 1
import os
import socket
import sys
import time

from client.config import HOST, PORT

pid = int(sys.argv[1])
limite = time.monotonic() + 20

# Qt peut dépasser le délai fixe au premier démarrage d'un venv neuf.
while time.monotonic() < limite:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        sys.exit("Le serveur s'est arrêté au démarrage.")
    try:
        with socket.create_connection((HOST, PORT), timeout=0.5):
            sys.exit(0)
    except OSError:
        time.sleep(0.1)

sys.exit(f"Le serveur ne répond pas sur {HOST}:{PORT}.")
PY

bash "$RACINE/client/lancer_simulation.sh" "$DENSITE" "${2:-0.4}" "${3:-TOUS}" &
CLIENTS_PID=$!
wait "$SERVEUR_PID"
