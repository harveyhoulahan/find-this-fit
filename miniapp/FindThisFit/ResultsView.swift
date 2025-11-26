import SwiftUI

struct ResultsView: View {
    let results: [SearchResultItem]
    @Environment(\.openURL) private var openURL

    private let columns = [
        GridItem(.flexible(), spacing: 16),
        GridItem(.flexible(), spacing: 16)
    ]

    var body: some View {
        LazyVGrid(columns: columns, spacing: 20) {
            ForEach(results) { item in
                Button {
                    openListing(item)
                } label: {
                    VStack(alignment: .leading, spacing: 0) {
                        // Image section with badges
                        ZStack(alignment: .bottomLeading) {
                            GeometryReader { geo in
                                listingImage(for: item)
                                    .frame(width: geo.size.width, height: geo.size.width * 1.2)
                                    .clipped()
                                    .background(Color.gray.opacity(0.15))
                                    .overlay(
                                        // Subtle gradient overlay on image
                                        LinearGradient(
                                            colors: [Color.clear, Color.clear, Color.black.opacity(0.3)],
                                            startPoint: .top,
                                            endPoint: .bottom
                                        )
                                    )
                            }
                            .aspectRatio(1/1.2, contentMode: .fit)

                            // Price and match badges overlaid on image
                            VStack(alignment: .leading, spacing: 6) {
                                HStack(spacing: 6) {
                                    // Price badge
                                    Text(item.displayPrice)
                                        .font(.system(.caption2, design: .rounded, weight: .bold))
                                        .foregroundStyle(.white)
                                        .padding(.horizontal, 8)
                                        .padding(.vertical, 4)
                                        .background(
                                            Capsule()
                                                .fill(Color.black.opacity(0.7))
                                                .overlay(
                                                    Capsule()
                                                        .strokeBorder(Color.white.opacity(0.2), lineWidth: 0.5)
                                                )
                                        )
                                    
                                    // Match percentage badge
                                    Text(item.matchLabel)
                                        .font(.system(.caption2, design: .rounded, weight: .bold))
                                        .foregroundStyle(.white)
                                        .padding(.horizontal, 8)
                                        .padding(.vertical, 4)
                                        .background(
                                            Capsule()
                                                .fill(
                                                    LinearGradient(
                                                        colors: [
                                                            Color(red: 1.0, green: 0.42, blue: 0.58),
                                                            Color(red: 0.45, green: 0.25, blue: 0.98)
                                                        ],
                                                        startPoint: .leading,
                                                        endPoint: .trailing
                                                    )
                                                )
                                        )
                                    
                                    Spacer()
                                }
                            }
                            .padding(8)
                        }
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))

                        // Title section below image
                        VStack(alignment: .leading, spacing: 4) {
                            Text(item.title ?? "Fashion item")
                                .font(.system(.caption, design: .rounded, weight: .semibold))
                                .foregroundStyle(.white)
                                .lineLimit(2)
                                .multilineTextAlignment(.leading)
                                .fixedSize(horizontal: false, vertical: true)
                            
                            HStack(spacing: 4) {
                                Image(systemName: "arrow.up.right")
                                    .font(.system(size: 9, weight: .bold))
                                    .foregroundStyle(Color(red: 1.0, green: 0.42, blue: 0.58))
                                Text("View")
                                    .font(.system(size: 10, weight: .medium, design: .rounded))
                                    .foregroundStyle(Color.white.opacity(0.6))
                            }
                        }
                        .padding(.horizontal, 6)
                        .padding(.top, 10)
                        .padding(.bottom, 6)
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .buttonStyle(.plain)
            }
        }
    }

    @ViewBuilder
    private func listingImage(for item: SearchResultItem) -> some View {
        if let urlString = item.imageURL, let url = URL(string: urlString) {
            AsyncImage(url: url) { phase in
                switch phase {
                case .empty:
                    ZStack {
                        Color.gray.opacity(0.15)
                        ProgressView()
                            .tint(.white.opacity(0.5))
                    }
                case .success(let image):
                    image
                        .resizable()
                        .scaledToFill()
                case .failure:
                    ZStack {
                        Color.gray.opacity(0.2)
                        Image(systemName: "photo")
                            .font(.title3)
                            .foregroundStyle(.white.opacity(0.3))
                    }
                @unknown default:
                    Color.gray.opacity(0.2)
                }
            }
        } else {
            ZStack {
                LinearGradient(
                    colors: [
                        Color.white.opacity(0.08),
                        Color(red: 0.45, green: 0.25, blue: 0.98).opacity(0.2),
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                Image(systemName: "photo")
                    .font(.title3)
                    .foregroundStyle(.white.opacity(0.3))
            }
        }
    }

    private func openListing(_ item: SearchResultItem) {
        if let link = item.redirectURL, let url = URL(string: link) {
            openURL(url)
        } else if let urlString = item.url, let url = URL(string: urlString) {
            openURL(url)
        }
    }
}
