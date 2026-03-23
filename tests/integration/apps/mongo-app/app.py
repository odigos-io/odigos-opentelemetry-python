from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from pymongo import MongoClient


client = MongoClient("mongodb://mongo:27017/")


async def test(request):
    db = client["testdb"]
    collection = db["items"]
    collection.insert_one({"name": "test_item", "value": 42})
    count = collection.count_documents({})
    return JSONResponse({"collection": "items", "count": count})


app = Starlette(routes=[Route("/test", test)])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
