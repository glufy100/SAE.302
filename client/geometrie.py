"""Geometrie 2D en Python standard : aucune dependance graphique sur les clients."""

from dataclasses import dataclass
from math import cos, sin, radians


@dataclass(frozen=True)
class Point:
    """Représente un point ou un vecteur immuable en deux dimensions."""
    _x: float
    _y: float

    def x(self):
        """Renvoie l'abscisse."""
        return self._x

    def y(self):
        """Renvoie l'ordonnée."""
        return self._y

    def __add__(self, autre):
        """Additionne les coordonnées des deux points."""
        return Point(self._x + autre._x, self._y + autre._y)

    def __sub__(self, autre):
        """Soustrait les coordonnées de l'autre point."""
        return Point(self._x - autre._x, self._y - autre._y)

    def __mul__(self, nombre):
        """Multiplie les deux coordonnées par un scalaire."""
        return Point(self._x * nombre, self._y * nombre)

    def manhattanLength(self):
        """Renvoie la somme des valeurs absolues des deux coordonnées."""
        return abs(self._x) + abs(self._y)


class Courbe:
    """Courbe de Bezier cubique utilisee pour les virages d'origine."""

    def __init__(self, debut):
        """Fixe le point de départ de la courbe."""
        self.debut = debut

    def cubicTo(self, premier, second, fin):
        """Définit les deux points de contrôle et le point final de la courbe."""
        self.premier, self.second, self.fin = premier, second, fin

    def pointAtPercent(self, t):
        """Évalue la courbe au paramètre t compris entre 0 et 1."""
        return (self.debut * ((1-t)**3) + self.premier * (3*(1-t)**2*t)
                + self.second * (3*(1-t)*t*t) + self.fin * (t**3))


class Rectangle:
    """Rectangle oriente et axes servant au test de separation des contours."""

    def __init__(self, centre, angle, longueur, largeur):
        """Calcule les axes et les bornes du rectangle orienté selon un angle en degrés."""
        self.cx, self.cy = centre.x(), centre.y()
        self.hx, self.hy = longueur / 2, largeur / 2
        c, s = cos(radians(angle)), sin(radians(angle))
        self.axes = ((c, s), (-s, c))
        ex, ey = self.hx * abs(c) + self.hy * abs(s), self.hx * abs(s) + self.hy * abs(c)
        self.bornes = (self.cx-ex, self.cy-ey, self.cx+ex, self.cy+ey)

    def intersects(self, autre):
        """Détecte un recouvrement de deux rectangles orientés par les axes séparateurs."""
        # Écarte les rectangles éloignés avant de projeter leurs côtés sur les axes.
        if not bornes_communes(self.bornes, autre.bornes):
            return False
        dx, dy = autre.cx-self.cx, autre.cy-self.cy
        for ax, ay in self.axes + autre.axes:
            rayon = sum(h * abs(x*ax+y*ay) for h, (x, y) in zip((self.hx, self.hy), self.axes))
            rayon += sum(h * abs(x*ax+y*ay) for h, (x, y) in zip((autre.hx, autre.hy), autre.axes))
            if abs(dx*ax+dy*ay) >= rayon - 1e-8:
                return False
        return True


def bornes_communes(a, b):
    """Vérifie le recouvrement strict de deux boîtes alignées sur les axes."""
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


class Contour:
    """Ensemble de rectangles, pour une voiture ou l'enveloppe de son trajet."""

    def __init__(self, rectangles=()):
        """Fige les rectangles et calcule leur boîte englobante commune."""
        self.rectangles = tuple(rectangles)
        self.bornes = (min(r.bornes[0] for r in self.rectangles),
                       min(r.bornes[1] for r in self.rectangles),
                       max(r.bornes[2] for r in self.rectangles),
                       max(r.bornes[3] for r in self.rectangles)) if self.rectangles else None

    def united(self, autre):
        """Construit un contour rassemblant les rectangles des deux contours."""
        return Contour(self.rectangles + autre.rectangles)

    def intersects(self, autre):
        """Cherche une paire de rectangles qui se recouvrent entre les deux contours."""
        if self.bornes is None or autre.bornes is None or not bornes_communes(self.bornes, autre.bornes):
            return False
        return any(a.intersects(b) for a in self.rectangles for b in autre.rectangles)
