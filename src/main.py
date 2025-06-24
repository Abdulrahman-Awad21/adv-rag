from fastapi import FastAPI
from utils.metrics import setup_metrics
from config.lifespan import lifespan
from routes import base, data, nlp, auth
from routes.project import project_router
from routes.vision import vision_router
from routes.admin import admin_router
from routes.user import user_router # Add user router import

# Initialize the FastAPI app with the lifespan manager
app = FastAPI(lifespan=lifespan)

# Setup Prometheus metrics
setup_metrics(app)

# Include all the application routers
app.include_router(auth.auth_router)
app.include_router(base.base_router)
app.include_router(project_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)
app.include_router(vision_router)
app.include_router(admin_router)
app.include_router(user_router) # Add user router