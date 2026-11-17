FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[api]"
ENV CODEVERSE_PROVIDER=deterministic
EXPOSE 8000
CMD ["uvicorn", "codeverse.api:app", "--host", "0.0.0.0", "--port", "8000"]
