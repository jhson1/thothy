"use client";

import React, { useState, useEffect } from "react";
import AgentCard from "./AgentCard";
import { useAuth } from "../contexts/AuthContext";

interface Agent {
    id: string;
    name: string;
    description: string;
    graph_name?: string;
    code?: string;
}

export default function AgentHub() {
    const { user } = useAuth();
    const [agents, setAgents] = useState<Agent[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchAgents = async () => {
            setLoading(true);
            try {
                const response = await fetch("/api/agents");
                const data = await response.json();
                setAgents(data);
            } catch (error) {
                setAgents([]);
            } finally {
                setLoading(false);
            }
        };
        fetchAgents();
    }, []);

    if (loading) {
        return (
            <div className="flex justify-center items-center min-h-[200px]">
                <p>Loading...</p>
            </div>
        );
    }

    if (agents.length === 0) {
        return (
            <p className="text-center text-muted-foreground">
                No agents found. Start by creating your first agent!
            </p>
        );
    }

    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {agents.map((agent) => (
                <AgentCard key={agent.id} agent={agent} />
            ))}
        </div>
    );
} 