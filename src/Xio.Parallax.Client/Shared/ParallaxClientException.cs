namespace Xio.Parallax.Client.Shared;

/// <summary>
/// Thrown when the client refuses to act rather than guess: batching without operator-configured
/// caps, or giving up after a poll timeout.
/// </summary>
public sealed class ParallaxClientException : Exception
{
    /// <summary>
    /// Creates a new <see cref="ParallaxClientException"/> naming what the client refused to do
    /// and why.
    /// </summary>
    /// <param name="message">What the client refused to do, and why.</param>
    public ParallaxClientException(string message)
        : base(message)
    {
    }

    /// <summary>Creates a new <see cref="ParallaxClientException"/> with no message.</summary>
    public ParallaxClientException()
    {
    }

    /// <summary>Creates a new <see cref="ParallaxClientException"/> wrapping an inner exception.</summary>
    /// <param name="message">What the client refused to do, and why.</param>
    /// <param name="innerException">The exception that caused this refusal.</param>
    public ParallaxClientException(string message, Exception innerException)
        : base(message, innerException)
    {
    }
}
