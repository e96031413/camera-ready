import React from "react";
import {
  useCurrentFrame,
  interpolate,
  Img,
  staticFile,
} from "remotion";
import { Audio } from "@remotion/media";

export type SlideSceneProps = {
  imagePath: string;
  audioPath: string | null;
  durationInFrames: number;
};

export const SlideScene: React.FC<SlideSceneProps> = ({
  imagePath,
  audioPath,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();

  // Ken Burns effect: subtle zoom from 1.0 to 1.02 over the full duration
  const scale = interpolate(
    frame,
    [0, durationInFrames],
    [1.0, 1.02],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        overflow: "hidden",
        backgroundColor: "#000",
        position: "relative",
      }}
    >
      <div
        style={{
          width: "100%",
          height: "100%",
          transform: `scale(${scale})`,
          transformOrigin: "center center",
        }}
      >
        <Img
          src={staticFile(imagePath)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      </div>

      {audioPath ? <Audio src={staticFile(audioPath)} /> : null}
    </div>
  );
};
