namespace Xio.Parallax.Client.Verification.Interfaces;

/// <summary>Checks one base64 Ed25519 signature over a preimage under the record's public key.</summary>
internal interface ISignatureChecker
{
    /// <summary>Returns the named check's verdict; an unusable key or signature text fails it.</summary>
    VerificationCheck Check(XioSignatureCheckRequest request);
}
