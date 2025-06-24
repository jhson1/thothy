"use client";

import React from "react";
import { useParams } from "next/navigation";
import { Thread } from "@/components/thread";

export default function AgentPage() {
  // Get the assistantId from the URL
  const params = useParams();
  const assistantId = params?.graph_name as string;

  // Function to render the appropriate content based on agent type
  const renderAgentContent = () => {
    switch (assistantId) {
      case "chat_graph":
      case "data_graph":
      case "data_research_graph":
      case "dashboard_graph":
      case "task_graph":
      case "research_graph":
      case "slide_graph":
      case "slide_build_graph":
      case "ui_graph":
      case "ui_eval_graph":
      case "ui_build_graph":
        return <Thread />;
      default:
        return (
          <div className="container mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold mb-6">Agent: {assistantId}</h1>
            <p className="text-gray-600">
              This agent type is not yet implemented.
            </p>
          </div>
        );
    }
  };

  return renderAgentContent();
}
