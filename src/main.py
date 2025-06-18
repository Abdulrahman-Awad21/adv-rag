from fastapi import FastAPI
from utils.metrics import setup_metrics
from config.lifespan import lifespan
from routes import base, data, nlp
from routes.project import project_router
from routes.vision import vision_router

# Initialize the FastAPI app with the lifespan manager
app = FastAPI(lifespan=lifespan)

# Setup Prometheus metrics
setup_metrics(app)

# Include all the application routers
app.include_router(base.base_router)
app.include_router(project_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)
app.include_router(vision_router)