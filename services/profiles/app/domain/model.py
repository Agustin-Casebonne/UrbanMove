from enum import Enum

from pydantic import BaseModel, field_validator


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

    @field_validator("email")
    @classmethod
    def email_must_contain_at(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("email debe contener '@'")
        return v

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name no puede estar vacío")
        return v

class ProfileNotFound(Exception):
    pass