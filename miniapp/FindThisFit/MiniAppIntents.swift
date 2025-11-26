import AppIntents
import Foundation
import SwiftUI

struct SearchResultItem: Identifiable, Codable {
    let id: Int
    let externalID: String?
    let title: String?
    let description: String?
    let price: Double?
    let url: String?
    let imageURL: String?
    let distance: Double?
    let redirectURL: String?

    enum CodingKeys: String, CodingKey {
        case id
        case externalID = "external_id"
        case title
        case description
        case price
        case url
        case imageURL = "image_url"
        case distance
        case redirectURL = "redirect_url"
    }

    var displayPrice: String {
        guard let price else { return "—" }
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "GBP"
        return formatter.string(from: NSNumber(value: price)) ?? "£\(price)"
    }

    var matchLabel: String {
        guard let distance else { return "Visual match" }
        let clamped = max(0.0, min(1.0, 1.0 - min(distance, 1.0)))
        return "Match \(Int(clamped * 100))%"
    }
}

enum BackendClient {
    static var baseURL: URL = {
        if let configURL = Bundle.main.object(forInfoDictionaryKey: "API_BASE_URL") as? String,
           let url = URL(string: configURL) {
            return url
        }
        return URL(string: "http://localhost:8000")!
    }()

    static func search(imageData: Data) async throws -> [SearchResultItem] {
        let imageBase64 = imageData.base64EncodedString()
        let payload = ["image_base64": imageBase64]
        var request = URLRequest(url: baseURL.appendingPathComponent("search_by_image"))
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: payload, options: [])

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw NSError(domain: "BackendClient", code: 1, userInfo: [NSLocalizedDescriptionKey: "Server error"])
        }
        let decoded = try JSONDecoder().decode(SearchResponse.self, from: data)
        return decoded.items
    }
    
    static func searchByText(query: String) async throws -> [SearchResultItem] {
        let payload = ["query": query]
        var request = URLRequest(url: baseURL.appendingPathComponent("search_by_text"))
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: payload, options: [])

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw NSError(domain: "BackendClient", code: 1, userInfo: [NSLocalizedDescriptionKey: "Server error"])
        }
        let decoded = try JSONDecoder().decode(SearchResponse.self, from: data)
        return decoded.items
    }
    
    static func searchCombined(imageData: Data, query: String) async throws -> [SearchResultItem] {
        let imageBase64 = imageData.base64EncodedString()
        let payload: [String: Any] = [
            "image_base64": imageBase64,
            "query": query
        ]
        var request = URLRequest(url: baseURL.appendingPathComponent("search_combined"))
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: payload, options: [])

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw NSError(domain: "BackendClient", code: 1, userInfo: [NSLocalizedDescriptionKey: "Server error"])
        }
        let decoded = try JSONDecoder().decode(SearchResponse.self, from: data)
        return decoded.items
    }
}

struct SearchResponse: Codable {
    let items: [SearchResultItem]
}

struct FindThisFitIntent: AppIntent {
    static var title: LocalizedStringResource = "Find Similar Clothing"
    static var description = IntentDescription("Snap or pick a garment and find similar Depop listings.")

    @Parameter(title: "Photo")
    var photo: IntentFile

    func perform() async throws -> some IntentResult & ProvidesDialog {
        guard let url = photo.fileURL else {
            throw NSError(domain: "FindThisFitIntent", code: 0, userInfo: [NSLocalizedDescriptionKey: "No file URL for photo"])
        }
        let data = try Data(contentsOf: url)
        let results = try await BackendClient.search(imageData: data)
        return .result(dialog: "Found similar items!", view: ResultsView(results: results))
    }
}
