-- DOM: the tool on CTRL with ecology on, livestock-as-prey off and v7.domestic {ON}; then rotation enabled.
local sw = reqscript('seasonal-wildlife'); local c = sw.loadConfig()
c.v7.domestic = {ON}; c.ecology.enabled = true; c.ecology.livestock = false; c.groups.enabled = true; c.layers.land = true
sw.saveConfig(c); dfhack.run_command_silent('seasonal-wildlife', 'enable')
local c2 = sw.loadConfig()
print(('eco domcfg domestic=%s livestock=%s ecology=%s enabled=%s'):format(tostring(c2.v7.domestic), tostring(c2.ecology.livestock), tostring(c2.ecology.enabled), tostring(c2.enabled)))
