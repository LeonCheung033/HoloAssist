from typing import Any


class Session:
    def __init__(self) -> None:
        self._opened = True

    async def close(self) -> None:
        self._opened = False


async def get_session() -> Session:
    # TODO: replace with async engine / sessionmaker using Settings.database.dsn
    return Session()