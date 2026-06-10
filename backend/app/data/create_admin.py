"""Crea (o actualiza la contraseña de) un usuario administrador.

    python -m app.data.create_admin <usuario> <contraseña>
    python -m app.data.create_admin           # modo interactivo

La contraseña se guarda **hasheada** (PBKDF2) en la tabla `admin_users`.
"""

from __future__ import annotations

import asyncio
import getpass
import sys

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, engine
from app.core.security import hash_password
from app.models.admin_user import AdminUser


async def main() -> None:
    if len(sys.argv) >= 3:
        username, password = sys.argv[1], sys.argv[2]
    else:
        username = input("Usuario: ").strip()
        password = getpass.getpass("Contraseña: ")

    if not username or not password:
        print("Usuario y contraseña son obligatorios.")
        return

    async with AsyncSessionLocal() as db:
        user = (
            await db.execute(select(AdminUser).where(AdminUser.username == username))
        ).scalar_one_or_none()
        if user is None:
            db.add(AdminUser(username=username, password_hash=hash_password(password)))
            action = "creado"
        else:
            user.password_hash = hash_password(password)
            action = "actualizado"
        await db.commit()
    await engine.dispose()
    print(f"Usuario administrador '{username}' {action}.")


if __name__ == "__main__":
    asyncio.run(main())
