from enum import Enum

from pydantic import BaseModel


class VehicleType(str, Enum):
    BIKE = "BIKE"
    SCOOTER = "SCOOTER"


class Profile(BaseModel):
    user_id: str
    name: str
    email: str
    phone_number: str | None = None
    preferred_vehicle_type: VehicleType | None = None
    active: bool = True
    created_at: str
    updated_at: str



class ProfileNotFound(Exception):
    pass