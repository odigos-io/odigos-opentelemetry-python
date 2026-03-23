from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from pymemcache.client.base import Client


memcached = Client(("memcached", 11211))


async def test(request):
    memcached.set("test_key", "hello_from_memcached")
    value = memcached.get("test_key")
    return JSONResponse({"key": "test_key", "value": value.decode()})


app = Starlette(routes=[Route("/test", test)])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
