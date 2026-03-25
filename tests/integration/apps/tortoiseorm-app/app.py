from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from tortoise import Tortoise, fields
from tortoise.models import Model

try:
    from tortoise.context import TortoiseContext
    HAS_CONTEXT = True
except ImportError:
    HAS_CONTEXT = False


class Event(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)

    class Meta:
        table = "events"


DB_URL = "postgres://testuser:testpass@postgres:5432/testdb"
_schemas_created = False


async def _init_and_query():
    global _schemas_created
    await Tortoise.init(db_url=DB_URL, modules={"models": ["__main__"]})
    if not _schemas_created:
        await Tortoise.generate_schemas()
        _schemas_created = True
    event = await Event.create(name="test_event")
    count = await Event.all().count()
    await Tortoise.close_connections()
    return {"id": event.id, "count": count}


async def test(request):
    if HAS_CONTEXT:
        async with TortoiseContext():
            result = await _init_and_query()
    else:
        result = await _init_and_query()
    return JSONResponse(result)


app = Starlette(routes=[Route("/test", test)])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
