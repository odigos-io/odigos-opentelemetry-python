from aiohttp import web
import random


async def rolldice(request):
    return web.Response(text=str(random.randint(1, 6)))


app = web.Application()
app.router.add_get("/rolldice", rolldice)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8080)
