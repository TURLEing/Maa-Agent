# Copilot screen actions

Local Copilot JSON may contain `Click` and `Swipe` actions in addition to deployment
and skill actions. These are MAA game-screen actions sent through the connected
controller, not desktop mouse coordinates.

Coordinates use the normalized **1280 x 720** game image. Rectangles are
`[x, y, width, height]`; all four values must be integers (not booleans), dimensions
must be positive, and the whole rectangle must fit in that image.

```json
[
  {"type":"Click", "rect":[800,430,1,1]},
  {"type":"Swipe", "begin":[980,670,1,1], "end":[820,330,1,1], "duration":1000}
]
```

For `Swipe`, an explicitly supplied `duration` must be a positive integer in
milliseconds. If omitted, MAA uses its default. Timing fields such as `pre_delay`,
`post_delay`, and battle conditions retain MAA's normal semantics.

Monitor size and Windows display scaling do not determine these coordinates.
The game aspect ratio, UI layout, camera position, operator ordering and timing
can affect whether an action hits its intended target. Bounds validation only
checks the coordinate format and extent; inspect the current game image and read
the author's requirements before execution. The observer currently requires a
normalized 1280 x 720 capture. Other coordinate spaces are not supported here.

Run these scripts through `run-copilot` after stage verification. Existing settings
still prohibit support units and sanity potions and enforce operator requirements.
`Command` actions remain rejected. Screen actions are not an unrestricted desktop
control API and are not accepted by the battle-only `resume` interface.

## Validation and attribution

On November 1, 2026, CN TL-10 completed with three stars using a screen-action
script from [PRTS Copilot 108697](https://prts.plus/copilot/108697), credited there
to 萨拉托加. The same script subsequently completed a recorded reenactment with
three stars on Windows, MuMu, MAA Core 6.20.1 and maa-cli 0.7.5. The deployment
coordinates and timing belong to the shared script's author; this project added
adapter support and validation. The third-party script and account logs are not
bundled. This validates that particular workflow, not every screen-action script.
