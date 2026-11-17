from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.campaigns import router
from app.keitaro.client import KeitaroError
from app.services.errors import ServiceError

app = FastAPI(title="Keitaro wrapper")
app.include_router(router)

FIELD_LABELS = {
    "name": "Название",
    "geo": "Гео",
    "offer_ids": "Офферы",
    "offer_id": "Оффер",
    "share": "Вес",
}


@app.exception_handler(ServiceError)
def service_error(_: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=exc.status_code)


@app.exception_handler(KeitaroError)
def keitaro_error(_: Request, exc: KeitaroError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=502)


@app.exception_handler(RequestValidationError)
def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Ошибки валидации запроса — одной понятной строкой, а не списком pydantic."""
    messages = []
    for error in exc.errors():
        if error["type"] == "value_error":
            # Текст из наших валидаторов в schemas.py уже написан для пользователя.
            messages.append(str(error["ctx"]["error"]))
            continue
        field = error["loc"][-1] if error["loc"] else ""
        label = FIELD_LABELS.get(str(field), str(field) or "Запрос")
        problem = "обязательное поле" if error["type"] == "missing" else "некорректное значение"
        messages.append(f"{label}: {problem}")
    return JSONResponse({"detail": "; ".join(messages)}, status_code=422)
