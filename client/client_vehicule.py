"""Transport TCP des clients ; chaque client calcule integralement sa voiture."""

from dataclasses import asdict
from functools import lru_cache
import json
import socket
import time

if __package__:
    from .config import HOST, PORT, LIGNE_ARRET, PAS_AVANCEMENT, PAS_SIMULATION
    from .conduite import ConduiteVehicule, Perception, proposer_arrivee
else:
    from config import HOST, PORT, LIGNE_ARRET, PAS_AVANCEMENT, PAS_SIMULATION
    from conduite import ConduiteVehicule, Perception, proposer_arrivee


def _get_parametres_simulation():
    """Les reglages de conduite appartiennent au client."""
    return LIGNE_ARRET, PAS_AVANCEMENT, PAS_SIMULATION


def get_ligne_arret():
    """Renvoie la progression correspondant à la ligne d'arrêt."""
    return _get_parametres_simulation()[0]


def get_pas_avancement():
    """Renvoie le nombre de points proposés à chaque pas de conduite."""
    return _get_parametres_simulation()[1]


def get_pas_simulation():
    """Renvoie le délai en secondes entre deux publications acceptées."""
    return _get_parametres_simulation()[2]


def prochaine_position(position, feu, pas_avancement=PAS_AVANCEMENT, ligne_arret=LIGNE_ARRET):
    """Calcule un pas borné par la ligne d'arrêt au rouge et par la sortie."""
    if feu != 'VERT' and position <= ligne_arret:
        return min(position + pas_avancement, ligne_arret)
    return min(position + pas_avancement, 100)


def echanger(client, lecteur, message):
    """Envoie une commande UTF-8 et décompose la réponse du serveur.

    Lève une erreur si le serveur ferme la connexion ou répond ERREUR.
    """
    client.sendall((message + '\n').encode('utf-8'))
    reponse = lecteur.readline()
    if not reponse:
        raise ConnectionError('Le carrefour a ferme la connexion.')
    morceaux = reponse.strip().split('|', 1)
    if morceaux[0] == 'ERREUR':
        raise ValueError(morceaux[1] if len(morceaux) > 1 else 'Erreur du serveur')
    return morceaux


def selectionner(client, lecteur, carrefour):
    """Sélectionne le carrefour avant l'inscription, la croix étant le choix par défaut."""
    if carrefour != 'CROIX' and echanger(client, lecteur, f'CARREFOUR|{carrefour}') != ['OK']:
        raise ValueError('Impossible de selectionner le carrefour')


@lru_cache(maxsize=2)
def get_trajets(carrefour='CROIX'):
    """Récupère et mémorise les manœuvres autorisées pour chaque entrée du carrefour."""
    with socket.create_connection((HOST, PORT), timeout=10) as client:
        with client.makefile('r', encoding='utf-8') as lecteur:
            selectionner(client, lecteur, carrefour)
            reponse = echanger(client, lecteur, 'GET_TRAJETS')
            if reponse[0] != 'TRAJETS':
                raise ValueError('Reponse GET_TRAJETS invalide')
            return json.loads(reponse[1])


def recevoir_instantane(client, lecteur):
    """Demande au serveur l'état courant du carrefour et décode le JSON."""
    reponse = echanger(client, lecteur, 'INSTANTANE')
    if reponse[0] != 'INSTANTANE':
        raise ValueError('Instantane invalide')
    return json.loads(reponse[1])


def publier(client, lecteur, commande, vehicule, revision):
    """Envoie un rapport complet de véhicule avec la révision utilisée pour son calcul."""
    paquet = {'revision': revision, 'vehicule': asdict(vehicule)}
    return echanger(client, lecteur, commande + '|' + json.dumps(paquet))


def simuler_vehicule(nom, type_vehicule, direction, manoeuvre, carrefour='CROIX'):
    """Inscrit un véhicule, publie chacun de ses pas et signale sa sortie.

    Recalcule le mouvement si le serveur signale une révision périmée.
    """
    try:
        delai = get_pas_simulation()
        with socket.create_connection((HOST, PORT), timeout=10) as client:
            with client.makefile('r', encoding='utf-8') as lecteur:
                selectionner(client, lecteur, carrefour)
                while True:
                    instantane = recevoir_instantane(client, lecteur)
                    vehicule = proposer_arrivee(nom, type_vehicule, direction, manoeuvre, instantane)
                    # La place proposée reste valable tant que la révision est inchangée.
                    reponse = publier(client, lecteur, 'IDENTITE', vehicule, instantane['revision'])
                    if reponse == ['OK']:
                        break
                    if reponse != ['REESSAYER']:
                        raise ValueError('Inscription refusee')
                print(f'{nom} arrive par {direction} ({manoeuvre.lower()}).')
                if type_vehicule == 'urgence':
                    if echanger(client, lecteur, 'URGENCE') != ['PASSAGE_AUTORISE']:
                        raise ValueError('Priorite non accordee')
                    print(f'{nom} a la priorite.')
                while vehicule.progression < 100:
                    instantane = recevoir_instantane(client, lecteur)
                    perception = Perception(instantane)
                    vehicule = perception.vehicules[nom]
                    proposition, attente = ConduiteVehicule(perception).calculer(vehicule)
                    reponse = publier(client, lecteur, 'POSITION', proposition, instantane['revision'])
                    if reponse == ['REESSAYER']:
                        # Une autre voiture ou un feu a change : relire et recalculer.
                        time.sleep(0.001)
                        continue
                    if reponse != ['OK']:
                        raise ValueError('Publication refusee')
                    vehicule = proposition
                    if attente:
                        print(f'{nom} attend a {vehicule.progression} %.')
                    else:
                        print(f'{nom} : progression {max(0, vehicule.progression)} %')
                    time.sleep(delai)
                if echanger(client, lecteur, 'TERMINE') != ['OK']:
                    raise ValueError('Passage non enregistre')
                print(f'{nom} a traverse le carrefour.')
    except (OSError, KeyError, IndexError, ValueError, ConnectionError) as erreur:
        print(f'{nom} : {erreur}')
