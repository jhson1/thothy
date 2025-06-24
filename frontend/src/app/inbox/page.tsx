"use client";

import { AgentInbox } from "@/components/agent-inbox";
import React, { useEffect, useState } from "react";
import { Toaster } from "sonner";
import { ThreadsProvider } from "@/components/agent-inbox/contexts/ThreadContext";
import { SidebarProvider } from "@/components/ui/sidebar";
import Header from "@/components/Header";
import { AppSidebarTrigger } from "@/components/app-sidebar";
import { BreadCrumb } from "@/components/agent-inbox/components/breadcrumb";
import { cn } from "@/lib/utils";
import { useThreadsContext } from "@/components/agent-inbox/contexts/ThreadContext";
import { prettifyText } from "@/components/agent-inbox/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";

// Custom Sidebar component that can scroll with parent
function CustomScrollableSidebar() {
  const { agentInboxes, changeAgentInbox, loading } = useThreadsContext();
  const [openInboxes, setOpenInboxes] = useState(true);
  const [openAgent, setOpenAgent] = useState(true);
  const [isLoadingAgents, setIsLoadingAgents] = useState(false);

  // No need to fetch projects from supabase anymore
  // Instead, we'll filter for project_graph directly from agentInboxes

  const gradients = [
    "linear-gradient(to right, #FF416C, #FF4B2B)",
    "linear-gradient(to right, #4158D0, #C850C0)",
    "linear-gradient(to right, #0093E9, #80D0C7)",
    "linear-gradient(to right, #8EC5FC, #E0C3FC)",
    "linear-gradient(to right, #43E97B, #38F9D7)",
    "linear-gradient(to right, #FA8BFF, #2BD2FF)",
    "linear-gradient(to right, #FEE140, #FA709A)",
    "linear-gradient(to right, #3EECAC, #EE74E1)",
    "linear-gradient(to right, #4facfe, #00f2fe)",
    "linear-gradient(to right, #F6D242, #FF52E5)",
    "linear-gradient(to right, #00C6FB, #005BEA)",
    "linear-gradient(to right, #FEC163, #DE4313)",
    "linear-gradient(to right, #92FE9D, #00C9FF)",
    "linear-gradient(to right, #FC466B, #3F5EFB)",
    "linear-gradient(to right, #3B2667, #BC78EC)",
  ];

  function hashString(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash;
    }
    return Math.abs(hash);
  }

  // Filter agents for Project and Agent lists
  // Show project_graph agents in the Project section
  const projectGraphAgents = agentInboxes.filter((inbox) =>
    inbox.graphId === "project_graph"
  );

  // Add default project_graph if none exist
  const projectAgentInboxes = projectGraphAgents.length > 0 ? projectGraphAgents : [
    {
      id: "default_project_graph",
      graphId: "project_graph",
      name: "Project Graph",
      selected: false
    }
  ];

  const otherAgentInboxes = agentInboxes.filter(
    (inbox) => inbox.graphId !== "project_graph"
  );

  return (
    <div className="flex-shrink-0 w-64 bg-[#F9FAFB] border-r-0">
      <div className="flex flex-col pb-9 pt-6">
        <div className="flex items-center justify-between px-11">
          <span className="text-xl font-semibold flex-shrink-0">Inbox</span>
          <AppSidebarTrigger isOutside={false} className="mt-1" />
        </div>
        <div className="flex-1 pt-6 px-2">
          {loading ? (
            <div className="flex flex-col gap-2 pl-7">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 p-2 animate-pulse"
                >
                  <div className="w-6 h-6 rounded-md bg-gray-200" />
                  <div className="h-4 bg-gray-200 rounded w-24" />
                </div>
              ))}
            </div>
          ) : (
            <>
              {/* Collapsible Project Section */}
              <Collapsible open={openInboxes} onOpenChange={setOpenInboxes}>
                <CollapsibleTrigger asChild>
                  <div className="flex items-center cursor-pointer select-none text-sm font-medium text-gray-500 mb-2 pl-2">
                    <span className="mr-2">Project</span>
                    <span>{openInboxes ? "▾" : "▸"}</span>
                  </div>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div className="flex flex-col gap-2 pl-7 mb-6">
                    {projectAgentInboxes.map((item, idx) => {
                      const label = item.name || prettifyText(item.graphId);
                      return (
                        <div
                          key={`graph-id-${item.graphId}-${idx}`}
                          className={cn(
                            "flex items-center w-full",
                            item.selected ? "bg-gray-100 rounded-md" : ""
                          )}
                        >
                          <TooltipProvider>
                            <Tooltip delayduration={200}>
                              <TooltipTrigger asChild>
                                <button
                                  className="flex items-center gap-2 p-2 w-full text-left hover:bg-gray-100 rounded-md"
                                  onClick={() =>
                                    changeAgentInbox(item.id, false)
                                  }
                                >
                                  <div
                                    className="w-6 h-6 rounded-md flex-shrink-0 flex items-center justify-center text-white"
                                    style={{
                                      background:
                                        gradients[
                                          hashString(item.graphId) %
                                            gradients.length
                                        ],
                                    }}
                                  >
                                    {label.slice(0, 1).toUpperCase()}
                                  </div>
                                  <span className="truncate min-w-0 font-medium text-gray-600">
                                    {label}
                                  </span>
                                </button>
                              </TooltipTrigger>
                              <TooltipContent>{label}</TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </div>
                      );
                    })}
                  </div>
                </CollapsibleContent>
              </Collapsible>

              {/* Collapsible Agent Section */}
              <Collapsible open={openAgent} onOpenChange={setOpenAgent}>
                <CollapsibleTrigger asChild>
                  <div className="flex items-center cursor-pointer select-none text-sm font-medium text-gray-500 mb-2 pl-2">
                    <span className="mr-2">Agent</span>
                    <span>{openAgent ? "▾" : "▸"}</span>
                  </div>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div className="flex flex-col gap-2 pl-7 mb-6">
                    {otherAgentInboxes.map((item, idx) => {
                        const label = item.name || prettifyText(item.graphId);
                        return (
                          <div
                            key={`graph-id-${item.graphId}-${idx}`}
                            className={cn(
                              "flex items-center w-full",
                              item.selected ? "bg-gray-100 rounded-md" : ""
                            )}
                          >
                            <TooltipProvider>
                              <Tooltip delayduration={200}>
                                <TooltipTrigger asChild>
                                  <button
                                    className="flex items-center gap-2 p-2 w-full text-left hover:bg-gray-100 rounded-md"
                                    onClick={() =>
                                      changeAgentInbox(item.id, false)
                                    }
                                  >
                                    <div
                                      className="w-6 h-6 rounded-md flex-shrink-0 flex items-center justify-center text-white"
                                      style={{
                                        background:
                                          gradients[
                                            hashString(item.graphId) %
                                              gradients.length
                                          ],
                                      }}
                                    >
                                      {label.slice(0, 1).toUpperCase()}
                                    </div>
                                    <span className="truncate min-w-0 font-medium text-gray-600">
                                      {label}
                                    </span>
                                  </button>
                                </TooltipTrigger>
                                <TooltipContent>{label}</TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          </div>
                        );
                      })
                    }
                  </div>
                </CollapsibleContent>
              </Collapsible>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function InboxPage(): React.ReactNode {
  return (
    <React.Suspense fallback={<div>Loading (layout)...</div>}>
      <Toaster position="top-right" expand={true} richColors />
      <div className="flex flex-col h-screen w-full">
        <Header currentView="inbox" />
        <ThreadsProvider>
          <SidebarProvider>
            {/* Scrollable area: custom sidebar + main content */}
            <div className="flex flex-1 flex-row overflow-y-auto w-full gap-6 pt-6 pl-6 bg-[#F9FAFB]">
              <CustomScrollableSidebar />
              {/* Main content */}
              <div className="flex flex-col gap-6 w-full">
                <AppSidebarTrigger isOutside={true} />
                <BreadCrumb className="pl-5" />
                <div
                  className={cn(
                    "bg-white rounded-tl-[58px]",
                    "overflow-x-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100"
                  )}
                >
                  <div className="flex flex-col w-full">
                    <AgentInbox />
                  </div>
                </div>
              </div>
            </div>
          </SidebarProvider>
        </ThreadsProvider>
      </div>
    </React.Suspense>
  );
}
