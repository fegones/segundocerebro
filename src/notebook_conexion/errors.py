"""Errores públicos sin volcar credenciales, cuerpos HTTP ni secretos."""


class BridgeError(Exception):
    """Error controlado; su texto se puede presentar al operador."""


class ConfigurationError(BridgeError):
    """Configuración o identidad incompleta."""


class PermissionDenied(BridgeError):
    """Operación prohibida por política local."""


class RemoteServiceError(BridgeError):
    """Fallo HTTP expresado sin el cuerpo remoto, que puede contener PII."""


class SecurityError(BridgeError):
    """Validación de seguridad fallida."""
