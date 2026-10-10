/** Edit mode is lit a little brighter so the layout is easy to read. */
export function Lighting({ edit = false }: { edit?: boolean }) {
  return (
    <>
      <ambientLight intensity={edit ? 0.42 : 0.22} />
      <directionalLight
        position={[12, 20, 9]}
        intensity={1.35}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-34}
        shadow-camera-right={34}
        shadow-camera-top={34}
        shadow-camera-bottom={-34}
        shadow-camera-near={1}
        shadow-camera-far={80}
        shadow-bias={-0.0004}
      />
      <directionalLight position={[-8, 6, -10]} intensity={0.3} color="#6f8cff" />
    </>
  )
}
