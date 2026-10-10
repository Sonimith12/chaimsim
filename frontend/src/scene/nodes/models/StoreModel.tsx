import { MODEL_FIT, MODEL_PATHS } from '../../models/ModelRegistry'
import { BuildingModel, type BuildingProps } from './BuildingModel'

/** Retailers: the smallest building. */
export function StoreModel(props: BuildingProps) {
  return <BuildingModel {...props} path={MODEL_PATHS.retailer} footprint={MODEL_FIT.retailer} />
}
