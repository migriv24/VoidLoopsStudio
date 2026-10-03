/*
 * native/src/glyphs.hpp — the VLS glyph set, ported from voidloops/model.py.
 *
 * The Python NODE_KINDS table is the behavioral spec (the reference
 * implementation); this is its native form in Void Maiz's glyph-descriptor
 * convention: ports live in hints.ports as a flat array — index 0 the
 * principal, auxiliaries 1..n in declaration order (inlets, then `p:<field>`
 * param inlets, then outlets) — and wire relations are the reduce contract's
 * numeric "i:j" form (developer question #17's lean). Port names are display
 * hints; the model speaks indices, so glyph port order is append-only.
 *
 * UI-free on purpose: links plain voidmaiz (no ImGui). Faces live in app.cpp.
 */
#pragma once

#include <string>
#include <vector>

namespace maiz { class Core; }

namespace vls {

/* Signal types a wire can carry (model.py SIGNAL_TYPES). */
inline constexpr const char* AUDIO = "audio";
inline constexpr const char* EVENTS = "events";
inline constexpr const char* CLOCK = "clock";
inline constexpr const char* CONTROL = "control";

/* Register every DAW glyph (content + node kinds) on a fresh core. Glyphs are
 * host config, not state — call after every Core construction. */
void register_glyphs(maiz::Core& core);

/* Net port index for a glyph's named port, per the convention above.
 * "prin" (or the content glyph's principal name) → 0; unknown → -1. */
int port_index(const std::string& glyph, const std::string& port);

/* The "i:j" relation joining src_glyph.out_port → dst_glyph.in_port.
 * Empty string if either port is unknown — never guess an index. */
std::string relation(const std::string& src_glyph, const std::string& out_port,
                     const std::string& dst_glyph, const std::string& in_port);

/* Add-palette entries (glyph, label, category), node kinds first, content
 * glyphs last. UI-free mirror of maiz::AddPalette::Entry — the shell copies. */
struct PaletteEntry {
    std::string glyph, label, category;
};
std::vector<PaletteEntry> palette_entries();

/* Build the starter patch (the Python ui() starter, through the dispatcher):
 * clock → sequence → osc → output at 96 PPQN, the C-major arpeggio held
 * inside the sequence as note runes tagged node:<seq>. Names the mantle
 * "main". Returns false if any dispatch failed. */
bool build_starter_patch(maiz::Core& core);

} // namespace vls
