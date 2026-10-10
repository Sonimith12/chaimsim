import { MODEL_FIT, MODEL_PATHS } from '../../models/ModelRegistry'
import { BuildingModel, type BuildingProps } from './BuildingModel'

/** Suppliers and manufacturers: the largest building. */
export function FactoryModel(props: BuildingProps) {
  return <BuildingModel {...props} path={MODEL_PATHS.supplier} footprint={MODEL_FIT.supplier} />
}
