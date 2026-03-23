from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from elasticsearch import Elasticsearch


es = Elasticsearch("http://elasticsearch:9200")


async def test(request):
    es.index(index="test-index", id="1", document={"title": "Test", "value": 42})
    es.indices.refresh(index="test-index")
    result = es.search(index="test-index", query={"match_all": {}})
    count = result["hits"]["total"]["value"]
    return JSONResponse({"index": "test-index", "hits": count})


app = Starlette(routes=[Route("/test", test)])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
