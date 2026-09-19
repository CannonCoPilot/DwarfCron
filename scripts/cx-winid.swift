import CoreGraphics
import Foundation
let list = CGWindowListCopyWindowInfo(CGWindowListOption(arrayLiteral: .optionAll), kCGNullWindowID) as! [[String: Any]]
for w in list {
    let owner = w["kCGWindowOwnerName"] as? String ?? ""
    let name = w["kCGWindowName"] as? String ?? ""
    let num = w["kCGWindowNumber"] as? Int ?? -1
    let pid = w["kCGWindowOwnerPID"] as? Int ?? -1
    let b = w["kCGWindowBounds"] as? [String: Any] ?? [:]
    let onscreen = w["kCGWindowIsOnscreen"] as? Bool ?? false
    if owner.contains("Dwarf") || owner.contains("wine") || name.contains("Dwarf") || pid == 50928 {
        print("\(num)|pid=\(pid)|onscreen=\(onscreen)|\(owner)|\(name)|\(b["X"] ?? 0),\(b["Y"] ?? 0),\(b["Width"] ?? 0)x\(b["Height"] ?? 0)")
    }
}
