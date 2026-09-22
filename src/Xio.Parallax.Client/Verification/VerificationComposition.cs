namespace Xio.Parallax.Client.Verification;

/// <summary>The verification domain's wiring: each stateless service built once, over the interfaces it depends on; the public entry points compose from here.</summary>
internal static class VerificationComposition
{
    internal static readonly IVerificationEncoding Encoding = new VerificationEncoding();

    internal static readonly IPemCertificateParser PemParser = new PemCertificateParser();

    internal static readonly ICanonicalPreimageBuilder PreimageBuilder = new CanonicalPreimageBuilder();

    internal static readonly ISignatureChecker SignatureChecker = new SignatureChecker(Encoding);

    internal static readonly IRecordAdmission Admission = new RecordAdmission(Encoding);

    internal static readonly IImageHashChecker ImageHashChecker = new ImageHashChecker();

    internal static readonly IManifestChecker ManifestChecker = new ManifestChecker(Encoding,
                                                                                    PreimageBuilder,
                                                                                    SignatureChecker);

    internal static readonly ICertificateChainValidator ChainValidator = new CertificateChainValidator(PemParser);
}
