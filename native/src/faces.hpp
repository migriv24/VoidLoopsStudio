/*
 * native/src/faces.hpp — VLS's node faces: the widgets ON the nodes.
 *
 * Host-side face wiring per Void Maiz's face protocol (a face reads the
 * projected node and compiles dispatcher commands — it never touches model
 * state). The rotary knob was born here (2026-07-16) and absorbed into the
 * kit the same day (MESSAGE_FOR_VLS.md §4) — VLS now consumes
 * maiz::face_knob, wearing the VLS amber through the ImGui style
 * (style.cpp::apply_ui_style). This file is just the per-glyph wiring.
 */
#pragma once

#include "voidmaiz/face.hpp"

namespace vls {

/* Register every VLS face on the registry. */
void install_faces(maiz::FaceRegistry& faces);

} // namespace vls
