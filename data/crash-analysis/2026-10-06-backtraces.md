# DF crash backtraces, 1-6 Oct 2026 (backtrace_10_1, _10_3, _10_6)

DF 53.16 win64 STEAM, DFHack 53.16-r2, CrossOver (wine-11.0). Image base 0x140000000 (no relocation), so the
`dwarf fortress (+0x...)` offsets are RVAs. Functions found from the exe's .pdata; screen methods matched
against the vtable addresses in DFHack's symbols.xml (`v0.53.16 win64 STEAM`); slot order from df-structures
`abstract_interfacest`: 0 get_rect, 1 feed, 2 logic, 3 render. Tools: llvm-objdump (Xcode), a small PE
parser (session scratchpad pemap.py / strs.py).

## Signature A: DF's own worldgen (backtrace_10_1 = 1 Oct 21:57, backtrace_10_6 = 6 Oct 14:30)

Identical stacks:

| frame | RVA | function | what it is |
|---|---|---|---|
| 0 | ucrtbase +0x171b4 | memmove | `movdqu` reading off the end of mapped memory |
| 1 | +0xb9ab0 | 0xb9a90 | `std::vector<int32>::erase(index)`: memmove(&v[i], &v[i+1], end-&v[i+1]); end -= 4 |
| 2 | +0x987aaa | 0x97e2a0 (50 KB) | entity government / landholders (strings: CUSTOM_LAW_MAKER, baron(ess), hearthperson) |
| 3 | +0xf73127 | 0xf706f0 | worldgen stage (strings: "Final <biome> region count fails by") |
| 4 | +0xf5563f | 0xf4f820 | worldgen driver (geography checks, "A world gen error from DF", errorlog.txt) |
| 5 | +0xdf5a33 | 0xdf3b00 | **viewscreen_new_regionst::logic** (vtable slot 2): world generation |
| 6-7 | dfhack +0x92e622, overlay.plug +0x1b5ee | | DFHack's interpose of the screen's logic: pass-through only |
| 8-10 | +0xc38a15, +0x8e5bd3, +0x8e6f39 | | DF main loop |

**Mechanism (exact).** In 0x97e2a0 two local vectors are kept in step: rbp+0x518 (pointers, apparently sites)
and rbp+0x898 (int32 keys). Loop (at 0x140987a06..ab0):

    while (P.size() && r14 > 0):
        key = K[P.size()-1]
        for i = P.size()-1 downto 0:
            if K[i] == key:  act(P[i], entity, -1, true, true)   // 0xbb0ee0
                             r14--; P.erase(i); K.erase(i)

Indexes come from P's size. At the crash the erase length was exactly -4 bytes in both dumps
(6 Oct: len = -0x362688C + 0x3626888 advanced; 1 Oct: -0xc08d0 + 0xc08cc), i.e. `K.erase(K.size())`:
**K is one element shorter than P.** The first comparison then reads the same past-the-end slot twice
(key = K[n], K[n] == key), always "matches", and the erase runs memmove with size_t(-4) until it faults.
Index 238 (6 Oct) and 213 (1 Oct). The vectors are filled by 0x9960a0 / 0x996fd0 from the entity's site
links (flags at +0x1c) and its child site-government entities' site links (world.entities.all binary search).
So DF's site redistribution among landholders builds the two lists one entry apart in some worlds.

**Not ours.** aquarium.plug is absent in the 1 Oct dump (installed 2-3 Oct) and present but not on the stack on
6 Oct; DFHack/overlay appear only as the interpose thunk every screen's logic goes through. Only one mod copy
exists in data/installed_mods (seasonal_wildlife_aquarium, 2 Oct), so no Workshop entity mod was in use.
The two 29 Sep crashes during M500a worldgen (crash logs only, no stack) are plausibly the same bug.

**What to do.** It is DF's bug, in vanilla 53.16 code. A crashed gen loses only that gen; regenerate (another
seed). If the same seed + parameters crash again it is deterministic and worth a Bay 12 Mantis report with the
seed, the parameter set (prefs/world_gen.txt) and this mechanism.

## Signature B: aquarium plugin (backtrace_10_3 = 3 Oct 19:10) - fixed

`aquarium.plug+0x19a9d` `mov edi,[rax+rcx*4]`, rax = 0 (viewport screentexpos), rcx = 0x798, on dfhooks' update
path. The plugin read DF's screen buffers from the update thread while the user zoomed (buffer mid-reallocation).
Diagnosed and fixed the same day (plugin log E22): the update thread no longer touches any screen buffer;
sprites are learned on the render thread. No recurrence since. Current wet-sprite copies (E45) go through
DFHack's Textures API from the update thread, not raw renderer calls.

## Other crash logs (no backtrace kept; DF keeps one backtrace file per day)

| crash log | known cause |
|---|---|
| 17 Sep 15:48, 1 Oct 08:55 (SIGSEGV) | unknown, no stack |
| 29 Sep 21:54, 22:34 | during M500a worldgen (likely signature A) |
| 2 Oct 14:40 | stale Continue list after a save folder was moved with DF up (memory save-dir-while-running) |
| 3 Oct 17:38 | plugin map-load texture race (fixed) |
| 5 Oct 14:28 | rig autosave wrote a test fort into the user's autosave (fixed: rig autosave guard, S1) |

Side effect found 6 Oct: the 14:30 crash killed the rig's DF before `cx-lifecycle stop`, so d_init kept the
rig's [AUTOSAVE:NONE]; restored to [AUTOSAVE:SEMIANNUAL] with `cx-lifecycle autosave restore` (the DF started
at 14:35 had already read NONE).
