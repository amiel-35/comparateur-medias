# Cadrages : une image, deux services du compose (« fabrique » et « guichet », voir docker-compose.yml). Lancée seule,
# sans commande, elle fait les deux dans un processus, comme avant la phase 2.
FROM python:3.13-slim

# curl : lecture des flux RSS et contrôle de santé. tzdata : les éditions sont datées en heure de Paris.
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

# Seule dépendance : le SDK Anthropic, pour le mode « api » de la fabrique.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY comparateur /app/comparateur
WORKDIR /app

# Utilisateur sans privilège ; /data est le volume persistant (base, cache, site généré).
RUN useradd --system --uid 10001 --home /app comparateur && mkdir -p /data && chown comparateur /data
USER comparateur
VOLUME /data

ENV COMPARATEUR_DONNEES=/data \
    COMPARATEUR_LLM=api \
    COMPARATEUR_DERRIERE_PROXY=1 \
    PORT=8080 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8080/sante || exit 1

# Au démarrage : crée la base et charge les médias si besoin, réécrit le site depuis les éditions gardées, puis sert.
CMD ["sh", "-c", "python -m comparateur init && python -m comparateur pages && exec python -m comparateur servir"]
