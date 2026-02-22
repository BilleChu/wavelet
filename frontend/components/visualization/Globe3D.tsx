'use client'

import { useRef, useMemo, useState, useEffect, Suspense } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Sphere, Html, useTexture } from '@react-three/drei'
import * as THREE from 'three'

interface GlobalEvent {
  id: string
  title: string
  description: string
  type: 'market' | 'policy' | 'economic' | 'geopolitical' | 'technology'
  lat: number
  lng: number
  time: string
  impact: 'high' | 'medium' | 'low'
}

interface CityMarker {
  name: string
  lat: number
  lng: number
  importance: 'major' | 'secondary'
}

const majorCities: CityMarker[] = [
  { name: '纽约', lat: 40.7128, lng: -74.006, importance: 'major' },
  { name: '伦敦', lat: 51.5074, lng: -0.1278, importance: 'major' },
  { name: '东京', lat: 35.6762, lng: 139.6503, importance: 'major' },
  { name: '上海', lat: 31.2304, lng: 121.4737, importance: 'major' },
  { name: '香港', lat: 22.3193, lng: 114.1694, importance: 'major' },
  { name: '新加坡', lat: 1.3521, lng: 103.8198, importance: 'major' },
]

const eventTypeColors: Record<string, string> = {
  market: '#f59e0b',
  policy: '#8b5cf6',
  economic: '#10b981',
  geopolitical: '#ef4444',
  technology: '#06b6d4',
}

function latLngToVector3(lat: number, lng: number, radius: number): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180)
  const theta = (lng + 180) * (Math.PI / 180)
  const x = -(radius * Math.sin(phi) * Math.cos(theta))
  const z = radius * Math.sin(phi) * Math.sin(theta)
  const y = radius * Math.cos(phi)
  return new THREE.Vector3(x, y, z)
}

function Earth({ rotationSpeed = 0.001 }: { rotationSpeed?: number }) {
  const meshRef = useRef<THREE.Mesh>(null)
  const [hovered, setHovered] = useState(false)
  
  useFrame((_, delta) => {
    if (meshRef.current && !hovered) {
      meshRef.current.rotation.y += rotationSpeed
    }
  })
  
  const earthMaterial = useMemo(() => {
    return new THREE.ShaderMaterial({
      uniforms: { time: { value: 0 } },
      vertexShader: `
        varying vec3 vNormal;
        void main() {
          vNormal = normalize(normalMatrix * normal);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float time;
        varying vec3 vNormal;
        void main() {
          vec3 baseColor = vec3(0.05, 0.08, 0.12);
          float fresnel = pow(1.0 - abs(dot(vNormal, vec3(0.0, 0.0, 1.0))), 2.0);
          vec3 glowColor = vec3(0.2, 0.4, 0.6);
          vec3 finalColor = mix(baseColor, glowColor, fresnel * 0.3);
          gl_FragColor = vec4(finalColor, 1.0);
        }
      `,
      transparent: true,
    })
  }, [])
  
  useFrame(({ clock }) => {
    if (earthMaterial.uniforms) {
      earthMaterial.uniforms.time.value = clock.getElapsedTime()
    }
  })
  
  return (
    <Sphere ref={meshRef} args={[2, 64, 64]} onPointerOver={() => setHovered(true)} onPointerOut={() => setHovered(false)}>
      <primitive object={earthMaterial} attach="material" />
    </Sphere>
  )
}

function Atmosphere() {
  return (
    <Sphere args={[2.15, 64, 64]}>
      <meshBasicMaterial color="#1a4a6e" transparent opacity={0.15} side={THREE.BackSide} />
    </Sphere>
  )
}

interface Globe3DProps {
  events?: GlobalEvent[]
  onEventClick?: (event: GlobalEvent) => void
  onCityClick?: (city: CityMarker) => void
  showCities?: boolean
  showConnections?: boolean
  rotationSpeed?: number
  className?: string
}

export default function Globe3D({
  events = [],
  onEventClick,
  onCityClick,
  showCities = true,
  showConnections = true,
  rotationSpeed = 0.0005,
  className = '',
}: Globe3DProps) {
  const [mounted, setMounted] = useState(false)
  
  useEffect(() => { setMounted(true) }, [])
  
  if (!mounted) {
    return <div className={`w-full h-full flex items-center justify-center ${className}`}>
      <div className="w-16 h-16 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
    </div>
  }
  
  return (
    <div className={`w-full h-full ${className}`}>
      <Canvas camera={{ position: [0, 0, 5], fov: 45 }} gl={{ antialias: true, alpha: true }} dpr={[1, 2]}>
        <Suspense fallback={null}>
          <ambientLight intensity={0.3} />
          <pointLight position={[10, 10, 10]} intensity={0.5} />
          <Earth rotationSpeed={rotationSpeed} />
          <Atmosphere />
        </Suspense>
      </Canvas>
    </div>
  )
}

export type { GlobalEvent, CityMarker }
