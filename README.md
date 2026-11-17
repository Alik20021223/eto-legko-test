# Keitaro wrapper

Обёртка над трекером Keitaro: создаёт кампании по шаблону и управляет офферами
и их весами в потоке. Бэкенд — FastAPI + SQLAlchemy + Alembic, фронт — React (Vite).

## Как это работает

Кампания создаётся в Keitaro с доменом `kylovoa.com`, группой `FORTESTS`,
источником `FORTESTS` и двумя потоками:

1. фильтр страны (`country`, `accept`, гео кампании) → редирект на `https://google.com`;
2. остальной трафик → офферы с весами.

Домен, группа, источник и адрес редиректа задаются в `.env`
(`CAMPAIGN_DOMAIN`, `CAMPAIGN_GROUP`, `CAMPAIGN_TRAFFIC_SOURCE`, `FALLBACK_URL`).

Состав офферов редактируется локально как черновик и уходит в Keitaro только по push:

| Действие | Что делает |
| --- | --- |
| fetch | заменяет черновик состоянием потока в Keitaro и обновляет список потоков; оффер, которого в потоке Keitaro больше нет, остаётся убранным, и его можно вернуть; веса остальных не пересчитываются |
| add / remove / bring back | добавляет, убирает, возвращает оффер в черновике |
| pin / unpin | закрепляет вес оффера (без `share` — текущий): пересчёт его не трогает |
| пересчёт весов | остаток до 100% делит поровну между незакреплёнными |
| push | отправляет в Keitaro активные офферы, перечитывает поток и сверяет, что сохранилось |
| cancel | откатывает черновик к последнему fetch/push |

Веса — целые проценты, у активных офферов в сумме ровно 100: если это не так,
интерфейс показывает предупреждение, а push отказывает. Убранный оффер после push
исчезает из потока Keitaro и остаётся только в локальной базе (серый, 0%),
поэтому его можно вернуть.

Справочник гео для формы создания — `GET /api/geos` (коды ISO 3166-1 alpha-2;
в Admin API Keitaro списка стран нет, он лежит в `app/geo.py`).

## Структура бэкенда

- `app/keitaro/client.py`, `types.py` — единственное место, которое знает Keitaro API;
- `app/services/creator.py` — создание кампании и потоков;
- `app/services/editor.py` — правки черновика;
- `app/services/sync.py` — fetch и push;
- `app/services/weights.py` — пересчёт весов (чистые функции);
- `tests/fake_keitaro.py` — Keitaro в памяти на уровне HTTP.

## Запуск

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate   # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                              # вписать KEITARO_API_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, /api проксируется на :8000
```

## Проверки

```bash
cd backend && pytest
cd frontend && npm run build
```
