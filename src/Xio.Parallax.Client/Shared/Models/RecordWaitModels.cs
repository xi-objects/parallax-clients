namespace Xio.Parallax.Client.Shared.Models;

/// <summary>
/// Options for <see cref="ParallaxClient.WaitForRecordAsync"/>: how long to wait between record
/// polls, and how long to keep polling before giving up.
/// </summary>
/// <param name="PollInterval">
/// How long to wait between record polls, and the starting point for the bounded exponential
/// backoff between later polls. Required: there is no default.
/// </param>
/// <param name="PollTimeout">
/// How long to keep polling before giving up. Required: there is no default, since only the
/// caller knows how long is reasonable to wait for a record to publish.
/// </param>
public sealed record RecordWaitOptions(TimeSpan PollInterval, TimeSpan PollTimeout);
