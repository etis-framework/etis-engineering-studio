FROM python:3.14-slim@sha256:ce40764625a4ff50df3548277632e7f96c4e77fe75fa848aae9885476e7df5a4
WORKDIR /app
COPY apps/api/requirements.txt /app/requirements.txt
COPY apps/api/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir --require-hashes -r /app/requirements.lock
COPY apps/api /app/apps/api
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
RUN groupadd --system etis \
    && useradd --system --gid etis --home-dir /app --shell /usr/sbin/nologin etis \
    && chown -R etis:etis /app

USER etis

EXPOSE 8000
CMD ["uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
