FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# openssh-client powers the Terminal tab. The TUI itself only talks to the
# backend HTTP API.
RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /usr/sbin/nologin tui \
    && install -d -m 700 -o tui -g tui /home/tui/.ssh

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scp_tui ./scp_tui

USER tui
CMD ["python", "-m", "scp_tui"]
