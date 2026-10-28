import uvicorn

from .config import settings


def main() -> None:
    uvicorn.run("agentic_web_search.api.main:app", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
