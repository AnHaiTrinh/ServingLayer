import os
from typing import Annotated

import redis
from fastapi import Depends


def get_redis():
    r = redis.Redis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'))
    try:
        yield r
    finally:
        r.close()


RedisDependency = Annotated[redis.Redis, Depends(get_redis)]