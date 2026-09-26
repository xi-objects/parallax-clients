namespace Xio.Parallax.Client.Tests.Shared;

/// <summary>
/// A <see cref="FactAttribute"/> that skips its test when the named fixture subfolder under
/// <c>fixtures/</c> is not present. <c>fixtures/</c> is a local capture, never part of the
/// repository, so a fresh clone must skip these tests rather than fail them.
/// </summary>
public sealed class FixtureFactAttribute : FactAttribute
{
    /// <summary>
    /// Skips the test unless <c>fixtures/&lt;fixtureSubfolder&gt;</c> is a directory next to the
    /// test binaries.
    /// </summary>
    /// <param name="fixtureSubfolder">The fixture subfolder the test reads, e.g. "record".</param>
    public FixtureFactAttribute(string fixtureSubfolder)
    {
        var path = Path.Combine(AppContext.BaseDirectory, "fixtures", fixtureSubfolder);
        if (!Directory.Exists(path))
        {
            Skip = $"fixtures/{fixtureSubfolder} is not present: a local capture, not part of the repository";
        }
    }
}
