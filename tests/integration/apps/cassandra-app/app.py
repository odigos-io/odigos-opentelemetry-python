import traceback
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route


async def test(request):
    try:
        from cassandra.cluster import Cluster
        cluster = Cluster(["cassandra"])
        session = cluster.connect()
        session.execute(
            "CREATE KEYSPACE IF NOT EXISTS test_ks "
            "WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}"
        )
        session.set_keyspace("test_ks")
        session.execute(
            "CREATE TABLE IF NOT EXISTS items (id int PRIMARY KEY, name text)"
        )
        session.execute("INSERT INTO items (id, name) VALUES (1, 'test')")
        rows = session.execute("SELECT * FROM items WHERE id = 1")
        row = rows.one()
        cluster.shutdown()
        return JSONResponse({"id": row.id, "name": row.name})
    except Exception as exc:
        traceback.print_exc()
        return JSONResponse({"error": str(exc)}, status_code=500)


app = Starlette(routes=[Route("/test", test)])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
