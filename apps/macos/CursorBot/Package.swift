// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "CursorBot",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "CursorBot", targets: ["CursorBot"])
    ],
    dependencies: [
        .package(url: "https://github.com/Alamofire/Alamofire.git", from: "5.8.0"),
        .package(url: "https://github.com/daltoniam/Starscream.git", from: "4.0.0"),
        .package(url: "https://github.com/apple/swift-collections.git", from: "1.0.0"),
    ],
    targets: [
        .executableTarget(
            name: "CursorBot",
            dependencies: [
                "Alamofire",
                "Starscream",
                .product(name: "Collections", package: "swift-collections"),
            ],
            path: "Sources",
            exclude: ["Info.plist", "CursorBot.entitlements"]
        )
    ]
)
