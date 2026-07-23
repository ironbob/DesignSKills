// Keyframe easing mechanism — sample fixture for tech-mechanism-analysis.
// Demonstrates: store → find → interpolate(eased) → apply to render property.

export type Easing = "linear" | "ease-in-out";

export interface Keyframe {
  time: number;   // seconds
  value: number;
  easing: Easing; // curve applied toward the NEXT keyframe
}

// Storage: a single flat timeline (one animated property only).
// There is NO track dimension — frames is just a sorted list.
export class KeyframeTrack {
  private frames: Keyframe[] = [];

  // Produce: append a keyframe, keep sorted by time.
  addKeyframe(time: number, value: number, easing: Easing = "linear") {
    this.frames.push({ time, value, easing });
    this.frames.sort((a, b) => a.time - b.time);
    return this;
  }

  // Flow + Process: sample the animated value at time t.
  sampleAt(t: number): number {
    if (this.frames.length === 0) return 0;
    if (t <= this.frames[0].time) return this.frames[0].value;
    const last = this.frames[this.frames.length - 1];
    if (t >= last.time) return last.value;
    // Flow: linear scan for the surrounding keyframe pair.
    let i = 0;
    while (i < this.frames.length - 1 && this.frames[i + 1].time < t) {
      i++;
    }
    const a = this.frames[i];
    const b = this.frames[i + 1];
    // Process: normalize progress, apply easing, then linearly interpolate.
    const u = (t - a.time) / (b.time - a.time);
    const e = applyEasing(a.easing, u);
    return a.value + (b.value - a.value) * e;
  }
}

// Easing maps linear progress u∈[0,1] to eased progress.
// NOTE: closed enum + switch — curves are hardcoded, not data-driven.
export function applyEasing(easing: Easing, u: number): number {
  switch (easing) {
    case "linear":
      return u;
    case "ease-in-out":
      // cubic ease-in-out (piecewise)
      if (u < 0.5) return 4 * u * u * u;
      return 1 - Math.pow(-2 * u + 2, 3) / 2;
  }
  return u; // fallback (unreachable for valid Easing)
}
