// orders.ts — 前端订单 API 客户端
import axios from 'axios'
// 003
// 004
// 005
// 006
// 007
export async function createOrder(payload) {
  return axios.post('/orders', payload)
}
