namespace Xio.Parallax.Client.Tests.Sequences.Models;

// PC-102: validates SequenceOpenRequest's optional expected size
public sealed class SequenceOpenRequestTests
{
    [Fact]
    public void ExpectedSize_left_null_is_allowed()
    {
        var request = new SequenceOpenRequest(Array.Empty<ManifestPart>(), null);

        Assert.Null(request.ExpectedSize);
    }

    [Fact]
    public void ExpectedSize_must_be_above_zero_when_given()
    {
        var exception = Assert.Throws<ArgumentException>(() => new SequenceOpenRequest(Array.Empty<ManifestPart>(), 0));

        Assert.Equal("expectedSize", exception.ParamName);
        Assert.Throws<ArgumentException>(() => new SequenceOpenRequest(Array.Empty<ManifestPart>(), -1));
    }

    [Fact]
    public void ExpectedSize_is_kept_when_positive()
    {
        var request = new SequenceOpenRequest(Array.Empty<ManifestPart>(), 42);

        Assert.Equal(42, request.ExpectedSize);
    }
}
