import asyncio
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import boto3

AWS_CONFIG = {
    "endpoint_url": "http://localstack:4566",
    "region_name": "us-east-1",
    "aws_access_key_id": "test",
    "aws_secret_access_key": "test",
}


def _sync_sqs_test():
    sqs = boto3.client("sqs", **AWS_CONFIG)

    queue = sqs.create_queue(QueueName="test-queue")
    queue_url = queue["QueueUrl"]

    sqs.send_message(QueueUrl=queue_url, MessageBody="hello from boto3")

    response = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
    messages = response.get("Messages", [])
    body = messages[0]["Body"] if messages else "no message"

    sqs.delete_queue(QueueUrl=queue_url)

    return {"sqs_message": body}


async def test(request):
    result = await asyncio.to_thread(_sync_sqs_test)
    return JSONResponse(result)


app = Starlette(routes=[Route("/test", test)])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
