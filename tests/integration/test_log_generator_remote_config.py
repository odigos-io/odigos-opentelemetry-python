"""InstrumentationRule + Sampling YAML fixtures applied to log-generator-app."""

import logging
import threading
from pathlib import Path
from unittest import mock

import pytest
import yaml
from opentelemetry.trace import SpanKind

import opamp.http_client
from initializer import setup_logging
from initializer.diagnose import apply_log_levels_from_opamp
from initializer.odigos_sampler import OdigosSampler
from opamp.http_client import MockOpAMPClient

FIXTURES_DIR = Path(__file__).parent / "fixtures"
LOG_GENERATOR_CLIENT_ATTRIBUTES = {
    "http.method": "GET",
    "http.url": "http://localhost:8080/health",
}


def _load_container_config() -> dict:
    instrumentation_rule = yaml.safe_load((FIXTURES_DIR / "log-generator-instrumentation-rule.yaml").read_text())
    sampling = yaml.safe_load((FIXTURES_DIR / "log-generator-sampling.yaml").read_text())

    container_config = {"agentDiagnostics": instrumentation_rule["spec"]["agentDiagnostics"]}
    container_config["traces"] = {"headSampling": {"noisyOperations": sampling["spec"]["noisyOperations"]}}
    return container_config


@pytest.fixture
def remote_config():
    return _load_container_config()


@pytest.fixture
def mock_opamp_with_remote_config(remote_config):
    class _RemoteConfigMockOpAMPClient(MockOpAMPClient):
        def __init__(self, opamp_connection_event, *args, **kwargs):
            super().__init__(opamp_connection_event, *args, **kwargs)
            self.container_config = remote_config

        def get_initial_sampler_config(self):
            return remote_config["traces"]["headSampling"]

    with (
        mock.patch("opamp.http_client.MockOpAMPClient", _RemoteConfigMockOpAMPClient),
        mock.patch("initializer.components.MockOpAMPClient", _RemoteConfigMockOpAMPClient),
    ):
        yield


@pytest.fixture
def odigos_logger():
    setup_logging()
    return logging.getLogger("odigos")


def test_agent_diagnostics_and_head_sampling_apply_together(remote_config, odigos_logger, caplog):
    apply_log_levels_from_opamp(remote_config)

    sampler = OdigosSampler()
    sampler.update_config(remote_config["traces"]["headSampling"])

    # The odigos logger has propagate=False, so caplog's root handler never sees its
    # records. Attach caplog's handler to the odigos logger directly to capture them.
    odigos_logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.DEBUG, logger="odigos"):
            sampler.should_sample(
                parent_context=None,
                trace_id=0x0123456789ABCDEF0123456789ABCDEF,
                name="GET",
                kind=SpanKind.CLIENT,
                attributes=LOG_GENERATOR_CLIENT_ATTRIBUTES,
            )
    finally:
        odigos_logger.removeHandler(caplog.handler)

    assert odigos_logger.isEnabledFor(logging.DEBUG)
    assert "Running Should_sample" in caplog.text
    assert "e2e-50pct" in caplog.text
    assert "lowest percentage 50" in caplog.text


def test_mock_opamp_client_serves_merged_remote_config(mock_opamp_with_remote_config, remote_config):
    class Event:
        event = threading.Event()

    client = opamp.http_client.MockOpAMPClient(Event)
    assert client.container_config["agentDiagnostics"]["odigosLogLevel"] == "debug"
    assert client.get_initial_sampler_config()["noisyOperations"][0]["percentageAtMost"] == 50
