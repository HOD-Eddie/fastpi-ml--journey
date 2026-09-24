# FastAPI Production & ML Deployment — Lesson Notes

## Learning Goal

Build a reliable FastAPI application suitable for modern cloud deployment, especially when the API serves an ML model.

Core themes:

- Containerization with Docker
- Configuration and environment variables
- FastAPI lifecycle/model management
- Health checks
- Concurrency
- Workers and threads
- ML model memory considerations
- Horizontal scaling
- Load balancing
- Kubernetes concepts

---

# 1. Docker: Images vs Containers

## Key idea

A **Docker image** is a packaged, reusable blueprint containing the application, runtime, and dependencies.

A **container** is a running instance of that image.

One image can create multiple containers.

```text
Docker Image
    |
    +----> Container 1
    |
    +----> Container 2
    |
    +----> Container 3
```

Containers improve deployment consistency, but they do not make software independent of the host kernel. Linux containers share the host kernel (or run through a Linux VM in some environments).

Kubernetes can orchestrate containers; it does not replace the need for container images.

---

# 2. Dockerfile Layering

A basic FastAPI Dockerfile:

```dockerfile
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Key architectural principle

Copy dependency files before application source:

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
```

Docker caches layers.

If application code changes but `requirements.txt` does not, Docker can reuse the dependency-installation layer instead of reinstalling heavy packages.

This matters enormously for ML dependencies such as PyTorch or ONNX Runtime.

---

# 3. `.dockerignore`

Typical contents:

```text
.venv/
__pycache__/
.git/
.env
*.pyc
```

## Why?

The Docker build context should not contain unnecessary files, local virtual environments, Git metadata, Python cache files, or secrets.

`.env` is configuration/secrets, not a dependency.

Dependencies belong in files such as:

```text
requirements.txt
pyproject.toml
```

---

# 4. Docker Port Mapping

Example:

```bash
docker run -p 9000:8000 my-fastapi-app
```

Meaning:

```text
Host port 9000
      ↓
Container port 8000
      ↓
Uvicorn
```

The browser/client therefore accesses:

```text
http://localhost:9000/
```

Inside the container, Uvicorn should normally bind to:

```text
0.0.0.0:8000
```

not:

```text
127.0.0.1:8000
```

because `127.0.0.1` would only expose the service inside the container itself.

---

# 5. Health Checks

Health endpoints let infrastructure determine whether an application should receive traffic or be restarted.

## Liveness

Question:

> "Is this application process alive?"

Typical response:

```http
200 OK
```

If liveness fails, an orchestrator such as Kubernetes may restart the container.

## Readiness

Question:

> "Can this application serve requests right now?"

Typical responses:

```http
200 OK
```

when ready, and:

```http
503 Service Unavailable
```

when not ready.

If readiness fails, the instance should normally be removed from traffic rather than immediately restarted.

## Example

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/health/live")
def live():
    return {"status": "alive"}

@app.get("/health/ready")
def ready():
    if app.state.model is None:
        raise HTTPException(status_code=503)

    return {"status": "ready"}
```

## Important distinction

```text
Liveness  → Should I restart you?
Readiness → Should I send traffic to you?
```

A model can be unavailable while the FastAPI process is still alive:

```text
FastAPI process → alive
Model           → unavailable

/health/live  → 200
/health/ready → 503
```

That does not necessarily mean the process should be restarted.

---

# 6. FastAPI Lifespan

For ML APIs, heavy model initialization should normally happen during application startup rather than inside every request.

Modern FastAPI lifespan pattern:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = load_model(...)
    yield
    app.state.model = None

app = FastAPI(lifespan=lifespan)
```

## Lifecycle semantics

Code before `yield`:

```python
app.state.model = load_model(...)
```

runs during startup.

Code after `yield`:

```python
app.state.model = None
```

runs during shutdown.

This meaning comes from FastAPI's lifespan/context-manager protocol.

`yield` itself is a Python language feature; it is not inherently "startup" or "shutdown."

---

# 7. Python `yield`

A generator pauses at `yield` and preserves its state.

Example:

```python
def test():
    print("A")
    yield 1

    print("B")
    yield 2

    print("C")
    yield 3

    print("D")

g = test()

print(next(g))
print(next(g))
print(next(g))
```

Output:

```text
A
1
B
2
C
3
```

After yielding `3`, execution is paused before:

```python
print("D")
```

## `return` vs `yield`

`return`:

- produces a value
- terminates the function

`yield`:

- produces a value
- pauses execution
- preserves state
- allows execution to resume later

In FastAPI lifespan, the framework uses the point around `yield` to distinguish startup from shutdown.

---

# 8. Loading an ML Model Once

## Bad pattern

```python
@app.post("/predict")
def predict(data):
    model = load_model()
    return model.predict(data)
```

This potentially loads/initializes the model repeatedly.

For a large model this creates unnecessary:

- latency
- memory pressure
- CPU/GPU work

## Better pattern

Load once at application startup:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = load_model(...)
    yield
    app.state.model = None
```

Then reuse:

```python
@app.post("/predict")
def predict(data):
    return app.state.model.predict(data)
```

The goal is:

```text
Application starts
       ↓
Load model once
       ↓
Keep model in memory
       ↓
Requests reuse same model
       ↓
Application shuts down
       ↓
Release resources
```

---

# 9. `app.state`

`app.state` provides application-scoped state.

Example:

```python
app.state.model = load_model(...)
```

The model has an explicit home associated with that FastAPI application instance.

This is preferable to scattering application-wide state through arbitrary globals.

## Important nuance

The primary benefit is not that it "isolates the model from routes."

The important ideas are:

- application-scoped state
- explicit ownership
- lifecycle association
- separate state for separate FastAPI application instances

---

# 10. Model Loading Before `yield`

Correct:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = load_model(...)
    yield
```

The model loads before the application enters its running state.

If:

```python
load_model(...)
```

raises an exception before `yield`, application startup fails.

This is desirable when the model is a required dependency.

Incorrect ordering:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    app.state.model = load_model(...)
```

This would place model loading after the application has entered its running phase, which is not appropriate for a required startup dependency.

---

# 11. Configuration vs Application Code

Avoid hardcoding deployment-specific values:

```python
MODEL_PATH = "/home/user/models/model.onnx"
DEVICE = "cuda"
```

This couples the application to a particular environment.

Better:

```text
MODEL_PATH=/models/model.onnx
DEVICE=cuda
```

Configuration should be supplied by the deployment environment.

This follows the principle:

> Build the image once. Configure it when you run it.

Hardcoding does not inherently expose secrets. The more precise problem is **configuration coupling**.

---

# 12. `pydantic-settings`

Example:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_path: str
    device: str = "cpu"
    log_level: str = "INFO"

settings = Settings()
```

Environment variables map naturally:

```text
MODEL_PATH=/models/model.onnx
DEVICE=cuda
LOG_LEVEL=INFO
```

`model_path` is required because it has no default.

If it is missing:

```python
Settings()
```

raises a Pydantic validation error.

`device` defaults to:

```text
cpu
```

when `DEVICE` is not supplied.

## Important distinction

Environment variables are a **configuration mechanism**.

They are not automatically secure.

Ordinary configuration:

```text
MODEL_PATH
DEVICE
LOG_LEVEL
```

Sensitive configuration:

```text
API_KEY
DATABASE_PASSWORD
JWT_SECRET
```

Sensitive values should be handled with appropriate secret-management mechanisms in production.

---

# 13. `.env` and Deployment

Different environments can provide configuration differently.

```text
Local development
    → .env

Docker Compose
    → environment / .env / Compose configuration

Cloud VM
    → environment variables / secret manager

Kubernetes
    → ConfigMaps / Secrets

CI/CD
    → environment variables / secret store
```

Do not commit real `.env` secrets.

Use:

```text
.env.example
```

for documentation:

```text
MODEL_PATH=/models/model.onnx
DEVICE=cpu
DATABASE_URL=your_database_url_here
```

The README should document required configuration, but should not contain actual secrets.

---

# 14. Application Structure

A simple separation:

```text
fastapi-ml/
├── app/
│   ├── main.py
│   ├── config.py
│   └── model.py
├── requirements.txt
├── Dockerfile
├── .dockerignore
└── .env.example
```

## Responsibilities

`config.py`

- configuration
- environment parsing
- validation

`model.py`

- model loading
- model-related logic

`main.py`

- FastAPI application assembly
- routes
- lifecycle wiring

This improves cohesion and reduces unnecessary coupling.

It also supports the Single Responsibility Principle: each module has a clearer reason to change.

---

# 15. Synchronous vs Asynchronous FastAPI Endpoints

Example synchronous endpoint:

```python
@app.post("/predict")
def predict(data):
    return app.state.model.predict(data)
```

FastAPI/Starlette can execute synchronous path-operation functions through a thread pool rather than blocking the event-loop thread directly.

Important:

> This does NOT mean one thread is created for every request.

The thread pool is limited.

Requests can wait when available worker threads are exhausted.

---

# 16. `async def` and Blocking ML Inference

This can be dangerous:

```python
@app.post("/predict")
async def predict(data):
    return app.state.model.predict(data)
```

If:

```python
model.predict(...)
```

is synchronous and blocking, it can block the event-loop thread.

While it is blocked, the event loop cannot execute other coroutine work.

Example:

```text
Request A
   ↓
event loop
   ↓
blocking model.predict()
   ↓
event loop is occupied
   ↓
Request B waits
```

If inference takes 2 seconds:

- B arrives 1 second after A starts → B can wait about 1 remaining second.
- B arrives immediately after A starts → B can wait about 2 seconds.
- B arrives after A completes → B does not wait on A's inference.

## Core principle

```text
async + await on an async operation
    → event loop can work on other tasks while waiting

async + blocking synchronous function
    → event loop can be blocked
```

`async` does not automatically make blocking code concurrent.

---

# 17. Workers vs Threads vs Requests

These are different concepts.

## Worker

A Uvicorn worker is a separate **OS process**.

Example:

```bash
uvicorn app.main:app --workers 4
```

Conceptually:

```text
Worker 1
Worker 2
Worker 3
Worker 4
```

Each worker has independent process memory.

## Thread

Threads exist inside processes.

A worker can have a thread pool for synchronous request handlers.

Conceptually:

```text
Worker 1
├── Thread → Request A
├── Thread → Request B
└── Thread → Request C
```

## Request

A request is work being handled by the application.

Therefore:

> Multiple workers ≠ multiple requests.

A single worker can handle multiple requests.

---

# 18. ML Model Duplication Across Workers

This is critical for ML deployment.

Suppose:

```text
Model = 2 GB
Workers = 4
```

Each worker may load its own model copy:

```text
Worker 1 → 2 GB
Worker 2 → 2 GB
Worker 3 → 2 GB
Worker 4 → 2 GB
```

Potential model memory:

```text
4 × 2 GB = 8 GB
```

This is before considering:

- OS memory
- Python runtime
- FastAPI/Uvicorn
- request data
- framework allocations
- other processes

The same principle can matter for GPU memory. Multiple processes can result in multiple model copies on the GPU depending on the framework and architecture.

Therefore:

> More CPU cores does not automatically mean "use more workers" for an ML API.

Worker count must be considered alongside:

- model memory
- CPU
- GPU
- inference characteristics
- concurrency
- throughput

---

# 19. Vertical Scaling

Vertical scaling means increasing resources on one machine.

Example:

```text
Machine
├── more RAM
├── more CPU
└── stronger GPU
```

Using more workers on one machine is still constrained by that machine's resources.

Example:

```text
8 GB RAM
2 GB model
4 workers

Potential model footprint:
4 × 2 GB = 8 GB
```

The machine still needs RAM for everything else.

---

# 20. Horizontal Scaling

Horizontal scaling means adding more instances/machines.

Example:

```text
Machine A → FastAPI + Model
Machine B → FastAPI + Model
Machine C → FastAPI + Model
```

A load balancer can distribute traffic across them.

```text
             Load Balancer
             /     |     \
            ↓      ↓      ↓
        Machine A Machine B Machine C
```

Horizontal scaling moves the resource ceiling outward, but does not remove all limits. The overall fleet is still constrained by infrastructure, networking, cost, orchestration, etc.

If each machine loads a 2 GB model:

```text
3 machines × 2 GB = 6 GB
```

across the fleet.

This duplication can be intentional to gain additional capacity or availability.

---

# 21. Load Balancing

A load balancer distributes requests across instances.

Example:

```text
                 Load Balancer
                 /     |     \
                ↓      ↓      ↓
              API-1  API-2  API-3
```

A simple distribution might look like:

```text
API-1 → R1 R4 R7
API-2 → R2 R5 R8
API-3 → R3 R6 R9
```

Real systems can use more sophisticated algorithms and account for health, connection state, capacity, and other factors.

## Readiness matters

Suppose:

```text
API-1 → ready
API-2 → not ready
API-3 → ready
```

Traffic should be directed to the ready instances.

Readiness therefore helps infrastructure determine whether an instance belongs in the traffic pool.

The load balancer does not necessarily determine application health itself; it can rely on health/readiness information from the application or orchestrator.

---

# 22. Kubernetes

Kubernetes is an orchestration system.

A simplified architecture:

```text
                    Kubernetes
                        │
          ┌─────────────┼─────────────┐
          ↓             ↓             ↓
       Pod/API-1     Pod/API-2     Pod/API-3
          │             │             │
      Container      Container      Container
          │             │             │
       FastAPI       FastAPI       FastAPI
          │             │             │
        Model         Model         Model
```

A **Pod** is the unit Kubernetes schedules.

In a simple deployment, one Pod contains one application container.

Kubernetes can:

- restart failed containers
- maintain replicas
- remove unready Pods from service traffic
- replace failed Pods
- scale replicas
- coordinate deployment of application instances

---

# 23. Kubernetes: Liveness vs Readiness

Suppose a model becomes unavailable but the FastAPI process remains alive:

```text
FastAPI process → alive
Model           → unavailable

Liveness  → 200
Readiness → 503
```

The Pod can be removed from traffic without necessarily being restarted.

If the process itself becomes unhealthy:

```text
Liveness → fails
```

Kubernetes may restart the container.

Core mental model:

```text
Liveness
    ↓
"Should I restart you?"

Readiness
    ↓
"Should I send traffic to you?"
```

---

# 24. Startup Failure of a Required Model

If model loading happens before `yield`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = load_model(...)
    yield
```

and loading fails:

```text
load_model()
    ↓
exception
    ↓
startup fails
    ↓
application does not become ready
```

This is appropriate when the model is a required dependency.

However, slow initialization introduces another concern.

---

# 25. Current Lesson Endpoint: Startup Probes

This is the **next topic to continue from**.

Suppose:

```text
Model loading time = 45 seconds
```

If Kubernetes starts liveness checking immediately and the application does not respond during initialization, Kubernetes could interpret the situation as a failure.

That can produce an undesirable restart loop:

```text
Start
  ↓
Load model
  ↓
45 seconds needed
  ↓
Liveness fails too early
  ↓
Restart
  ↓
Load model again
  ↓
Liveness fails again
  ↓
Restart...
```

Kubernetes provides **startup probes** for this kind of initialization period.

The next lesson should explain:

- what a startup probe is
- how it differs from liveness/readiness
- how startup probes protect slow ML initialization
- how the three probes work together
- then the relevant Kubernetes configuration

---

# Architectural Summary

The concepts fit together like this:

```text
                  Client
                    │
                    ↓
              Load Balancer
                    │
          ┌─────────┼─────────┐
          ↓         ↓         ↓
        Pod 1     Pod 2     Pod 3
          │         │         │
      Container Container Container
          │         │         │
        FastAPI   FastAPI   FastAPI
          │         │         │
       Lifespan  Lifespan  Lifespan
          │         │         │
       ML Model  ML Model  ML Model
          │         │         │
       /predict /predict /predict
          │         │         │
       health    health    health
       probes    probes    probes
```

Within each application:

```text
Application startup
       ↓
pydantic-settings loads configuration
       ↓
FastAPI lifespan begins
       ↓
Load ML model once
       ↓
Store model in app.state
       ↓
Application becomes ready
       ↓
Receive prediction requests
       ↓
Reuse in-memory model
       ↓
Application shutdown
       ↓
Release resources
```

---

# Core Principles to Remember

1. **Build the image once; configure it at runtime.**
2. **Load expensive ML models once, not once per request.**
3. **Use FastAPI lifespan for application-scoped startup/shutdown resources.**
4. **`yield` pauses execution; FastAPI's lifespan protocol gives the code around it startup/shutdown meaning.**
5. **Readiness controls traffic; liveness controls restart decisions.**
6. **`async` does not make blocking ML inference asynchronous.**
7. **A worker is a process, not a container.**
8. **Multiple workers can duplicate a model in memory.**
9. **More CPU cores does not automatically mean more ML workers.**
10. **Vertical scaling increases resources on one machine; horizontal scaling adds instances.**
11. **Load balancing distributes traffic across available instances.**
12. **Readiness allows unhealthy/unready instances to be removed from the traffic pool.**
13. **Kubernetes orchestrates application instances and their lifecycle.**
14. **ML deployment decisions must consider CPU, RAM, GPU memory, model size, inference time, and concurrency together.**

---

# Current Learning State

The learner understands:

- Docker fundamentals
- Dockerfile layer caching
- `.dockerignore`
- container networking/port mapping
- liveness vs readiness
- FastAPI lifespan
- Python `yield`
- model lifecycle
- `app.state`
- environment configuration
- `pydantic-settings`
- configuration/secrets separation
- application modularity
- synchronous vs asynchronous FastAPI handlers
- event-loop blocking
- worker processes vs threads vs requests
- model memory duplication across workers
- vertical vs horizontal scaling
- load balancing
- Kubernetes Pods
- liveness/readiness behavior

## Resume point

**NEXT TOPIC: Kubernetes startup probes for slow ML model initialization.**

Teaching format to preserve:

1. Explain one bite-sized concept.
2. Use practical FastAPI/ML deployment examples.
3. Ask one challenging recall question.
4. Grade/correct the learner's answer.
5. Continue to the next micro-lesson.
6. Do not restart the curriculum or dump all remaining material at once.
