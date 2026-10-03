/*
 * native/src/style.cpp — the VLS look (see style.hpp).
 */
#include "style.hpp"

#include "imgui.h"

#include <cstring>

namespace vls {

maiz::CanvasTheme theme_dark() {
    maiz::CanvasTheme t = maiz::CanvasTheme::dark();
    t.canvas_bg = IM_COL32(20, 20, 25, 255);        // graphite, near-black
    t.grid = IM_COL32(33, 33, 41, 255);
    t.node_bg = IM_COL32(38, 38, 47, 245);
    t.node_border = IM_COL32(58, 58, 70, 255);
    t.node_border_sel = IM_COL32(232, 168, 64, 255); // warm amber selection
    t.header_default = IM_COL32(47, 47, 58, 255);
    t.text_dim = IM_COL32(140, 140, 152, 255);
    t.tag_text = IM_COL32(150, 150, 165, 255);
    t.principal = IM_COL32(216, 160, 64, 255);       // fettuccine amber
    t.linguine = IM_COL32(136, 136, 160, 220);
    t.loose = IM_COL32(90, 90, 104, 160);
    t.marquee_fill = IM_COL32(232, 168, 64, 24);
    t.marquee_line = IM_COL32(232, 168, 64, 140);
    t.wire_ok = IM_COL32(96, 190, 120, 255);
    t.wire_bad = IM_COL32(220, 100, 90, 255);
    t.wire_neutral = IM_COL32(150, 150, 160, 200);
    t.chrome = IM_COL32(120, 120, 134, 255);
    t.hover = IM_COL32(240, 184, 88, 255);
    return t;
}

maiz::CanvasTheme theme_light() {
    maiz::CanvasTheme t = maiz::CanvasTheme::light();
    t.node_border_sel = IM_COL32(198, 124, 16, 255); // the amber identity survives daylight
    t.principal = IM_COL32(182, 118, 24, 255);
    t.marquee_fill = IM_COL32(198, 124, 16, 22);
    t.marquee_line = IM_COL32(198, 124, 16, 150);
    t.hover = IM_COL32(198, 124, 16, 255);
    return t;
}

maiz::CanvasStyle canvas_style(bool light) {
    maiz::CanvasStyle s;
    s.theme = light ? theme_light() : theme_dark();
    // The port style registry (typed wires take these colors too). Shape
    // taxonomy per style.hpp: the second channel, never color alone.
    s.port_types["audio"] = {signal_color("audio", light), maiz::PortShape::Circle};
    s.port_types["events"] = {signal_color("events", light), maiz::PortShape::Ring};
    s.port_types["clock"] = {signal_color("clock", light), maiz::PortShape::Triangle};
    s.port_types["control"] = {signal_color("control", light), maiz::PortShape::Square};
    s.node_w = 180.0f;        // roomier default face (knobs need elbow room)
    s.header_h = 24.0f;
    s.port_row = 21.0f;
    s.port_radius = 5.0f;     // bigger grab targets during a jam
    s.port_hit_radius = 10.0f;
    s.rounding = 8.0f;        // softer corners than the Maiz default
    s.grid_step = 28.0f;
    return s;
}

void apply_ui_style(bool light) {
    if (light) ImGui::StyleColorsLight();
    else ImGui::StyleColorsDark();
    ImGuiStyle& st = ImGui::GetStyle();
    // The amber identity rides the ImGui style into the kit's widgets
    // (the knob reads SliderGrab — MESSAGE_FOR_VLS.md §4).
    const ImVec4 amber = light ? ImVec4(0.776f, 0.486f, 0.063f, 1.0f)   // #c67c10
                               : ImVec4(0.910f, 0.659f, 0.251f, 1.0f);  // #e8a840
    st.Colors[ImGuiCol_SliderGrab] = amber;
    st.Colors[ImGuiCol_SliderGrabActive] = amber;
    st.Colors[ImGuiCol_CheckMark] = amber;
    st.FrameRounding = 4.0f;
    st.GrabRounding = 4.0f;
}

unsigned signal_color(const char* signal, bool light) {
    // Chosen to stay apart for the common color-vision deficiencies; the
    // upstream port-style registry ask pairs each with a SHAPE for the same
    // reason (color must never be the only channel).
    if (!light) {
        if (!std::strcmp(signal, "audio")) return IM_COL32(240, 176, 72, 255);   // amber
        if (!std::strcmp(signal, "events")) return IM_COL32(110, 195, 130, 255); // green
        if (!std::strcmp(signal, "clock")) return IM_COL32(120, 170, 240, 255);  // blue
        if (!std::strcmp(signal, "control")) return IM_COL32(205, 120, 205, 255); // magenta
        return IM_COL32(150, 150, 155, 255);
    }
    if (!std::strcmp(signal, "audio")) return IM_COL32(196, 128, 20, 255);
    if (!std::strcmp(signal, "events")) return IM_COL32(52, 140, 78, 255);
    if (!std::strcmp(signal, "clock")) return IM_COL32(58, 110, 196, 255);
    if (!std::strcmp(signal, "control")) return IM_COL32(158, 66, 158, 255);
    return IM_COL32(120, 120, 126, 255);
}

} // namespace vls
