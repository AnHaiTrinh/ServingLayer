from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from .db import DatabaseDependency
from .models import Sensor, Camera

api_key_header = APIKeyHeader(name="X-API-Key")


def get_sensor_by_api_key(db: DatabaseDependency, api_key: str = Depends(api_key_header)):
    sensor = db.query(Sensor).filter(Sensor.api_key == api_key).first()
    if not sensor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Invalid API key')
    return sensor


SensorDependency = Annotated[Sensor, Depends(get_sensor_by_api_key)]


def get_camera_by_api_key(db: DatabaseDependency, api_key: str = Depends(api_key_header)):
    camera = db.query(Camera).filter(Camera.api_key == api_key).first()
    if not camera:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Invalid API key')
    return camera


CameraDependency = Annotated[Camera, Depends(get_camera_by_api_key)]
