import AppKit

let destination = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true)

func png(_ pixels: Int) -> Data {
    let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: pixels, pixelsHigh: pixels,
        bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
        colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    let context = NSGraphicsContext(bitmapImageRep: bitmap)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = context
    context.cgContext.scaleBy(x: CGFloat(pixels)/1024, y: CGFloat(pixels)/1024)
    let base = NSBezierPath(roundedRect: NSRect(x: 70, y: 70, width: 884, height: 884), xRadius: 200, yRadius: 200)
    NSGradient(starting: NSColor(calibratedRed: 0.40, green: 0.43, blue: 0.94, alpha: 1),
               ending: NSColor(calibratedRed: 0.22, green: 0.24, blue: 0.69, alpha: 1))!.draw(in: base, angle: -70)
    NSGraphicsContext.saveGraphicsState()
    let shadow = NSShadow(); shadow.shadowColor = NSColor.black.withAlphaComponent(0.18)
    shadow.shadowBlurRadius = 35; shadow.shadowOffset = NSSize(width: 0, height: -15); shadow.set()
    let card = NSBezierPath(roundedRect: NSRect(x: 218, y: 290, width: 588, height: 465), xRadius: 84, yRadius: 84)
    NSColor.white.setFill(); card.fill()
    let tail = NSBezierPath(); tail.move(to: NSPoint(x: 295, y: 322)); tail.line(to: NSPoint(x: 295, y: 222))
    tail.curve(to: NSPoint(x: 327, y: 228), controlPoint1: NSPoint(x: 295, y: 204), controlPoint2: NSPoint(x: 310, y: 215))
    tail.line(to: NSPoint(x: 425, y: 306)); tail.close(); tail.fill()
    NSGraphicsContext.restoreGraphicsState()
    let purple = NSColor(calibratedRed: 0.34, green: 0.36, blue: 0.82, alpha: 1)
    for (x, y, width) in [(295.0, 620.0, 278.0), (295, 520, 408), (295, 420, 220)] {
        purple.withAlphaComponent(y == 520 ? 0.55 : 1).setFill()
        NSBezierPath(roundedRect: NSRect(x: x, y: y, width: width, height: 36), xRadius: 18, yRadius: 18).fill()
    }
    NSColor(calibratedRed: 1, green: 0.44, blue: 0.60, alpha: 1).setFill()
    NSBezierPath(ovalIn: NSRect(x: 605, y: 204, width: 228, height: 228)).fill()
    let triangle = NSBezierPath(); triangle.move(to: NSPoint(x: 696, y: 264)); triangle.line(to: NSPoint(x: 696, y: 372))
    triangle.line(to: NSPoint(x: 778, y: 318)); triangle.close()
    NSColor.white.setFill(); triangle.fill()
    NSGraphicsContext.restoreGraphicsState()
    return bitmap.representation(using: .png, properties: [:])!
}

for size in [16, 32, 128, 256, 512] {
    try png(size).write(to: destination.appendingPathComponent("icon_\(size)x\(size).png"))
    try png(size*2).write(to: destination.appendingPathComponent("icon_\(size)x\(size)@2x.png"))
}
