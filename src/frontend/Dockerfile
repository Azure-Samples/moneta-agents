FROM python:3.12-slim

# V1
FROM python:3.12-slim

LABEL version="0.1"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN groupadd -g 1001 app && \
    useradd -u 1001 -g app -m app

COPY requirements.txt /home/app
COPY app.py /home/app
COPY config.py /home/app
COPY resources /home/app/resources

WORKDIR /home/app
RUN python -m pip install -r requirements.txt

RUN chown -R app:app /home/app

EXPOSE 8501

USER app
WORKDIR /home/app
ENTRYPOINT ["streamlit", "run", "/home/app/app.py", "--server.port=8000", "--server.address=0.0.0.0", "--server.enableXsrfProtection", "false"]