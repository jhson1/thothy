"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../contexts/AuthContext";
import { createClient } from "@/utils/supabase/client";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Pencil, Trash2 } from "lucide-react";

interface Agent {
  id: string;
  name: string;
  description: string;
  imageUrl?: string;
  graph_name: string;
  created_at?: string;
}

interface AgentCardProps {
  agent: Agent;
}

// Function to generate a consistent gradient based on agent name
const getGradientColors = (name: string): [string, string] => {
  // Simple hash function to generate consistent numbers from string
  const hash = name.split('').reduce((acc, char) => {
    return char.charCodeAt(0) + ((acc << 5) - acc);
  }, 0);

  // Vibrant color pairs with explicit typing
  const colorPairs: Array<[string, string]> = [
    ['#FF6B6B', '#4ECDC4'], // Red to Teal
    ['#FFE66D', '#4CB8C4'], // Yellow to Cyan
    ['#A64DFF', '#FF6B6B'], // Purple to Red
    ['#00D2FF', '#FF5E62'], // Blue to Coral
    ['#4776E6', '#8E54E9'], // Electric Blue to Purple
    ['#FF8008', '#FFC837'], // Orange to Yellow
    ['#7303c0', '#ec38bc'], // Deep Purple to Pink
    ['#38ef7d', '#11998e'], // Bright Green to Teal
  ];

  // Use hash to select a consistent color pair
  const pairIndex = Math.abs(hash) % colorPairs.length;
  return colorPairs[pairIndex];
};

export default function AgentCard({ agent }: AgentCardProps) {
  const router = useRouter();
  const { user } = useAuth();
  const supabase = createClient();

  const handleCardClick = () => {
    if (agent.graph_name) {
      router.push(`/agents/${agent.graph_name}`);
    } else {
      alert("This agent doesn't have a valid configuration");
    }
  };

  const [gradientStart, gradientEnd] = getGradientColors(agent.name);

  return (
    <Card className="flex flex-col h-full w-full max-w-full hover:shadow-md transition-shadow">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <CardTitle>{agent.name}</CardTitle>
          {agent.created_at && (
            <CardDescription>
              Added on {new Date(agent.created_at).toLocaleDateString()}
            </CardDescription>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col justify-between">
        <p className="text-sm text-muted-foreground mb-2 line-clamp-3 break-words overflow-hidden text-ellipsis">{agent.description}</p>
      </CardContent>
      <CardFooter className="flex flex-col gap-2 p-4 mt-auto sticky bottom-0 bg-white z-10">
        <Button
          variant="outline"
          className="w-full"
          onClick={handleCardClick}
        >
          Run
        </Button>
      </CardFooter>
    </Card>
  );
}
