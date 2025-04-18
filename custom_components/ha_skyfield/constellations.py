# custom_components/ha_skyfield/constellations.py

import os
import datetime
import math
import logging

import numpy as np
from skyfield.api import Star

_LOGGER = logging.getLogger(__name__)

THIS_DIR = os.path.split(__file__)[0]
DATA_FILE = os.path.join(THIS_DIR, "constellations_by_RA_Dec.dat")

ZODIAC = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpius", "Sagittarius", "Capricornus",
    "Aquarius", "Pisces",
]

DEFAULT_CONSTELLATIONS = ZODIAC + [
    "Cassiopeia", "Orion", "Pegasus", "UrsaMajor"
]


def read_data():
    """
    Read constellation lines from the data file.
    """
    constellations = {}
    with open(DATA_FILE) as datafile:
        for line in datafile:
            line = line.strip()
            if not line or line.startswith("#"):  
                continue

            parts = line.split()
            if len(parts) != 5:
                continue
            name, ra1, dec1, ra2, dec2 = parts
            const_data = constellations.setdefault(name, [])
            const_data.append(
                (
                    (float(ra1) / 360 * 24, float(dec1)),
                    (float(ra2) / 360 * 24, float(dec2)),
                )
            )
    return constellations


class Constellation:
    """A single constellation representation."""

    def __init__(self, name, radec_pairs, sky):
        self.name = name
        self._radec_pairs = radec_pairs
        self._sky = sky

    def draw(self, ax, when):
        """Draw this constellation with theme colors and sizes."""
        try:
            # Fetch theme values
            star_col       = self._sky._colors.get("star_color", "#64CDFA")
            star_alpha     = self._sky._colors.get("star_alpha", 0.6)
            star_size      = self._sky._colors.get("star_size", 10)
            const_col      = self._sky._colors.get("constellation_color", "#64CDFA")
            const_lw       = self._sky._colors.get("constellation_linewidth", 0.5)
            const_alpha    = self._sky._colors.get("constellation_alpha", 0.1)

            plotted = []  # avoid duplicate points

            for (ra1, dec1), (ra2, dec2) in self._radec_pairs:
                star1 = Star(ra_hours=ra1, dec_degrees=dec1)
                star2 = Star(ra_hours=ra2, dec_degrees=dec2)
                azi1, alt1 = self._sky.compute_position(star1, when)
                azi2, alt2 = self._sky.compute_position(star2, when)

                # skip if both points are off-disk
                if alt1 > 90 and alt2 > 90:
                    continue

                # draw first star
                if (azi1, alt1) not in plotted:
                    ax.scatter(
                        azi1, alt1,
                        s=star_size,
                        alpha=star_alpha,
                        color=star_col,
                        edgecolor=star_col,
                        zorder=2,
                    )
                    plotted.append((azi1, alt1))

                # draw second star
                if (azi2, alt2) not in plotted:
                    ax.scatter(
                        azi2, alt2,
                        s=star_size,
                        alpha=star_alpha,
                        color=star_col,
                        edgecolor=star_col,
                        zorder=2,
                    )
                    plotted.append((azi2, alt2))

                # handle azimuth wrap-around
                if azi2 - azi1 > math.pi:
                    azi1 += 2 * math.pi
                elif azi1 - azi2 > math.pi:
                    azi2 += 2 * math.pi

                # draw connecting line
                ax.plot(
                    np.linspace(azi1, azi2, 10),
                    np.linspace(alt1, alt2, 10),
                    "-",
                    color=const_col,
                    linewidth=const_lw,
                    alpha=const_alpha,
                    zorder=1,
                )

        except Exception as e:
            _LOGGER.error(
                "Error drawing constellation %s: %s", self.name, e, exc_info=True
            )


def build_constellations(sky, whitelist=None):
    """
    Build Constellation objects for the selected names.
    """
    data = read_data()
    results = []
    for name, radec_pairs in data.items():
        if whitelist is None or name in whitelist:
            results.append(Constellation(name, radec_pairs, sky))
    return results
