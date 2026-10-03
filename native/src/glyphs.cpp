/*
 * native/src/glyphs.cpp — the VLS glyph set (see glyphs.hpp).
 *
 * Mirrors voidloops/model.py NODE_KINDS + CONTENT_GLYPHS, kind for kind and
 * field for field. When this table and the Python one disagree, the Python
 * one wins until the native compile pipeline replaces it (native milestone 3).
 */
#include "glyphs.hpp"

#include "voidmaiz/embed.hpp"

#include <string_view>

namespace vls {
namespace {

struct Port {
    const char* name;
    const char* signal;
    bool multi = false;
};

struct Kind {
    const char* glyph;
    const char* label;
    const char* category; // model.py CATEGORIES; "content" for content glyphs
    std::vector<const char*> fields;
    std::vector<Port> inlets;
    std::vector<Port> outlets;
    std::vector<const char*> params; // bindable fields → `p:<field>` control inlets
    int face_w = 0, face_h = 0;      // hints.face; 0 = renderer default
    std::vector<std::pair<const char*, const char*>> editors; // field → widget kind
    const char* enter = nullptr;     // hints.enter: content field naming a mantle
    const char* principal = "prin";  // display name for port 0
};

const char* category_color(std::string_view cat) {
    if (cat == "input") return "#2f7d7d";
    if (cat == "time-event") return "#4a5fc1";
    if (cat == "generator") return "#7a4fcf";
    if (cat == "transform") return "#2f7d5a";
    if (cat == "combine") return "#b8862d";
    if (cat == "utility") return "#55555e";
    if (cat == "loop") return "#9a7b2d";
    if (cat == "output") return "#8a3b3b";
    return "#4a4a52"; // content
}

const std::vector<Kind>& kinds() {
    static const std::vector<Kind> k = {
        // ── node kinds (model.py NODE_KINDS, same order) ────────────────────
        {"clock", "Clock", "time-event", {"rate"},
         {}, {{"clk", CLOCK}}, {}},
        {"sequencer", "Sequencer", "time-event", {"length", "offset", "repeat"},
         {{"clk", CLOCK}}, {{"notes", EVENTS}}, {}},
        {"sequence", "Sequence", "time-event",
         {"length", "offset", "repeat", "transpose"},
         {{"clk", CLOCK}, {"arr", EVENTS, true}}, {{"notes", EVENTS}},
         {"transpose"}, 180, 96, {{"transpose", "knob:-24,24,0,1"}}},
        {"midi", "MIDI", "time-event", {"length", "offset", "repeat", "transpose"},
         {{"clk", CLOCK}, {"arr", EVENTS, true}}, {{"notes", EVENTS}},
         {"transpose"}, 180, 96, {{"transpose", "knob:-24,24,0,1"}}},
        {"osc", "Oscillator", "generator", {"wave", "tuning"},
         {{"notes", EVENTS}}, {{"out", AUDIO}},
         {"tuning"}, 180, 116,
         {{"wave", "combo:sine,saw,square,triangle"}, {"tuning", "knob:-24,24,0,1"}}},
        {"sampler", "Sampler", "generator", {"root"},
         {{"notes", EVENTS}, {"sample", AUDIO}}, {{"out", AUDIO}},
         {"root"}, 150, 96, {{"root", "knob:0,127,60,1"}}},
        {"vst-instrument", "VST Instrument", "generator", {"plugin", "preset"},
         {{"notes", EVENTS}}, {{"out", AUDIO}}, {}},
        {"sample-in", "Sample", "input", {"path", "gain"},
         {}, {{"out", AUDIO}}, {"gain"}, 0, 0, {{"gain", "knob:0,2,1"}}},
        {"midi-in", "MIDI In", "input", {"path"},
         {}, {{"notes", EVENTS}}, {}},
        {"time-of-day", "Time of day", "input", {"override"},
         {}, {{"out", CONTROL}}, {}},
        {"effect", "Effect", "transform", {"type", "amount", "feedback"},
         {{"in", AUDIO}}, {{"out", AUDIO}},
         {"amount", "feedback"}, 180, 116,
         {{"type", "combo:gain,delay"},
          {"amount", "knob:0,1,0.5"},
          {"feedback", "knob:0,0.99"}}},
        {"vst-effect", "VST Effect", "transform", {"plugin", "preset"},
         {{"in", AUDIO}}, {{"out", AUDIO}}, {}},
        {"value", "Value", "utility", {"value"},
         {}, {{"out", CONTROL}}, {}, 150, 72},
        {"math", "Math", "utility", {"op", "a", "b"},
         {{"a", CONTROL}, {"b", CONTROL}}, {{"out", CONTROL}}, {}, 0, 0,
         {{"op", "combo:add,sub,mul,div,min,max,pow,mod"}}},
        {"map", "Map range", "utility", {"in_min", "in_max", "out_min", "out_max"},
         {{"in", CONTROL}}, {{"out", CONTROL}}, {}},
        {"compare", "Compare", "utility", {"op", "a", "b"},
         {{"a", CONTROL}, {"b", CONTROL}}, {{"out", CONTROL}}, {}, 0, 0,
         {{"op", "combo:lt,le,gt,ge,eq,ne"}}},
        {"mix", "Mix", "combine", {"gain"},
         {{"in", AUDIO, true}}, {{"out", AUDIO}},
         {"gain"}, 150, 96, {{"gain", "knob:0,2,1"}}},
        {"output", "Output", "output", {"gain", "duration"},
         {{"in", AUDIO}}, {}, {"gain"}, 180, 96, {{"gain", "knob:0,2,1"}}},
        // The Loop's real ports are dynamic (the inner graph's free ports,
        // resolved by the compiler) — statically it declares none.
        {"loop", "Loop", "loop", {"patch"},
         {}, {}, {}, 0, 0, {}, "patch"},
        // ── content glyphs (things living *inside* a node) ──────────────────
        {"note", "Note", "content", {"pitch", "start", "length", "velocity"},
         {{"mod", ""}}, {}, {}, 170, 120,
         {{"pitch", "number:1,0,127"}, {"velocity", "knob:0,127,90,1"}},
         nullptr, "to-instrument"},
        {"automation", "Automation point", "content", {"target", "start", "value"},
         {}, {}, {}, 0, 0, {}, nullptr, "to-param"},
        {"sample", "Sample", "content", {"path", "start", "gain"},
         {}, {}, {}, 0, 0, {}, nullptr, "to-instrument"},
    };
    return k;
}

std::string glyph_json(const Kind& k) {
    std::string s = "{\"glyph\":\"";
    s += k.glyph;
    s += "\",\"label\":\"";
    s += k.label;
    s += "\",\"fields\":[";
    for (size_t i = 0; i < k.fields.size(); ++i) {
        if (i) s += ",";
        s += "\"";
        s += k.fields[i];
        s += "\"";
    }
    s += "],\"hints\":{\"color\":\"";
    s += category_color(k.category);
    s += "\",\"category\":\"";
    s += k.category;
    s += "\"";
    if (k.face_w || k.face_h) {
        s += ",\"face\":{\"w\":" + std::to_string(k.face_w) +
             ",\"h\":" + std::to_string(k.face_h) + "}";
    }
    if (k.enter) {
        s += ",\"enter\":\"";
        s += k.enter;
        s += "\"";
    }
    if (!k.editors.empty()) {
        s += ",\"editors\":{";
        for (size_t i = 0; i < k.editors.size(); ++i) {
            if (i) s += ",";
            s += "\"";
            s += k.editors[i].first;
            s += "\":\"";
            s += k.editors[i].second;
            s += "\"";
        }
        s += "}";
    }
    s += ",\"ports\":[{\"name\":\"";
    s += k.principal;
    s += "\",\"principal\":true}";
    auto emit = [&s](const char* name, const char* type, const char* dir, bool multi) {
        s += ",{\"name\":\"";
        s += name;
        s += "\",\"dir\":\"";
        s += dir;
        s += "\",\"type\":\"";
        s += type;
        s += "\"";
        if (multi) s += ",\"multi\":true";
        s += "}";
    };
    for (const Port& p : k.inlets) emit(p.name, p.signal, "in", p.multi);
    for (const char* f : k.params)
        emit(("p:" + std::string(f)).c_str(), CONTROL, "in", false);
    for (const Port& p : k.outlets) emit(p.name, p.signal, "out", p.multi);
    s += "]}}";
    return s;
}

} // namespace

void register_glyphs(maiz::Core& core) {
    for (const Kind& k : kinds()) core.register_glyph(glyph_json(k));
}

int port_index(const std::string& glyph, const std::string& port) {
    for (const Kind& k : kinds()) {
        if (glyph != k.glyph) continue;
        if (port == k.principal || port == "prin") return 0;
        int idx = 1;
        for (const Port& p : k.inlets) {
            if (port == p.name) return idx;
            ++idx;
        }
        for (const char* f : k.params) {
            if (port == "p:" + std::string(f)) return idx;
            ++idx;
        }
        for (const Port& p : k.outlets) {
            if (port == p.name) return idx;
            ++idx;
        }
        return -1;
    }
    return -1;
}

std::string relation(const std::string& src_glyph, const std::string& out_port,
                     const std::string& dst_glyph, const std::string& in_port) {
    int i = port_index(src_glyph, out_port);
    int j = port_index(dst_glyph, in_port);
    if (i < 0 || j < 0) return {};
    return std::to_string(i) + ":" + std::to_string(j);
}

std::vector<PaletteEntry> palette_entries() {
    std::vector<PaletteEntry> out;
    for (const Kind& k : kinds()) out.push_back({k.glyph, k.label, k.category});
    return out;
}

bool build_starter_patch(maiz::Core& core) {
    const int ppqn = 96;
    bool ok = true;
    auto run = [&](const std::string& cmd) { ok = core.dispatch(cmd).ok && ok; };

    run("mantle new main");
    run("rune new clock clk");
    run("setjson clk rate " + std::to_string(ppqn));
    run("setjson clk pos [40,80]");
    run("rune new sequence seq");
    run("setjson seq length " + std::to_string(4 * ppqn));
    run("setjson seq pos [280,80]");
    run("rune new osc osc1");
    run("set osc1 wave saw");
    run("setjson osc1 tuning 0");
    run("setjson osc1 pos [540,80]");
    run("rune new output out1");
    run("setjson out1 gain 1");
    run("setjson out1 pos [800,80]");

    run("link clk seq --relation " + relation("clock", "clk", "sequence", "clk"));
    run("link seq osc1 --relation " + relation("sequence", "notes", "osc", "notes"));
    run("link osc1 out1 --relation " + relation("osc", "out", "output", "in"));

    // The C-major arpeggio, held inside the sequence (containment = the
    // node:<seq> tag — notes stay first-class and tag-selectable). Placed in a
    // row beneath the graph until the piano-roll face lands (milestone 6).
    const int pitches[4] = {60, 64, 67, 72}; // C4 E4 G4 C5
    for (int i = 0; i < 4; ++i) {
        std::string n = "n" + std::to_string(i + 1);
        run("rune new note " + n);
        run("setjson " + n + " pitch " + std::to_string(pitches[i]));
        run("setjson " + n + " start " + std::to_string(i * ppqn));
        run("setjson " + n + " length " + std::to_string(ppqn));
        run("setjson " + n + " velocity 90");
        run("setjson " + n + " pos [" + std::to_string(160 + i * 200) + ",320]");
        run("tag " + n + " +node:seq");
    }
    return ok;
}

} // namespace vls
