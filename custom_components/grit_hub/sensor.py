"""Sensors for GRIT Hub."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory

from .api import obj_id
from .const import DEVICE_TYPES, DOMAIN, SENSOR_DEVICE_TYPES
from .entity import GritHubEntity


ENVIRONMENTAL_SENSORS = {
    "airquality": (
        ("density01", "PM1", "µg/m³", SensorDeviceClass.PM1),
        ("density25", "PM2.5", "µg/m³", SensorDeviceClass.PM25),
        ("density4", "PM4", "µg/m³", SensorDeviceClass.PM4),
        ("density10", "PM10", "µg/m³", SensorDeviceClass.PM10),
        ("temperature", "Temperature", "°C", SensorDeviceClass.TEMPERATURE),
        ("humidity", "Humidity", "%", SensorDeviceClass.HUMIDITY),
        ("carbonDioxide", "Carbon Dioxide", "ppm", SensorDeviceClass.CO2),
        ("volatileOrganic", "VOC Index", None, None),
        ("nitrogenOxide", "NOx Index", None, None),
    ),
    "pressure": (
        ("pressure", "Pressure", "mbar", SensorDeviceClass.PRESSURE),
        ("temperature", "Temperature", "°C", SensorDeviceClass.TEMPERATURE),
    ),
}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = [
        GritHubStatusSensor(coordinator),
        GritHubDeviceCountSensor(coordinator),
        GritHubIpAddressSensor(coordinator),
        GritHubSoftwareVersionSensor(coordinator),
        GritHubSoftwareBranchSensor(coordinator),
    ]
    for dev_type in SENSOR_DEVICE_TYPES:
        for dev in coordinator.data.get("devices", {}).get(dev_type, []):
            if obj_id(dev) is not None:
                entities.append(GritHubGenericDeviceSensor(coordinator, dev_type, dev))
                for field, name, unit, device_class in ENVIRONMENTAL_SENSORS.get(
                    dev_type, ()
                ):
                    entities.append(
                        GritHubMeasurementSensor(
                            coordinator,
                            entry.entry_id,
                            dev_type,
                            dev,
                            field,
                            name,
                            unit,
                            device_class,
                        )
                    )
    for dev_type in DEVICE_TYPES:
        for dev in coordinator.data.get("devices", {}).get(dev_type, []):
            if obj_id(dev) is None:
                continue
            entities.extend(
                (
                    GritHubMqttRssiSensor(
                        coordinator, entry.entry_id, dev_type, dev
                    ),
                    GritHubMqttFirmwareSensor(
                        coordinator, entry.entry_id, dev_type, dev
                    ),
                    GritHubMqttLastReceivedSensor(
                        coordinator, entry.entry_id, dev_type, dev
                    ),
                )
            )
    async_add_entities(entities)


class GritHubStatusSensor(GritHubEntity, SensorEntity):
    _attr_name = "Status"
    _attr_unique_id = "grit_hub_status"
    _attr_icon = "mdi:hubspot"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        return "online" if self.coordinator.last_update_success else "offline"


class GritHubDeviceCountSensor(GritHubEntity, SensorEntity):
    _attr_name = "Device Count"
    _attr_unique_id = "grit_hub_device_count"
    _attr_icon = "mdi:counter"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        return sum(len(v) for v in self.coordinator.data.get("devices", {}).values())


class GritHubIpAddressSensor(GritHubEntity, SensorEntity):
    _attr_name = "Hub IP Address"
    _attr_unique_id = "grit_hub_ip_address"
    _attr_icon = "mdi:ip-network"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> str | None:
        value = self.hub_data.get("ipAddressEthernet")
        return value if isinstance(value, str) else None


class GritHubSoftwareVersionSensor(GritHubEntity, SensorEntity):
    _attr_name = "Hub Software Version"
    _attr_unique_id = "grit_hub_software_version"
    _attr_icon = "mdi:chip"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> str | None:
        value = self.hub_data.get("hubVersion")
        return value if isinstance(value, str) else None


class GritHubSoftwareBranchSensor(GritHubEntity, SensorEntity):
    _attr_name = "Software Branch"
    _attr_unique_id = "grit_hub_software_branch"
    _attr_icon = "mdi:source-branch"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> str | None:
        value = self.hub_data.get("branch")
        return value if isinstance(value, str) else None


class GritHubGenericDeviceSensor(GritHubEntity, SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, device_type, device):
        super().__init__(coordinator, device_type, device)
        ident = obj_id(device)
        self._attr_unique_id = f"grit_hub_{device_type}_{ident}_status"
        self._attr_name = "Status"

    @property
    def native_value(self):
        attributes = self.diagnostic_attributes
        return attributes.get("status") or attributes.get("state") or attributes.get("mode") or "unknown"

    @property
    def extra_state_attributes(self):
        return self.diagnostic_attributes


class GritHubMeasurementSensor(GritHubEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator, entry_id, device_type, device, field, name, unit, device_class
    ):
        super().__init__(coordinator, device_type, device)
        self._field = field
        self._attr_unique_id = (
            f"grit_hub_{entry_id}_{device_type}_{self._device_id}_{field}"
        )
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class

    @property
    def native_value(self):
        value = self.mqtt_state.get(self._field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return value

    @property
    def available(self):
        return self.live_available and self.native_value is not None


class GritHubMqttRssiSensor(GritHubEntity, SensorEntity):
    _attr_name = "MQTT RSSI"
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = "dBm"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry_id, device_type, device):
        super().__init__(coordinator, device_type, device)
        ident = obj_id(device)
        self._attr_unique_id = (
            f"grit_hub_{entry_id}_{device_type}_{ident}_mqtt_rssi"
        )

    @property
    def native_value(self):
        value = self.mqtt_state.get("rssi")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return value

    @property
    def available(self) -> bool:
        return self.native_value is not None


class GritHubMqttFirmwareSensor(GritHubEntity, SensorEntity):
    _attr_name = "MQTT Firmware"
    _attr_icon = "mdi:chip"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry_id, device_type, device):
        super().__init__(coordinator, device_type, device)
        ident = obj_id(device)
        self._attr_unique_id = (
            f"grit_hub_{entry_id}_{device_type}_{ident}_mqtt_firmware"
        )

    @property
    def native_value(self):
        value = self.mqtt_state.get("firmware_version")
        return value if isinstance(value, str) else None

    @property
    def available(self) -> bool:
        return self.native_value is not None


class GritHubMqttLastReceivedSensor(GritHubEntity, SensorEntity):
    _attr_name = "MQTT Last Received"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry_id, device_type, device):
        super().__init__(coordinator, device_type, device)
        ident = obj_id(device)
        self._attr_unique_id = (
            f"grit_hub_{entry_id}_{device_type}_{ident}_mqtt_last_received"
        )

    @property
    def native_value(self):
        value = self.mqtt_state.get("last_received_at")
        if not isinstance(value, datetime):
            return None
        try:
            offset = value.utcoffset()
        except (OverflowError, ValueError):
            return None
        return value if value.tzinfo is not None and offset is not None else None

    @property
    def available(self) -> bool:
        # Remain available while MQTT is up so "never seen this session" is
        # distinct (unknown) from broker/coordinator unavailability.
        return (
            self.coordinator.last_update_success
            and self.coordinator.mqtt_connected
        )
