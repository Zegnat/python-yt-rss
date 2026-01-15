FROM python:3.11-slim-bookworm AS builder
COPY requirements.txt requirements.txt
RUN pip install --user --no-cache-dir -r requirements.txt gunicorn
COPY app.py /app/
COPY static/ /app/static/
COPY templates/ /app/templates/

FROM gcr.io/distroless/python3-debian12
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app /app
WORKDIR /app
ENV PYTHONPATH=/root/.local/lib/python3.11/site-packages
EXPOSE 5000
CMD ["/root/.local/bin/gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
