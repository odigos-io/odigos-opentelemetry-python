from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route


async def test(request):
    results = {}

    import pymysql
    conn = pymysql.connect(
        host="mysql", port=3306,
        user="testuser", password="testpass",
        database="testdb",
    )
    cur = conn.cursor()
    cur.execute("SELECT 1")
    results["pymysql"] = cur.fetchone()[0]
    cur.close()
    conn.close()

    return JSONResponse(results)


app = Starlette(routes=[Route("/test", test)])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
