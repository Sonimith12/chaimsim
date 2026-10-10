import { MODEL_FIT, MODEL_PATHS } from '../../models/ModelRegistry'
import { BuildingModel, type BuildingProps } from './BuildingModel'

/** Distribution centres: slightly smaller than a factory. */
export function WarehouseModel(props: BuildingProps) {
  return (
    <BuildingModel
      {...props}
      path={MODEL_PATHS.distribution_center}
      footprint={MODEL_FIT.distribution_center}
    />
  )
}
