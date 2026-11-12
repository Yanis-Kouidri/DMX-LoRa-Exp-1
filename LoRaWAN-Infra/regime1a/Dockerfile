# Traitement du régime 1a (traitement.py). Le code n'est pas copié dans l'image :
# il est lu dans le dépôt monté en lecture seule sur /repo, si bien qu'un
# git pull suffit à le mettre à jour (voir ../README.md).
FROM python:3.12.15-alpine

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

CMD ["python", "-u", "/repo/LoRaWAN-Infra/regime1a/traitement.py"]
