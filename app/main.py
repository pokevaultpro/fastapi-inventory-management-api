from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.database import engine, Base
from app.routers import (auth, products, favorites, supermarkets, recipes, recipe_items,
                         cart, users, shopping_history, flyer_catalog)
from dotenv import load_dotenv
load_dotenv()

from fastapi import Request
from fastapi.responses import JSONResponse



app = FastAPI()

STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    import traceback
    print(traceback.format_exc())  # stampa completa in console
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},  # restituisce il messaggio al client
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "null"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(favorites.router)
app.include_router(supermarkets.router)
app.include_router(recipes.router)
app.include_router(recipe_items.router)
app.include_router(cart.router)
app.include_router(users.router)
app.include_router(shopping_history.router)
app.include_router(flyer_catalog.router)