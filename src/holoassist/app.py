from fastapi import FastAPI

from holoassist.core.middleware import setup_middlewares

app = FastAPI(title="holoassist")
setup_middlewares(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
