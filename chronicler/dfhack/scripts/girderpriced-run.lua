-- girderpriced-run.lua — Unpause, clear blockers, verify advancement

print("=== GAME UNBLOCK ===")

-- Check focus
local focus = dfhack.gui.getCurFocus(true)
print("Focus: " .. tostring(focus[1]))

-- Clear popups
local ps = df.global.world.status.popups
local pop_count = #ps
while #ps > 0 do ps:erase(0) end
df.global.world.status.display_timer = 0
print("Cleared " .. pop_count .. " popups")

-- Dismiss any overlay viewscreens
for i = 1, 10 do
    local f = dfhack.gui.getCurFocus(true)
    if f[1] == "dwarfmode/Default" then break end
    dfhack.screen._doSimulateInput(dfhack.gui.getCurViewscreen(),
        {df.interface_key.LEAVESCREEN})
end
print("Focus after cleanup: " .. tostring(dfhack.gui.getCurFocus(true)[1]))

-- Force unpause
df.global.pause_state = false
print("Pause state: " .. tostring(df.global.pause_state))

-- Read current tick
print("Tick: " .. dfhack.world.ReadCurrentTick())
print("Year: " .. dfhack.world.ReadCurrentYear())
