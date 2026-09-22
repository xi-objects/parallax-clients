namespace Xio.Parallax.Client.Verification.Services;

internal sealed class SignatureChecker(IVerificationEncoding _encoding) : ISignatureChecker
{
    public VerificationCheck Check(XioSignatureCheckRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        if (request.PublicKey is not { } publicKey)
        {
            return new VerificationCheck(request.Name, VerificationOutcome.Failed, VerificationConstants.PublicKeyUnusableDetail);
        }

        var signature = _encoding.TryBase64(request.SignatureText);
        if (signature is null)
        {
            return new VerificationCheck(request.Name, VerificationOutcome.Failed, "The signature is absent or not base64.");
        }

        return VerifyEd25519(publicKey.Span, request.Preimage.Span, signature)
            ? new VerificationCheck(request.Name, VerificationOutcome.Passed, "The Ed25519 signature verifies under publicKey.")
            : new VerificationCheck(request.Name, VerificationOutcome.Failed, "The Ed25519 signature does not verify under publicKey.");
    }

    private static bool VerifyEd25519(ReadOnlySpan<byte> publicKey, ReadOnlySpan<byte> message, byte[] signature)
    {
        if (publicKey.Length != VerificationConstants.Ed25519PublicKeyLength || signature.Length != VerificationConstants.Ed25519SignatureLength)
        {
            return false;
        }

        Ed25519PublicKeyParameters key;
        try
        {
            key = new Ed25519PublicKeyParameters(publicKey);
        }
        catch (ArgumentException)
        {
            return false;
        }

        var signer = new Ed25519Signer();
        signer.Init(false, key);
        signer.BlockUpdate(message);
        return signer.VerifySignature(signature);
    }
}
