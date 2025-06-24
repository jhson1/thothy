import React, { useEffect, useState, useRef } from "react";
import { useStreamContext } from "@langchain/langgraph-sdk/react-ui";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { MarkdownText } from "@/components/thread/markdown-text";

// TypeScript interfaces matching the Python classes from state.py
interface Section {
  name: string;
  description: string;
  research: boolean;
  content: string;
}

export default function DataResearchGraphComponent(props: {
  topic?: string;
  sections?: Section[];
  completed_sections?: Section[];
}) {
  const { meta } = useStreamContext<{ MetaType: { ui: any; artifact: any } }>();

  // Safely access meta.artifact with proper type checking
  const artifactMeta = (meta as any)?.artifact;
  const [ArtifactContent, { open, setOpen, context, setContext }] =
    artifactMeta || [
      {},
      { open: false, setOpen: () => {}, context: {}, setContext: () => {} },
    ];

  // State to persistently store sections so they don't get lost when props.sections becomes undefined
  const persistentSectionsRef = useRef<Section[]>([]);
  const [sectionData, setSectionData] = useState<Section[]>([]);

  useEffect(() => {
    setOpen(true);
  }, [props.sections, props.topic, props.completed_sections]);

  // Helper function to safely get sections array
  const getSectionsArray = (): Section[] => {
    if (!props.sections) {
      return [];
    }

    // Check if sections is the expected Sections object with sections property
    if (Array.isArray(props.sections)) {
      return props.sections;
    }

    return [];
  };

  // Initialize updated sections when props.sections changes
  useEffect(() => {
    if (
      props.sections &&
      props.sections.length > 0 &&
      props.completed_sections &&
      props.completed_sections.length > 0
    ) {
      return;
    }

    const sectionsArray = getSectionsArray();

    // Only update if we have sections AND (we don't have persistent sections OR the new sections are different)
    if (sectionsArray.length > 0) {
      const shouldUpdate =
        persistentSectionsRef.current.length === 0 ||
        JSON.stringify(persistentSectionsRef.current.map((s) => s.name)) !==
          JSON.stringify(sectionsArray.map((s) => s.name));

      if (shouldUpdate) {
        // Create a new array to avoid reference issues
        persistentSectionsRef.current = [...sectionsArray];
        setSectionData(persistentSectionsRef.current);
      }
    }
  }, [props.sections]);

  // Update persistentSectionsRef when completed_sections prop changes
  useEffect(() => {
    if (
      props.completed_sections &&
      props.completed_sections.length > 0 &&
      persistentSectionsRef.current.length > 0
    ) {
      // Update sections in persistentSectionsRef by matching name
      const updatedSections = persistentSectionsRef.current.map((section) => {
        const updated = props.completed_sections!.find(
          (completed) => completed.name === section.name
        );
        return updated ? { ...section, ...updated } : section;
      });

      persistentSectionsRef.current = updatedSections;
      setSectionData(persistentSectionsRef.current);
    }
  }, [props.completed_sections]);

  // Format the report content with proper markdown-like styling
  return (
    <div className="h-full">
      <button
        className="mb-4 px-4 py-2 rounded text-white bg-blue-600 hover:bg-blue-700 transition-colors font-semibold shadow"
        onClick={() => setOpen(!open)}
      >
        {open ? "Click to hide report" : "Click to display report"}
      </button>

      <ArtifactContent title={<div>{props.topic || "Data Research Report"}</div>}>
        <div
          className="space-y-4 max-h-[80vh] overflow-y-auto pr-2"
          style={{ scrollbarGutter: "stable", scrollbarWidth: "thin" }}
        >
          {/* Display sections if available */}
          {sectionData.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Report Sections</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {sectionData.map((section, index) => {
                    return (
                      <div
                        key={index}
                        className="border rounded-lg p-4 bg-gray-50"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="text-lg font-semibold">
                            {section.name}
                          </h3>
                        </div>
                        <p className="text-gray-600 mb-3">
                          {section.description}
                        </p>

                        {section.content && (
                          <div className="bg-white p-3 rounded border">
                            <div className="text-gray-700 leading-relaxed prose prose-sm max-w-none">
                              <MarkdownText>{section.content}</MarkdownText>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </ArtifactContent>
    </div>
  );
}
