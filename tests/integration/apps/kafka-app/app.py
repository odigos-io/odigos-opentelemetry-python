from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route


async def test(request):
    results = {}

    from kafka import KafkaProducer, KafkaConsumer

    producer = KafkaProducer(bootstrap_servers="kafka:9092")
    future = producer.send("test-kp", value=b"hello kafka-python")
    future.get(timeout=10)
    producer.close()

    consumer = KafkaConsumer(
        "test-kp",
        bootstrap_servers="kafka:9092",
        auto_offset_reset="earliest",
        consumer_timeout_ms=10000,
        group_id="test-kp-group",
    )
    for message in consumer:
        results["kafka_python"] = message.value.decode()
        break
    consumer.close()

    from confluent_kafka import Producer as CProducer, Consumer as CConsumer

    cp = CProducer({"bootstrap.servers": "kafka:9092"})
    cp.produce("test-ck", value=b"hello confluent")
    cp.flush(timeout=10)

    cc = CConsumer({
        "bootstrap.servers": "kafka:9092",
        "group.id": "test-ck-group",
        "auto.offset.reset": "earliest",
    })
    cc.subscribe(["test-ck"])
    msg = cc.poll(timeout=10.0)
    if msg and not msg.error():
        results["confluent_kafka"] = msg.value().decode()
    else:
        results["confluent_kafka"] = "no message"
    cc.close()

    return JSONResponse(results)


app = Starlette(routes=[Route("/test", test)])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
