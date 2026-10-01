-- ocean-waves.lua  (PROTOTYPE, UNTESTED)
-- Draws animated sprites on map tiles where DF's own simulation has an ocean
-- wave front (world.event.ocean_waves) or a flow of type OceanWave / SeaFoam /
-- Mist in a visible map block. Graphics raws have no token for OceanWave or
-- SeaFoam (only FLOW_WATER_MIST etc.), so vanilla draws nothing for them.
--@module = true

local overlay = require('plugins.overlay')
local guidm   = require('gui.dwarfmode')

local scriptmanager = require('script-manager')
local MOD_DIR = scriptmanager.getModSourcePath('ocean_waves_overlay')
-- 8 frames x 2 rows of 32x32; row 0 = wave crest, row 1 = foam/mist
-- cache in _G: overlay, CLI and reload each run their own copy of a script
_G.__ocean_waves_tex = _G.__ocean_waves_tex or
    dfhack.textures.loadTileset((MOD_DIR or '.')..'/images/waves.png', 32, 32, true)
local TEX = _G.__ocean_waves_tex
local NFRAMES = 8

local FT = df.flow_type
local WANT = {[FT.OceanWave]='crest', [FT.SeaFoam]='foam', [FT.Mist]='foam'}

local cells = {}   -- key "x,y" -> 'crest'|'foam'  (current window_z only)

local function scan()
    cells = {}
    local z = df.global.window_z
    -- 1) wave fronts kept by the event handler (cheap: a short vector)
    for _, w in ipairs(df.global.world.event.ocean_waves) do
        if w.z == z then cells[w.cur.x..','..w.cur.y] = 'crest' end
    end
    -- 2) flows in the visible blocks only
    local vp = guidm.Viewport.get()
    for bx = vp.x1 // 16, vp.x2 // 16 do
        for by = vp.y1 // 16, vp.y2 // 16 do
            local blk = dfhack.maps.getTileBlock(bx*16, by*16, z)
            if blk then
                for _, fl in ipairs(blk.flows) do
                    local kind = WANT[fl.type]
                    if kind and fl.density > 0 and fl.pos.z == z then
                        cells[fl.pos.x..','..fl.pos.y] = cells[fl.pos.x..','..fl.pos.y] or kind
                    end
                end
            end
        end
    end
end

WavesOverlay = defclass(WavesOverlay, overlay.OverlayWidget)
WavesOverlay.ATTRS{
    desc='Animated ocean waves, sea foam and mist on the fort map.',
    default_enabled=true,
    viewscreens={'dwarfmode', 'dungeonmode'},
    fullscreen=true,
    overlay_onupdate_max_freq_seconds=0.25,   -- rescan 4x/s, render every frame
}

function WavesOverlay:overlay_onupdate() scan() end

function WavesOverlay:onRenderFrame()
    if not dfhack.screen.inGraphicsMode() or not next(cells) then return end
    local frame = (dfhack.getTickCount() // 120) % NFRAMES       -- ~8 fps animation
    local crest = dfhack.textures.getTexposByHandle(TEX[1 + frame])
    local foam  = dfhack.textures.getTexposByHandle(TEX[1 + NFRAMES + frame])
    guidm.renderMapOverlay(function(pos)
        local kind = cells[pos.x..','..pos.y]
        if not kind then return nil end
        return {ch='~', fg=COLOR_WHITE, keep_lower=true}, nil, (kind == 'crest') and crest or foam
    end)
end

OVERLAY_WIDGETS = {waves=WavesOverlay}
