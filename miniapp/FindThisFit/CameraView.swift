import PhotosUI
import SwiftUI
import UIKit

struct CameraView: View {
    @State private var selectedItem: PhotosPickerItem?
    @State private var imageData: Data?
    @State private var results: [SearchResultItem] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var showImagePicker = false
    @State private var imageSourceType: UIImagePickerController.SourceType = .photoLibrary
    @State private var showCameraAlert = false
    @State private var searchText = ""
    @FocusState private var isTextFieldFocused: Bool

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [
                    Color(red: 0.08, green: 0.09, blue: 0.13),
                    Color(red: 0.05, green: 0.06, blue: 0.10),
                ],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()

            ScrollView(showsIndicators: false) {
                VStack(spacing: 20) {
                    header
                    
                    // Combined interface - always show both options
                    captureCard
                    textSearchSection
                    searchButton
                    
                    proTip
                    statusSection

                    if !results.isEmpty {
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                Text("Similar Items")
                                    .font(.system(.title2, design: .rounded, weight: .heavy))
                                    .foregroundStyle(.white)
                                
                                Spacer()
                                
                                Text("\(results.count)")
                                    .font(.system(.title3, design: .rounded, weight: .bold))
                                    .foregroundStyle(.white.opacity(0.5))
                            }
                            .padding(.horizontal, 4)
                        }
                        .padding(.top, 8)
                        
                        ResultsView(results: results)
                            .animation(.spring(response: 0.45, dampingFraction: 0.85), value: results.count)
                    }
                }
                .padding(20)
            }
        }
        .onChange(of: selectedItem) { _, newValue in
            guard let newValue else { return }
            Task { await loadImage(item: newValue) }
        }
        .sheet(isPresented: $showImagePicker) {
            ImagePicker(sourceType: imageSourceType) { image in
                if let data = image.jpegData(compressionQuality: 0.8) {
                    imageData = data
                }
            }
        }
        .alert("Camera Not Available", isPresented: $showCameraAlert) {
            Button("OK", role: .cancel) { }
        } message: {
            Text("Camera is not available on this device or in the simulator. Please use a physical device to take photos.")
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Image(systemName: "sparkles")
                    .foregroundStyle(
                        LinearGradient(
                            colors: [Color(red: 1.0, green: 0.42, blue: 0.58), Color(red: 0.45, green: 0.25, blue: 0.98)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .font(.title3.weight(.bold))
                Text("Fashion search")
                    .font(.system(.callout, design: .rounded, weight: .medium))
                    .foregroundStyle(Color.white.opacity(0.7))
            }
            Text("Find This Fit")
                .font(.system(size: 38, weight: .heavy, design: .rounded))
                .foregroundStyle(.white)
                .tracking(-0.5)
            Text("Use a photo, describe it, or both for best results.")
                .font(.system(.subheadline, design: .rounded))
                .foregroundStyle(Color.white.opacity(0.65))
                .lineSpacing(2)
        }
        .padding(.top, 4)
        .padding(.bottom, 8)
    }
    
    private var textSearchSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Image(systemName: "text.bubble.fill")
                    .foregroundStyle(Color.white.opacity(0.7))
                    .font(.system(.subheadline, weight: .semibold))
                Text("Describe the item (optional)")
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.white.opacity(0.8))
            }
            
            TextField("e.g., vintage denim jacket with patches...", text: $searchText, axis: .vertical)
                .focused($isTextFieldFocused)
                .font(.system(.body, design: .rounded))
                .foregroundStyle(.white)
                .lineLimit(2...4)
                .padding(14)
                .background(
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .fill(Color.white.opacity(0.08))
                        .overlay(
                            RoundedRectangle(cornerRadius: 14, style: .continuous)
                                .stroke(Color.white.opacity(0.15), lineWidth: 1)
                        )
                )
        }
    }

    private var captureCard: some View {
        VStack(spacing: 12) {
            HStack(spacing: 8) {
                Image(systemName: "camera.viewfinder")
                    .foregroundStyle(Color.white.opacity(0.7))
                    .font(.system(.subheadline, weight: .semibold))
                Text("Add a photo (optional)")
                    .font(.system(.subheadline, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.white.opacity(0.8))
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            
            ZStack {
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .fill(DS.cardGradient)

                if let imageData, let uiImage = UIImage(data: imageData) {
                    ZStack(alignment: .topTrailing) {
                        Image(uiImage: uiImage)
                            .resizable()
                            .scaledToFill()
                            .frame(maxWidth: .infinity)
                            .frame(height: 180)
                            .clipped()
                            .cornerRadius(16)
                        
                        // Remove button
                        Button {
                            withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
                                self.imageData = nil
                            }
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .font(.system(.title2, weight: .semibold))
                                .foregroundStyle(.white)
                                .background(
                                    Circle()
                                        .fill(Color.black.opacity(0.5))
                                        .padding(-4)
                                )
                        }
                        .padding(10)
                    }
                } else {
                    // Image picker buttons
                    HStack(spacing: 12) {
                        // Camera button
                        Button {
                            if UIImagePickerController.isSourceTypeAvailable(.camera) {
                                imageSourceType = .camera
                                showImagePicker = true
                            } else {
                                showCameraAlert = true
                            }
                        } label: {
                            VStack(spacing: 8) {
                                Image(systemName: "camera.fill")
                                    .font(.system(.title2, weight: .semibold))
                                    .foregroundStyle(
                                        LinearGradient(
                                            colors: [
                                                Color(red: 1.0, green: 0.42, blue: 0.58),
                                                Color(red: 0.45, green: 0.25, blue: 0.98),
                                            ],
                                            startPoint: .topLeading,
                                            endPoint: .bottomTrailing
                                        )
                                    )
                                Text("Camera")
                                    .font(.system(.caption, design: .rounded, weight: .semibold))
                                    .foregroundStyle(Color.white.opacity(0.9))
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 20)
                        }
                        
                        Divider()
                            .background(Color.white.opacity(0.2))
                            .frame(height: 60)
                        
                        // Photo library button
                        PhotosPicker(selection: $selectedItem, matching: .images, photoLibrary: .shared()) {
                            VStack(spacing: 8) {
                                Image(systemName: "photo.on.rectangle")
                                    .font(.system(.title2, weight: .semibold))
                                    .foregroundStyle(
                                        LinearGradient(
                                            colors: [
                                                Color(red: 1.0, green: 0.42, blue: 0.58),
                                                Color(red: 0.45, green: 0.25, blue: 0.98),
                                            ],
                                            startPoint: .topLeading,
                                            endPoint: .bottomTrailing
                                        )
                                    )
                                Text("Library")
                                    .font(.system(.caption, design: .rounded, weight: .semibold))
                                    .foregroundStyle(Color.white.opacity(0.9))
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 20)
                        }
                    }
                    .padding(.horizontal, 20)
                }
            }
            .frame(height: 180)
            .shadow(color: Color.black.opacity(0.2), radius: 12, x: 0, y: 6)
        }
    }
    
    private var searchButton: some View {
        VStack(spacing: 12) {
            Button {
                isTextFieldFocused = false
                Task { await performSearch() }
            } label: {
                HStack(spacing: 10) {
                    if isLoading {
                        ProgressView()
                            .tint(.white)
                    } else {
                        Image(systemName: "sparkles.rectangle.stack.fill")
                            .font(.system(.body, weight: .bold))
                    }
                    Text(isLoading ? "Searching..." : hasSearchContent ? "Search" : "Add photo or description")
                        .font(.system(.body, design: .rounded, weight: .bold))
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 16)
                .background(
                    hasSearchContent ?
                    AnyView(LinearGradient(
                        colors: [
                            Color(red: 1.0, green: 0.42, blue: 0.58),
                            Color(red: 0.45, green: 0.25, blue: 0.98)
                        ],
                        startPoint: .leading,
                        endPoint: .trailing
                    )) :
                    AnyView(Color.white.opacity(0.1))
                )
                .foregroundStyle(.white)
                .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            }
            .disabled(!hasSearchContent || isLoading)
            .opacity(!hasSearchContent ? 0.5 : 1)
            
            if hasSearchContent {
                Button {
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
                        imageData = nil
                        searchText = ""
                        results = []
                        errorMessage = nil
                    }
                } label: {
                    HStack(spacing: 8) {
                        Image(systemName: "arrow.counterclockwise")
                            .font(.system(.subheadline, weight: .semibold))
                        Text("Clear all")
                            .font(.system(.subheadline, design: .rounded, weight: .semibold))
                    }
                    .foregroundStyle(Color.white.opacity(0.6))
                    .padding(.vertical, 8)
                }
            }
        }
    }
    
    private var hasSearchContent: Bool {
        imageData != nil || !searchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private var proTip: some View {
        HStack(spacing: 12) {
            Image(systemName: "lightbulb.fill")
                .foregroundStyle(
                    LinearGradient(
                        colors: [Color.yellow.opacity(0.9), Color.orange.opacity(0.8)],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )
                .font(.system(.body, weight: .semibold))
            
            VStack(alignment: .leading, spacing: 4) {
                Text("Pro tip")
                    .font(.system(.caption, design: .rounded, weight: .bold))
                    .foregroundStyle(Color.white.opacity(0.9))
                    .textCase(.uppercase)
                    .tracking(0.5)
                Text("Combine photo + description for the most accurate results")
                    .font(.system(.subheadline, design: .rounded))
                    .foregroundStyle(Color.white.opacity(0.75))
            }
            
            Spacer()
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(Color.white.opacity(0.04))
                .overlay(
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .stroke(Color.white.opacity(0.08), lineWidth: 1)
                )
        )
    }

    private var statusSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            if let errorMessage {
                HStack(spacing: 12) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundStyle(Color(red: 1.0, green: 0.42, blue: 0.58))
                        .font(.system(.body, weight: .semibold))
                    Text(errorMessage)
                        .font(.system(.subheadline, design: .rounded))
                        .foregroundStyle(.white)
                    Spacer()
                }
                .padding(16)
                .background(
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .fill(Color.red.opacity(0.12))
                        .overlay(
                            RoundedRectangle(cornerRadius: 14, style: .continuous)
                                .stroke(Color.red.opacity(0.3), lineWidth: 1)
                        )
                )
            } else {
                HStack(spacing: 12) {
                    Image(systemName: "lock.shield.fill")
                        .foregroundStyle(Color.green.opacity(0.9))
                        .font(.system(.body, weight: .semibold))
                    Text("Private & secure • Photos processed on demand")
                        .font(.system(.footnote, design: .rounded, weight: .medium))
                        .foregroundStyle(Color.white.opacity(0.7))
                    Spacer()
                }
                .padding(14)
                .background(
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .fill(Color.white.opacity(0.03))
                        .overlay(
                            RoundedRectangle(cornerRadius: 12, style: .continuous)
                                .stroke(Color.white.opacity(0.06), lineWidth: 1)
                        )
                )
            }
        }
    }

    @MainActor
    private func loadImage(item: PhotosPickerItem) async {
        do {
            if let data = try await item.loadTransferable(type: Data.self) {
                imageData = data
            }
        } catch {
            errorMessage = "Failed to load image: \(error.localizedDescription)"
        }
    }
    
    @MainActor
    private func performSearch() async {
        let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        
        // Need at least one input
        guard imageData != nil || !query.isEmpty else {
            errorMessage = "Please add a photo or description to search"
            return
        }
        
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        
        do {
            let fetched: [SearchResultItem]
            
            // Combined search (image + text)
            if let imageData = imageData, !query.isEmpty {
                fetched = try await BackendClient.searchCombined(imageData: imageData, query: query)
            }
            // Image only
            else if let imageData = imageData {
                fetched = try await BackendClient.search(imageData: imageData)
            }
            // Text only
            else {
                fetched = try await BackendClient.searchByText(query: query)
            }
            
            withAnimation(.spring(response: 0.45, dampingFraction: 0.85)) {
                results = fetched
            }
        } catch {
            errorMessage = "Search failed: \(error.localizedDescription)"
        }
    }
}

// MARK: - UIImagePickerController Wrapper
struct ImagePicker: UIViewControllerRepresentable {
    let sourceType: UIImagePickerController.SourceType
    let onImagePicked: (UIImage) -> Void
    @Environment(\.dismiss) private var dismiss
    
    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = sourceType
        picker.delegate = context.coordinator
        return picker
    }
    
    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}
    
    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }
    
    class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let parent: ImagePicker
        
        init(_ parent: ImagePicker) {
            self.parent = parent
        }
        
        func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey : Any]) {
            if let image = info[.originalImage] as? UIImage {
                parent.onImagePicked(image)
            }
            parent.dismiss()
        }
        
        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            parent.dismiss()
        }
    }
}
