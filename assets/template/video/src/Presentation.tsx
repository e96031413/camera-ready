import React from "react";
import {
  TransitionSeries,
  linearTiming,
} from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { SlideScene } from "./SlideScene";
import type { PresentationProps } from "./Root";

export const Presentation: React.FC<PresentationProps> = ({
  slides,
  transitionDurationFrames,
}) => {
  if (slides.length === 0) {
    return (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#000",
          color: "#fff",
          fontSize: 48,
          fontFamily: "sans-serif",
        }}
      >
        No slides provided
      </div>
    );
  }

  return (
    <TransitionSeries>
      {slides.map((slide, index) => {
        const elements: React.ReactNode[] = [];

        // Add slide sequence
        elements.push(
          <TransitionSeries.Sequence
            key={`slide-${index}`}
            durationInFrames={slide.durationInFrames}
          >
            <SlideScene
              imagePath={slide.imagePath}
              audioPath={slide.audioPath}
              durationInFrames={slide.durationInFrames}
            />
          </TransitionSeries.Sequence>,
        );

        // Add transition between slides (not after the last one)
        if (index < slides.length - 1) {
          elements.push(
            <TransitionSeries.Transition
              key={`transition-${index}`}
              presentation={fade()}
              timing={linearTiming({
                durationInFrames: transitionDurationFrames,
              })}
            />,
          );
        }

        return elements;
      })}
    </TransitionSeries>
  );
};
