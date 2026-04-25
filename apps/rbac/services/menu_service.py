from typing import Optional

from apps.rbac.models.menu import Menu
from apps.rbac.schemas.menu import MenuCreate, MenuUpdate
from apps.rbac.services.crud_base import CRUDBase


class MenuService(CRUDBase[Menu, MenuCreate, MenuUpdate]):
    def __init__(self):
        super().__init__(model=Menu)

    async def get_by_menu_path(self, path: str) -> Optional["Menu"]:
        return await self.model.filter(path=path).first()


menu_service = MenuService()
