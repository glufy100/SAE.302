# Carrefour intelligent — SAE 302

Simulation de deux carrefours connectés, **en croix et en T**, réalisée dans le
cadre de la SAE 302 « Développer des applications communicantes ».
Les véhicules normaux et prioritaires échangent avec le carrefour par sockets TCP.
Le passage d'une ambulance, d'un pompier ou d'un véhicule de police déclenche une
adaptation des feux.

## Équipe

**Groupe Jedi** · Louis Erb et Maxence Nordmann

## Installer et lancer depuis les sources

Il faut Git, Python 3.11 à 3.13 et une session graphique pour le serveur.
L'installation locale a été vérifiée avec Python 3.11.9 sous macOS. Le
déploiement prévu sur deux VM utilise Python 3.13 sous Debian 13.

Sous macOS ou Linux, ouvrir un premier terminal pour installer les dépendances
et démarrer le serveur :

```bash
git clone https://github.com/glufy100/SAE.302.git
cd SAE.302
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
SAE302_BIND_HOST=127.0.0.1 python -m server.carrefour
```

Dans un deuxième terminal, depuis le dossier `SAE.302`, générer des voitures et
des ambulances sur les deux carrefours :

```bash
source .venv/bin/activate
bash client/lancer_simulation.sh 3 0.4
```

Pour lancer le serveur et les générateurs avec une seule commande, activer le
venv puis exécuter `SAE302_BIND_HOST=127.0.0.1 bash lancer_simulation.sh 3 0.4`.

Sous Windows PowerShell, utiliser directement le Python du venv :

```powershell
git clone https://github.com/glufy100/SAE.302.git
cd SAE.302
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SAE302_BIND_HOST = "127.0.0.1"
.\.venv\Scripts\python.exe -m server.carrefour
```

Dans deux autres terminaux PowerShell ouverts dans `SAE.302`, lancer
`.\.venv\Scripts\python.exe -m client.voiture 3 --carrefour T`, puis
`.\.venv\Scripts\python.exe -m client.urgence Ambulance S DROITE --carrefour T`.
Ces commandes font circuler des voitures sur le T et déclenchent le passage
d'une ambulance depuis le sud.

Le client cible `127.0.0.1:5050` par défaut. Pour joindre un serveur distant,
définir `SAE302_HOST` sur le client avec l'IP du serveur et donner la même
valeur à `SAE302_PORT` des deux côtés si le port change. Le serveur doit écouter
sur son interface réseau accessible aux clients. Le [guide Debian](doc/Installation.md)
détaille les réglages pour deux VM.

## Architecture

Le déploiement cible utilise **deux VM Debian 13 séparées** :

| VM | Composants | Prérequis |
|---|---|---|
| Serveur | Feux, priorités, interface, rapports et SQLite | Python 3.13, PySide6, bureau graphique |
| Client | Générateurs et calcul de chaque véhicule | Python 3.13, terminal |

Les clients calculent les positions de départ, trajectoires, distances de sécurité,
collisions, virages à gauche, dépassements, rangements et réinsertions. Le serveur
transmet des instantanés, vérifie le format et la révision des rapports, puis affiche
les coordonnées reçues. Les deux carrefours ont leur propre trafic, leurs feux et
leurs compteurs, accessibles sur un seul port TCP : **5050** par défaut.

## Installer les paquets Debian

Les deux paquets sont disponibles dans [dist/](dist/) :

- [Télécharger le serveur](https://github.com/glufy100/SAE.302/raw/refs/heads/main/dist/sae302-server_1.0.0_all.deb)
- [Télécharger le client](https://github.com/glufy100/SAE.302/raw/refs/heads/main/dist/sae302-client_1.0.0_all.deb)
- [Empreintes SHA-256](dist/SHA256SUMS)

Copier chaque paquet sur la VM correspondante. Dans le dossier contenant le
paquet serveur, sur la **VM serveur**, ouvrir un terminal de la session graphique :

```bash
sudo apt update
sudo apt install ./sae302-server_1.0.0_all.deb
sae302-server
```

Sur la **VM client**, dans le dossier contenant son paquet :

```bash
sudo apt update
sudo apt install ./sae302-client_1.0.0_all.deb
sudo nano /etc/sae302/client.conf
```

Renseigner l'adresse réelle de la VM serveur, par exemple :

```ini
SAE302_HOST=192.168.56.10
SAE302_PORT=5050
```

Démarrer les véhicules après le serveur :

```bash
sae302-client 3 0.4
```

Les VM doivent pouvoir communiquer sur TCP 5050. Le serveur reste ouvert dans
sa session graphique et se lance sous l'utilisateur normal, sans `sudo`.
APT installe les dépendances nécessaires ; le client n'utilise pas PySide6.

Le [guide d'installation Debian 13](doc/Installation.md) explique le réseau
virtuel, la configuration des deux VM, les tests de connexion, les sauvegardes,
les mises à jour et la désinstallation.

## Commandes des véhicules

| Exemple | Depuis les sources avec le venv activé | Avec les paquets Debian |
|---|---|---|
| Voitures et ambulances sur les deux carrefours | `bash client/lancer_simulation.sh 3 0.4` | `sae302-client 3 0.4` |
| Trafic sur le T | `bash client/lancer_simulation.sh 3 0.4 T` | `sae302-client 3 0.4 T` |
| Voitures seules sur la croix | `bash client/lancer_simulation.sh 3 0 CROIX` | `sae302-client 3 0 CROIX` |
| Générateur de voitures pour le T | `python -m client.voiture 3 --carrefour T` | `sae302-voiture 3 --carrefour T` |
| Une ambulance entrant par le sud du T | `python -m client.urgence Ambulance S DROITE --carrefour T` | `sae302-urgence Ambulance S DROITE --carrefour T` |

Le premier argument du lanceur est une densité de voitures entière, au moins 1.
Le deuxième est une densité d'urgences entre 0 et 1. Le troisième vaut `TOUS`,
`CROIX` ou `T`. Les commandes individuelles ciblent la croix par défaut.
La croix possède les branches `N`, `S`, `E`, `O` ; le T possède `S`, `E`, `O`.
Les générateurs demandent au serveur les trajets autorisés.

Arrêter les générateurs avec `Ctrl+C`, puis fermer la fenêtre du serveur.

Le dossier `client/` peut être copié seul sur la VM des véhicules et utilisé avec
Python standard. Les lancements directs lisent les variables d'environnement et
les valeurs de repli des modules `config.py`. Les fichiers `/etc/sae302/*.conf`
sont chargés uniquement par les lanceurs des paquets Debian.
Les réglages de conduite sont définis dans `client/config.py`.

## Construire les paquets et tester

Depuis la racine du dépôt, avec le venv activé :

```bash
python packaging/build_deb.py
python -m unittest discover -s tests
```

Le constructeur utilise Python standard, fonctionne sous Linux et macOS et produit
les deux `.deb` ainsi que `dist/SHA256SUMS`. Les paquets contiennent uniquement le
code du rôle concerné, sa configuration, ses lanceurs et sa documentation.

La suite de **55 tests** a réussi sous macOS, dans un venv Python 3.11.9 avec
PySide6 6.9.2. Elle couvre la conduite, les échanges TCP, la séparation des rôles,
SQLite et le contenu des paquets. Le binôme a également mené des essais sur
deux VM accessibles via SSH. La recette complète des paquets livrés sous
Debian 13 reste à confirmer avec la procédure du guide.

## Données et statistiques

Chaque onglet affiche ses passages, ses urgences et son temps d'attente total.
Les compteurs sont remis à zéro au redémarrage. SQLite conserve les passages
terminés : type de véhicule, direction et temps d'attente.

- Depuis les sources : `server/data/carrefour.sqlite3` par défaut.
- Avec le paquet serveur : `~/.local/share/sae302/carrefour.sqlite3`, sauf
  configuration de `XDG_DATA_HOME` ou `SAE302_DB_PATH`.

## Documentation

- [Bilan du projet](Bilan_Projet.pdf)
- [Annexe IA-graphie](IAGraphie.pdf)
- [Installation sur deux VM Debian 13](doc/Installation.md)
- [Documentation technique et diagrammes UML](doc/Documentation_Technique.md)
- [Commandes et modules clients](client/README.md)
- [Serveur et protocole TCP](server/README.md)
- [Planning prévisionnel](doc/Diagramme_Gantt.md)
- [Contraintes de bibliothèques du sujet](Stack_Technique.md)

Licence : [Apache 2.0](LICENSE).
