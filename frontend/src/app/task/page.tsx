"use client";

import React, { useState, useEffect } from "react";
import Header from "@/components/Header";
import { Plus, Edit, Trash2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button as ShadcnButton } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Client } from "@langchain/langgraph-sdk";
import { useAuth } from "@/contexts/AuthContext";
import { Thread } from "@/components/thread";
import { ThreadProvider } from "@/providers/Thread";
import { StreamProvider } from "@/providers/Stream";
import { ArtifactProvider } from "@/components/thread/artifact";
import { cn } from "@/lib/utils";
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
import { useQueryState } from "nuqs";

interface Task {
  id: string;
  name: string;
  description?: string;
  agent_id: string;
  prompt: string;
  session_id?: string;
  assistant_id?: string;
  user_id: string;
  created_at: string;
  updated_at?: string;
}

interface Agent {
  id: string;
  name: string;
  description: string;
  graph_name: string;
}

// Custom Sidebar component for projects
function TaskSidebar({
  currentTask,
  setCurrentTask,
}: {
  currentTask: Task | null;
  setCurrentTask: (task: Task | null) => void;
}) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    agent_id: "",
    prompt: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [openTasks, setOpenTasks] = useState(true);
  const [showThreadList, setShowThreadList] = useQueryState("showThreadList", {
    defaultValue: "false",
  });
  const [runStatus, setRunStatus] = useState<{
    threadId: string;
    status: string;
    runId?: string;
    interrupt?: any;
  } | null>(null);

  const { session } = useAuth();

  // Fetch projects and agents
  useEffect(() => {
    fetchTasks();
    fetchAgents();
  }, []);

  // Clean up run status when project changes
  useEffect(() => {
    if (runStatus && runStatus.threadId !== currentTask?.session_id) {
      setRunStatus(null);
    }
  }, [currentTask, runStatus]);

  const fetchTasks = async () => {
    try {
      const response = await fetch("/api/tasks");
      if (response.ok) {
        const data = await response.json();
        setTasks(data);
        // Set first project as current if none selected
        if (data.length > 0 && !currentTask) {
          setCurrentTask(data[0]);
        }
      }
    } catch (error) {
      console.error("Error fetching tasks:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAgents = async () => {
    try {
      const response = await fetch("/api/agents");
      if (response.ok) {
        const data = await response.json();
        setAgents(data);
      }
    } catch (error) {
      console.error("Error fetching agents:", error);
    }
  };

  const createLangGraphClient = () => {
    const apiUrl = process.env.NEXT_PUBLIC_LANGGRAPH_API_URL;
    const accessToken = session?.access_token;

    if (!accessToken) {
      throw new Error(
        "No access token found. User might not be authenticated."
      );
    }

    return new Client({
      apiUrl,
      defaultHeaders: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
  };

  const handleCreateTask = () => {
    setFormData({ name: "", description: "", agent_id: "", prompt: "" });
    setCreateDialogOpen(true);
  };

  const handleEditTask = (task: Task) => {
    setSelectedTask(task);
    setFormData({
      name: task.name,
      description: task.description || "",
      agent_id: task.agent_id,
      prompt: task.prompt,
    });
    setEditDialogOpen(true);
  };

  const handleDeleteTask = (task: Task) => {
    setSelectedTask(task);
    setDeleteDialogOpen(true);
  };

  const handleFormSubmit = async (isEdit: boolean = false) => {
    if (!formData.name || !formData.agent_id || !formData.prompt) {
      alert("Please fill in all required fields (Name, Agent, and Prompt)");
      return;
    }

    setSubmitting(true);

    try {
      let threadId = selectedTask?.session_id;
      let assistantId = selectedTask?.assistant_id;

      // Create thread and assistant if it's a new project or if editing and no thread exists
      if (!isEdit || !threadId) {
        const client = createLangGraphClient();
        const agent = agents.find((a) => a.id === formData.agent_id);
        if (!agent) {
          alert("Selected agent not found");
          return;
        }

        // Create assistant first
        const assistant = await client.assistants.create({
          graphId: "task_graph",
          config: {
            configurable: {
              graph_name: agent.graph_name,
            },
          },
        });
        assistantId = assistant.assistant_id;

        // Create thread
        const thread = await client.threads.create();
        threadId = thread.thread_id;
      }

      const taskData = {
        ...formData,
        session_id: threadId,
        assistant_id: assistantId,
      };

      const url = isEdit ? `/api/tasks/${selectedTask?.id}` : "/api/tasks";
      const method = isEdit ? "PUT" : "POST";

      const response = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(taskData),
      });

      if (response.ok) {
        const updatedTask = await response.json();
        await fetchTasks();
        setCreateDialogOpen(false);
        setEditDialogOpen(false);
        setFormData({ name: "", description: "", agent_id: "", prompt: "" });
        setSelectedTask(null);

        // Set as current task if it's new
        if (!isEdit) {
          setCurrentTask(updatedTask);
        }

        // Start the run if it's a new task
        if (!isEdit && threadId && assistantId) {
          await startRun(threadId, assistantId, formData.prompt);
        }
      } else {
        const error = await response.json();
        alert(`Error: ${error.error}`);
      }
    } catch (error) {
      console.error("Error saving task:", error);
      alert("Failed to save task");
    } finally {
      setSubmitting(false);
    }
  };

  const startRun = async (
    threadId: string,
    assistantId: string,
    prompt: string
  ) => {
    try {
      const client = createLangGraphClient();

      const run = await client.runs.create(threadId, assistantId, {
        streamMode: ["messages-tuple", "values"],
        streamSubgraphs: true,
        input: { messages: [{ role: "user", content: prompt }] },
        multitaskStrategy: "enqueue",
        config: {
          configurable: {
            graph_name: currentTask?.agent_id,
          },
        },
      });

      // Set up run status monitoring
      setRunStatus({
        threadId,
        status: "running",
        runId: run.run_id,
      });

      // Start monitoring the run status
      monitorRunStatus(threadId, run.run_id);
    } catch (error) {
      console.error("Error starting run:", error);
    }
  };

  const monitorRunStatus = async (threadId: string, runId: string) => {
    try {
      const client = createLangGraphClient();

      // Poll the run status
      const pollInterval = setInterval(async () => {
        try {
          const run = await client.runs.get(threadId, runId);

          if (run.status === "interrupted") {
            // Get thread state to check for interrupts
            const threadState = await client.threads.getState(threadId);

            setRunStatus({
              threadId,
              status: "interrupted",
              runId,
              interrupt: threadState.tasks?.[0] || null,
            });
            clearInterval(pollInterval);
          } else if (run.status === "success" || run.status === "error") {
            setRunStatus({
              threadId,
              status: run.status,
              runId,
            });
            clearInterval(pollInterval);
          }
        } catch (error) {
          console.error("Error polling run status:", error);
          clearInterval(pollInterval);
        }
      }, 2000); // Poll every 2 seconds

      // Clean up after 5 minutes to prevent infinite polling
      setTimeout(
        () => {
          clearInterval(pollInterval);
        },
        5 * 60 * 1000
      );
    } catch (error) {
      console.error("Error monitoring run status:", error);
    }
  };

  const handleResumeRun = async (resumeValue?: any) => {
    if (
      !runStatus ||
      runStatus.status !== "interrupted" ||
      !currentTask?.assistant_id
    )
      return;

    try {
      const client = createLangGraphClient();

      // Resume the run using Command with resume value
      const resumeRun = await client.runs.create(
        runStatus.threadId,
        currentTask.assistant_id,
        {
          command: { resume: resumeValue || true },
        }
      );

      // Update status and continue monitoring
      setRunStatus({
        ...runStatus,
        status: "running",
        runId: resumeRun.run_id,
      });

      monitorRunStatus(runStatus.threadId, resumeRun.run_id);
    } catch (error) {
      console.error("Error resuming run:", error);
    }
  };

  const confirmDeleteTask = async () => {
    if (!selectedTask) return;

    setSubmitting(true);

    try {
      const response = await fetch(`/api/tasks/${selectedTask.id}`, {
        method: "DELETE",
      });

      if (response.ok) {
        await fetchTasks();
        setDeleteDialogOpen(false);
        // Reset current task if it was deleted
        if (currentTask?.id === selectedTask.id) {
          setCurrentTask(null);
        }
        setSelectedTask(null);
      } else {
        const error = await response.json();
        alert(`Error: ${error.error}`);
      }
    } catch (error) {
      console.error("Error deleting task:", error);
      alert("Failed to delete task");
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const getAgentName = (agentId: string) => {
    const agent = agents.find((a) => a.id === agentId);
    return agent?.name || "Unknown Agent";
  };

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

  return (
    <>
      <div className="flex-shrink-0 w-64 bg-[#F9FAFB] border-r-0">
        <div className="flex flex-col pb-9 pt-6">
          <div className="flex items-center justify-between px-11">
            <span className="text-xl font-semibold flex-shrink-0">Tasks</span>
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
                {/* Create Task Button */}
                <div className="px-7 mb-4">
                  <ShadcnButton
                    onClick={handleCreateTask}
                    className="w-full flex items-center gap-2"
                    size="sm"
                  >
                    <Plus className="w-4 h-4" />
                    New Task
                  </ShadcnButton>
                </div>

                {/* Show Thread List Toggle */}
                <div className="px-7 mb-4">
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="show-thread-list"
                      checked={showThreadList === "true"}
                      onCheckedChange={(checked) =>
                        setShowThreadList(checked ? "true" : "false")
                      }
                    />
                    <Label htmlFor="show-thread-list" className="text-sm">
                      Show Thread List
                    </Label>
                  </div>
                </div>

                {/* Interrupt Status */}
                {runStatus?.status === "interrupted" &&
                  runStatus.threadId === currentTask?.session_id && (
                    <div className="px-7 mb-4">
                      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-2">
                          <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></div>
                          <span className="text-sm font-medium text-yellow-800">
                            Run Interrupted
                          </span>
                        </div>
                        <p className="text-xs text-yellow-700 mb-3">
                          {runStatus.interrupt?.name === "chatbot"
                            ? "The chatbot has paused and is waiting for your approval to continue."
                            : "The agent has paused and is waiting for your input or approval to continue."}
                        </p>
                        <div className="flex flex-col gap-2">
                          <div className="flex gap-2">
                            <ShadcnButton
                              size="sm"
                              onClick={() => handleResumeRun(true)}
                              className="text-xs flex-1"
                            >
                              ✓ Continue
                            </ShadcnButton>
                            <ShadcnButton
                              size="sm"
                              variant="outline"
                              onClick={() => handleResumeRun(false)}
                              className="text-xs flex-1"
                            >
                              ✗ Stop
                            </ShadcnButton>
                          </div>
                          <ShadcnButton
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              const customInput = prompt(
                                "Enter custom resume value (optional):"
                              );
                              handleResumeRun(customInput || "user_input");
                            }}
                            className="text-xs"
                          >
                            Custom Input
                          </ShadcnButton>
                        </div>
                      </div>
                    </div>
                  )}

                {/* Run Status Indicator */}
                {runStatus &&
                  runStatus.threadId === currentTask?.session_id &&
                  runStatus.status !== "interrupted" && (
                    <div className="px-7 mb-4">
                      <div
                        className={cn(
                          "flex items-center gap-2 px-3 py-2 rounded-lg text-xs",
                          runStatus.status === "running" &&
                            "bg-blue-50 text-blue-700 border border-blue-200",
                          runStatus.status === "success" &&
                            "bg-green-50 text-green-700 border border-green-200",
                          runStatus.status === "error" &&
                            "bg-red-50 text-red-700 border border-red-200"
                        )}
                      >
                        <div
                          className={cn(
                            "w-2 h-2 rounded-full",
                            runStatus.status === "running" &&
                              "bg-blue-500 animate-pulse",
                            runStatus.status === "success" && "bg-green-500",
                            runStatus.status === "error" && "bg-red-500"
                          )}
                        ></div>
                        <span className="font-medium">
                          {runStatus.status === "running" && "Running..."}
                          {runStatus.status === "success" && "Completed"}
                          {runStatus.status === "error" && "Error"}
                        </span>
                      </div>
                    </div>
                  )}

                {/* Collapsible Tasks Section */}
                <Collapsible open={openTasks} onOpenChange={setOpenTasks}>
                  <CollapsibleTrigger asChild>
                    <div className="flex items-center cursor-pointer select-none text-sm font-medium text-gray-500 mb-2 pl-2">
                      <span className="mr-2">My Tasks</span>
                      <span>{openTasks ? "▾" : "▸"}</span>
                    </div>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <div className="flex flex-col gap-2 pl-7 mb-6">
                      {tasks.length === 0 ? (
                        <p className="text-sm text-gray-500 p-2">
                          No tasks yet
                        </p>
                      ) : (
                        tasks.map((task, idx) => {
                          const label = task.name;
                          return (
                            <div
                              key={`task-${task.id}-${idx}`}
                              className={cn(
                                "flex items-center w-full",
                                currentTask?.id === task.id
                                  ? "bg-gray-100 rounded-md"
                                  : ""
                              )}
                            >
                              <TooltipProvider>
                                <Tooltip delayduration={200}>
                                  <TooltipTrigger asChild>
                                    <button
                                      className="flex items-center gap-2 p-2 w-full text-left hover:bg-gray-100 rounded-md"
                                      onClick={() => setCurrentTask(task)}
                                    >
                                      <div
                                        className="w-6 h-6 rounded-md flex-shrink-0 flex items-center justify-center text-white"
                                        style={{
                                          background:
                                            gradients[
                                              hashString(task.id) %
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
                                  <TooltipContent>
                                    <div>
                                      <p className="font-medium">{label}</p>
                                      <p className="text-xs text-gray-500">
                                        {getAgentName(task.agent_id)}
                                      </p>
                                      <p className="text-xs text-gray-500">
                                        Created {formatDate(task.created_at)}
                                      </p>
                                    </div>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                              <div className="flex gap-1 pr-2">
                                <ShadcnButton
                                  variant="ghost"
                                  size="sm"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleEditTask(task);
                                  }}
                                  className="h-6 w-6 p-0"
                                >
                                  <Edit className="w-3 h-3" />
                                </ShadcnButton>
                                <ShadcnButton
                                  variant="ghost"
                                  size="sm"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDeleteTask(task);
                                  }}
                                  className="h-6 w-6 p-0"
                                >
                                  <Trash2 className="w-3 h-3" />
                                </ShadcnButton>
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Create/Edit Task Dialog */}
      <Dialog
        open={createDialogOpen || editDialogOpen}
        onOpenChange={(open) => {
          if (!open) {
            setCreateDialogOpen(false);
            setEditDialogOpen(false);
            setFormData({
              name: "",
              description: "",
              agent_id: "",
              prompt: "",
            });
            setSelectedTask(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>
              {editDialogOpen ? "Edit Task" : "Create New Task"}
            </DialogTitle>
            <DialogDescription>
              {editDialogOpen
                ? "Update your task details."
                : "Create a new task and run it with an agent."}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Task Name</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                placeholder="Enter task name"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                placeholder="Describe your task (optional)"
                rows={3}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="agent">Select Agent</Label>
              <Select
                value={formData.agent_id}
                onValueChange={(value) =>
                  setFormData({ ...formData, agent_id: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Choose an agent" />
                </SelectTrigger>
                <SelectContent>
                  {agents.map((agent) => (
                    <SelectItem key={agent.id} value={agent.id}>
                      {agent.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="prompt">Initial Prompt</Label>
              <Textarea
                id="prompt"
                value={formData.prompt}
                onChange={(e) =>
                  setFormData({ ...formData, prompt: e.target.value })
                }
                placeholder="Enter your initial prompt for the agent"
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <ShadcnButton
              variant="outline"
              onClick={() => {
                setCreateDialogOpen(false);
                setEditDialogOpen(false);
              }}
            >
              Cancel
            </ShadcnButton>
            <ShadcnButton
              onClick={() => handleFormSubmit(editDialogOpen)}
              disabled={submitting}
            >
              {submitting
                ? "Saving..."
                : editDialogOpen
                  ? "Update Task"
                  : "Create & Run"}
            </ShadcnButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete the task "{selectedTask?.name}" and
              stop any running threads. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDeleteTask}
              disabled={submitting}
            >
              {submitting ? "Deleting..." : "Delete Task"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

export default function TaskPage() {
  const [currentTask, setCurrentTask] = useState<Task | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [showThreadList] = useQueryState("showThreadList", {
    defaultValue: "false",
  });
  const [chatHistoryOpen, setChatHistoryOpen] = useQueryState(
    "chatHistoryOpen",
    { defaultValue: "false" }
  );
  const [threadId, setThreadId] = useQueryState("threadId");
  const [assistantId, setAssistantId] = useQueryState("assistantId");

  // Sync showThreadList with chatHistoryOpen
  useEffect(() => {
    setChatHistoryOpen(showThreadList);
  }, [showThreadList, setChatHistoryOpen]);

  // Set threadId and assistantId when currentTask changes
  useEffect(() => {
    if (currentTask?.session_id) {
      setThreadId(currentTask.session_id);
    } else {
      setThreadId(null);
    }

    // Set assistantId based on current task's assistant_id
    if (currentTask?.assistant_id) {
      setAssistantId(currentTask.assistant_id);
    } else {
      setAssistantId(null);
    }
  }, [currentTask, setThreadId, setAssistantId]);

  const fetchAgents = async () => {
    try {
      const response = await fetch("/api/agents");
      if (response.ok) {
        const data = await response.json();
        setAgents(data);
      }
    } catch (error) {
      console.error("Error fetching agents:", error);
    }
  };

  const getCurrentAgent = () => {
    if (!currentTask) return null;
    return agents.find((a) => a.id === currentTask.agent_id);
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const currentAgent = getCurrentAgent();

  return (
    <div className="flex flex-col h-screen w-full">
      <Header currentView="task" />
      <div className="flex flex-1 flex-row overflow-y-auto w-full gap-6 pt-6 pl-6 bg-[#F9FAFB]">
        <TaskSidebar
          currentTask={currentTask}
          setCurrentTask={setCurrentTask}
        />

        {/* Main content - Thread view */}
        <div className="flex flex-col gap-6 w-full">
          <div
            className={cn(
              "bg-white rounded-tl-[58px] h-full",
              "overflow-x-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100"
            )}
          >
            <div className="flex flex-col w-full h-full">
              {currentTask && currentTask.session_id && currentAgent ? (
                <ThreadProvider
                  assistantId={currentTask.assistant_id}
                  apiUrl={process.env.NEXT_PUBLIC_LANGGRAPH_API_URL}
                >
                  <StreamProvider
                    apiUrl={process.env.NEXT_PUBLIC_LANGGRAPH_API_URL}
                    assistantId={currentTask.assistant_id}
                  >
                    <ArtifactProvider>
                      <Thread />
                    </ArtifactProvider>
                  </StreamProvider>
                </ThreadProvider>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-gray-500">
                  <h3 className="text-lg font-semibold mb-2">
                    {currentTask ? "Loading task..." : "No task selected"}
                  </h3>
                  <p className="text-sm">
                    {currentTask
                      ? "Setting up your task workspace..."
                      : "Select a task from the sidebar to start chatting"}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
