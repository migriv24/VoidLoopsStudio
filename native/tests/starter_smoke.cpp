/*
 * starter_smoke — milestone 1's headless exit test, first half: the VLS glyph
 * set registers, the starter patch builds through the dispatcher, its wires
 * project TYPED (the numeric "i:j" relations resolve against the glyph port
 * tables — question #17's convention round-trips), and the state document
 * replays into an identical projection.
 */
#include "glyphs.hpp"

#include "voidmaiz/embed.hpp"
#include "voidmaiz/project.hpp"

#include <cstdio>
#include <string>

static int failures = 0;
#define CHECK(cond)                                                       \
    do {                                                                  \
        if (!(cond)) {                                                    \
            std::printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond);   \
            ++failures;                                                   \
        }                                                                 \
    } while (0)

static const maiz::SceneWire* find_wire(const maiz::Scene& s, const std::string& from,
                                        const std::string& to) {
    for (const auto& w : s.wires)
        if (w.from == from && w.to == to) return &w;
    return nullptr;
}

int main() {
    // ── port indexing: the named⇄linear map matches the declaration order ──
    CHECK(vls::port_index("clock", "clk") == 1);
    CHECK(vls::port_index("sequence", "clk") == 1);
    CHECK(vls::port_index("sequence", "arr") == 2);
    CHECK(vls::port_index("sequence", "p:transpose") == 3);
    CHECK(vls::port_index("sequence", "notes") == 4);
    CHECK(vls::port_index("osc", "notes") == 1);
    CHECK(vls::port_index("osc", "p:tuning") == 2);
    CHECK(vls::port_index("osc", "out") == 3);
    CHECK(vls::port_index("output", "in") == 1);
    CHECK(vls::port_index("output", "prin") == 0);
    CHECK(vls::port_index("output", "nope") == -1);
    CHECK(vls::port_index("no-such-glyph", "in") == -1);
    CHECK(vls::relation("osc", "out", "output", "in") == "3:1");
    CHECK(vls::relation("osc", "out", "output", "nope").empty());

    // ── the starter patch builds and projects ───────────────────────────────
    maiz::Core core;
    vls::register_glyphs(core);
    CHECK(vls::build_starter_patch(core));

    maiz::Scene scene = maiz::project_scene(core);
    CHECK(scene.mantle == "main");
    CHECK(scene.nodes.size() == 8); // clk seq osc1 out1 + 4 notes
    CHECK(scene.wires.size() == 3);

    const maiz::SceneWire* w = find_wire(scene, "seq", "osc1");
    CHECK(w != nullptr);
    if (w) {
        CHECK(w->kind == maiz::SceneWire::Kind::Linguine); // typed, not loose
        CHECK(w->from_port == 4);
        CHECK(w->to_port == 1);
    }
    const maiz::SceneNode* seq = scene.find("seq");
    CHECK(seq != nullptr);
    if (seq) {
        CHECK(seq->glyph == "sequence");
        CHECK(seq->placed);
        // ports carry names + signal types from the glyph hints
        CHECK(seq->inputs.size() == 3);  // clk, arr, p:transpose
        CHECK(seq->outputs.size() == 1); // notes
        CHECK(seq->outputs[0].type == std::string(vls::EVENTS));
    }
    const maiz::SceneNode* note = scene.find("n1");
    CHECK(note != nullptr);
    if (note) {
        bool tagged = false;
        for (const auto& t : note->tags) tagged = tagged || t == "node:seq";
        CHECK(tagged); // containment = the node:<seq> tag
    }

    // ── the state document replays into the same picture ────────────────────
    maiz::Core replayed(core.export_state());
    vls::register_glyphs(replayed); // glyphs are host config, not state
    replayed.dispatch("use main");
    maiz::Scene again = maiz::project_scene(replayed);
    CHECK(again.nodes.size() == scene.nodes.size());
    CHECK(again.wires.size() == scene.wires.size());
    const maiz::SceneWire* w2 = find_wire(again, "seq", "osc1");
    CHECK(w2 && w2->kind == maiz::SceneWire::Kind::Linguine);

    if (failures) {
        std::printf("%d check(s) failed\n", failures);
        return 1;
    }
    std::printf("starter smoke: all checks passed\n");
    return 0;
}
