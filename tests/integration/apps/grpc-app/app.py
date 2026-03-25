import grpc
from concurrent import futures
import threading
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

import test_pb2
import test_pb2_grpc

GRPC_PORT = 50051


class GreeterServicer(test_pb2_grpc.GreeterServicer):
    def SayHello(self, request, context):
        return test_pb2.HelloReply(message=f"Hello, {request.name}!")


def run_grpc_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    test_pb2_grpc.add_GreeterServicer_to_server(GreeterServicer(), server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    server.wait_for_termination()


grpc_thread = threading.Thread(target=run_grpc_server, daemon=True)
grpc_thread.start()


async def test(request):
    channel = grpc.insecure_channel(f"localhost:{GRPC_PORT}")
    stub = test_pb2_grpc.GreeterStub(channel)
    response = stub.SayHello(test_pb2.HelloRequest(name="integration-test"))
    channel.close()
    return JSONResponse({"message": response.message})


app = Starlette(routes=[Route("/test", test)])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
