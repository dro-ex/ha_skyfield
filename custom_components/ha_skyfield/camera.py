# <config_dir>/custom_components/ha_skyfield/camera.py

from __future__ import annotations
import logging
import io
from datetime import timedelta

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.camera import Camera
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE

from .bodies import Sky

_LOGGER = logging.getLogger(__name__)

DOMAIN = "skyfield"
ICON = "mdi:sun"
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)

# Configuration keys
CONF_SHOW_CONSTELLATIONS = "show_constellations"
CONF_SHOW_TIME = "show_time"
CONF_SHOW_LEGEND = "show_legend"
CONF_CONSTELLATION_LIST = "constellations_list"
CONF_PLANET_LIST = "planet_list"
CONF_NORTH_UP = "north_up"
CONF_HORIZONTAL_FLIP = "horizontal_flip"
CONF_IMAGE_TYPE = "image_type"
CONF_DEFAULT_THEME = "default_theme"
CONF_COLOR_PRESETS = "color_presets"
CONF_REFRESH_INTERVAL = "refresh_interval"

# Schema for the presets mapping
PRESETS_SCHEMA = vol.Schema({cv.string: dict})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_SHOW_CONSTELLATIONS, default=False): cv.boolean,
        vol.Optional(CONF_SHOW_TIME, default=True): cv.boolean,
        vol.Optional(CONF_SHOW_LEGEND, default=True): cv.boolean,
        vol.Optional(CONF_CONSTELLATION_LIST): cv.ensure_list,
        vol.Optional(CONF_PLANET_LIST): cv.ensure_list,
        vol.Optional(CONF_NORTH_UP, default=False): cv.boolean,
        vol.Optional(CONF_HORIZONTAL_FLIP, default=False): cv.boolean,
        vol.Optional(CONF_IMAGE_TYPE, default="png"): cv.string,
        vol.Optional(CONF_DEFAULT_THEME, default="dark"): cv.string,
        vol.Optional(CONF_COLOR_PRESETS, default={}): PRESETS_SCHEMA,
        vol.Optional(CONF_REFRESH_INTERVAL, default=300): cv.positive_int,
    }
)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Skyfield camera platform."""
    latitude = config.get(CONF_LATITUDE, hass.config.latitude)
    longitude = config.get(CONF_LONGITUDE, hass.config.longitude)
    tzname = str(hass.config.time_zone)

    show_const = config[CONF_SHOW_CONSTELLATIONS]
    show_time = config[CONF_SHOW_TIME]
    show_legend = config[CONF_SHOW_LEGEND]
    constellations = config.get(CONF_CONSTELLATION_LIST)
    planets = config.get(CONF_PLANET_LIST)
    north_up = config[CONF_NORTH_UP]
    horizontal_flip = config[CONF_HORIZONTAL_FLIP]
    image_type = config[CONF_IMAGE_TYPE]
    default_theme = config[CONF_DEFAULT_THEME]
    color_presets = config[CONF_COLOR_PRESETS]
    refresh_interval = config[CONF_REFRESH_INTERVAL]

    tmpdir = "/tmp/skyfield"
    _LOGGER.debug(
        "Setting up skyfield camera (theme=%s, refresh=%ss)",
        default_theme,
        refresh_interval,
    )

    panel = SkyFieldCam(
        latitude,
        longitude,
        tzname,
        tmpdir,
        show_const,
        show_time,
        show_legend,
        constellations,
        planets,
        north_up,
        horizontal_flip,
        image_type,
        default_theme,
        color_presets,
        refresh_interval=refresh_interval,
    )

    add_entities([panel], True)


class SkyFieldCam(Camera):
    """Home Assistant Camera entity for Skyfield plots."""

    def __init__(
        self,
        latitude,
        longitude,
        tzname,
        tmpdir,
        show_constellations,
        show_time,
        show_legend,
        constellations,
        planets,
        north_up,
        horizontal_flip,
        image_type,
        default_theme,
        color_presets,
        refresh_interval: int,
    ):
        super().__init__()
        self._latitude = latitude
        self._longitude = longitude
        self._tzname = tzname
        self._tmpdir = tmpdir
        self._show_constellations = show_constellations
        self._show_time = show_time
        self._show_legend = show_legend
        self._constellations = constellations
        self._planets = planets
        self._north_up = north_up
        self._horizontal_flip = horizontal_flip
        self._image_type = image_type
        self._default_theme = default_theme
        self._color_presets = color_presets
        self._refresh_interval = refresh_interval

        self.sky = Sky(
            (latitude, longitude),
            tzname,
            show_constellations,
            show_time,
            show_legend,
            constellations,
            planets,
            north_up,
            horizontal_flip,
            image_type,
            default_theme=default_theme,
            presets=color_presets,
        )
        self._loaded = False

    @property
    def frame_interval(self):
        """Return the configured refresh interval (in seconds)."""
        return self._refresh_interval

    @property
    def name(self):
        return "SkyField"

    @property
    def icon(self):
        return ICON

    def camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        """Return a bytes image of the sky plot."""
        if not self._loaded:
            _LOGGER.debug("Loading sky data for the first time")
            self.sky.load(self._tmpdir)
            self._loaded = True

        _LOGGER.debug("Rendering skyfield plot")
        buf = io.BytesIO()
        self.sky.plot_sky(buf)
        buf.seek(0)
        return buf.getvalue()
