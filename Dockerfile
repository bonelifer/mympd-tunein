FROM python:3.11-slim-bookworm

WORKDIR /app
COPY bridge.py .
COPY vendor/ vendor/
USER 65534:65534
EXPOSE 18766
ENTRYPOINT ["python", "-u", "bridge.py", "--config", "/config/tunein.cfg"]
CMD ["--listen", "0.0.0.0"]
