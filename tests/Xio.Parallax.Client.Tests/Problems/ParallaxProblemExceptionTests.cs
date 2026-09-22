namespace Xio.Parallax.Client.Tests.Problems;

public sealed class ParallaxProblemExceptionTests
{
    [Fact]
    public void FromApiException_ReadsStatusSlugAndEveryExtensionField()
    {
        var problem = new ProblemDetails
        {
            Type = "urn:xio:parallax:problem:already-registered",
            Title = "Already registered",
            Detail = "This image is already registered.",
            Status = 409,
            ResponseStatusCode = 409,
            AdditionalData = new Dictionary<string, object>
            {
                ["traceId"] = "trace-123",
                ["cap"] = "registrations",
                ["registrationId"] = "33333333-3333-3333-3333-333333333333",
                ["registrationRemaining"] = 5,
                ["lookupRemaining"] = 10,
            },
            ResponseHeaders = new Dictionary<string, IEnumerable<string>>
            {
                ["Retry-After"] = ["7"],
            },
        };

        var wrapped = ParallaxProblemException.FromApiException(problem);

        Assert.Equal(409, wrapped.Status);
        Assert.Equal("urn:xio:parallax:problem:already-registered", wrapped.Type);
        Assert.Equal("already-registered", wrapped.Slug);
        Assert.Equal("Already registered", wrapped.Title);
        Assert.Equal("This image is already registered.", wrapped.Detail);
        Assert.Equal("trace-123", wrapped.TraceId);
        Assert.Equal("registrations", wrapped.Cap);
        Assert.Equal(Guid.Parse("33333333-3333-3333-3333-333333333333"), wrapped.RegistrationId);
        Assert.Equal(5, wrapped.RegistrationRemaining);
        Assert.Equal(10, wrapped.LookupRemaining);
        Assert.Equal(TimeSpan.FromSeconds(7), wrapped.RetryAfter);
    }

    [Fact]
    public void FromApiException_LeavesSlugNullWhenTheTypeCarriesNoProblemUrn()
    {
        var problem = new ProblemDetails
        {
            Type = "https://example.com/not-a-parallax-urn",
            Status = 400,
            ResponseStatusCode = 400,
            AdditionalData = new Dictionary<string, object>(),
        };

        var wrapped = ParallaxProblemException.FromApiException(problem);

        Assert.Null(wrapped.Slug);
    }

    [Fact]
    public void FromApiException_LeavesRetryAfterNullWhenTheHeaderIsAbsent()
    {
        var problem = new ProblemDetails
        {
            Type = "urn:xio:parallax:problem:validation-failed",
            Status = 400,
            ResponseStatusCode = 400,
            AdditionalData = new Dictionary<string, object>(),
        };

        var wrapped = ParallaxProblemException.FromApiException(problem);

        Assert.Null(wrapped.RetryAfter);
    }

    [Fact]
    public void FromApiException_FallsBackToTheStatusCodeAloneWhenTheFailureCarriesNoProblemBody()
    {
        var exception = new ApiException("Internal Server Error") { ResponseStatusCode = 500 };

        var wrapped = ParallaxProblemException.FromApiException(exception);

        Assert.Equal(500, wrapped.Status);
        Assert.Null(wrapped.Type);
        Assert.Null(wrapped.Slug);
        Assert.Equal("Internal Server Error", wrapped.Detail);
    }
}
