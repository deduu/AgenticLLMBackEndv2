# app/routes/status.py
from fastapi import APIRouter
from ..models.model_pool import ParallelModelPool

router = APIRouter()

# Assume model_pool is initialized elsewhere and imported
from ..dependencies import medium_model_pool

@router.get("/model-pool-status")
async def get_model_pool_status():
    status = [{'device': instance['device'], 'in_use': instance['in_use']} for instance in medium_model_pool.model_instances]
    return {"model_instances": status}
