from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import redis


pool = redis.ConnectionPool(host="redis", port=6379, db=0)


async def test(request):
    client = redis.Redis(connection_pool=pool)
    client.set("test_key", "hello_from_redis")
    value = client.get("test_key")
    return JSONResponse({"key": "test_key", "value": value.decode()})


app = Starlette(routes=[Route("/test", test)])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
