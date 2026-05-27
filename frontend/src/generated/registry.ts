import type { ComponentType } from 'react'

import { CustomerGeneratedPage, generatedCustomerGeneratedPageRoute } from './customer'
import { SupplierGeneratedPage, generatedSupplierGeneratedPageRoute } from './supplier'

export type GeneratedRuntimeRoute = {
  path: string
  title: string
  entity: string
  component: ComponentType
}

export const generatedRuntimeRoutes: GeneratedRuntimeRoute[] = [
  {
    path: `/generated${generatedCustomerGeneratedPageRoute.path}`,
    title: generatedCustomerGeneratedPageRoute.title,
    entity: 'customer',
    component: CustomerGeneratedPage,
  },
  {
    path: `/generated${generatedSupplierGeneratedPageRoute.path}`,
    title: generatedSupplierGeneratedPageRoute.title,
    entity: 'supplier',
    component: SupplierGeneratedPage,
  },
]
