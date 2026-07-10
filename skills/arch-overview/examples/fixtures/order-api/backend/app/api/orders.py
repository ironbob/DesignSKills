# orders.py — 订单 API 路由层
from fastapi import APIRouter
from app.services import order_service
# 004 router 定义
# 005
# 006
# 007
# 008
# 009
# 010
# 011
# 012
# 013
# 014
router = APIRouter()
@router.post("/orders")
def create_order(req):
    return order_service.create_order(req)
