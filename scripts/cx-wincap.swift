// cx-wincap.swift — stream ONE window's pixels to stdout as raw BGRA frames.
//
// ScreenCaptureKit captures the window itself, so DF is recorded even when a
// terminal covers it (ffmpeg's screen input records whatever is on top: it
// caught another session's terminal, 6 Oct). cx-record.sh pipes this into
// ffmpeg (-f rawvideo -pix_fmt bgra -s WxH).
//
//   cx-wincap <window-id> <seconds> <fps>
// stderr: one line "size W H" before the first frame, then a summary.
// Frames are pushed at the stream's rate; a frame DF did not change is
// repeated, so the output keeps real time.
import AppKit
import Foundation
import ScreenCaptureKit
import CoreMedia
import CoreVideo

let args = CommandLine.arguments
guard args.count == 4, let wid = UInt32(args[1]), let secs = Double(args[2]), let fps = Int32(args[3]) else {
    FileHandle.standardError.write("usage: cx-wincap <window-id> <seconds> <fps>\n".data(using: .utf8)!)
    exit(2)
}

final class Sink: NSObject, SCStreamOutput {
    let out = FileHandle.standardOutput
    var w = 0, h = 0, n = 0
    var last: Data?
    func stream(_ stream: SCStream, didOutputSampleBuffer sb: CMSampleBuffer, of type: SCStreamOutputType) {
        guard type == .screen else { return }
        // an idle frame carries no pixels: repeat the last one
        if let att = CMSampleBufferGetSampleAttachmentsArray(sb, createIfNecessary: false) as? [[SCStreamFrameInfo: Any]],
           let raw = att.first?[.status] as? Int, let st = SCFrameStatus(rawValue: raw), st != .complete {
            if st == .idle, let d = last { out.write(d); n += 1 }
            return
        }
        guard let pb = CMSampleBufferGetImageBuffer(sb) else { return }
        CVPixelBufferLockBaseAddress(pb, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(pb, .readOnly) }
        let bw = CVPixelBufferGetWidth(pb), bh = CVPixelBufferGetHeight(pb), stride = CVPixelBufferGetBytesPerRow(pb)
        if w == 0 { w = bw; h = bh; FileHandle.standardError.write("size \(w) \(h)\n".data(using: .utf8)!) }
        guard bw == w, bh == h, let base = CVPixelBufferGetBaseAddress(pb) else { return }
        var d = Data(capacity: w * h * 4)
        for y in 0..<h { d.append(base.advanced(by: y * stride).assumingMemoryBound(to: UInt8.self), count: w * 4) }
        last = d
        out.write(d)
        n += 1
    }
}

// a command-line tool must set up its app context first, or CoreGraphics
// asserts (CGS_REQUIRE_INIT) when the stream starts
_ = NSApplication.shared
let sink = Sink()
let done = DispatchSemaphore(value: 0)
Task {
    do {
        let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: false)
        guard let win = content.windows.first(where: { $0.windowID == wid }) else {
            FileHandle.standardError.write("cx-wincap: no window \(wid)\n".data(using: .utf8)!)
            exit(4)
        }
        let filter = SCContentFilter(desktopIndependentWindow: win)
        let cfg = SCStreamConfiguration()
        let scale = Int(filter.pointPixelScale)
        cfg.width = Int(win.frame.width) * max(1, scale)
        cfg.height = Int(win.frame.height) * max(1, scale)
        cfg.pixelFormat = kCVPixelFormatType_32BGRA
        cfg.minimumFrameInterval = CMTime(value: 1, timescale: fps)
        cfg.showsCursor = false
        cfg.queueDepth = 6
        let stream = SCStream(filter: filter, configuration: cfg, delegate: nil)
        try stream.addStreamOutput(sink, type: .screen, sampleHandlerQueue: DispatchQueue(label: "cap"))
        try await stream.startCapture()
        try await Task.sleep(nanoseconds: UInt64(secs * 1e9))
        try await stream.stopCapture()
        FileHandle.standardError.write("cx-wincap: \(sink.n) frames\n".data(using: .utf8)!)
    } catch {
        FileHandle.standardError.write("cx-wincap: \(error)\n".data(using: .utf8)!)
        exit(5)
    }
    done.signal()
}
done.wait()
