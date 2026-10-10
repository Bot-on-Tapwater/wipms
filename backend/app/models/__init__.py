"""Import every model here so SQLAlchemy and Alembic can see all tables."""
from app.models.labourer import Labourer
from app.models.payment import PaymentRecord
from app.models.permission import Permission, RolePermission
from app.models.project import Project, WalletTransaction
from app.models.user import RevokedToken, User
from app.models.work import Work, WorkImage, WorkLabourer

__all__ = [
    "Labourer",
    "PaymentRecord",
    "Permission",
    "RolePermission",
    "Project",
    "WalletTransaction",
    "RevokedToken",
    "User",
    "Work",
    "WorkImage",
    "WorkLabourer",
]
