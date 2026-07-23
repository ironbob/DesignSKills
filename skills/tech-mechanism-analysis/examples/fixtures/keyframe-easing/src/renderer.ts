import { KeyframeTrack } from "./keyframe";

// Effect: bind a sampled value onto a render target's property.
export class PropertyBinding {
  constructor(private target: object, private property: string) {}

  // Called every frame: pull from track, write directly to the object.
  update(track: KeyframeTrack, time: number) {
    const v = track.sampleAt(time);
    (this.target as any)[this.property] = v;
  }
}
