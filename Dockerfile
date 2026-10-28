FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && python -m playwright install --with-deps chromium
COPY src/ src/
COPY evals/ evals/
ENV PYTHONPATH=/app/src PORT=8000
EXPOSE 8000
CMD ["uvicorn", "agentic_web_search.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
