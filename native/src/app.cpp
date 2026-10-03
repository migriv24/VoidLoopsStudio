/*
 * native/src/app.cpp — Void Loops Studio, native shell (milestone 1).
 *
 * The Python editor's replacement, on Void Maiz: canvas + inspector + log
 * strip + command bar over a live core. A pure dispatcher client, exactly
 * like the browser page was — every gesture the canvas compiles is dispatched
 * and the scene re-projected (the one-sync rule); the shell owns no model
 * state. Layout mirrors Void Maiz's canvas_window example on purpose: that
 * is the blessed host pattern.
 *
 * The project file is the native shell's own (default.native.vlp.json) until
 * the Python-era importer lands — see developer question #17.
 */
#include "faces.hpp"
#include "glyphs.hpp"
#include "style.hpp"

#include "voidmaiz/canvas.hpp"
#include "voidmaiz/embed.hpp"
#include "voidmaiz/face.hpp"
#include "voidmaiz/gesture.hpp"
#include "voidmaiz/inspector.hpp"
#include "voidmaiz/project.hpp"
#include "voidmaiz/widget.hpp"
#include "voidmaiz/widgets.hpp"

#include "imgui_impl_glfw.h"
#include "imgui_impl_opengl3.h"
#include <GLFW/glfw3.h>

#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

namespace {

std::filesystem::path project_path() {
    const char* home = std::getenv("USERPROFILE");
    if (!home) home = std::getenv("HOME");
    std::filesystem::path base = home ? home : ".";
    return base / "Documents" / "VoidLoopsProjects" / "default.native.vlp.json";
}

std::string read_file(const std::filesystem::path& p) {
    std::ifstream in(p, std::ios::binary);
    if (!in) return {};
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

bool write_file(const std::filesystem::path& p, const std::string& text) {
    std::error_code ec;
    std::filesystem::create_directories(p.parent_path(), ec);
    std::ofstream out(p, std::ios::binary | std::ios::trunc);
    if (!out) return false;
    out << text;
    return bool(out);
}

} // namespace

int main() {
    glfwSetErrorCallback([](int code, const char* desc) {
        std::fprintf(stderr, "glfw error %d: %s\n", code, desc);
    });
    if (!glfwInit()) return 1;
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 0);
    GLFWwindow* window =
        glfwCreateWindow(1360, 800, "Void Loops Studio — native", nullptr, nullptr);
    if (!window) { glfwTerminate(); return 1; }
    glfwMakeContextCurrent(window);
    glfwSwapInterval(1);

    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGui_ImplGlfw_InitForOpenGL(window, true);
    ImGui_ImplOpenGL3_Init("#version 130");

    // The studio look defaults dark (a DAW at night); the toggle survives.
    bool light_mode = false;
    maiz::CanvasStyle canvas_style = vls::canvas_style(light_mode);
    auto apply_theme = [&] {
        vls::apply_ui_style(light_mode);
        canvas_style = vls::canvas_style(light_mode);
    };
    apply_theme();

    // ── the project: load the user's file, or mint the starter patch ────────
    const std::filesystem::path path = project_path();
    const std::string saved_state = read_file(path);
    maiz::Core core = saved_state.empty() ? maiz::Core() : maiz::Core(saved_state);

    std::vector<maiz::LogEntry> log;
    core.set_log_sink([&](std::string_view level, std::string_view op, std::string_view msg) {
        log.push_back({std::string(level), std::string(op), std::string(msg)});
    });
    core.dispatch("config set actor human:vls-native");
    vls::register_glyphs(core); // host config, re-registered every open

    if (saved_state.empty()) {
        vls::build_starter_patch(core);
        write_file(path, core.export_state());
        std::printf("created starter project: %s\n", path.string().c_str());
    } else {
        core.dispatch("use main");
    }

    maiz::Scene scene = maiz::project_scene(core);
    maiz::EditorState ed;
    ed.cam.x = -20;
    ed.cam.y = -20;
    if (maiz::Camera saved; maiz::parse_camera(core.dispatch("config get view.camera").data, saved))
        ed.cam = saved;

    maiz::AddPalette palette;
    for (const vls::PaletteEntry& e : vls::palette_entries())
        palette.entries.push_back({e.glyph, e.label, e.category});

    maiz::FaceRegistry faces;
    vls::install_faces(faces);
    maiz::WidgetRegistry widgets = maiz::WidgetRegistry::defaults();

    maiz::CommandBarState cmdbar;
    int undo_depth = 0;
    auto refresh_undo_depth = [&] {
        maiz::Result h = core.dispatch("history");
        undo_depth = (h.lines.size() == 1 && h.lines[0] == "(no history)")
                         ? 0
                         : (int)h.lines.size();
    };
    refresh_undo_depth();

    bool dirty = false;
    auto save_project = [&] {
        if (write_file(path, core.export_state())) dirty = false;
    };
    auto dispatch_and_reproject = [&](const std::string& cmd) {
        maiz::Result r = core.dispatch(cmd);
        scene = maiz::project_scene(core); // the one-sync rule
        refresh_undo_depth();
        if (r.ok) dirty = true;
        return r;
    };

    while (!glfwWindowShouldClose(window)) {
        glfwPollEvents();
        if (glfwGetWindowAttrib(window, GLFW_ICONIFIED)) { glfwWaitEvents(); continue; }
        ImGui_ImplOpenGL3_NewFrame();
        ImGui_ImplGlfw_NewFrame();
        ImGui::NewFrame();

        const bool ctrl_s = ImGui::GetIO().KeyCtrl && ImGui::IsKeyPressed(ImGuiKey_S, false);
        if (ctrl_s) save_project();

        const ImGuiViewport* vp = ImGui::GetMainViewport();
        ImGui::SetNextWindowPos(vp->WorkPos);
        ImGui::SetNextWindowSize(ImVec2(vp->WorkSize.x * 0.78f, vp->WorkSize.y * 0.76f));
        ImGui::Begin("Canvas", nullptr,
                     ImGuiWindowFlags_NoTitleBar | ImGuiWindowFlags_NoResize |
                         ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoCollapse);
        ImGui::Text("patch: %s   nodes: %d   wires: %d   undo: %d   zoom: %.2f%s",
                    scene.mantle.c_str(), (int)scene.nodes.size(), (int)scene.wires.size(),
                    undo_depth, ed.cam.zoom, dirty ? "   *unsaved" : "");
        ImGui::SameLine(0, 24);
        if (ImGui::SmallButton("save")) save_project();
        ImGui::SameLine();
        if (ImGui::SmallButton("undo")) dispatch_and_reproject("undo");
        ImGui::SameLine();
        if (ImGui::SmallButton("redo")) dispatch_and_reproject("redo");
        ImGui::SameLine();
        if (ImGui::SmallButton(light_mode ? "dark" : "light")) {
            light_mode = !light_mode;
            apply_theme();
        }
        ImGui::SameLine(0, 24);
        ImGui::TextDisabled("drag port: wire | shift+A: add | wheel: zoom | mid/right: pan | ctrl+S: save");
        maiz::CanvasIO cio = maiz::edit_canvas("vls-canvas", scene, ed, canvas_style,
                                               &palette, &faces);
        for (const auto& cmd : cio.commands) dispatch_and_reproject(cmd);
        ImGui::End();

        ImGui::SetNextWindowPos(ImVec2(vp->WorkPos.x + vp->WorkSize.x * 0.78f, vp->WorkPos.y));
        ImGui::SetNextWindowSize(ImVec2(vp->WorkSize.x * 0.22f, vp->WorkSize.y * 0.76f));
        ImGui::Begin("Inspector", nullptr,
                     ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoMove |
                         ImGuiWindowFlags_NoCollapse);
        maiz::CanvasIO iio = maiz::draw_inspector(scene, ed, &widgets);
        for (const auto& cmd : iio.commands) dispatch_and_reproject(cmd);
        ImGui::End();

        ImGui::SetNextWindowPos(ImVec2(vp->WorkPos.x, vp->WorkPos.y + vp->WorkSize.y * 0.76f));
        ImGui::SetNextWindowSize(ImVec2(vp->WorkSize.x, vp->WorkSize.y * 0.24f));
        ImGui::Begin("Log", nullptr,
                     ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoMove |
                         ImGuiWindowFlags_NoCollapse);
        float footer = ImGui::GetFrameHeightWithSpacing();
        ImGui::BeginChild("##lines", ImVec2(0, -footer));
        maiz::draw_log_strip(log);
        ImGui::EndChild();
        maiz::CanvasIO bio = maiz::draw_command_bar(cmdbar);
        for (const auto& cmd : bio.commands) {
            maiz::Result r = dispatch_and_reproject(cmd);
            log.push_back({">", cmd, r.text().empty() ? (r.ok ? "ok" : "failed") : r.text()});
        }
        ImGui::End();

        ImGui::Render();
        int w, h;
        glfwGetFramebufferSize(window, &w, &h);
        glViewport(0, 0, w, h);
        if (light_mode) glClearColor(0.93f, 0.93f, 0.94f, 1.0f);
        else glClearColor(0.08f, 0.08f, 0.10f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);
        ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
        glfwSwapBuffers(window);
    }

    // The icon's project survives the session, like the Python editor's did.
    save_project();
    std::printf("saved: %s\n", path.string().c_str());

    ImGui_ImplOpenGL3_Shutdown();
    ImGui_ImplGlfw_Shutdown();
    ImGui::DestroyContext();
    glfwDestroyWindow(window);
    glfwTerminate();
    return 0;
}
