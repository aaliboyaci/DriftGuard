"""ORM model file collectors (Sequelize, Prisma, etc.)."""

from driftguard.collectors.orm.prisma_collector import PrismaCollector
from driftguard.collectors.orm.sequelize_collector import SequelizeCollector

__all__ = [
    "PrismaCollector",
    "SequelizeCollector",
]
