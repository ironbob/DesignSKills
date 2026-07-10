# main.py — app 入口（FastAPI）
from fastapi import FastAPI
from app.api import orders
from app.services.payment import strategy
# 004 bootstrap
# 005
# 006
# 007
# 008
# 009
# 010
# 011
app = FastAPI()
app.include_router(orders.router)
# 014
# 015
# 016
# 017
# 018
# 019
# Kafka 消息队列配置
kafka = configure_kafka()
# 022
# 023
# 024
# Worker 消费订单事件
worker = OrderWorker(kafka)
