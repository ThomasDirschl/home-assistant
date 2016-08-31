"""
A sensor that monitors trands in other components.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.template/
"""
import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.components.sensor import ENTITY_ID_FORMAT, PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_FRIENDLY_NAME,
    ATTR_ENTITY_ID)
from homeassistant.helpers.entity import Entity, generate_entity_id
from homeassistant.helpers.event import track_state_change

_LOGGER = logging.getLogger(__name__)
CONF_SENSORS = 'sensors'
CONF_ATTRIBUTE = 'attribute'
CONF_UP = 'up'
CONF_DOWN = 'down'

SENSOR_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id,
    vol.Optional(CONF_ATTRIBUTE): cv.string,
    vol.Optional(ATTR_FRIENDLY_NAME): cv.string,
    vol.Optional(CONF_UP, default='Up'): cv.string,
    vol.Optional(CONF_DOWN, default='Down'): cv.string,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SENSORS): vol.Schema({cv.slug: SENSOR_SCHEMA}),
})


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the template sensors."""
    sensors = []

    for device, device_config in config[CONF_SENSORS].items():
        entity_id = device_config[ATTR_ENTITY_ID]
        attribute = device_config.get(CONF_ATTRIBUTE)
        friendly_name = device_config.get(ATTR_FRIENDLY_NAME, device)
        up_message = device_config[CONF_UP]
        down_message = device_config[CONF_DOWN]

        sensors.append(
            SensorTrend(
                hass,
                device,
                friendly_name,
                entity_id,
                attribute,
                up_message,
                down_message)
            )
    if not sensors:
        _LOGGER.error("No sensors added")
        return False
    add_devices(sensors)
    return True


class SensorTrend(Entity):
    """Representation of a Template Sensor."""

    # pylint: disable=too-many-arguments, too-many-instance-attributes
    def __init__(self, hass, device_id, friendly_name,
                 target_entity, attribute, up_message, down_message):
        """Initialize the sensor."""
        self._hass = hass
        self.entity_id = generate_entity_id(ENTITY_ID_FORMAT, device_id,
                                            hass=hass)
        self._name = friendly_name
        self._target_entity = target_entity
        self._attribute = attribute
        self._up_message = up_message
        self._down_message = down_message
        self._state = None
        self.from_state = None
        self.to_state = None

        self.update()

        def template_sensor_state_listener(entity, old_state, new_state):
            """Called when the target device changes state."""
            self.from_state = old_state
            self.to_state = new_state
            self.update_ha_state(True)

        track_state_change(hass, target_entity,
                           template_sensor_state_listener)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    def update(self):
        """Get the latest data and update the states."""
        if self.from_state and self.to_state:
            try:
                if self._attribute:
                    from_value = float(
                        self.from_state.attributes.get(self._attribute))
                    to_value = float(
                        self.to_state.attributes.get(self._attribute))
                else:
                    from_value = float(self.from_state.state)
                    to_value = float(self.to_state.state)

                if to_value > from_value:
                    self._state = self._up_message
                elif to_value < from_value:
                    self._state = self._down_message
            except ValueError as ex:
                self._state = '-'
                _LOGGER.error(ex)
