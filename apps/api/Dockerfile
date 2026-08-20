FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a
WORKDIR /app
COPY apps/api/requirements.txt /app/requirements.txt
COPY apps/api/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir --require-hashes -r /app/requirements.lock
COPY apps/api /app/apps/api
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
COPY course-model /app/course-model

RUN test -f /app/course-model/course.json \
    && test -f /app/course-model/phases.json \
    && test -f /app/course-model/rubrics.json \
    && test -f /app/course-model/starter_baseline.json
RUN groupadd --system etis \
    && useradd --system --gid etis --home-dir /app --shell /usr/sbin/nologin etis \
    && chown -R etis:etis /app

USER etis

EXPOSE 8000
CMD ["uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
