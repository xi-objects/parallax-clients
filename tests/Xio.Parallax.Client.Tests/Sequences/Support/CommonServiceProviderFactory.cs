namespace Xio.Parallax.Client.Tests.Sequences.Support;

// PC-104: the one Xio.Parallax.Common composition the sequence tests share for their reference encode and decode
/// <summary>Composes a Xio.Parallax.Common service provider for the tests' reference PX frame encode and decode.</summary>
internal static class CommonServiceProviderFactory
{
    /// <summary>Builds the provider, with a null logger standing in for the host Common's hash service expects.</summary>
    /// <returns>A provider resolving Common's encoder and decoder; the caller disposes it.</returns>
    internal static ServiceProvider Build()
    {
        var services = new ServiceCollection();
        services.AddSingleton(typeof(ILogger<>), typeof(NullLogger<>));
        services.AddXioParallaxCommon();
        return services.BuildServiceProvider();
    }
}
