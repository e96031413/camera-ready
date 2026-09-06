import React from "react";
import { Composition } from "remotion";
import { Presentation } from "./Presentation";

export type SlideData = {
  imagePath: string;
  audioPath: string | null;
  durationInFrames: number;
  title: string;
};

export type PresentationProps = {
  slides: SlideData[];
  transitionDurationFrames: number;
  fps: number;
};

const calculateMetadata = ({
  props,
}: {
  props: PresentationProps;
}) => {
  const { slides, transitionDurationFrames } = props;

  // Total duration is the sum of all slide durations minus overlap from transitions.
  // There are (slides.length - 1) transitions, each overlapping by transitionDurationFrames.
  const totalSlideDuration = slides.reduce(
    (sum, slide) => sum + slide.durationInFrames,
    0,
  );
  const totalTransitionOverlap =
    slides.length > 1
      ? (slides.length - 1) * transitionDurationFrames
      : 0;
  const totalDuration = Math.max(
    1,
    totalSlideDuration - totalTransitionOverlap,
  );

  return {
    durationInFrames: totalDuration,
    fps: props.fps,
    width: 1920,
    height: 1080,
  };
};

export const Root: React.FC = () => {
  return (
    <Composition
      id="Presentation"
      component={Presentation}
      durationInFrames={300}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{
        slides: [],
        transitionDurationFrames: 15,
        fps: 30,
      }}
      calculateMetadata={calculateMetadata}
    />
  );
};
