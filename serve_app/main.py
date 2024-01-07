import json
from datetime import datetime
import collections
import requests
from typing import Optional
from sqlalchemy import func as F
from fastapi import FastAPI, Query, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .db import DatabaseDependency
from .auth import SensorDependency, CameraDependency
from .models import ParkingSpace, RatingFeedback, Vehicle, ActivityLog
from .redis import RedisDependency
from .schemas import (CapacityReport, ParkingSpaceState, ParkingSpaceOut, ReserveOrder, RatingReport, ValidateModel,
                      VehicleReport)
from .kafka import KafkaProducerDependency

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


@app.get('/sensors', response_model=ParkingSpaceState, status_code=status.HTTP_200_OK)
def get_sensor_state(
    sensor: SensorDependency,
    db: DatabaseDependency,
):
    parking_space_id = sensor.parking_space_id
    parking_space = db.query(ParkingSpace).filter(ParkingSpace.id == parking_space_id).first()
    if not parking_space:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail='Associated parking space not found')
    return parking_space


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


@app.post('/reserve', status_code=status.HTTP_204_NO_CONTENT)
def reserve_space(
        reserve_order: ReserveOrder,
        kafka_producer: KafkaProducerDependency
):
    exception = None

    def acked(err, msg):
        if err is not None:
            nonlocal exception
            print(f"Failed to deliver message {msg}: {err}")
            exception = HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                      detail='Failed to reserve space')

    message = reserve_order.model_dump()
    del message['parking_space_id']
    message['updated_at'] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
    message['state'] = 'reserved'
    kafka_producer.produce(
        topic='parking_space_state_raw',
        key=str(reserve_order.parking_space_id),
        value=json.dumps(message),
        callback=acked
    )
    kafka_producer.poll(1)
    if exception:
        raise exception
    return


@app.post('/validate/in', response_model=ParkingSpaceOut, status_code=status.HTTP_200_OK)
def validate_in(
        camera: CameraDependency,
        db: DatabaseDependency,
        info: ValidateModel
):
    license_plate = info.license_plate
    vehicle = db.query(Vehicle).filter(Vehicle.license_plate == license_plate).first()
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Vehicle not registered')
    if vehicle.owner_id != info.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Vehicle not owned by user')

    vehicle_type = vehicle.vehicle_type
    parking_lot_id = camera.parking_lot_id
    resp = requests.get('http://localhost:8000/parking_lots', params={
        'parking_lot_id': parking_lot_id,
    })
    if resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f'Fail to get space status for parking lot {parking_lot_id}')
    free_space = resp.json()[vehicle_type]['free']
    if free_space == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Parking lot is full')

    parking_space_list = requests.get('http://localhost:8000/recommend', params={
        'parking_lot_id': parking_lot_id,
        'vehicle_type': vehicle_type,
    })
    if parking_space_list.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Fail to get parking space')
    parking_space = parking_space_list.json()[0]

    response = requests.post('http://localhost:8000/reserve', json={
        'parking_space_id': parking_space['id'],
        'vehicle_id': vehicle.id,
    })
    if response.status_code != 204:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Fail to reserve parking space')

    activity_log = ActivityLog(
        activity_type='in',
        vehicle_id=vehicle.id,
        parking_lot_id=parking_lot_id,
        timestamp=info.timestamp,
    )
    db.add(activity_log)
    db.commit()
    return parking_space


@app.post('/validate/out', status_code=status.HTTP_204_NO_CONTENT)
def validate_out(
        camera: CameraDependency,
        db: DatabaseDependency,
        info: ValidateModel
):
    license_plate = info.license_plate
    vehicle = db.query(Vehicle).filter(Vehicle.license_plate == license_plate).first()
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Vehicle not registered')
    if vehicle.owner_id != info.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Vehicle not owned by user')
    activity_log = ActivityLog(
        activity_type='out',
        vehicle_id=vehicle.id,
        parking_lot_id=camera.parking_lot_id,
        timestamp=info.timestamp,
    )
    db.add(activity_log)
    db.commit()
    return


@app.get('/vehicles', response_model=list[VehicleReport], status_code=status.HTTP_200_OK)
def get_vehicle_by_hour(
        redis: RedisDependency,
        final_time: int = Query(default_factory=lambda: int(datetime.utcnow().timestamp()), ge=0),
        hour_range: int = Query(default=24, ge=1, le=24),
):
    res = []
    for hour in range(hour_range):
        datetime_format = datetime.fromtimestamp(final_time - 3600 * hour).strftime("%Y-%m-%d %H:00:00")
        key = f'parking_lot_vehicle:{datetime_format}'
        record = {
            'hour': datetime_format,
        }
        for vehicle_type in ['car', 'motorbike', 'truck']:
            vehicle = redis.hget(key, vehicle_type)
            if not vehicle:
                vehicle = 0
            record[vehicle_type] = int(vehicle)
        res.append(record)
    return res


@app.get('/', status_code=status.HTTP_200_OK)
def health_check():
    return {'message': 'OK'}
