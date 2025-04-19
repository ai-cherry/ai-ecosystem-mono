from fastapi import FastAPI
from orchestrator import router

app = FastAPI()

# Include the agent router
app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Orchestrator Core"}
