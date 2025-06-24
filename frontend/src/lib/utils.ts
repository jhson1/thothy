import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatLargeNumber(value: number): string {
  if (value >= 1_000_000_000_000) {
    return `${(value / 1_000_000_000_000).toFixed(1)}T`;
  } else if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)}B`;
  } else if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  } else if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}k`;
  }
  return value.toString();
}

export function randomChartGenerator() {
  const categories = ["Q1", "Q2", "Q3", "Q4"];
  const series = [
    {
      name: "Revenue",
      data: [
        Math.floor(Math.random() * 100) + 50,
        Math.floor(Math.random() * 100) + 50,
        Math.floor(Math.random() * 100) + 50,
        Math.floor(Math.random() * 100) + 50,
      ],
    },
  ];
  
  return {
    categories,
    series,
  };
}
