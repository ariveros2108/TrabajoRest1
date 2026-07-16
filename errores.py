from datetime import datetime, timezone

INSTANCE = "/v1/estadisticas/ventas"


def _timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def error_400(detail, method):
    return {
        "detail": detail,
        "instance": INSTANCE,
        "status": 400,
        "title": "Bad Request",
        "type": "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/400",
        "timestamp": _timestamp(),
        "errorCode": "VF",
        "errorLabel": "Validación Fallida",
        "method": method,
    }


def error_500(detail, method):
    return {
        "detail": detail,
        "instance": INSTANCE,
        "status": 500,
        "title": "Internal Server Error",
        "type": "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/500",
        "timestamp": _timestamp(),
        "errorCode": "IE",
        "errorLabel": "Error Interno",
        "method": method,
    }
