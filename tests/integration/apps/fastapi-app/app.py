from fastapi import FastAPI
import random

app = FastAPI()


@app.get("/rolldice")
async def rolldice():
    return {"result": random.randint(1, 6)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
