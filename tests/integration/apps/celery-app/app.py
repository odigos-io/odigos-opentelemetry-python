from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from celery import Celery

celery_app = Celery("tasks", broker="redis://redis:6379/1", backend="redis://redis:6379/1")
celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = True


@celery_app.task
def add(x, y):
    return x + y


async def test(request):
    result = add.delay(4, 4)
    value = result.get(timeout=5)
    return JSONResponse({"result": value})


app = Starlette(routes=[Route("/test", test)])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
