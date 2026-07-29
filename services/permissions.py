# services/permissions.py
from fastapi import Depends, HTTPException, status

from models import Usuario
from services.auth_service import obtener_usuario_actual

# Roles válidos del sistema (ver README: admin, medico, enfermero, visor).
ROLES_VALIDOS = ["admin", "medico", "enfermero", "visor"]


def requiere_rol(*roles_permitidos: str):
    """Dependencia FastAPI que exige sesión iniciada Y que el rol del usuario
    esté entre los permitidos. Uso: Depends(requiere_rol("admin", "medico")).
    """

    def _verificar(usuario: Usuario = Depends(obtener_usuario_actual)) -> Usuario:
        if usuario.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenés permisos para realizar esta acción",
            )
        return usuario

    return _verificar
