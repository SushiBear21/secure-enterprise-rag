ARG BASE_IMAGE=python:3.13-slim
FROM ${BASE_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 EDGE_STATE=/state
WORKDIR /app
COPY app/authorization.py /app/authorization.py
COPY edge_lab/service.py /app/service.py
USER 10001:10001
EXPOSE 8080
CMD ["python","/app/service.py"]
