/*
 * native/src/style.hpp — the VLS look: the DAW's own canvas style.
 *
 * Void Maiz's default themes were right for its demos; VLS gets its own
 * identity (the author's 2026-07-16 makeover call). Everything here rides
 * Maiz's host surface — CanvasTheme colors, CanvasStyle metrics, and the
 * port style registry (CanvasStyle::port_types, landed upstream same day on
 * our ask — MESSAGE_FOR_VLS.md §1/§2): each signal type gets a color AND a
 * shape, and typed wires take the color too. Nothing is patched library-side.
 *
 * The shape taxonomy (shape is the second channel — color must never be the
 * only one): audio = filled circle (the continuous stream), events = ring
 * (discrete messages), clock = triangle (the pulse), control = square (the
 * Python editor's box-shaped control slots, kept as muscle-memory parity).
 * The principal diamond stays the theme's — principals are untyped.
 */
#pragma once

#include "voidmaiz/canvas.hpp"

namespace vls {

/* The studio theme: near-black graphite, warm amber accents — a DAW at night.
 * The light variant stays honest for daylight jams. */
maiz::CanvasTheme theme_dark();
maiz::CanvasTheme theme_light();

/* VLS metrics over Maiz defaults (wider nodes, softer corners, bigger port
 * grab targets — pointer-friendly during a jam), plus the port style
 * registry: the four signal types with their colors and shapes. */
maiz::CanvasStyle canvas_style(bool light);

/* The ImGui chrome theme + VLS accents: StyleColorsDark/Light, then the
 * amber threaded through (SliderGrab drives the kit knob's identity —
 * MESSAGE_FOR_VLS.md §4). Call whenever the theme toggles. */
void apply_ui_style(bool light);

/* Signal-type accents, shared by faces/widgets (ImU32, IM_COL32 packing). */
unsigned signal_color(const char* signal, bool light);

} // namespace vls
