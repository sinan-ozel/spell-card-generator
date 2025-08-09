[![Release & Nightly](https://github.com/sinan-ozel/spell-card-generator/actions/workflows/release-and-nightly.yaml/badge.svg)](https://github.com/sinan-ozel/spell-card-generator/actions/workflows/release-and-nightly.yaml)
[![Docker Pulls](https://img.shields.io/docker/pulls/sinan-ozel/spell-card-generator)](https://hub.docker.com/r/sinan-ozel/spell-card-generator)
[![Docker Image Size](https://img.shields.io/docker/image-size/sinan-ozel/spell-card-generator/latest)](https://hub.docker.com/r/sinan-ozel/spell-card-generator)



# Spell Card Generator

A FastAPI-based API for generating Dungeons & Dragons spell cards as images.
Supports multiple card formatters and asynchronous card generation with optional callback notifications.

---

## Features

- Generate spell cards via a REST API
- Multiple card formatters (easily extensible)
- Asynchronous card creation with optional callback URL
- Dockerized for easy deployment and testing
- Automated linting and CI/CD workflows
- Local use with `docker` as the only requirement

---

## Quick Start

### 1. **Clone the repository**

```bash
git clone https://github.com/YOUR_USERNAME/spell-card-generator.git
cd spell-card-generator
```

### 2. **Build and run with Docker Compose**

```bash
docker compose -f tests/docker-compose.yaml --project-directory tests up --build
```

### 3. **API Usage Example**

#### **POST /v1/generate**

Request:
```json
{
  "spell_data": {
    "title": "Acid Splash",
    "casting_time": "1 action",
    "spell_range": "60 feet",
    "components": "V, S",
    "duration": "Instantaneous",
    "description": "You hurl a bubble of acid...",
    "school": "Conjuration",
    "level": 0
  },
  "callback_url": "http://your-callback-server/callback"  // optional
}
```

Response:
```json
{
  "status": "queued",
  "title": "Acid Splash"
}
```

#### **Callback Example**

If `callback_url` is provided, a POST request will be sent to it when the card is ready:

```json
{
  "status": "ready",
  "title": "Acid Splash",
  "level": 0,
  "filename": "L0.Acid-Splash.jpg",
  "url": "/cards/plain/L0.Acid-Splash.jpg"
}
```

### 4. **Get available generators**

#### **GET /v1/generators**

Response:
```json
{
  "plain": "available"
}
```

---

## API Documentation

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- OpenAPI JSON: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## Development

### **Linting and Formatting**

Run all linters and formatters in a container:

```bash
docker run --rm -v "$PWD":/workspace -w /workspace python:3.11-slim bash autolint.sh
```

### **Running Tests**

```bash
docker compose -f tests/docker-compose.yaml --project-directory tests up --build --abort-on-container-exit --exit-code-from test
```

---

## Extending Formatters

Add new card formatters in `src/formatters/` and update the API to use them as needed.

---

## License

MIT License

---

## Contributing

Pull requests are welcome! Please