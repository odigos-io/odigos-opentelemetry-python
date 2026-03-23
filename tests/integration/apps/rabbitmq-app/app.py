from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route


async def test(request):
    results = {}

    import pika
    connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
    channel = connection.channel()
    channel.queue_declare(queue="test_pika")
    channel.basic_publish(exchange="", routing_key="test_pika", body=b"hello pika")
    method, properties, body = channel.basic_get(queue="test_pika", auto_ack=True)
    results["pika"] = body.decode() if body else "no message"
    connection.close()

    import aio_pika
    connection = await aio_pika.connect_robust("amqp://guest:guest@rabbitmq/")
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue("test_aio_pika")
        await channel.default_exchange.publish(
            aio_pika.Message(body=b"hello aio_pika"),
            routing_key="test_aio_pika",
        )
        message = await queue.get()
        await message.ack()
        results["aio_pika"] = message.body.decode()

    return JSONResponse(results)


app = Starlette(routes=[Route("/test", test)])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
