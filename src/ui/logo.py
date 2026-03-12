"""
Logo ETP (EPP Tester Platform) — généré via QPainter.

Crée le logo programmatiquement : pas de dépendance fichier image,
fonctionne en mode développement et dans le binaire compilé.
"""

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QColor, QFont, QIcon, QLinearGradient, QPainter, QPen, QPixmap,
)


def create_etp_pixmap(size: int = 64) -> QPixmap:
    """Crée le logo ETP comme QPixmap.

    Args:
        size: taille en pixels (carré)

    Returns:
        QPixmap avec fond transparent
    """
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)

    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # --- Fond dégradé bleu arrondi ---
    grad = QLinearGradient(QPointF(0, 0), QPointF(0, size))
    grad.setColorAt(0.0, QColor("#1976d2"))
    grad.setColorAt(1.0, QColor("#0d47a1"))
    p.setBrush(grad)
    border_w = max(1, size // 32)
    p.setPen(QPen(QColor("#42a5f5"), border_w))
    radius = size // 6
    p.drawRoundedRect(QRectF(2, 2, size - 4, size - 4), radius, radius)

    # --- Réseau (3 nœuds + lignes) ---
    n_y_top = size * 0.22
    n_y_mid = size * 0.42
    nodes = [
        QPointF(size * 0.24, n_y_top),
        QPointF(size * 0.76, n_y_top),
        QPointF(size * 0.50, n_y_mid),
    ]
    p.setPen(QPen(QColor("#90caf9"), max(1.0, size / 42)))
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            p.drawLine(nodes[i], nodes[j])
    p.setBrush(QColor("#bbdefb"))
    p.setPen(Qt.PenStyle.NoPen)
    dot_r = max(2.0, size / 20.0)
    for n in nodes:
        p.drawEllipse(n, dot_r, dot_r)

    # --- Texte "EPP" ---
    font_main = QFont("Arial", max(int(size * 0.22), 8), QFont.Weight.Bold)
    p.setFont(font_main)
    p.setPen(QColor("white"))
    p.drawText(QRectF(0, size * 0.44, size, size * 0.28),
               Qt.AlignmentFlag.AlignCenter, "EPP")

    # --- Texte "TESTER" ---
    font_sub = QFont("Arial", max(int(size * 0.10), 6))
    p.setFont(font_sub)
    p.setPen(QColor("#90caf9"))
    p.drawText(QRectF(0, size * 0.72, size, size * 0.18),
               Qt.AlignmentFlag.AlignCenter, "TESTER")

    p.end()
    return px


def create_etp_icon(size: int = 32) -> QIcon:
    """Crée le logo ETP comme QIcon (pour la barre de titre)."""
    return QIcon(create_etp_pixmap(size))
