# Studentt API

A small service that accepts task requests and processes code via an AI pipeline. Deployed on Hugging Face Spaces.

## Features
- Accepts structured task requests
- Processes instructions and returns generated output
- Simple JSON API for easy integration

## Endpoints
- `POST /handle_task` — Accepts task details and returns processed results.

Example request payload:
```json
{
    "round": 1,
    "instruction": "Generate a web app"
}
```

Example curl:
```bash
curl -X POST "https://<your-space>.hf.space/handle_task" \
    -H "Content-Type: application/json" \
    -d '{"round": 1, "instruction": "Generate a web app"}'
```

Example response (200 OK):
```json
{
    "round": 1,
    "status": "success",
    "result": "Generated project files and instructions..."
}
```

## Deployment
This service is intended to run on Hugging Face Spaces. Configure your space to expose the `/handle_task` endpoint and wire the AI processing pipeline as needed.

## Contributing
- Open issues and PRs for fixes or improvements.
- Keep changes small and focused.

## License
MIT License — see LICENSE file for details.