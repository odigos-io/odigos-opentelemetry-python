from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import pymssql


async def test(request):
    conn = pymssql.connect(
        server="mssql",
        port="1433",
        user="sa",
        password="TestPass123!",
        database="master",
    )
    cursor = conn.cursor()
    cursor.execute("SELECT 1 AS result")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return JSONResponse({"result": row[0]})


app = Starlette(routes=[Route("/test", test)])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
