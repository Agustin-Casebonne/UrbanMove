"""Configuración común de los tests de identity.

main.py exige JWT_SECRET (no hay valor por defecto). Se define aquí un valor
solo para tests, para que no dependan de la máquina ni del CI.
"""

import os

os.environ.setdefault("JWT_SECRET", "secreto-solo-para-tests")
