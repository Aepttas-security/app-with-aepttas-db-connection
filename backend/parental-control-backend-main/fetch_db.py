import asyncio
from app.database import async_session
from sqlalchemy.future import select
from app.models.db_models import Child, User

async def main():
    async with async_session() as session:
        result = await session.execute(select(Child))
        children = result.scalars().all()
        for c in children:
            print(f"Child: id={c.child_id} name={c.child_name} age={c.age} parent={c.parent_id} code={c.linking_code}")

        result = await session.execute(select(User))
        users = result.scalars().all()
        for u in users:
            print(f"User: id={u.id} email={u.email}")

if __name__ == "__main__":
    asyncio.run(main())
