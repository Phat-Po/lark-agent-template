FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bake the git commit hash into the image for stale-code detection
ARG GIT_COMMIT=unknown
RUN echo "$GIT_COMMIT" > .git-commit && \
    mkdir -p data && chmod +x entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
