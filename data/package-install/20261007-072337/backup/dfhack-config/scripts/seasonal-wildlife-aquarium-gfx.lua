-- seasonal-wildlife-aquarium-gfx.lua -- builds the Aquarium graphics mod (translucent water, river and brook streaks, mist)
-- from the player's OWN installed vanilla sheets. v7.1 (aquarium stream; docs/v7.1/aquarium.md, 2 Oct 2026).
-- Pure Lua 5.3: a PNG decoder (zlib inflate: stored, fixed and dynamic Huffman; filters 0-4; colour types 0, 2, 3, 4, 6 at
-- 8 bits) and a PNG encoder (fixed Huffman with run matches), so nothing outside DFHack is needed. Bay 12's sheets are never
-- shipped: the tile pages are made on the player's machine at `seasonal-wildlife aquarium install`. The desk twin is
-- tools/aquarium/make_aquarium_mod.py (Pillow); tests/aquarium checks the two write the same raws and the same pixels.
--@ module = true
--[====[

seasonal-wildlife-aquarium-gfx
==============================

The graphics-mod builder behind ``seasonal-wildlife aquarium install``. Not a command of its own: the engine's
``aquarium`` verb calls it. See ``help seasonal-wildlife``.

]====]

local GFX = { VERSION = 1, MOD_ID = 'seasonal_wildlife_aquarium', STAMP = 'sw_aquarium_stamp.txt' }
-- GFX.pace: nil, or a function the decoders call every few thousand bytes / every row. The bed sets it only while it
-- runs a decode inside its own coroutine, to slice a sheet's decode across scans (fail-fast: no 100+ ms first scan).
GFX.pace = nil

-- alpha for tile water level 7 -> 1, the flow-streak alpha scale, the mist alpha scale (docs/v7.1/aquarium.md section 3)
GFX.PRESETS = {
    vanilla  = { alpha = { 255, 255, 255, 255, 230, 204, 179 }, flows = 1.0,  mist = 1.0,  tint = false },
    subtle   = { alpha = { 215, 205, 195, 185, 175, 165, 150 }, flows = 1.0,  mist = 0.9,  tint = true },
    aquarium = { alpha = { 150, 140, 130, 120, 110, 100, 90 },  flows = 0.75, mist = 0.75, tint = true },
    clear    = { alpha = { 105, 95, 85, 75, 65, 58, 50 },       flows = 0.5,  mist = 0.6,  tint = true },
    shallows = { alpha = { 255, 255, 255, 140, 115, 100, 90 },  flows = 0.75, mist = 0.75, tint = true },
    custom   = { alpha = { 150, 140, 130, 120, 110, 100, 90 },  flows = 0.75, mist = 0.75, tint = true },
}
GFX.PRESET_ORDER = { 'vanilla', 'subtle', 'aquarium', 'clear', 'shallows', 'custom' }
GFX.TINT = { 220, 235, 245, 0.15 }   -- mist: RGB 15% toward a cool white
GFX.DIGIT_MIN = 200                  -- a label pixel with min(R,G,B) above this is a depth digit: kept opaque
GFX.SOURCES = { liquids = 'liquids.png', flows = { 'flows.png', 'flows2.png', 'flows3.png', 'flows4.png' }, mist = 'event_flows.png' }
GFX.DIRS = { 'NW', 'NE', 'SE', 'SW', 'N', 'S', 'W', 'E' }   -- the FLOWS pages' row order (vanilla graphics_fluids.txt)
-- the bed, baked into the art (v7.1-bed round 5, user 3 Oct: "can't the tool just replace the tileset at the graphics
-- raws level?" -- a per-frame script clips in and out on scroll). Standing water (ocean, lakes, pools, cavern water: all
-- drawn with UNDERWATER_1..7) gets DF's sand floor (sand_floor.png, the SAND_TAN row) composited UNDER the preset's water
-- tile, opaque; river and brook beds (RIVER_BED_* / BROOK_BED_*, their own tokens) get mud under the water. Integer
-- arithmetic only, so make_aquarium_mod.py writes the same pixels.
GFX.BAKE_SOURCES = { sand = 'sand_floor.png', floors = 'floors.png', river = 'river.png', brook = 'brook.png' }
GFX.MUD_CELL = { 1, 7 }                      -- floors.png DIRT_FLOOR_5: the mud's texture
GFX.MUD_BAKE = { rgb = { 178, 136, 88 }, contrast = 45, cue = 45, water_row = 6, water_pct = 50, river_pct = 70 }   -- wet brown; texture
-- contrast %; the bed's shape cue %; the liquids-page row whose water goes over it (6 = level 1, the lightest) at
-- water_pct % of its alpha: vanilla water is cyan, so a full tile turns the brown olive; the RIVER_TO_ streaks add the rest
-- the shape rows of vanilla river.png / brook.png (graphics_fluids.txt RIVER_BED_* rows 0..15; brooks have the first 14)
GFX.BED_SHAPES = { '', '_N', '_S', '_W', '_E', '_N_W', '_N_E', '_S_E', '_S_W', '_NW', '_NE', '_SE', '_SW', '_SOURCE', '_NW_SE', '_NE_SW' }
GFX.BROOK_SHAPES = 14

--========================================================================================
-- bytes
--========================================================================================
local function u32be(s, i)
    local a, b, c, d = s:byte(i, i + 3)
    return (a << 24) | (b << 16) | (c << 8) | d
end
local function be32(n) return string.char((n >> 24) & 255, (n >> 16) & 255, (n >> 8) & 255, n & 255) end

local CRC
local function crc32(s, crc)
    if not CRC then
        CRC = {}
        for n = 0, 255 do
            local c = n
            for _ = 1, 8 do c = (c & 1) == 1 and (0xEDB88320 ~ (c >> 1)) or (c >> 1) end
            CRC[n] = c
        end
    end
    crc = (crc or 0) ~ 0xFFFFFFFF
    for i = 1, #s do crc = CRC[(crc ~ s:byte(i)) & 255] ~ (crc >> 8) end
    return crc ~ 0xFFFFFFFF
end
GFX.crc32 = crc32

--========================================================================================
-- inflate (RFC 1950/1951), after zlib's puff.c: canonical Huffman decoding, one bit at a time
--========================================================================================
local LBASE = { 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258 }
local LEXT  = { 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0 }
local DBASE = { 1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513, 769, 1025, 1537, 2049, 3073, 4097,
                6145, 8193, 12289, 16385, 24577 }
local DEXT  = { 0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13 }
local CLORDER = { 16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15 }

local function huff(lengths, n)
    local count, offs, symbol = {}, {}, {}
    for l = 0, 15 do count[l] = 0 end
    for s = 0, n - 1 do local l = lengths[s] or 0; count[l] = count[l] + 1 end
    offs[1] = 0
    for l = 1, 14 do offs[l + 1] = offs[l] + count[l] end
    for s = 0, n - 1 do
        local l = lengths[s] or 0
        if l ~= 0 then symbol[offs[l]] = s; offs[l] = offs[l] + 1 end
    end
    return { count = count, symbol = symbol }
end

-- Inflates the zlib stream in string s; returns a 1-based byte array and its length.
function GFX.inflate(s)
    local pos = 3   -- skip the 2-byte zlib header
    local cmf = s:byte(1)
    if not cmf or (cmf & 15) ~= 8 then error('not a zlib deflate stream', 0) end
    local bitbuf, bitcnt = 0, 0
    local out, o = {}, 1
    local function bits(n)
        while bitcnt < n do
            local b = s:byte(pos)
            if not b then error('inflate: out of input', 0) end
            pos = pos + 1
            bitbuf = bitbuf | (b << bitcnt); bitcnt = bitcnt + 8
        end
        local v = bitbuf & ((1 << n) - 1)
        bitbuf = bitbuf >> n; bitcnt = bitcnt - n
        return v
    end
    local function decode(h)
        local code, first, index = 0, 0, 0
        local count, symbol = h.count, h.symbol
        for len = 1, 15 do
            if bitcnt == 0 then
                local b = s:byte(pos)
                if not b then error('inflate: out of input', 0) end
                pos = pos + 1; bitbuf = b; bitcnt = 8
            end
            code = code | (bitbuf & 1); bitbuf = bitbuf >> 1; bitcnt = bitcnt - 1
            local c = count[len]
            if code - c < first then return symbol[index + (code - first)] end
            index = index + c; first = (first + c) << 1; code = code << 1
        end
        error('inflate: bad Huffman code', 0)
    end
    local nextPace = 8192
    local function codes(lh, dh)
        while true do
            if o >= nextPace then nextPace = o + 8192; local pace = GFX.pace; if pace then pace() end end
            local sym = decode(lh)
            if sym < 256 then out[o] = sym; o = o + 1
            elseif sym == 256 then return
            else
                sym = sym - 257
                if sym >= 29 then error('inflate: bad length symbol', 0) end
                local len = LBASE[sym + 1] + bits(LEXT[sym + 1])
                local ds = decode(dh)
                if ds >= 30 then error('inflate: bad distance symbol', 0) end
                local dist = DBASE[ds + 1] + bits(DEXT[ds + 1])
                if dist >= o then error('inflate: distance too far back', 0) end
                local from = o - dist
                for k = 0, len - 1 do out[o + k] = out[from + k] end
                o = o + len
            end
        end
    end
    local FIXL, FIXD
    repeat
        local last = bits(1)
        local btype = bits(2)
        if btype == 0 then
            bitbuf, bitcnt = 0, 0
            local len = s:byte(pos) | (s:byte(pos + 1) << 8)
            pos = pos + 4
            for k = 0, len - 1 do out[o + k] = s:byte(pos + k) end
            o = o + len; pos = pos + len
        elseif btype == 1 then
            if not FIXL then
                local l = {}
                for i = 0, 143 do l[i] = 8 end
                for i = 144, 255 do l[i] = 9 end
                for i = 256, 279 do l[i] = 7 end
                for i = 280, 287 do l[i] = 8 end
                FIXL = huff(l, 288)
                local d = {}
                for i = 0, 29 do d[i] = 5 end
                FIXD = huff(d, 30)
            end
            codes(FIXL, FIXD)
        elseif btype == 2 then
            local nlen, ndist, ncode = bits(5) + 257, bits(5) + 1, bits(4) + 4
            local cl = {}
            for i = 0, 18 do cl[i] = 0 end
            for i = 1, ncode do cl[CLORDER[i]] = bits(3) end
            local ch = huff(cl, 19)
            local lengths, i = {}, 0
            while i < nlen + ndist do
                local sym = decode(ch)
                if sym < 16 then lengths[i] = sym; i = i + 1
                else
                    local rep, val
                    val = 0
                    if sym == 16 then
                        if i == 0 then error('inflate: repeat with no length', 0) end
                        val = lengths[i - 1]; rep = 3 + bits(2)
                    elseif sym == 17 then rep = 3 + bits(3)
                    else rep = 11 + bits(7) end
                    for _ = 1, rep do lengths[i] = val; i = i + 1 end
                end
            end
            local ll, dl = {}, {}
            for k = 0, nlen - 1 do ll[k] = lengths[k] end
            for k = 0, ndist - 1 do dl[k] = lengths[nlen + k] end
            codes(huff(ll, nlen), huff(dl, ndist))
        else
            error('inflate: bad block type', 0)
        end
    until last == 1
    return out, o - 1
end

--========================================================================================
-- PNG decode -> { w, h, px } with px a 1-based RGBA byte array (4 per pixel)
--========================================================================================
local function paeth(a, b, c)
    local p = a + b - c
    local pa, pb, pc = math.abs(p - a), math.abs(p - b), math.abs(p - c)
    if pa <= pb and pa <= pc then return a elseif pb <= pc then return b end
    return c
end

function GFX.decode(data)
    if data:sub(1, 8) ~= '\137PNG\r\n\26\n' then error('not a PNG file', 0) end
    local pos, w, h, depth, ctype, interlace = 9, nil, nil, nil, nil, nil
    local idat, plte, trns = {}, nil, nil
    while pos <= #data do
        local len = u32be(data, pos)
        local typ = data:sub(pos + 4, pos + 7)
        local body = data:sub(pos + 8, pos + 7 + len)
        if typ == 'IHDR' then
            w, h, depth, ctype, interlace = u32be(body, 1), u32be(body, 5), body:byte(9), body:byte(10), body:byte(13)
        elseif typ == 'PLTE' then plte = body
        elseif typ == 'tRNS' then trns = body
        elseif typ == 'IDAT' then idat[#idat + 1] = body
        elseif typ == 'IEND' then break end
        pos = pos + 12 + len
    end
    if not w then error('PNG without IHDR', 0) end
    if depth ~= 8 then error(('PNG bit depth %s is not supported (8 only)'):format(tostring(depth)), 0) end
    if interlace ~= 0 then error('interlaced PNG is not supported', 0) end
    local bpp = ({ [0] = 1, [2] = 3, [3] = 1, [4] = 2, [6] = 4 })[ctype]
    if not bpp then error('PNG colour type ' .. tostring(ctype) .. ' is not supported', 0) end
    local raw, n = GFX.inflate(table.concat(idat))
    local stride = w * bpp
    if n < h * (stride + 1) then error('PNG data is short', 0) end
    -- unfilter in place into rows (1-based flat array of w*h*bpp)
    local cur = {}
    local r = 1
    for y = 0, h - 1 do
        local pace = GFX.pace; if pace then pace() end
        local ft = raw[r]; r = r + 1
        local base = y * stride
        for x = 1, stride do
            local v = raw[r]; r = r + 1
            local a = x > bpp and cur[base + x - bpp] or 0
            local b = y > 0 and cur[base - stride + x] or 0
            if ft == 1 then v = v + a
            elseif ft == 2 then v = v + b
            elseif ft == 3 then v = v + ((a + b) >> 1)
            elseif ft == 4 then v = v + paeth(a, b, (x > bpp and y > 0) and cur[base - stride + x - bpp] or 0)
            elseif ft ~= 0 then error('PNG filter type ' .. tostring(ft), 0) end
            cur[base + x] = v & 255
        end
    end
    if ctype == 6 then return { w = w, h = h, px = cur } end
    local px = {}
    local tr = {}
    if trns then for i = 1, #trns do tr[i - 1] = trns:byte(i) end end
    for i = 0, w * h - 1 do
        if i & 4095 == 0 then local pace = GFX.pace; if pace then pace() end end
        local R, G, B, A
        if ctype == 2 then
            R, G, B = cur[i * 3 + 1], cur[i * 3 + 2], cur[i * 3 + 3]; A = 255
            if trns and #trns >= 6 and R == trns:byte(2) and G == trns:byte(4) and B == trns:byte(6) then A = 0 end
        elseif ctype == 3 then
            local k = cur[i + 1]
            R, G, B = plte:byte(k * 3 + 1), plte:byte(k * 3 + 2), plte:byte(k * 3 + 3)
            A = tr[k] or 255
        elseif ctype == 0 then
            R = cur[i + 1]; G, B, A = R, R, 255
            if trns and #trns >= 2 and R == trns:byte(2) then A = 0 end
        else
            R = cur[i * 2 + 1]; G, B, A = R, R, cur[i * 2 + 2]
        end
        px[i * 4 + 1], px[i * 4 + 2], px[i * 4 + 3], px[i * 4 + 4] = R, G, B, A
    end
    return { w = w, h = h, px = px }
end

--========================================================================================
-- PNG encode: RGBA 8-bit, Sub filter, one fixed-Huffman deflate block with distance-1 run matches
--========================================================================================
local function bitWriter()
    local bytes, n, acc, cnt = {}, 0, 0, 0
    local W = {}
    function W.put(v, len)   -- LSB first
        acc = acc | (v << cnt); cnt = cnt + len
        while cnt >= 8 do n = n + 1; bytes[n] = acc & 255; acc = acc >> 8; cnt = cnt - 8 end
    end
    function W.huff(code, len)   -- Huffman codes go MSB first
        local rev = 0
        for _ = 1, len do rev = (rev << 1) | (code & 1); code = code >> 1 end
        W.put(rev, len)
    end
    function W.finish()
        if cnt > 0 then n = n + 1; bytes[n] = acc & 255; acc, cnt = 0, 0 end
        local parts = {}
        for i = 1, n, 4096 do parts[#parts + 1] = string.char(table.unpack(bytes, i, math.min(n, i + 4095))) end
        return table.concat(parts)
    end
    return W
end
local function litCode(W, v)
    if v <= 143 then W.huff(0x30 + v, 8)
    elseif v <= 255 then W.huff(0x190 + v - 144, 9)
    elseif v <= 279 then W.huff(v - 256, 7)
    else W.huff(0xC0 + v - 280, 8) end
end
local function lenCode(W, len)
    local i = #LBASE
    while LBASE[i] > len do i = i - 1 end
    litCode(W, 256 + i)
    if LEXT[i] > 0 then W.put(len - LBASE[i], LEXT[i]) end
end

function GFX.deflate(raw, n)
    local W = bitWriter()
    W.put(1, 1); W.put(1, 2)   -- BFINAL, fixed Huffman
    local i = 1
    while i <= n do
        local v = raw[i]
        if i > 1 and v == raw[i - 1] then
            local run = 1
            while i + run <= n and raw[i + run] == v and run < 258 do run = run + 1 end
            if run >= 3 then
                lenCode(W, run); W.huff(0, 5)   -- distance code 0 = distance 1
                i = i + run
            else
                litCode(W, v); i = i + 1
            end
        else
            litCode(W, v); i = i + 1
        end
    end
    litCode(W, 256)
    local a, b = 1, 0
    for k = 1, n do a = (a + raw[k]) % 65521; b = (b + a) % 65521 end
    return '\120\1' .. W.finish() .. be32((b << 16) | a)
end

local function chunk(typ, body) return be32(#body) .. typ .. body .. be32(crc32(typ .. body)) end

function GFX.encode(img)
    local w, h, px = img.w, img.h, img.px
    local stride = w * 4
    local raw, r = {}, 0
    for y = 0, h - 1 do
        r = r + 1; raw[r] = 1   -- Sub
        local base = y * stride
        for x = 1, stride do
            r = r + 1
            raw[r] = (px[base + x] - (x > 4 and px[base + x - 4] or 0)) & 255
        end
    end
    local ihdr = be32(w) .. be32(h) .. string.char(8, 6, 0, 0, 0)
    return '\137PNG\r\n\26\n' .. chunk('IHDR', ihdr) .. chunk('IDAT', GFX.deflate(raw, r)) .. chunk('IEND', '')
end

--========================================================================================
-- the transforms (docs/v7.1/aquarium.md section 3)
--========================================================================================
local function blank(w, h)
    local px = {}
    for i = 1, w * h * 4 do px[i] = 0 end
    return { w = w, h = h, px = px }
end
-- copy the 32x32 cell (sc, sr) of src to (dc, dr) of dst
local function copyCell(src, sc, sr, dst, dc, dr)
    for y = 0, 31 do
        local so = ((sr * 32 + y) * src.w + sc * 32) * 4
        local d0 = ((dr * 32 + y) * dst.w + dc * 32) * 4
        for k = 1, 128 do dst.px[d0 + k] = src.px[so + k] end
    end
end
local function round(x) return math.floor(x + 0.5) end

-- the preset as a table { alpha[1..7] (levels 7..1), flows, mist, tint }; custom alphas from `alphas`
function GFX.preset(name, alphas)
    local p = GFX.PRESETS[name]
    if not p then error('unknown preset ' .. tostring(name), 0) end
    local a = {}
    for i = 1, 7 do a[i] = p.alpha[i] end
    if name == 'custom' and type(alphas) == 'table' then
        for i = 1, 7 do local v = tonumber(alphas[i]); if v then a[i] = math.max(0, math.min(255, math.floor(v))) end end
    end
    return { name = name, alpha = a, flows = p.flows, mist = p.mist, tint = p.tint }
end

-- liquids.png (7 rows) -> SW_AQ_LIQUIDS 64x224: column 0 the water tiles, column 1 the depth-label tiles
function GFX.liquidsPage(src, p)
    local dst = blank(64, 224)
    for row = 0, 6 do
        copyCell(src, 0, row, dst, 0, row)
        copyCell(src, 2, row, dst, 1, row)
        local A = p.alpha[row + 1]
        for y = row * 32, row * 32 + 31 do
            for x = 0, 63 do
                local i = (y * 64 + x) * 4
                if dst.px[i + 4] > 0 then
                    local digit = x >= 32 and math.min(dst.px[i + 1], dst.px[i + 2], dst.px[i + 3]) > GFX.DIGIT_MIN
                    if not digit then dst.px[i + 4] = A end
                end
            end
        end
    end
    return dst
end
-- a flows page: every alpha scaled
function GFX.flowsPage(src, p)
    local dst = { w = src.w, h = src.h, px = {} }
    local s, d = src.px, dst.px
    for i = 1, src.w * src.h * 4, 4 do
        d[i], d[i + 1], d[i + 2] = s[i], s[i + 1], s[i + 2]
        d[i + 3] = math.min(255, round(s[i + 3] * p.flows))
    end
    return dst
end
-- event_flows.png column 2 rows 0..3 (FLOW_WATER_MIST 1..4) -> SW_AQ_MIST 32x128, alpha scaled, tinted
function GFX.mistPage(src, p)
    local dst = blank(32, 128)
    for row = 0, 3 do copyCell(src, 2, row, dst, 0, row) end
    local tr, tg, tb, t = GFX.TINT[1], GFX.TINT[2], GFX.TINT[3], GFX.TINT[4]
    local d = dst.px
    for i = 1, 32 * 128 * 4, 4 do
        if d[i + 3] > 0 then
            if p.tint then
                d[i] = round(d[i] * (1 - t) + tr * t)
                d[i + 1] = round(d[i + 1] * (1 - t) + tg * t)
                d[i + 2] = round(d[i + 2] * (1 - t) + tb * t)
            end
            d[i + 3] = math.min(255, round(d[i + 3] * p.mist))
        end
    end
    return dst
end
-- straight-alpha "over" in integers (the same in Python): a src pixel of alpha a over an opaque dst channel
local function overI(d, s, a) return (d * (255 - a) + s * a + 127) // 255 end
local function lumI(r, g, b) return (299 * r + 587 * g + 114 * b) // 1000 end
-- the liquids page baked: under each tile of the page (water column 0, label column 1, row = 7 - level) the sand cell
-- (sand_floor.png row 0, column (level - 1) % 4, so neighbouring depths do not repeat one tile), every pixel opaque
function GFX.bakeLiquids(page, sand)
    local d, sp = page.px, sand.px
    for row = 0, 6 do
        local level = 7 - row
        local sc = (level - 1) % 4
        for y = 0, 31 do
            for x = 0, 63 do
                local i = ((row * 32 + y) * 64 + x) * 4
                local si = (y * sand.w + sc * 32 + (x % 32)) * 4
                local a = d[i + 4]
                d[i + 1] = overI(sp[si + 1], d[i + 1], a)
                d[i + 2] = overI(sp[si + 2], d[i + 2], a)
                d[i + 3] = overI(sp[si + 3], d[i + 3], a)
                d[i + 4] = 255
            end
        end
    end
    return page
end
-- one mud cell (dst col dc, row dr of the 64x512 beds page): DF's soil floor cell recoloured wet brown with its contrast
-- softened, shaded by the vanilla bed cell's (cue col cc, row cr) luminance relative to that sheet's plain bed (0, 0),
-- then the preset's water tile of row MUD_BAKE.water_row over it; opaque
local function mudCell(dst, dc, dr, floors, cue, cr, page, wrow, flip, pct)
    local M, C, Q = GFX.MUD_BAKE.rgb, GFX.MUD_BAKE.contrast, GFX.MUD_BAKE.cue
    wrow, flip, pct = wrow or GFX.MUD_BAKE.water_row, flip or 0, pct or GFX.MUD_BAKE.water_pct
    local fc, fr = GFX.MUD_CELL[1], GFX.MUD_CELL[2]
    local fp, cp, wp = floors.px, cue.px, page.px
    local sum, sum0 = 0, 0
    for y = 0, 31 do
        for x = 0, 31 do
            local fi = ((fr * 32 + y) * floors.w + fc * 32 + x) * 4
            sum = sum + lumI(fp[fi + 1], fp[fi + 2], fp[fi + 3])
            local ci = (y * cue.w + x) * 4
            sum0 = sum0 + lumI(cp[ci + 1], cp[ci + 2], cp[ci + 3])
        end
    end
    local ML, LV0 = math.max(1, sum // 1024), math.max(1, sum0 // 1024)
    for y = 0, 31 do
        for x = 0, 31 do
            -- a variant mirrors the mud and its cue (1: left-right, 2: top-bottom, 3: both); the water tile is not mirrored
            local mx, my = (flip & 1 ~= 0) and (31 - x) or x, (flip & 2 ~= 0) and (31 - y) or y
            local fi = ((fr * 32 + my) * floors.w + fc * 32 + mx) * 4
            local l = lumI(fp[fi + 1], fp[fi + 2], fp[fi + 3])
            local t = ML + ((l - ML) * C) // 100
            local ci = ((cr * 32 + my) * cue.w + mx) * 4
            local lv = lumI(cp[ci + 1], cp[ci + 2], cp[ci + 3])
            local f = 1000 + ((lv - LV0) * Q * 10) // LV0
            local wi = ((wrow * 32 + y) * 64 + x) * 4
            local a = wp[wi + 4] * pct // 100
            local di = ((dr * 32 + y) * dst.w + dc * 32 + x) * 4
            for c = 1, 3 do
                local v = (M[c] * t // ML) * f // 1000
                if v < 0 then v = 0 elseif v > 255 then v = 255 end
                dst.px[di + c] = overI(v, wp[wi + c], a)
            end
            dst.px[di + 4] = 255
        end
    end
end
-- SW_AQ_BEDS 64x512: column 0 the 16 river-bed shapes (cues from river.png column 0), column 1 the 14 brook-bed shapes
-- (brook.png); every frame and every brook variant of a shape uses its one cell (a still bed: DF does not animate
-- rivers in fortress mode, rig 2 Oct). With no bake: a transparent page (no token is bound to it)
function GFX.bedsPage(floors, river, brook, page)
    local dst = blank(64, 512)
    if not floors then return dst end
    for r = 0, #GFX.BED_SHAPES - 1 do mudCell(dst, 0, r, floors, river, r, page) end
    for r = 0, GFX.BROOK_SHAPES - 1 do mudCell(dst, 1, r, floors, brook, r, page) end
    return dst
end

-- SW_AQ_RIVER 128x224 (not bound by the raws: the overlay loads it with dfhack.textures.loadTileset): rivers and brooks
-- as mud under water, for the cells DF draws with the (sand-baked) standing-water tile -- river cells carry the same
-- liquid flag (rig 3 Oct, AQUA_LAKE z55: sand ripples on the river). Row = 7 - water level (like the liquids page),
-- column = a mirrored variant 0..3; the mud of the plain river bed under that level's preset water at river_pct % alpha
-- (70: a full river reads wetter than a shallow one, the brown still shows).
-- With no bake: transparent.
function GFX.riverPage(floors, river, page)
    local dst = blank(128, 224)
    if not floors then return dst end
    for row = 0, 6 do
        for v = 0, 3 do mudCell(dst, v, row, floors, river, 0, page, row, v, GFX.MUD_BAKE.river_pct) end
    end
    return dst
end

-- the 7 water tiles of a liquids page as packed 0xRRGGBBAA arrays (row-major, 32x32), for the aquarium's makeTile (byte-swapped there for DF):
-- tiles[level] for tile water level 1..7 (the veil)
function GFX.waterTiles(page)
    local tiles = {}
    for row = 0, 6 do
        local level = 7 - row
        local t = {}
        for y = 0, 31 do
            for x = 0, 31 do
                local i = ((row * 32 + y) * page.w + x) * 4
                t[#t + 1] = (page.px[i + 1] << 24) | (page.px[i + 2] << 16) | (page.px[i + 3] << 8) | page.px[i + 4]
            end
        end
        tiles[level] = t
    end
    return tiles
end

--========================================================================================
-- the bed (v7.1-bed; docs/v7.1/aquarium.md section 4.6): DF draws no floor under a water cell (rig, 2 Oct 2026: the
-- background layer of a shallow river cell holds the same texpos as a soil wall, the generic dark fill), so translucent
-- water shows only that fill. The overlay writes a bed sprite into the background layer instead; these are its sources
-- (cells of the player's own vanilla sheets, never shipped) and the pure pixel transform (tint, depth).
--========================================================================================
-- BMP (floors.bmp holds the floor variants 5B/5C/5D): uncompressed 24- or 32-bit, bottom-up or top-down; DF's
-- magenta key (255,0,255) becomes transparent. Returns { w, h, px } like GFX.decode.
local function u32le(s, i) local a, b, c, d = s:byte(i, i + 3); return a | (b << 8) | (c << 16) | (d << 24) end
local function u16le(s, i) local a, b = s:byte(i, i + 1); return a | (b << 8) end
function GFX.decodeBMP(data)
    if data:sub(1, 2) ~= 'BM' or #data < 54 then error('not a BMP file', 0) end
    local off, w, h = u32le(data, 11), u32le(data, 19), u32le(data, 23)
    if h >= 0x80000000 then h = h - 0x100000000 end
    local bpp, comp = u16le(data, 29), u32le(data, 31)
    if (bpp ~= 24 and bpp ~= 32) or (comp ~= 0 and not (comp == 3 and bpp == 32)) then
        error(('BMP %d-bit, compression %d is not supported (24/32-bit uncompressed only)'):format(bpp, comp), 0)
    end
    local topdown = h < 0
    if topdown then h = -h end
    local bypp = bpp // 8
    local stride = ((w * bypp + 3) // 4) * 4
    if #data < off + stride * h then error('BMP data is short', 0) end
    local px = {}
    for y = 0, h - 1 do
        local pace = GFX.pace; if pace then pace() end
        local srow = topdown and y or (h - 1 - y)
        local base = off + srow * stride
        for x = 0, w - 1 do
            local b, g, r = data:byte(base + x * bypp + 1, base + x * bypp + 3)
            local a = 255
            if r == 255 and g == 0 and b == 255 then a = 0 end
            local i = (y * w + x) * 4
            px[i + 1], px[i + 2], px[i + 3], px[i + 4] = r, g, b, a
        end
    end
    return { w = w, h = h, px = px }
end

-- The bed families: per family, its variants as { sheet file, column, row } (32x32 cells). The full-tile floor sprites
-- only: in floors.png the 3x3 blocks are a nine-patch whose corner and edge pieces are mostly transparent (DIRT_FLOOR_1 at
-- (0,6) is empty: that is why the rig's first try drew black); the centre _5 is the floor, its variants _5B/_5C/_5D sit in
-- ALT_FLOORS (floors.bmp column 7). Sand has one row per colour (vanilla graphics_tiles.txt SAND_FLOOR_5..5D,
-- SAND_YELLOW_..., SAND_WHITE_..., SAND_BLACK_..., SAND_RED_...); pebbles PEBBLES_FLOOR_5..5D; river and brook
-- RIVER_BED:1:1..4 and BROOK_BED:1:1..4 (DF's own teal water-over-bed pictures: kept as the `bed river df` choice).
GFX.BED = {
    stone   = { { 'floors.png', 1, 4 }, { 'floors.bmp', 7, 4 }, { 'floors.bmp', 7, 5 }, { 'floors.bmp', 7, 6 } },
    dirt    = { { 'floors.png', 1, 7 }, { 'floors.bmp', 7, 7 }, { 'floors.bmp', 7, 8 }, { 'floors.bmp', 7, 9 } },
    pebbles = { { 'floor_pebbles.png', 0, 0 }, { 'floor_pebbles.png', 1, 0 }, { 'floor_pebbles.png', 2, 0 }, { 'floor_pebbles.png', 3, 0 } },
    river   = { { 'river.png', 0, 0 }, { 'river.png', 1, 0 }, { 'river.png', 2, 0 }, { 'river.png', 3, 0 } },
    brook   = { { 'brook.png', 0, 0 }, { 'brook.png', 1, 0 }, { 'brook.png', 2, 0 }, { 'brook.png', 3, 0 } },
    -- mud (v1, user 2 Oct: "SANDY floor for ocean water and MUDDY floor for rivers, lakes, pools, cavern water"): DF's
    -- own soil floor cells, recoloured wet brown (GFX.MUD) with their contrast softened
    mud     = { { 'floors.png', 1, 7 }, { 'floors.bmp', 7, 7 }, { 'floors.bmp', 7, 8 }, { 'floors.bmp', 7, 9 } },
}
-- the v1 beds (`aquarium bed material sand-mud`, the default): salt water lies on sand (sand_floor.png row 0, SAND_TAN,
-- untinted: the prototype's sand), fresh water on mud: the soil cells tinted toward a wet brown at strength 0.85 with
-- the texture's contrast at 0.6 (smooth, not clods)
GFX.SEA_BED = 'sand0'
GFX.MUD = { rgb = { 156, 118, 74 }, strength = 0.85, contrast = 0.45 }
-- sand rows of sand_floor.png: the vanilla sand token that row draws, and the row's mean colour measured on the vanilla
-- sheet (2 Oct 2026), for a modded sand matched by its own colour
GFX.SAND_ROWS = {
    { row = 0, token = 'SAND_TAN',    rgb = { 206, 159, 104 } },
    { row = 1, token = 'SAND_YELLOW', rgb = { 206, 171, 104 } },
    { row = 2, token = 'SAND_WHITE',  rgb = { 202, 182, 158 } },
    { row = 3, token = 'SAND_BLACK',  rgb = { 77, 73, 77 } },
    { row = 4, token = 'SAND_RED',    rgb = { 177, 82, 62 } },
}
for _, s in ipairs(GFX.SAND_ROWS) do
    local list = {}
    for c = 0, 3 do list[#list + 1] = { 'sand_floor.png', c, s.row } end
    GFX.BED['sand' .. s.row] = list
end
-- the sand row for a sand material: its token if vanilla, else the row nearest its colour
function GFX.sandRow(token, rgb)
    token = tostring(token or '')
    for _, s in ipairs(GFX.SAND_ROWS) do if token == s.token then return s.row end end
    if type(rgb) ~= 'table' then return 0 end
    local best, bd = 0, math.huge
    for _, s in ipairs(GFX.SAND_ROWS) do
        local d = (rgb[1] - s.rgb[1]) ^ 2 + (rgb[2] - s.rgb[2]) ^ 2 + (rgb[3] - s.rgb[3]) ^ 2
        if d < bd then best, bd = s.row, d end
    end
    return best
end
-- Water optics (v7.1-bed rig round 2: the clear preset over a grey-darkened stone bed read as dark paving, not sea).
-- Light through water loses red first, then green, least blue; the water body scatters its own blue-green back. Per
-- level of water above the bed (dw = tier + 0.5: the bed of a surface cell still lies under half a level on average)
-- each channel keeps T = exp(-k * dw * absorb) of the bed's light and gains WATER * SCATTER * (1 - T). So shallow beds
-- keep their sand or stone colour (a little cooler), deeper ones turn sea green, then deep blue-green, never grey or
-- black. Air between the view and a water surface further down (a lifted cell k levels below) fogs toward AIR by
-- AIR_F per level past the first, as DF's lower-level fog would.
GFX.WATER = { k = { 0.28, 0.11, 0.07 }, colour = { 14, 84, 108 }, scatter = 0.6 }
GFX.AIR = { colour = { 18, 26, 34 }, f = 0.85 }

-- a 32-bit mixing hash of a map position (salted), uniform enough for variants and patches
function GFX.hash(x, y, z, salt)
    local h = ((x * 73856093) ~ (y * 19349663) ~ (z * 83492791) ~ ((salt or 0) * 2654435761)) & 0xffffffff
    h = ((h ~ (h >> 16)) * 0x45d9f3b) & 0xffffffff
    h = ((h ~ (h >> 16)) * 0x45d9f3b) & 0xffffffff
    return h ~ (h >> 16)
end
-- the variant (1..n) for a map position
function GFX.bedVariant(x, y, z, n) return GFX.hash(x, y, z) % n + 1 end
-- smooth value noise in [0, 1) over a lattice of `scale` cells: patches of gravel in a stone or mud bed
function GFX.patch(x, y, z, scale)
    scale = scale or 5
    local fx, fy = x / scale, y / scale
    local ix, iy = math.floor(fx), math.floor(fy)
    local tx, ty = fx - ix, fy - iy
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    local function v(a, b) return (GFX.hash(a, b, z, 7) % 1000) / 1000 end
    local top = v(ix, iy) * (1 - tx) + v(ix + 1, iy) * tx
    local bot = v(ix, iy + 1) * (1 - tx) + v(ix + 1, iy + 1) * tx
    return top * (1 - ty) + bot * ty
end
GFX.PEBBLE_PATCH = { stone = 0.24, dirt = 0.16 }   -- share of a stone / soil bed under water drawn as gravel patches
-- the look of one bed cell: family (after gravel patches) and variant. Deep beds use fewer variants (their texture is
-- hardly visible through the water; fewer textures): 4 to 2 levels of water, 2 to 3.5, then 1.
function GFX.bedMix(fam, x, y, z, dw)
    local cut = GFX.PEBBLE_PATCH[fam]
    -- a per-cell nudge frays the patch edge, so a patch is not a square of the noise lattice
    if cut and GFX.patch(x, y, z, 5) + ((GFX.hash(x, y, z, 11) % 100) / 100 - 0.5) * 0.16 < cut then fam = 'pebbles' end
    local n = #(GFX.BED[fam] or {})
    dw = dw or 0.5
    if dw > 3.5 then n = math.min(n, 1) elseif dw > 2 then n = math.min(n, 2) end
    return fam, (n > 0 and GFX.bedVariant(x, y, z, n) or 1)
end
-- the water depth a bed cell is drawn at: its own tier (levels between the water surface and the bed) averaged with
-- its water neighbours' (self twice), plus half a level, quantised (0.25 to 2 levels, 0.5 to 4, then 1; at most 8.5),
-- so depth shades in small steps instead of one hard step per level. tierAt(x, y) -> tier, or nil where no bed.
function GFX.depthQ(dw)
    if dw < 2 then return math.floor(dw * 4 + 0.5) / 4 elseif dw < 4 then return math.floor(dw * 2 + 0.5) / 2 end
    return math.min(8.5, math.floor(dw + 0.5) + 0.5)
end
function GFX.bedDepth(tierAt, x, y)
    local t0 = tierAt(x, y) or 0
    local sum, n = t0 * 2, 2
    for dy = -1, 1 do
        for dx = -1, 1 do
            if dx ~= 0 or dy ~= 0 then
                local t = tierAt(x + dx, y + dy)
                if t then sum, n = sum + t, n + 1 end
            end
        end
    end
    return GFX.depthQ(sum / n + 0.5)
end

-- the RGBA of one 32x32 cell (c, r) of a decoded sheet, 1-based flat; nil when the cell lies outside the sheet
function GFX.cell(img, c, r)
    if not img or c < 0 or r < 0 or (c + 1) * 32 > img.w or (r + 1) * 32 > img.h then return nil end
    local out, k = {}, 0
    for y = 0, 31 do
        local so = ((r * 32 + y) * img.w + c * 32) * 4
        for i = 1, 128 do k = k + 1; out[k] = img.px[so + i] end
    end
    return out
end

local function clamp8(v) v = math.floor(v + 0.5); if v < 0 then return 0 elseif v > 255 then return 255 end; return v end
-- A bed tile as packed 0xRRGGBBAA (the tool's order; the aquarium's makeTile byte-swaps it for DF), opaque. opts:
--   tint {r,g,b}, strength 0..1: recolour toward the material keeping the texture (each pixel's luminance relative to
--     the cell's mean scales the tint, so at strength 1 the cell's mean lands on the material colour);
--   dw: levels of water over the bed (GFX.bedDepth), or tier (levels between the surface and the bed: dw = tier + 0.5),
--     through the water optics above, scaled by absorb (default 1; 0 = no water colour);
--   air: levels of open air between the view and the water surface (0 or 1 = none; 2+ fog);
--   contrast: the texture's contrast around the cell's mean (default 1; mud 0.6).
-- Transparent source pixels take the cell's mean colour (the bed must cover DF's fill).
function GFX.bedPixels(cell, opts)
    opts = opts or {}
    local n, sr, sg, sb, sl = 0, 0, 0, 0, 0
    for i = 1, 4096, 4 do
        if cell[i + 3] > 0 then
            n = n + 1
            sr, sg, sb = sr + cell[i], sg + cell[i + 1], sb + cell[i + 2]
            sl = sl + 0.299 * cell[i] + 0.587 * cell[i + 1] + 0.114 * cell[i + 2]
        end
    end
    if n == 0 then n, sr, sg, sb, sl = 1, 96, 88, 80, 89 end
    local mr, mg, mb, ml = sr / n, sg / n, sb / n, math.max(1, sl / n)
    local t, s = opts.tint, math.max(0, math.min(1, opts.strength or 0))
    if not t then s = 0 end
    -- the optics model only the water BELOW the surface level: DF's own water sprite (the mod's translucent tile)
    -- stands for the surface level's water, so a bed at the water's own level (dw 0.5) is the sprite's floor exactly as
    -- in the prototype figure (a sand floor, the seven water tiles composited over it)
    local dw = math.max(0, (opts.dw or (math.max(0, opts.tier or 0) + 0.5)) - 0.5)
    local ab = opts.absorb
    if ab == nil then ab = 1 end
    local W, K, sc = GFX.WATER.colour, GFX.WATER.k, GFX.WATER.scatter
    local Tr, Tg, Tb = 1, 1, 1
    if ab > 0 then Tr, Tg, Tb = math.exp(-K[1] * dw * ab), math.exp(-K[2] * dw * ab), math.exp(-K[3] * dw * ab) end
    local ar, ag, ab2 = W[1] * sc * (1 - Tr), W[2] * sc * (1 - Tg), W[3] * sc * (1 - Tb)
    local air = math.max(0, (opts.air or 0) - 1)
    local f = GFX.AIR.f ^ air
    local A = GFX.AIR.colour
    local fr, fg, fb = A[1] * (1 - f), A[2] * (1 - f), A[3] * (1 - f)
    local con = opts.contrast or 1
    local out = {}
    for p = 0, 1023 do
        local i = p * 4 + 1
        local r, g, b
        if cell[i + 3] > 0 then r, g, b = cell[i], cell[i + 1], cell[i + 2] else r, g, b = mr, mg, mb end
        if con ~= 1 then r, g, b = mr + (r - mr) * con, mg + (g - mg) * con, mb + (b - mb) * con end
        if s > 0 then
            local rel = (0.299 * r + 0.587 * g + 0.114 * b) / ml
            r = r * (1 - s) + t[1] * rel * s
            g = g * (1 - s) + t[2] * rel * s
            b = b * (1 - s) + t[3] * rel * s
        end
        r, g, b = r * Tr + ar, g * Tg + ag, b * Tb + ab2
        r, g, b = r * f + fr, g * f + fg, b * f + fb
        out[p + 1] = (clamp8(r) << 24) | (clamp8(g) << 16) | (clamp8(b) << 8) | 255
    end
    return out
end

-- one water tile of a preset over a bed tile, as DF composites them (straight alpha): for the desk preview
function GFX.over(bed, water)
    local out = {}
    for p = 1, 1024 do
        local b, w = bed[p], water[p]
        local a = (w & 255) / 255
        local function ch(sh) return clamp8((((w >> sh) & 255) * a) + (((b >> sh) & 255) * (1 - a))) end
        out[p] = (ch(24) << 24) | (ch(16) << 16) | (ch(8) << 8) | 255
    end
    return out
end

--========================================================================================
-- the raws (identical for every preset; tools/aquarium/make_aquarium_mod.py writes the same text)
--========================================================================================
function GFX.infoText()
    return table.concat({
        '[ID:' .. GFX.MOD_ID .. ']',
        '[NUMERIC_VERSION:' .. GFX.VERSION .. ']',
        '[DISPLAYED_VERSION:1.0]',
        '[EARLIEST_COMPATIBLE_NUMERIC_VERSION:1]',
        '[EARLIEST_COMPATIBLE_DISPLAYED_VERSION:1.0]',
        '[AUTHOR:seasonal-wildlife]',
        '[NAME:Seasonal Wildlife - Aquarium]',
        '[DESCRIPTION:Translucent water at every depth, matching river and brook streaks and waterfall mist, so you can '
            .. 'see the life of your seas, lakes and rivers. The tile pages are generated from your own vanilla sheets by '
            .. 'seasonal-wildlife aquarium install (or tools/aquarium/make_aquarium_mod.py).]',
        '' }, '\n')
end

function GFX.tilePageText()
    local t = { 'tile_page_sw_aquarium', '', '[OBJECT:TILE_PAGE]', '' }
    local function page(id, file, w, h)
        t[#t + 1] = '[TILE_PAGE:' .. id .. ']'
        t[#t + 1] = '\t[FILE:images/' .. file .. ']'
        t[#t + 1] = '\t[TILE_DIM:32:32]'
        t[#t + 1] = ('\t[PAGE_DIM_PIXELS:%d:%d]'):format(w, h)
        t[#t + 1] = ''
    end
    page('SW_AQ_LIQUIDS', 'sw_aq_liquids.png', 64, 224)
    for v = 1, 4 do page('SW_AQ_FLOWS' .. v, ('sw_aq_flows%d.png'):format(v), 512, 256) end
    page('SW_AQ_MIST', 'sw_aq_mist.png', 32, 128)
    page('SW_AQ_BEDS', 'sw_aq_beds.png', 64, 512)
    return table.concat(t, '\n')
end

function GFX.graphicsText(bake)
    bake = bake or 'sand'
    local t = { 'graphics_sw_aquarium', '', '[OBJECT:GRAPHICS]', '',
                bake == 'sand' and '-- standing water over a sand floor (baked): tile water level 7..1, and the same tiles with their depth digit --'
                    or '-- translucent standing water: tile water level 7..1, and the same tiles with their depth digit --' }
    for row = 0, 6 do t[#t + 1] = ('[TILE_GRAPHICS:SW_AQ_LIQUIDS:0:%d:UNDERWATER_%d]'):format(row, 7 - row) end
    for row = 0, 6 do t[#t + 1] = ('[TILE_GRAPHICS:SW_AQ_LIQUIDS:1:%d:UNDERWATER_%d_LABEL]'):format(row, 7 - row) end
    t[#t + 1] = ''
    t[#t + 1] = '-- river and brook flow streaks: both families use the same cells of the four flows pages --'
    for _, fam in ipairs({ 'BROOK', 'RIVER' }) do
        for v = 1, 4 do
            for row, dir in ipairs(GFX.DIRS) do
                for f = 1, 16 do
                    t[#t + 1] = ('[TILE_GRAPHICS:SW_AQ_FLOWS%d:%d:%d:%s_TO_%s:%d:%d]'):format(v, f - 1, row - 1, fam, dir, v, f)
                end
            end
        end
    end
    t[#t + 1] = ''
    t[#t + 1] = '-- waterfall and spray mist --'
    for row = 0, 3 do t[#t + 1] = ('[TILE_GRAPHICS:SW_AQ_MIST:0:%d:FLOW_WATER_MIST:%d]'):format(row, row + 1) end
    t[#t + 1] = ''
    if bake == 'sand' then
        t[#t + 1] = '-- river and brook beds: mud under the water (every frame of a shape, every brook variant, one cell) --'
        for r, sh in ipairs(GFX.BED_SHAPES) do
            for f = 1, 16 do t[#t + 1] = ('[TILE_GRAPHICS:SW_AQ_BEDS:0:%d:RIVER_BED%s:1:%d]'):format(r - 1, sh, f) end
        end
        for v = 1, 4 do
            for r = 1, GFX.BROOK_SHAPES do
                for f = 1, 16 do t[#t + 1] = ('[TILE_GRAPHICS:SW_AQ_BEDS:1:%d:BROOK_BED%s:%d:%d]'):format(r - 1, GFX.BED_SHAPES[r], v, f) end
            end
        end
        t[#t + 1] = ''
    end
    return table.concat(t, '\n')
end

function GFX.stampText(p, generator, sizes, bake)
    local a = {}
    for i = 1, 7 do a[i] = tostring(p.alpha[i]) end
    local function num(x) local s = ('%.2f'):format(x); return s end
    return table.concat({
        'mod=' .. GFX.MOD_ID, 'version=' .. GFX.VERSION, 'preset=' .. p.name, 'alpha=' .. table.concat(a, ','),
        'flows=' .. num(p.flows), 'mist=' .. num(p.mist), 'tint=' .. tostring(p.tint and true or false),
        'bed_bake=' .. (bake or 'off'), 'sources=' .. (sizes or ''), 'generator=' .. generator, '' }, '\n')
end
function GFX.parseStamp(text)
    local s = {}
    for line in tostring(text or ''):gmatch('[^\n]+') do
        local k, v = line:match('^([%w_]+)=(.*)$')
        if k then s[k] = v end
    end
    return s
end

--========================================================================================
-- the build: read the vanilla sheets, write the mod. fs = { read(path) -> data|nil, write(path, data) -> ok, mkdir(path) }
--========================================================================================
local function join(a, b) if a:sub(-1) == '/' or a:sub(-1) == '\\' then return a .. b end; return a .. '/' .. b end
GFX.join = join

function GFX.build(opts)
    local fs, src, out = opts.fs, opts.src, opts.out
    local p = GFX.preset(opts.preset or 'aquarium', opts.alphas)
    -- the bake: sand (default) or off; the vanilla preset is always the pure vanilla look (the restore path)
    local bake = (p.name == 'vanilla' or opts.bake == 'off') and 'off' or 'sand'
    local clock = opts.clock or os.clock
    local t0 = clock()
    local function load(name)
        local data = fs.read(join(src, name))
        if not data then error('cannot read ' .. join(src, name), 0) end
        return GFX.decode(data)
    end
    local sizes = {}
    local function note(name, img) sizes[#sizes + 1] = ('%s %dx%d'):format(name, img.w, img.h) end
    local gdir, idir = join(out, 'graphics'), join(join(out, 'graphics'), 'images')
    local written = {}
    local function put(path, data)
        if not fs.write(path, data) then error('cannot write ' .. path, 0) end
        written[#written + 1] = path
    end
    do   -- the small pages first; each source image is dropped as soon as its page is written
        local liq = load(GFX.SOURCES.liquids); note(GFX.SOURCES.liquids, liq)
        if liq.w < 96 or liq.h < 224 then error(('%s is %dx%d; expected at least 96x224 (3 columns x 7 rows)'):format(GFX.SOURCES.liquids, liq.w, liq.h), 0) end
        local mist = load(GFX.SOURCES.mist); note(GFX.SOURCES.mist, mist)
        if mist.w < 96 or mist.h < 128 then error(('%s is %dx%d; expected at least 96x128'):format(GFX.SOURCES.mist, mist.w, mist.h), 0) end
        fs.mkdir(idir)
        local page = GFX.liquidsPage(liq, p)
        local beds, rivers
        if bake == 'sand' then
            local B = GFX.BAKE_SOURCES
            local sand = load(B.sand); note(B.sand, sand)
            if sand.w < 128 or sand.h < 32 then error(('%s is %dx%d; expected at least 128x32'):format(B.sand, sand.w, sand.h), 0) end
            local floors = load(B.floors); note(B.floors, floors)
            local river = load(B.river); note(B.river, river)
            local brook = load(B.brook); note(B.brook, brook)
            if floors.w < 64 or floors.h < 256 or river.w < 32 or river.h < 512 or brook.w < 32 or brook.h < 448 then
                error('floors.png, river.png or brook.png is smaller than the vanilla sheets', 0)
            end
            beds = GFX.bedsPage(floors, river, brook, page)   -- the water tiles before the page is baked
            rivers = GFX.riverPage(floors, river, page)
            GFX.bakeLiquids(page, sand)
        else
            beds, rivers = GFX.bedsPage(nil), GFX.riverPage(nil)
        end
        put(join(idir, 'sw_aq_liquids.png'), GFX.encode(page))
        put(join(idir, 'sw_aq_beds.png'), GFX.encode(beds))
        put(join(idir, 'sw_aq_river.png'), GFX.encode(rivers))
        put(join(idir, 'sw_aq_mist.png'), GFX.encode(GFX.mistPage(mist, p)))
    end
    for v, name in ipairs(GFX.SOURCES.flows) do
        local img = load(name); note(name, img)
        if img.w ~= 512 or img.h ~= 256 then error(('%s is %dx%d; expected 512x256'):format(name, img.w, img.h), 0) end
        put(join(idir, ('sw_aq_flows%d.png'):format(v)), GFX.encode(GFX.flowsPage(img, p)))
    end
    put(join(out, 'info.txt'), GFX.infoText())
    put(join(gdir, 'tile_page_sw_aquarium.txt'), GFX.tilePageText())
    put(join(gdir, 'graphics_sw_aquarium.txt'), GFX.graphicsText(bake))
    put(join(out, GFX.CREATURE_TXT), GFX.creaturesText(GFX.creatureTexts(fs, GFX.creatureDir(src))))
    put(join(out, GFX.STAMP), GFX.stampText(p, opts.generator or 'lua', table.concat(sizes, '; '), bake))
    return { preset = p, files = written, seconds = clock() - t0, sources = sizes, bake = bake }
end

-- full sprites for vermin-class creatures (user 3 Oct): a creature whose vanilla graphics have a VERMIN tile and no
-- DEFAULT is drawn as DF's DEFAULTS placeholder (a teal blob) whenever it exists as a unit -- salmon, herring, shad, hake,
-- squid spawned in the water. DF merges CREATURE_GRAPHICS blocks by token (vanilla already splits one creature across the
-- small and portrait files), so the mod adds only the DEFAULT line, reusing the creature's own VERMIN tile.
GFX.CREATURE_TXT = 'graphics/graphics_sw_aquarium_creatures.txt'
-- vanilla_creatures_graphics/graphics, beside the vanilla_environment/graphics/images folder `src`
function GFX.creatureDir(src) return join(join(join(join(join(src, '..'), '..'), '..'), 'vanilla_creatures_graphics'), 'graphics') end
-- { name, text } of every creature graphics file (portraits and statues aside), sorted by name; fs.list optional
function GFX.creatureTexts(fs, dir)
    local names = {}
    for _, n in ipairs(fs.list and fs.list(dir) or {}) do
        n = tostring(n)
        if n:match('^graphics_creatures') and n:match('%.txt$') and not n:find('portrait') and not n:find('statue') then names[#names + 1] = n end
    end
    table.sort(names)
    local out = {}
    for _, n in ipairs(names) do
        local d = fs.read(join(dir, n))
        if d then out[#out + 1] = { name = n, text = d } end
    end
    return out
end
function GFX.creaturesText(texts)
    local have, vermin = {}, {}
    for _, f in ipairs(texts) do
        local cur, layerset
        for tag in f.text:gmatch('%[([^%]]+)%]') do
            local p = {}
            for x in (tag .. ':'):gmatch('([^:]*):') do p[#p + 1] = x end
            if (p[1] == 'CREATURE_GRAPHICS' or p[1] == 'CREATURE_CASTE_GRAPHICS') and #p > 1 then cur, layerset = p[2], nil
            elseif p[1]:match('CREATURE_GRAPHICS$') then cur = nil
            elseif cur then
                if p[1] == 'LAYER_SET' then
                    layerset = p[2] or ''
                    if layerset == 'DEFAULT' then have[cur] = true end
                elseif p[1] == 'DEFAULT' and layerset == nil then have[cur] = true
                elseif p[1] == 'VERMIN' and layerset == nil and #p >= 4 and not vermin[cur] then vermin[cur] = { p[2], p[3], p[4] } end
            end
        end
    end
    local toks = {}
    for tok in pairs(vermin) do if not have[tok] then toks[#toks + 1] = tok end end
    table.sort(toks)
    local t = { 'graphics_sw_aquarium_creatures', '', '[OBJECT:GRAPHICS]', '',
                '-- a full sprite for creatures that have only a vermin tile (their own tile, so a unit is not the placeholder) --', '' }
    for _, tok in ipairs(toks) do
        local v = vermin[tok]
        t[#t + 1] = ('[CREATURE_GRAPHICS:%s]'):format(tok)
        t[#t + 1] = ('\t[DEFAULT:%s:%s:%s:AS_IS]'):format(v[1], v[2], v[3])
        t[#t + 1] = ''
    end
    return table.concat(t, '\n')
end

-- the files a build writes, relative to the mod folder (uninstall removes exactly these, never anything else)
function GFX.files()
    local f = { 'info.txt', GFX.STAMP, 'graphics/tile_page_sw_aquarium.txt', 'graphics/graphics_sw_aquarium.txt', GFX.CREATURE_TXT,
                'graphics/images/sw_aq_liquids.png', 'graphics/images/sw_aq_mist.png', 'graphics/images/sw_aq_beds.png',
                'graphics/images/sw_aq_river.png' }
    for v = 1, 4 do f[#f + 1] = ('graphics/images/sw_aq_flows%d.png'):format(v) end
    return f
end

_ENV.GFX = GFX
return GFX
