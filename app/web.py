"""Entrypoint web: coincide con el target port 8000 del dominio Railway."""

import uvicorn

HOST = "0.0.0.0"
PORT = 8000


def main():
    # El puerto es deliberadamente fijo: PORT del panel no cambia el target 8000.
    uvicorn.run("app.main:app", host=HOST, port=PORT)


if __name__ == "__main__":
    main()
