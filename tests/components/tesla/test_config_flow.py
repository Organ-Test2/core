"""Test the Tesla config flow."""
from unittest.mock import patch

from teslajsonpy import TeslaException

from homeassistant import config_entries, data_entry_flow, setup
from homeassistant.components.tesla.const import DOMAIN
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    CONF_USERNAME,
)

from tests.common import MockConfigEntry, mock_coro


async def test_form(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.tesla.config_flow.TeslaAPI.connect",
        return_value=mock_coro(("test-refresh-token", "test-access-token")),
    ), patch(
        "homeassistant.components.tesla.async_setup", return_value=mock_coro(True)
    ) as mock_setup, patch(
        "homeassistant.components.tesla.async_setup_entry", return_value=mock_coro(True)
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "test", CONF_USERNAME: "test@email.com"}
        )

    assert result2["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == "test@email.com"
    assert result2["data"] == {
        "token": "test-refresh-token",
        "access_token": "test-access-token",
    }
    await hass.async_block_till_done()
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(hass):
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.tesla.config_flow.TeslaAPI.connect",
        side_effect=TeslaException(401),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "test-username", CONF_PASSWORD: "test-password"},
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "invalid_credentials"}


async def test_form_cannot_connect(hass):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.tesla.config_flow.TeslaAPI.connect",
        side_effect=TeslaException(code=404),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PASSWORD: "test-password", CONF_USERNAME: "test-username"},
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "connection_error"}


async def test_form_repeat_identifier(hass):
    """Test we handle repeat identifiers."""
    entry = MockConfigEntry(domain=DOMAIN, title="test-username", data={}, options=None)
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "homeassistant.components.tesla.config_flow.TeslaAPI.connect",
        return_value=mock_coro(("test-refresh-token", "test-access-token")),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "test-username", CONF_PASSWORD: "test-password"},
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {CONF_USERNAME: "identifier_exists"}


async def test_import(hass):
    """Test import step."""

    with patch(
        "homeassistant.components.tesla.config_flow.TeslaAPI.connect",
        return_value=mock_coro(("test-refresh-token", "test-access-token")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={CONF_PASSWORD: "test-password", CONF_USERNAME: "test-username"},
        )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == "test-username"
    assert result["data"][CONF_ACCESS_TOKEN] == "test-access-token"
    assert result["data"][CONF_TOKEN] == "test-refresh-token"
    assert result["description_placeholders"] is None


async def test_option_flow(hass):
    """Test config flow options."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=None)
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == "form"
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_SCAN_INTERVAL: 350}
    )
    assert result["type"] == "create_entry"
    assert result["data"] == {CONF_SCAN_INTERVAL: 350}


async def test_option_flow_input_floor(hass):
    """Test config flow options."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=None)
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == "form"
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_SCAN_INTERVAL: 1}
    )
    assert result["type"] == "create_entry"
    assert result["data"] == {CONF_SCAN_INTERVAL: 300}