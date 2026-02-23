from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import uvicorn

engine = create_engine("sqlite:////tmp/test.db", connect_args={"check_same_thread": False})
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100))


Base.metadata.create_all(engine)


async def rolldice(request):
    session = SessionLocal()
    try:
        session.add(Item(name="ping"))
        session.commit()
        count = session.execute(text("SELECT COUNT(*) FROM items")).scalar()
        return JSONResponse({"items": count})
    finally:
        session.close()


app = Starlette(routes=[Route("/rolldice", rolldice)])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
