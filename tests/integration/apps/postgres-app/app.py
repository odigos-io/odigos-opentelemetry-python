from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

PG_DSN = "host=postgres port=5432 dbname=testdb user=testuser password=testpass"


async def test(request):
    results = {}

    import psycopg2
    conn = psycopg2.connect(PG_DSN)
    cur = conn.cursor()
    cur.execute("SELECT 1")
    results["psycopg2"] = cur.fetchone()[0]
    cur.close()
    conn.close()

    import asyncpg
    conn = await asyncpg.connect(
        host="postgres", port=5432,
        user="testuser", password="testpass",
        database="testdb",
    )
    results["asyncpg"] = await conn.fetchval("SELECT 1")
    await conn.close()

    import psycopg
    conn = psycopg.connect(PG_DSN)
    results["psycopg"] = conn.execute("SELECT 1").fetchone()[0]
    conn.close()

    import aiopg
    async with aiopg.connect(PG_DSN) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1")
            results["aiopg"] = (await cur.fetchone())[0]

    return JSONResponse(results)


app = Starlette(routes=[Route("/test", test)])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
