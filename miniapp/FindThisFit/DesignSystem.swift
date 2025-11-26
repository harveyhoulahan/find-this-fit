import SwiftUI

enum DS {
    static let accentGradient = LinearGradient(
        colors: [
            Color(red: 1.0, green: 0.42, blue: 0.58),
            Color(red: 0.45, green: 0.25, blue: 0.98),
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
    static let surface = Color.white.opacity(0.08)
    static let stroke = Color.white.opacity(0.12)
    static let textPrimary = Color.white
    static let textMuted = Color.white.opacity(0.75)
    static let cardShadow = Color.black.opacity(0.25)
    static let cardGradient = LinearGradient(
        colors: [
            Color.white.opacity(0.04),
            Color.white.opacity(0.02),
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
}

extension View {
    func elevatedShadow() -> some View {
        shadow(color: DS.cardShadow, radius: 14, x: 0, y: 10)
    }
}

struct GlassCard<Content: View>: View {
    var padding: CGFloat = 14
    @ViewBuilder var content: () -> Content

    var body: some View {
        RoundedRectangle(cornerRadius: 18, style: .continuous)
            .fill(DS.surface)
            .overlay(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .stroke(DS.stroke, lineWidth: 1)
            )
            .overlay(
                content()
                    .padding(padding)
            )
    }
}

struct PillLabel: View {
    var text: String
    var gradient: LinearGradient? = nil
    var background: Color = Color.white.opacity(0.12)
    var textColor: Color = .white

    var body: some View {
        Text(text)
            .font(.system(.caption, design: .rounded, weight: .semibold))
            .foregroundStyle(textColor)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(
                Group {
                    if let gradient {
                        gradient
                    } else {
                        background
                    }
                }
            )
            .clipShape(Capsule())
    }
}

struct AccentButtonLabel: View {
    var title: String
    var subtitle: String?
    var icon: String = "bolt.fill"

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundStyle(.white)
                .font(.system(.headline, weight: .semibold))
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.system(.headline, design: .rounded, weight: .semibold))
                    .foregroundStyle(.white)
                if let subtitle {
                    Text(subtitle)
                        .font(.system(.footnote, design: .rounded))
                        .foregroundStyle(DS.textMuted)
                }
            }
            Spacer()
        }
        .padding()
        .frame(maxWidth: .infinity)
        .background(DS.accentGradient)
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            .elevatedShadow()
    }
}

struct PrimaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(.headline, design: .rounded, weight: .semibold))
            .foregroundStyle(.white)
            .padding(.vertical, 16)
            .padding(.horizontal, 18)
            .frame(maxWidth: .infinity)
            .background(
                DS.accentGradient
                    .brightness(configuration.isPressed ? -0.05 : 0)
            )
            .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
            .elevatedShadow()
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
            .animation(.spring(response: 0.2, dampingFraction: 0.7), value: configuration.isPressed)
    }
}
