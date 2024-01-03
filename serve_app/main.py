from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

import collections
from typing import Optional
from sqlalchemy import func as F
from fastapi import FastAPI, Query, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .db import DatabaseDependency
from .auth import SensorDependency
from .models import ParkingSpace, RatingFeedback
from .schemas import CapacityReport, State, ParkingSpaceOut, RatingReport

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/parking_lots", response_model=CapacityReport, status_code=status.HTTP_200_OK)
def get_parking_space_from_parking_lot(
        db: DatabaseDependency,
        parking_lot_id: Optional[int] = Query(default=None),
):
    response = collections.defaultdict(dict)
    query = db.query(ParkingSpace.vehicle_type, ParkingSpace.state, F.count()).group_by(
        ParkingSpace.vehicle_type, ParkingSpace.state
    )
    if parking_lot_id is not None:
        query = query.filter(ParkingSpace.parking_lot_id == parking_lot_id)
    result = query.all()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Information not found')
    for vehicle_type, state, count in result:
        response[vehicle_type][state] = count
    return response


@app.get('/sensors', response_model=State, status_code=status.HTTP_200_OK)
def get_sensor_state(
        sensor: SensorDependency,
        db: DatabaseDependency,
):
    parking_space_id = sensor.parking_space_id
    state = db.query(ParkingSpace.state).filter(ParkingSpace.id == parking_space_id).first()
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail='Associated parking space not found')
    return state


@app.get('/recommend', response_model=list[ParkingSpaceOut], status_code=status.HTTP_200_OK)
def recommend_parking_space(
        db: DatabaseDependency,
        parking_lot_id: Optional[int] = Query(default=None),
        vehicle_type: str = Query(regex='^(car|motorbike|truck)$'),
        num_results: int = Query(default=1, gt=0, le=10)
):
    query = db.query(ParkingSpace)
    if parking_lot_id is not None:
        query = query.filter(ParkingSpace.parking_lot_id == parking_lot_id)
    results = query.filter(
        ParkingSpace.vehicle_type == vehicle_type,
        ParkingSpace.state == 'free'
    ).limit(num_results).all()
    if not results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No parking space available')
    return results


@app.get('/rating', response_model=RatingReport, status_code=status.HTTP_200_OK)
def get_rating_from_parking_lot(
        db: DatabaseDependency,
        parking_lot_id: Optional[int] = Query(default=None),
):
    response = RatingReport(parking_lot_id=parking_lot_id)
    query = db.query(RatingFeedback.rating, F.count()).group_by(RatingFeedback.rating)
    if parking_lot_id is not None:
        query = query.filter(RatingFeedback.parking_lot_id == parking_lot_id)
    result = query.all()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Information not found')
    for rating, count in result:
        if rating == 1:
            response.one_star = count
        elif rating == 2:
            response.two_star = count
        elif rating == 3:
            response.three_star = count
        elif rating == 4:
            response.four_star = count
        elif rating == 5:
            response.five_star = count
    return response
