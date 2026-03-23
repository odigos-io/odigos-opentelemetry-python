from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

TARGET_URL = "http://flask-app:8080/rolldice"


async def test_all(request):
    results = {}

    import requests as req_lib
    response = req_lib.get(TARGET_URL)
    results["requests"] = response.status_code

    import urllib.request
    with urllib.request.urlopen(TARGET_URL) as response:
        response.read()
    results["urllib"] = "ok"

    import urllib3
    http = urllib3.PoolManager()
    response = http.request("GET", TARGET_URL)
    results["urllib3"] = response.status

    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(TARGET_URL)
    results["httpx"] = response.status_code

    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(TARGET_URL) as response:
            await response.text()
    results["aiohttp_client"] = "ok"

    return JSONResponse(results)


app = Starlette(routes=[Route("/test-all", test_all)])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
