"use client";

import { useStreamContext } from "@langchain/langgraph-sdk/react-ui";
import { useEffect, useState } from "react";
import SlideContent from "./presentation/components/SlideContent";
import { FooterProvider } from "./context/footerContext";

interface DashboardGraphProps {
  presentation_and_slides: any;
  slides_count: number;
  presentation_id: string;
}

export default function DashboardGraphComponent(props: DashboardGraphProps) {
  // Get the data from an agent by two way
  // 1. Use the props from push_ui_message function
  // 2. Use the context from the artifact

  const { meta } = useStreamContext<{ MetaType: { ui: any; artifact: any } }>();
  const [ArtifactContent, { open, setOpen }] = (meta as any).artifact;

  useEffect(() => {
    setOpen(true);
  }, [props.presentation_id]);

  return (
    <div className="bg-white rounded-lg p-4">
      <button
        className="mb-4 px-4 py-2 rounded text-white bg-blue-600 hover:bg-blue-700 transition-colors font-semibold shadow"
        onClick={() => setOpen(!open)}
      >
        {open ? "Hide Slide Data" : "Show Slide Data"}
      </button>

      <ArtifactContent title={<div>Slide Generation Results</div>}>
        <div className="max-h-[600px] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-400 scrollbar-track-gray-100">
          <div className="space-y-4">
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="text-lg font-semibold text-gray-800 mb-2">
                Presentation Summary
              </h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium text-gray-600">
                    Presentation ID:
                  </span>
                  <div className="font-mono text-xs bg-gray-100 p-1 rounded mt-1">
                    {props.presentation_id}
                  </div>
                </div>
                <div>
                  <span className="font-medium text-gray-600">
                    Slides Count:
                  </span>
                  <div className="text-2xl font-bold text-blue-600 mt-1">
                    {props.slides_count}
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-gray-50 p-4 rounded-lg">
              <FooterProvider>
                {props.presentation_and_slides &&
                  props.presentation_and_slides.slides &&
                  props.presentation_and_slides.slides.length > 0 &&
                  props.presentation_and_slides.slides.map((slide, index) => (
                    <SlideContent
                      key={`${slide.type}-${index}-${slide.index}}`}
                      slide={slide}
                      index={index}
                      presentationId={props.presentation_id}
                      onDeleteSlide={() => {}}
                    />
                  ))}
              </FooterProvider>
            </div>
          </div>
        </div>
      </ArtifactContent>
    </div>
  );
}
