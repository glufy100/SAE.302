#!/usr/bin/env bash

DOSSIER="$(cd "$(dirname "$0")" && pwd)"
RACINE="$(dirname "$DOSSIER")"

cd "$RACINE"
exec python3 -m server.carrefour
