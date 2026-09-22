namespace Xio.Parallax.Client.Verification.Models;

/// <summary>Thrown when a record or a trust root cannot be verified at all: an unimplemented algorithm, an unknown canonical version, a missing verification block, or no pinned root.</summary>
public sealed class VerificationRefusedException : Exception
{
    /// <summary>Creates the exception with the reason for the refusal.</summary>
    public VerificationRefusedException(string message)
        : base(message)
    {
    }

    /// <summary>Creates the exception with the reason for the refusal and the error that caused it.</summary>
    public VerificationRefusedException(string message, Exception innerException)
        : base(message, innerException)
    {
    }
}
