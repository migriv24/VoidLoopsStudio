/*
 * native/src/faces.cpp — VLS's node faces (see faces.hpp).
 */
#include "faces.hpp"

namespace vls {

void install_faces(maiz::FaceRegistry& faces) {
    faces.by_glyph["osc"] = [](maiz::FaceContext& ctx) {
        maiz::face_combo(ctx, "wave", {"sine", "saw", "square", "triangle"});
        maiz::face_knob(ctx, "tuning", -24.0f, 24.0f, /*integer=*/true);
    };
    faces.by_glyph["effect"] = [](maiz::FaceContext& ctx) {
        maiz::face_combo(ctx, "type", {"gain", "delay"});
        maiz::face_knob(ctx, "amount", 0.0f, 1.0f, false, 0.5f);
        ImGui::SameLine();
        maiz::face_knob(ctx, "feedback", 0.0f, 0.99f);
    };
    faces.by_glyph["mix"] = [](maiz::FaceContext& ctx) {
        maiz::face_knob(ctx, "gain", 0.0f, 2.0f, false, 1.0f);
    };
    faces.by_glyph["output"] = [](maiz::FaceContext& ctx) {
        maiz::face_knob(ctx, "gain", 0.0f, 2.0f, false, 1.0f);
    };
    faces.by_glyph["sampler"] = [](maiz::FaceContext& ctx) {
        maiz::face_knob(ctx, "root", 0.0f, 127.0f, /*integer=*/true, 60.0f);
    };
    faces.by_glyph["sequence"] = [](maiz::FaceContext& ctx) {
        maiz::face_knob(ctx, "transpose", -24.0f, 24.0f, /*integer=*/true);
    };
    faces.by_glyph["midi"] = [](maiz::FaceContext& ctx) {
        maiz::face_knob(ctx, "transpose", -24.0f, 24.0f, /*integer=*/true);
    };
    faces.by_glyph["value"] = [](maiz::FaceContext& ctx) {
        maiz::face_drag_number(ctx, "value", 0.01f); // unbounded — a knob would lie
    };
    // The note face is the piano roll's honest stand-in until milestone 6.
    faces.by_glyph["note"] = [](maiz::FaceContext& ctx) {
        maiz::face_drag_number(ctx, "pitch", 0.25f, 0.0f, 127.0f);
        maiz::face_knob(ctx, "velocity", 0.0f, 127.0f, /*integer=*/true, 90.0f);
    };
}

} // namespace vls
