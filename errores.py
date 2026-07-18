from datetime import datetime, timezone

INSTANCE = "/v1/estadisticas/ventas"


def _timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def error_response(status_code, detail, method):
    if status_code >= 500:
        title, codigo, etiqueta = "Internal Server Error", "IE", "Error Interno"
    else:
        title, codigo, etiqueta = "Bad Request", "VF", "Validación Fallida"
    return {
        "detail": str(detail),
        "instance": INSTANCE,
        "status": status_code,
        "title": title,
        "type": f"https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/{status_code}",
        "timestamp": _timestamp(),
        "errorCode": codigo,
        "errorLabel": etiqueta,
        "method": method,
    }


def error_400(detail, method):
    return error_response(400, detail, method)


def error_500(detail, method):
    return error_response(500, detail, method)