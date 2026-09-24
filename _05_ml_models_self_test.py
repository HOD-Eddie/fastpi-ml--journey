# build an ml loading and serving endpdoint,
# ensure model is loaded once and kept catched efficiently, and does not require to run on the event loop.
# loading a generative model of about 3GB

from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI

from _03_schemas import Product

def log_to_file(text: str, result):
    pass

def load_model():
    pass

models = {}
@asynccontextmanager
async def efficient_loading(app: FastAPI):
    models["generative"] = load_model()
    yield
    models.clear()


app = FastAPI(lifespan=efficient_loading)

@app.post("/predict")
def predict(input: Product, background_task: BackgroundTasks):
    model = models["generative"]
    result = model.predict(input.description)
    background_task.add_task(log_to_file, input.description, result)
    return result