# ---- builder stage: has pip, build tools, everything needed to install packages ----
FROM python:3.12-slim AS builder

WORKDIR /app
COPY pyproject.toml .
COPY app ./app

RUN pip install --no-cache-dir --prefix=/install .

# ---- runtime stage: only what's needed to actually RUN the app ----
FROM python:3.12-slim

WORKDIR /app

# Copy only the installed packages from the builder stage — none of pip's
# build cache, no compilers, nothing that was only needed to install
# things. This is what keeps the final image small.
COPY --from=builder /install /usr/local

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
