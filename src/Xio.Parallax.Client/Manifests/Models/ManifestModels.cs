namespace Xio.Parallax.Client.Manifests.Models;

/// <summary>
/// A manifest file beside an image, chosen by the integrator's user: JSON with the kind the caller
/// states, or JUMBF classified c2pa or jumbf by its own bytes through the JUMBF walk.
/// </summary>
/// <param name="Name">What a refusal calls this sidecar, for example its file name.</param>
/// <param name="Form">
/// <see cref="ManifestForm.Json"/> or <see cref="ManifestForm.Jumbf"/>; <see cref="ManifestForm.C2pa"/>
/// is a classification result, never an input, and is refused.
/// </param>
/// <param name="Kind">The kind of a JSON sidecar, required; null for a JUMBF sidecar, whose kind is classified from its bytes.</param>
/// <param name="Bytes">The sidecar's raw bytes, sent unchanged.</param>
public sealed record SidecarManifest(string Name,
                                     ManifestForm Form,
                                     string? Kind,
                                     ReadOnlyMemory<byte> Bytes)
{
    /// <summary>What a refusal calls this sidecar.</summary>
    public string Name { get; } = ValidateName(Name);

    /// <summary>The sidecar's form: JSON or JUMBF.</summary>
    public ManifestForm Form { get; } = ValidateForm(Form);

    /// <summary>The stated kind of a JSON sidecar; null for a JUMBF sidecar.</summary>
    public string? Kind { get; } = ValidateKind(Form, Kind);

    /// <summary>A JSON sidecar of the stated kind.</summary>
    /// <param name="name">What a refusal calls it.</param>
    /// <param name="kind">Its kind, validated against ^[A-Za-z0-9._-]{1,64}$.</param>
    /// <param name="bytes">Its JSON bytes.</param>
    /// <returns>The sidecar.</returns>
    public static SidecarManifest Json(string name, string kind, ReadOnlyMemory<byte> bytes)
    {
        return new SidecarManifest(name, ManifestForm.Json, kind, bytes);
    }

    /// <summary>A JUMBF sidecar, classified c2pa or jumbf from its bytes when resolved.</summary>
    /// <param name="name">What a refusal calls it.</param>
    /// <param name="bytes">Its JUMBF superbox bytes.</param>
    /// <returns>The sidecar.</returns>
    public static SidecarManifest Jumbf(string name, ReadOnlyMemory<byte> bytes)
    {
        return new SidecarManifest(name, ManifestForm.Jumbf, null, bytes);
    }

    /// <summary>Reads a JSON sidecar from disk, named by its file name.</summary>
    /// <param name="path">The path to read.</param>
    /// <param name="kind">Its kind, validated against ^[A-Za-z0-9._-]{1,64}$.</param>
    /// <returns>The sidecar.</returns>
    public static SidecarManifest JsonFile(string path, string kind)
    {
        ArgumentException.ThrowIfNullOrEmpty(path);
        return Json(Path.GetFileName(path), kind, File.ReadAllBytes(path));
    }

    /// <summary>Reads a JUMBF sidecar from disk, named by its file name.</summary>
    /// <param name="path">The path to read.</param>
    /// <returns>The sidecar.</returns>
    public static SidecarManifest JumbfFile(string path)
    {
        ArgumentException.ThrowIfNullOrEmpty(path);
        return Jumbf(Path.GetFileName(path), File.ReadAllBytes(path));
    }

    private static string ValidateName(string name)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(name);
        return name;
    }

    private static ManifestForm ValidateForm(ManifestForm form)
    {
        if (form is not (ManifestForm.Json or ManifestForm.Jumbf))
        {
            throw new ArgumentException($"A sidecar is JSON or JUMBF; '{form}' is a classification result, never an input.", nameof(form));
        }

        return form;
    }

    private static string? ValidateKind(ManifestForm form, string? kind)
    {
        if (form == ManifestForm.Jumbf)
        {
            return kind is null
                ? null
                : throw new ArgumentException("A JUMBF sidecar states no kind: its kind is classified from its bytes.", nameof(kind));
        }

        return kind is null
            ? throw new ArgumentException("A JSON sidecar needs its kind stated.", nameof(kind))
            : ManifestPart.ValidateKind(kind);
    }
}

/// <summary>Which manifests an image is registered with: its embedded JUMBF manifest store(s) or not, and its sidecars.</summary>
/// <param name="IncludeEmbedded">True to include every embedded JUMBF manifest store, each under its classified kind.</param>
/// <param name="Sidecars">The sidecars, sent first on the wire in this order.</param>
public sealed record ManifestSelection(bool IncludeEmbedded,
                                       IReadOnlyList<SidecarManifest> Sidecars)
{
    /// <summary>Neither embedded stores nor sidecars: the image is registered with no manifest.</summary>
    public static readonly ManifestSelection None = new(false, []);

    /// <summary>The sidecars, sent first on the wire in this order.</summary>
    public IReadOnlyList<SidecarManifest> Sidecars { get; } = Sidecars ?? throw new ArgumentNullException(nameof(Sidecars));
}

/// <summary>One image and the manifest selection its user chose.</summary>
/// <param name="Image">The image to register.</param>
/// <param name="Selection">Which manifests it is registered with.</param>
public sealed record ManifestRequest(ImageUpload Image,
                                     ManifestSelection Selection);

/// <summary>Why one image's manifests were refused.</summary>
/// <param name="FileName">The image's file name.</param>
/// <param name="Reason">The one reason its manifests were refused.</param>
public sealed record ManifestRefusal(string FileName,
                                     string Reason);
