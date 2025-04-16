import datetime
import math
import os
import yaml

from pytz import timezone
from skyfield.api import Loader
from skyfield.api import Topos

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from . import constellations

# use non-interactive backend
matplotlib.use("agg")

# Load custom colors from YAML
def load_color_config(preset_name=None):
    try:
        with open(os.path.join(os.path.dirname(__file__), "skyfield_config.yaml"), "r") as f:
            config = yaml.safe_load(f)
            presets = config.get("presets", {})
            default = config.get("default_theme", "dark")
            selected = preset_name or default
            return presets.get(selected, presets.get("dark", {}))
    except Exception:
        return {}

EARTH = "earth"
SUN = "sun"

class Sky:
    def __init__(
        self,
        latlong,
        tzname,
        show_constellations=True,
        show_time=True,
        show_legend=True,
        constellation_list=None,
        planet_list=None,
        north_up=False,
        horizontal_flip=False,
        image_type="png",
        color_preset=None,
    ):
        lat, long = latlong
        self._latlong = Topos(latitude_degrees=lat, longitude_degrees=long)
        self._timezone = timezone(tzname)
        self._planets = None
        self._ts = None
        self._location = None
        self._winter_solstice = None
        self._summer_solstice = None
        self.sun_position = None
        self._constellations = []
        self._points = []
        self._show_constellations = show_constellations
        self._show_time = show_time
        self._show_legend = show_legend
        self._north_up = north_up
        self._horizontal_flip = horizontal_flip
        self._image_type = image_type
        self._colors = load_color_config(color_preset)

        if constellation_list is None:
            self._constellation_names = constellations.DEFAULT_CONSTELLATIONS
        else:
            self._constellation_names = constellation_list
        self._planet_list = planet_list

    def load(self, tmpdir="."):
        if self._planets is None:
            self._load_sky_data(tmpdir)
            self._run_initial_computations()

    def _load_sky_data(self, tmpdir):
        load = Loader(tmpdir)
        self._planets = load("de421.bsp")
        self._ts = load.timescale()

    def _run_initial_computations(self):
        self._location = self._planets[EARTH] + self._latlong
        self._compute_solstice_paths()
        self._load_points()
        if self._show_constellations:
            self._constellations = constellations.build_constellations(
                self, self._constellation_names
            )

    def _load_points(self):
        self._points.clear()
        for name, planet_label in [
            ("Sun", SUN),
            ("Mercury", "mercury"),
            ("Venus", "venus"),
            ("Moon", "moon"),
            ("Mars", "mars"),
            ("Jupiter", "jupiter barycenter"),
            ("Saturn", "saturn barycenter"),
            ("Uranus", "uranus barycenter"),
            ("Neptune", "neptune barycenter"),
        ]:
            if self._planet_list and name not in self._planet_list:
                continue
            color = self._colors.get("planets", {}).get(name, "#ffffff")
            size = {
                "Sun": 500,
                "Mercury": 40,
                "Venus": 60,
                "Moon": 300,
                "Mars": 60,
                "Jupiter": 100,
                "Saturn": 90,
                "Uranus": 40,
                "Neptune": 30,
            }.get(name, 50)
            self._points.append(
                Point(name, self._planets[planet_label], color, size, self)
            )

    def _compute_solstice_paths(self):
        today = datetime.datetime.today()
        self._winter_solstice = BodyPath(
            self._planets[SUN],
            datetime.datetime(today.year, 12, 21),
            self,
            fmt="--",
            color=self._colors.get("solstice_winter", "#219ebc"),
            linewidth=1,
            alpha=0.8,
        )
        self._summer_solstice = BodyPath(
            self._planets[SUN],
            datetime.datetime(today.year, 6, 21),
            self,
            fmt="--",
            color=self._colors.get("solstice_summer", "#8ecae6"),
            linewidth=1,
            alpha=0.8,
        )

    @property
    def get_image_type(self):
        return self._image_type

    def compute_position(self, body, obs_datetime):
        obs_time = self._ts.utc(self._timezone.localize(obs_datetime))
        astrometric = self._location.at(obs_time).observe(body)
        alt, azi, _d = astrometric.apparent().altaz()
        alt = 90 - alt.radians * 180 / math.pi
        azi = azi.radians
        return azi, alt

    def plot_sky(self, output=None, when=None):
        if when is None:
            when = datetime.datetime.now()

        visible = [np.linspace(0, 2 * np.pi, 200), [90.0 for _i in range(200)]]

        fig, ax = plt.subplots(
            1, 1, figsize=(6, 6.2), subplot_kw={"projection": "polar"}
        )

        fig.patch.set_facecolor(self._colors.get("background_outer", "#0d1b2a"))
        ax.set_facecolor(self._colors.get("background_inner", "#1b263b"))
        ax.set_axisbelow(True)
        ax.set_theta_direction(1 if self._horizontal_flip else -1)

        ax.plot(*visible, "-", color=self._colors.get("grid_circle", "#0d1b2a"), linewidth=3, alpha=1.0)

        self._draw_objects(ax, when)

        if self._show_time:
            ax.annotate(
                str(when),
                xy=(0.09, 0.07),
                xycoords="figure fraction",
                horizontalalignment="left",
                verticalalignment="top",
                fontsize=8,
                color=self._colors.get("text", "#e0e1dd"),
            )

        if self._show_legend:
            fig.legend(
                loc="lower right",
                bbox_transform=fig.transFigure,
                ncol=3,
                markerscale=0.6,
                columnspacing=1,
                mode=None,
                handletextpad=0.05,
                labelcolor=self._colors.get("text", "#e0e1dd"),
                facecolor=self._colors.get("legend_face", "#1b263b"),
                edgecolor=self._colors.get("legend_edge", "#0d1b2a"),
            )

        ax.set_theta_zero_location("N" if self._north_up else "S", offset=0)
        ax.set_rmax(90)

        ax.set_rgrids(
            np.linspace(0, 90, 10),
            [f"{int(f)}˚" for f in np.linspace(90, 0, 10)],
            color=self._colors.get("rgrid_color", "#e0e1dd"),
        )
        ax.set_thetagrids(
            np.linspace(0, 360.0, 9),
            ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"],
            color=self._colors.get("tgrid_color", "#e0e1dd"),
        )
        fig.tight_layout()

        if output is None:
            plt.show()
        else:
            fig.savefig(output, format=self._image_type)
        plt.close()

    def _draw_objects(self, ax, when):
        today_sunpath = BodyPath(
            self._planets[SUN],
            datetime.datetime.now().replace(hour=0, minute=0),
            self,
            "-",
            color=self._colors.get("sun_today", "#ffb703"),
            linewidth=1,
            alpha=0.8,
        )

        for sunpath in [self._winter_solstice, self._summer_solstice, today_sunpath]:
            sunpath.draw(ax)

        for point in self._points:
            point.draw(ax, when)

        for constellation in self._constellations:
            constellation.draw(ax, when)


class BodyPath:
    def __init__(self, body, day, sky, fmt, color, linewidth=1, alpha=0.8):
        self._body = body
        self._day = day
        self._sky = sky
        self.path = None
        self.fmt = fmt
        self.color = color
        self.linewidth = linewidth
        self.alpha = alpha

        self._compute_daily_path()

    def _compute_daily_path(self, delta=datetime.timedelta(minutes=20)):
        data = []
        for interval in range(24 * 3 + 1):
            now = self._day + delta * interval
            azi, alt = self._sky.compute_position(self._body, now)
            data.append((azi, alt))
        self.path = list(zip(*data))

    def draw(self, ax):
        ax.plot(
            *self.path,
            self.fmt,
            color=self.color,
            linewidth=self.linewidth,
            alpha=self.alpha,
        )


class Point:
    def __init__(self, label, body, color, size, sky):
        self._label = label
        self._body = body
        self._size = size
        self._color = color
        self._sky = sky

    def draw(self, ax, when):
        azi, alt = self._sky.compute_position(self._body, when)

        ax.scatter(
            azi,
            alt,
            s=self._size * 3.5,
            alpha=0.2,
            color=self._color,
            edgecolor="none",
            linewidths=0,
            zorder=1,
        )

        ax.scatter(
            azi,
            alt,
            s=self._size,
            label=self._label,
            alpha=1.0,
            color=self._color,
            edgecolor="black",
            linewidths=0.5,
            zorder=2,
        )
