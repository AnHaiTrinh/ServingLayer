from enum import Enum

from pydantic import BaseModel


class StateType(str, Enum):
    free = 'free'
    occupied = 'occupied'
    reserved = 'reserved'


class VehicleType(str, Enum):
    car = 'car'
    motorbike = 'motorbike'
    truck = 'truck'


class State(BaseModel):
    state: StateType


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