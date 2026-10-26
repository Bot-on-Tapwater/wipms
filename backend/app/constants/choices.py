"""Fixed choice lists used by works, labourers and payments."""
from enum import Enum


class TaskCategory(str, Enum):
    """Category of a subcontracted work."""

    WELDING = "welding"
    ALUMINIUM_FABRICATION = "aluminium_fabrication"
    METALWORK = "metalwork"
    TILE_LAYING = "tile_laying"
    FLOORING_INSTALLATION = "flooring_installation"
    WOODWORKING = "woodworking"
    FURNITURE_MAKING = "furniture_making"
    FRAMING = "framing"
    REINFORCING_STEEL_BARS = "reinforcing_steel_bars"
    CONCRETE_REINFORCEMENT = "concrete_reinforcement"
    MACHINERY_REPAIR = "machinery_repair"
    EQUIPMENT_MAINTENANCE = "equipment_maintenance"
    OPERATING_HEAVY_MACHINERY = "operating_heavy_machinery"
    EQUIPMENT_HANDLING = "equipment_handling"
    PAINTING = "painting"
    SURFACE_FINISHING = "surface_finishing"
    SOLAR_WATER_HEATER_INSTALLATION = "solar_water_heater_installation"
    PLUMBING = "plumbing"
    ERECTING_SCAFFOLDING = "erecting_scaffolding"
    TEMPORARY_STRUCTURES = "temporary_structures"
    NETWORK_CABLING = "network_cabling"
    WIRING_INSTALLATION = "wiring_installation"
    ELECTRICAL_WIRING = "electrical_wiring"
    POWER_INSTALLATION = "power_installation"
    PIPE_FITTING = "pipe_fitting"
    WATER_SYSTEM_INSTALLATION = "water_system_installation"
    SPACE_PLANNING = "space_planning"
    HOME_DECOR = "home_decor"
    FURNISHING = "furnishing"
    ROAD_CONSTRUCTION = "road_construction"
    DRAINAGE = "drainage"
    EARTHWORKS = "earthworks"
    BRICKLAYING = "bricklaying"
    STONEWORK = "stonework"
    CONCRETE_WORK = "concrete_work"
    OTHER = "other"


class LabourerTitle(str, Enum):
    """Trade / title of a labourer."""

    WELDERS = "welders"
    ALUMINIUM_FABRICATORS = "aluminium_fabricators"
    TILING_INSTALLER = "tiling_installer"
    CARPENTERS = "carpenters"
    STEEL_FIXERS = "steel_fixers"
    PLANT_MECHANICS = "plant_mechanics"
    PLANT_OPERATORS = "plant_operators"
    PAINTERS = "painters"
    SOLAR_WATER_INSTALLER = "solar_water_installer"
    SCAFFOLDER = "scaffolder"
    STRUCTURAL_CABLING_INSTALLER = "structural_cabling_installer"
    ELECTRICIAN = "electrician"
    PLUMBER = "plumber"
    INTERIOR_DESIGNER = "interior_designer"
    CIVIL_WORKS = "civil_works"
    MASONRY = "masonry"
    CASUAL = "casual"
    PLASTERERS = "plasterers"
    INTERN = "intern"
    ATTACHE = "attache"
    STUDENT = "student"
    OTHER = "other"


class Gender(str, Enum):
    """Gender of a labourer. Optional, and only ever shown as totals."""

    MALE = "male"
    FEMALE = "female"


class PaymentStatus(str, Enum):
    """Payment state of a subcontracted work."""

    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"


class PaymentType(str, Enum):
    """What a payment record was for."""

    LABOURER = "labourer"
    SUBCONTRACTOR = "subcontractor"
    RETENTION = "retention"


class WalletTransactionType(str, Enum):
    """Direction of a project wallet movement."""

    DEPOSIT = "deposit"
    PAYOUT = "payout"


def label_for(value: str) -> str:
    """
    Turn a choice value like ``tile_laying`` into ``Tile Laying``.

    Args:
        value (str): Choice value, e.g. ``tile_laying``.

    Returns:
        str: Human readable label.
    """
    return value.replace("_", " ").title()
