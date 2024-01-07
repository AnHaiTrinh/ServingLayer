from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class StateType(str, Enum):
    free = 'free'
    occupied = 'occupied'
    reserved = 'reserved'


class VehicleType(str, Enum):
    car = 'car'
    motorbike = 'motorbike'
    truck = 'truck'


class Vehicle(BaseModel):
    id: int
    vehicle_type: VehicleType
    license_plate: str


class ParkingSpaceState(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    state: StateType
    vehicle: Optional[Vehicle] = None


class SpaceReport(BaseModel):
    free: int = 0
    occupied: int = 0
    reserved: int = 0


class CapacityReport(BaseModel):
    car: SpaceReport = SpaceReport()
    motorbike: SpaceReport = SpaceReport()
    truck: SpaceReport = SpaceReport()


class ParkingSpaceOut(BaseModel):
    id: int
    longitude: int
    latitude: int
    parking_lot_id: int
    vehicle_type: VehicleType
    state: StateType = StateType.free


class RatingReport(BaseModel):
    parking_lot_id: int
    one_star: int = 0
    two_star: int = 0
    three_star: int = 0
    four_star: int = 0
    five_star: int = 0


class ReserveOrder(BaseModel):
    parking_space_id: int
    vehicle_id: int


class ValidateModel(BaseModel):
    license_plate: str
    user_id: int
    timestamp: datetime


class VehicleReport(BaseModel):
    hour: str
    car: int = 0
    motorbike: int = 0
    truck: int = 0
