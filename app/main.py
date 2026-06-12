import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.database import engine, Base
from app.routers import (auth, products, favorites, supermarkets, recipes, recipe_items,
                         cart, users, shopping_history, flyer_catalog, profile, recipe_smart, admin, profile_role)
from dotenv import load_dotenv
load_dotenv()

from fastapi import Request
from fastapi.responses import JSONResponse



app = FastAPI(
    title='Inventory Management API',
    description='FastAPI backend for grocery, supermarket, cart, recipe, favorites, and shopping-history workflows.',
    version='1.0.0',
)

@app.get('/', tags=['health'])
async def root():
    return {'message': 'Inventory Management API', 'docs': '/docs'}

@app.get('/health', tags=['health'])
async def health_check():
    return {'status': 'ok'}

STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    import traceback
    print(traceback.format_exc())  # stampa completa in console
    detail = str(exc) if os.getenv('DEBUG_ERRORS') == '1' else 'Internal server error'
    return JSONResponse(
        status_code=500,
        content={'detail': detail},
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
app.include_router(profile.router)
app.include_router(recipe_smart.router)
app.include_router(admin.router)
app.include_router(profile_role.router)