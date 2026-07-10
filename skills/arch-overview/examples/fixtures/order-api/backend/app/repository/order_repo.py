# order_repo.py — 订单仓储层（PostgreSQL）
import psycopg2
# 003
# 004
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
# 015
# 016
# 017
# 018
# 019
# 020
# 021
# 022
# 023
from app.services.order_service import format_sku  # 反向依赖
# 025
# 026
# 027
# 028
# 029
    def save(self, order):
        self.db.insert(order)  # INSERT
# end
