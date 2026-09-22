namespace Xio.Parallax.Client.Tests.Multipart;

public sealed class ManifestPartTests
{
    [Theory]
    [InlineData("c2pa")]
    [InlineData("xi-manifest")]
    [InlineData("k1")]
    [InlineData("A.b_c-9")]
    public void Constructor_AcceptsAKindMatchingThePattern(string kind)
    {
        var part = new ManifestPart(kind, ManifestForm.Json, new byte[] { 1, 2, 3 });

        Assert.Equal(kind, part.Kind);
    }

    [Theory]
    [InlineData("")]
    [InlineData("has space")]
    [InlineData("has/slash")]
    [InlineData("has[bracket]")]
    public void Constructor_RejectsAKindNotMatchingThePattern(string kind)
    {
        Assert.Throws<ArgumentException>(() => new ManifestPart(kind, ManifestForm.Json, new byte[] { 1 }));
    }

    [Fact]
    public void Constructor_RejectsAKindLongerThan64Characters()
    {
        var kind = new string('a', 65);

        Assert.Throws<ArgumentException>(() => new ManifestPart(kind, ManifestForm.Json, new byte[] { 1 }));
    }

    [Fact]
    public void Constructor_AcceptsA64CharacterKind()
    {
        var kind = new string('a', 64);

        var part = new ManifestPart(kind, ManifestForm.Json, new byte[] { 1 });

        Assert.Equal(64, part.Kind.Length);
    }
}
