import Foundation
import Vision
import AppKit

func fail(_ message: String) -> Never {
    FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
    exit(1)
}

if CommandLine.arguments.count < 2 {
    fail("Usage: vision_ocr.swift <image-path>")
}

let imageURL = URL(fileURLWithPath: CommandLine.arguments[1])
guard let image = NSImage(contentsOf: imageURL) else {
    fail("Cannot read image: \(imageURL.path)")
}

var rect = CGRect(origin: .zero, size: image.size)
guard let cgImage = image.cgImage(forProposedRect: &rect, context: nil, hints: nil) else {
    fail("Cannot convert image: \(imageURL.path)")
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
request.recognitionLanguages = ["zh-Hans", "en-US"]

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
try handler.perform([request])

let observations = (request.results ?? []).sorted {
    if abs($0.boundingBox.midY - $1.boundingBox.midY) > 0.015 {
        return $0.boundingBox.midY > $1.boundingBox.midY
    }
    return $0.boundingBox.minX < $1.boundingBox.minX
}

for observation in observations {
    guard let candidate = observation.topCandidates(1).first else {
        continue
    }
    let text = candidate.string.trimmingCharacters(in: .whitespacesAndNewlines)
    if text.isEmpty {
        continue
    }
    let box = observation.boundingBox
    print("\(box.minX)\t\(box.minY)\t\(box.width)\t\(box.height)\t\(text)")
}

