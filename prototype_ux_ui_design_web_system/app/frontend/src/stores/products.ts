import { defineStore } from 'pinia'
import { api, type Product } from '@/api/client'

export const useProductsStore = defineStore('products', {
  state: () => ({
    products: [] as Product[],
    loaded: false,
    loading: false,
    error: '' as string,
  }),
  getters: {
    totalProjects: (s) => s.products.reduce((n, p) => n + p.projects.length, 0),
  },
  actions: {
    async fetchAll() {
      this.loading = true
      this.error = ''
      try {
        this.products = await api<Product[]>('/api/products')
        this.loaded = true
      } catch (e) {
        this.error = e instanceof Error ? e.message : String(e)
      } finally {
        this.loading = false
      }
    },
    async createProduct(payload: { name: string; requirement_doc: string; project: { name: string; platform: string } }) {
      const product = await api<Product>('/api/products', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      await this.fetchAll()
      return product
    },
  },
})
