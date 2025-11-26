"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import type React from "react";
import { useMemo, useRef } from "react";
import * as THREE from "three";

interface StitchProps {
	scrollProgress?: number;
}

const StitchAnimation: React.FC<StitchProps> = ({ scrollProgress = 0 }) => {
	const meshRefs = useRef<THREE.Mesh[]>([]);

	// Create realistic stitch geometry - thread going THROUGH fabric
	const stitchGeometry = useMemo(() => {
		const curve = new THREE.CatmullRomCurve3([
			new THREE.Vector3(-0.4, 0, 0.3),     // Front left
			new THREE.Vector3(-0.2, 0.15, 0.05), // Entering fabric
			new THREE.Vector3(0, 0.3, -0.3),     // Behind fabric
			new THREE.Vector3(0.2, 0.45, 0.05),  // Exiting fabric
			new THREE.Vector3(0.4, 0.6, 0.3),    // Front right
		]);
		return new THREE.TubeGeometry(curve, 30, 0.05, 12, false);
	}, []);

	// Calculate how many stitches to show - progressive reveal
	const baseStitches = 15;
	const additionalStitches = Math.floor(scrollProgress * 100);
	const numStitches = baseStitches + additionalStitches;
	const stitches = Array.from({ length: numStitches }, (_, i) => i);

	console.log('Rendering', numStitches, 'stitches, scroll:', scrollProgress);

	return (
		<group position={[0, 8, 0]}>
			{/* Fabric plane - using theme background color */}
			<mesh position={[0, -8, 0]} receiveShadow>
				<planeGeometry args={[15, 80]} />
				<meshStandardMaterial 
					color="#f5f5f5"
					roughness={0.9}
					metalness={0}
					side={2}
				/>
			</mesh>

			{/* Accent color thread stitches (FFCC91 - peach/orange) */}
			{stitches.map((i) => (
				<mesh
					key={i}
					ref={(el) => { if (el) meshRefs.current[i] = el; }}
					geometry={stitchGeometry}
					position={[0, -i * 0.7, 0]}
					castShadow
				>
					<meshStandardMaterial
						color="#FFCC91"
						emissive="#FFCC91"
						emissiveIntensity={i === numStitches - 1 ? 0.4 : 0.15}
						metalness={0.3}
						roughness={0.5}
					/>
				</mesh>
			))}
		</group>
	);
};

interface SceneProps {
	scrollProgress: number;
}

const Scene: React.FC<SceneProps> = ({ scrollProgress }) => {
	return (
		<Canvas
			shadows
			camera={{
				position: [0, 0, 25],
				fov: 50,
			}}
			style={{ background: "#ffffff" }}
		>
			<ambientLight intensity={2.5} />
			<directionalLight 
				position={[5, 5, 8]} 
				intensity={3} 
				castShadow
				shadow-mapSize-width={2048}
				shadow-mapSize-height={2048}
			/>
			<spotLight
				position={[0, 10, 10]}
				angle={0.3}
				penumbra={1}
				intensity={2}
				castShadow
			/>
			
			<StitchAnimation scrollProgress={scrollProgress} />
		</Canvas>
	);
};

interface HeroProps {
	scrollProgress: number;
}

export const Hero: React.FC<HeroProps> = ({ scrollProgress }) => {
	console.log('Hero scroll progress:', scrollProgress);
	return (
		<section className="fixed inset-0 w-screen h-screen z-0">
			<div className="absolute inset-0 w-full h-full">
				<Scene scrollProgress={scrollProgress} />
			</div>
		</section>
	);
};
