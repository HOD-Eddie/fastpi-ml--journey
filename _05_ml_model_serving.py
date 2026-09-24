# in this chapter, I'm exploring how FastAPI can be applied in ML model serving, and model loading.
# the goal is simple
# 1. Understand the concept of lifespan
# 2. Understand when to use async and when not to
# 

from fastapi import FastAPI
from contextlib import asynccontextmanager
class Payload:
    pass

def load_2gb_model():
    pass


app = FastAPI()

# this is a bad programming pattern
@app.post("/predict")
def predict(data: Payload):
    model = load_2gb_model() # <= this fuction loads the model, and stores in 
                                # the variable. This is done every time, for each request
                                # making it inefficient

    return model.predict(data)


# we must instead utilize the lifespan approach, that comes withe 
# async context manager.
ml_model = {}
@asynccontextmanager
async def lifespan(app: FastAPI):
    ml_model["resnet"] = load_2gb_model() # <= same function gets loaded here

    yield # all instructions before and after yield, are done only  once

    ml_model.clear() # <= very critical, since it let's clean up the memory


@app.post("/predict")
def predict(data: Payload):
    model = ml_model["resnet"]
    return model.predict(data)

# if we need our endpoint to take care other task outside of the server response or cliet request,
# then it is important these micro taks are done in the background. This prevents the client from
# waiting for response irrelevant to them. To do this, we use the BackgroundTask module

# example, I want to log or write my response to a file, for audit
from fastapi import BackgroundTasks # allows us to configure background operations that are important
                                    # but must not make the client wait to get them.
@app.post("/predict")
def predict(data: Payload, background_tasks: BackgroundTasks):
    model = ml_model["resnet"] # <= reuse of the once loaded model

    # background_tasks.add_task(log_to_db, data, result) <= this is the line.

    return model.predict(data) # before I return this, I also wanna do some micro taks.



from pydantic import BaseModel

class Payload(BaseModel):
    text: str


models = {}
@asynccontextmanager
async def lifespan(inst: FastAPI):
    models["sentiment"] = load_sentiment_model()
    yield
    models.clear()


inst = FastAPI(lifespan=lifespan)
@inst.post("/analyze")
def analyze(data: Payload, background_work: BackgroundTasks):
    model = models["sentiment"]
    result = model.predict(data.text)
    background_work.add_task(log_to_db, data.text, result)

    return result


@inst.get("/health")
async def get_health():
    return {"status": "ok"}