import { NodeCircleProgram } from 'sigma/rendering'

// Fragment shader identical to sigma's NodeCircleProgram, but with a thin
// dark border ring drawn inside the circle edge (no extra GPU attributes needed).
const FRAGMENT_SHADER_WITH_BORDER = /*glsl*/ `
  precision mediump float;

  varying vec4 v_color;
  varying vec2 v_diffVector;
  varying float v_radius;
  varying float v_border;

  uniform float u_correctionRatio;

  const vec4 transparent = vec4(0.0, 0.0, 0.0, 0.0);

  void main(void) {
    float aa = u_correctionRatio * 2.0;
    float borderWidth = u_correctionRatio * 3.5;

    // dist: negative inside, 0-aa at edge, positive outside
    float dist = length(v_diffVector) - v_radius + aa;

    // outer fade (antialiasing)
    float t = 0.0;
    if (dist > aa) {
      t = 1.0;
    } else if (dist > 0.0) {
      t = dist / aa;
    }

    // border zone: outermost borderWidth pixels inside the circle
    float borderThreshold = aa - borderWidth;
    vec4 pixelColor = v_color;
    if (dist > borderThreshold) {
      float blend = clamp((dist - borderThreshold) / borderWidth, 0.0, 1.0);
      vec4 borderColor = vec4(0.0, 0.0, 0.0, v_color.a * 0.55);
      pixelColor = mix(v_color, borderColor, blend);
    }

    gl_FragColor = mix(pixelColor, transparent, t);
  }
`

export class NodeBorderProgram extends NodeCircleProgram {
  getDefinition() {
    const def = super.getDefinition()
    return { ...def, FRAGMENT_SHADER_SOURCE: FRAGMENT_SHADER_WITH_BORDER }
  }
}
