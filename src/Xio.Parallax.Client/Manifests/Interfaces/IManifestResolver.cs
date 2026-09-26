namespace Xio.Parallax.Client.Manifests.Interfaces;

/// <summary>
/// Resolves each image's manifest selection into the manifest parts it is registered with,
/// refusing conflicts before anything is sent.
/// </summary>
public interface IManifestResolver
{
    /// <summary>Resolves every request, then returns one registration item per request in order, or refuses them all.</summary>
    /// <param name="requests">The images and the selection each one's user chose.</param>
    /// <returns>One <see cref="RegistrationItem"/> per request, in order.</returns>
    /// <exception cref="ManifestRefusalException">Any image was refused; every offending image is listed and nothing is returned.</exception>
    IReadOnlyList<RegistrationItem> Resolve(IReadOnlyList<ManifestRequest> requests);

    /// <summary>Resolves one image's selection into its manifest parts: sidecars first in the given order, then embedded stores in document order.</summary>
    /// <param name="image">The image.</param>
    /// <param name="selection">The selection its user chose.</param>
    /// <returns>The manifest parts, in wire order.</returns>
    /// <exception cref="ManifestRefusalException">The image was refused.</exception>
    IReadOnlyList<ManifestPart> Resolve(ImageUpload image, ManifestSelection selection);
}
