"""Test the dnsip config flow."""
from __future__ import annotations

from unittest.mock import patch

from aiodns.error import DNSError
import pytest

from homeassistant import config_entries
from homeassistant.components.dnsip.const import (
    CONF_HOSTNAME,
    CONF_IPV4,
    CONF_IPV6,
    CONF_RESOLVER,
    CONF_RESOLVER_IPV6,
    DOMAIN,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import (
    RESULT_TYPE_ABORT,
    RESULT_TYPE_CREATE_ENTRY,
    RESULT_TYPE_FORM,
)

from tests.common import MockConfigEntry


class RetrieveDNS:
    """Return list of test information."""

    @staticmethod
    async def query(hostname, qtype) -> dict[str, str]:
        """Return information."""
        return {"hostname": "1.2.3.4"}

    @property
    def nameservers(self) -> list[str]:
        """Return nameserver."""
        return ["1.2.3.4"]


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.dnsip.config_flow.aiodns.DNSResolver",
        return_value=RetrieveDNS(),
    ), patch(
        "homeassistant.components.dnsip.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOSTNAME: "home-assistant.io",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == "home-assistant.io"
    assert result2["data"] == {
        "hostname": "home-assistant.io",
        "name": "home-assistant.io",
        "ipv4": True,
        "ipv6": True,
    }
    assert result2["options"] == {
        "resolver": "208.67.222.222",
        "resolver_ipv6": "2620:0:ccc::2",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_error(hass: HomeAssistant) -> None:
    """Test validate url fails."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.dnsip.config_flow.aiodns.DNSResolver",
        side_effect=DNSError("Did not find"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOSTNAME: "home-assistant.io",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["step_id"] == "user"
    assert result2["errors"] == {"base": "invalid_hostname"}


@pytest.mark.parametrize(
    "p_input,p_output,p_options",
    [
        (
            {CONF_HOSTNAME: "home-assistant.io"},
            {
                "hostname": "home-assistant.io",
                "name": "home-assistant.io",
                "ipv4": True,
                "ipv6": True,
            },
            {
                "resolver": "208.67.222.222",
                "resolver_ipv6": "2620:0:ccc::2",
            },
        ),
        (
            {},
            {
                "hostname": "myip.opendns.com",
                "name": "myip",
                "ipv4": True,
                "ipv6": True,
            },
            {
                "resolver": "208.67.222.222",
                "resolver_ipv6": "2620:0:ccc::2",
            },
        ),
    ],
)
async def test_import_flow_success(
    hass: HomeAssistant,
    p_input: dict[str, str],
    p_output: dict[str, str],
    p_options: dict[str, str],
) -> None:
    """Test a successful import of YAML."""

    with patch(
        "homeassistant.components.dnsip.config_flow.aiodns.DNSResolver",
        return_value=RetrieveDNS(),
    ), patch(
        "homeassistant.components.dnsip.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=p_input,
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == p_output["name"]
    assert result2["data"] == p_output
    assert result2["options"] == p_options
    assert len(mock_setup_entry.mock_calls) == 1


async def test_flow_already_exist(hass: HomeAssistant) -> None:
    """Test flow when unique id already exist."""

    MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOSTNAME: "home-assistant.io",
            CONF_NAME: "home-assistant.io",
            CONF_IPV4: True,
            CONF_IPV6: True,
        },
        options={
            CONF_RESOLVER: "208.67.222.222",
            CONF_RESOLVER_IPV6: "2620:0:ccc::2",
        },
        unique_id="home-assistant.io",
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.dnsip.async_setup_entry",
        return_value=True,
    ), patch(
        "homeassistant.components.dnsip.config_flow.aiodns.DNSResolver",
        return_value=RetrieveDNS,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOSTNAME: "home-assistant.io",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_ABORT
    assert result2["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test options config flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="12345",
        data={
            CONF_HOSTNAME: "home-assistant.io",
            CONF_NAME: "home-assistant.io",
            CONF_IPV4: True,
            CONF_IPV6: False,
        },
        options={
            CONF_RESOLVER: "208.67.222.222",
            CONF_RESOLVER_IPV6: "2620:0:ccc::2",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.dnsip.config_flow.aiodns.DNSResolver",
        return_value=RetrieveDNS(),
    ), patch(
        "homeassistant.components.dnsip.async_setup_entry",
        return_value=True,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_RESOLVER: "8.8.8.8",
            CONF_RESOLVER_IPV6: "2001:4860:4860::8888",
        },
    )

    assert result["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result["data"] == {
        "resolver": "8.8.8.8",
        "resolver_ipv6": "2001:4860:4860::8888",
    }


@pytest.mark.parametrize(
    "p_input",
    [
        {
            CONF_HOSTNAME: "home-assistant.io",
            CONF_NAME: "home-assistant.io",
            CONF_RESOLVER: "208.67.222.222",
            CONF_RESOLVER_IPV6: "2620:0:ccc::2",
            CONF_IPV4: True,
            CONF_IPV6: False,
        },
        {
            CONF_HOSTNAME: "home-assistant.io",
            CONF_NAME: "home-assistant.io",
            CONF_RESOLVER: "208.67.222.222",
            CONF_RESOLVER_IPV6: "2620:0:ccc::2",
            CONF_IPV4: False,
            CONF_IPV6: True,
        },
    ],
)
async def test_options_error(hass: HomeAssistant, p_input: dict[str, str]) -> None:
    """Test validate url fails in options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="12345",
        data=p_input,
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.dnsip.async_setup_entry",
        return_value=True,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)

    with patch(
        "homeassistant.components.dnsip.config_flow.aiodns.DNSResolver",
        side_effect=DNSError("Did not find"),
    ):
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_RESOLVER: "192.168.200.34",
                CONF_RESOLVER_IPV6: "2001:4860:4860::8888",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["step_id"] == "init"
    if p_input[CONF_IPV4]:
        assert result2["errors"] == {"resolver": "invalid_resolver"}
    if p_input[CONF_IPV6]:
        assert result2["errors"] == {"resolver_ipv6": "invalid_resolver"}
