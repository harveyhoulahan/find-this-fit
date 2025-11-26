"use client";

import { Hero } from "@/components/ui/helix-hero";
import { HeroParallax } from "@/components/ui/hero-parallax";
import { useState, useEffect } from "react";

const depopProducts = [
  {
    title: "Vintage Y2K Cargo Pants",
    link: "https://depop.com",
    thumbnail: "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=600&q=80",
  },
  {
    title: "90s Oversized Denim Jacket",
    link: "https://depop.com",
    thumbnail: "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=600&q=80",
  },
  {
    title: "Retro Sports Windbreaker",
    link: "https://depop.com",
    thumbnail: "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=600&q=80",
  },
  {
    title: "Vintage Band T-Shirt",
    link: "https://depop.com",
    thumbnail: "https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=600&q=80",
  },
  {
    title: "Leather Moto Jacket",
    link: "https://depop.com",
    thumbnail: "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=600&q=80",
  },
  {
    title: "Corduroy Flare Pants",
    link: "https://depop.com",
    thumbnail: "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=600&q=80",
  },
  {
    title: "Vintage Silk Blouse",
    link: "https://depop.com",
    thumbnail: "https://images.unsplash.com/photo-1618932260643-eee4a2f652a6?w=600&q=80",
  },
  {
    title: "90s Platform Sneakers",
    link: "https://depop.com",
    thumbnail: "https://images.unsplash.com/photo-1460353581641-37baddab0fa2?w=600&q=80",
  },
  {
    title: "Chunky Knit Cardigan",
    link: "https://depop.com",
    thumbnail: "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?w=600&q=80",
  },
  {
    title: "Vintage Leather Bag",
    link: "https://depop.com",
    thumbnail: "https://images.unsplash.com/photo-1590874103328-eac38a683ce7?w=600&q=80",
  },
  {
    title: "Retro Sunglasses",
    link: "https://depop.com",
    thumbnail: "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=600&q=80",
  },
  {
    title: "Vintage Denim Skirt",
    link: "https://depop.com",
    thumbnail: "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=600&q=80",
  },
  {
    title: "90s Bucket Hat",
    link: "https://depop.com",
    thumbnail: "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=600&q=80",
  },
  {
    title: "Oversized Hoodie",
    link: "https://depop.com",
    thumbnail: "https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=600&q=80",
  },
  {
    title: "Vintage Bomber Jacket",
    link: "https://depop.com",
    thumbnail: "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=600&q=80",
  },
];

export default function Home() {
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const scrolled = window.scrollY;
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      const progress = Math.min(scrolled / maxScroll, 1);
      setScrollProgress(progress);
    };

    window.addEventListener('scroll', handleScroll);
    handleScroll(); // Initial call
    
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="bg-white">
      <Hero scrollProgress={scrollProgress} />
      <HeroParallax products={depopProducts} />
    </div>
  );
}
