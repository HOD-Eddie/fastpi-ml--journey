import asyncio
import logging
import os
from contextlib import asynccontextmanager

try:
    import torch
except ModuleNotFoundError:  # pragma: no cover - optional dependency for model runtime
    torch = None

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("uvicorn")

def load_model():
    pass

class Payload(BaseModel):
    text: str


def log_to_queue(text: str, result: str):
    logger.info("Prediction queued: %s -> %s", text, result)
 
# What changed and why:

# Config via environment variables, not hardcoded paths — different behavior per environment (dev/staging/prod) without code changes.
# Fail fast: if the model can't load, the process should crash on startup, not silently limp along and 500 on every request.
# Warm-up inference: many frameworks lazily compile kernels (CUDA, torch.compile, XLA) on first call — you want that latency spike 
# to happen before traffic arrives, not on your first real user.
models = {}
@asynccontextmanager
async def lifespan(app: FastAPI):
    device = os.getenv("MODEL_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
    try:
        model = load_model(path=os.getenv("MODEL_PATH"), device=device)
        model.eval()
        # Warm-up: run one dummy inference so CUDA kernels/JIT compile now,
        # not on the first real customer request
        with torch.no_grad():
            model.predict("warmup")
        models["generative"] = model
        app.state.ready = True  # readiness flag
        logger.info(f"Model loaded on {device}")
    except Exception:
        logger.exception("Model failed to load — refusing to start")
        raise  # crash the process; don't serve traffic with no model

    yield
    models.clear()
    if device == "cuda":
        torch.cuda.empty_cache()



# A /health vs a /ready distinction — this matters enough to call out separately:
app = FastAPI(lifespan=lifespan)
@app.get("/health")
async def health():
    return {"status": "alive"}  # is the process running at all?

@app.get("/ready")
async def ready():
    return {"ready": getattr(app.state, "ready", False)}  # is it safe to send traffic?


# Sync/async → concurrency limits and the multi-worker trap
# Two things bite people who only know the lesson-2 version:
# a) A 3GB+ model doesn't have unlimited room to run in parallel threads. '
# 'Even though def offloads to the thread pool, if 40 threads all try to run inference on the same GPU simultaneously, '
# 'you'll blow out GPU memory. Production code usually adds an explicit concurrency limit:

inference_semaphore = asyncio.Semaphore(int(os.getenv("MAX_CONCURRENT_INFERENCE", 4)))
@app.post("/predict")
async def predict(data: Payload, background_task: BackgroundTasks):
    model = models.get("generative")
    if model is None:
        raise HTTPException(status_code=503, detail="Model not ready")

    async with inference_semaphore:
        result = await asyncio.to_thread(model.predict, data.text)
    background_task.add_task(log_to_queue, data.text, result)
    # log_task.delay(data.text, result)  # Celery: goes to a queue, runs in a separate worker process, retries on failure
    return result
# Notice this flips back to async def — deliberately — using asyncio.to_thread explicitly instead of 
# relying on FastAPI's implicit def-offload, because the semaphore needs await to actually '
# 'throttle concurrency before dispatching to a thread. '
# 'This is a more advanced pattern than what we studied earlier taught, but it's built directly on it.





