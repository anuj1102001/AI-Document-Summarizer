from app.llm.client import _retry_after


def test_retry_after_reads_provider_hint():
    assert _retry_after(Exception("Quota exceeded. Please retry in 42.83s.")) == 43.83
    assert _retry_after(Exception("{'retryDelay': '17s'}")) == 18
    assert _retry_after(Exception("other error")) is None
