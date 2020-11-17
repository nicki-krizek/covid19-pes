#!/usr/bin/env python3
# pes.py: plot PES score for COVID-19 epidemic from open data
# Copyright (C) 2020 Tomas Krizek
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from argparse import ArgumentParser
from collections import namedtuple
import csv
from datetime import date, timedelta
import logging
import math
import urllib.request

import matplotlib.pyplot as plt
from matplotlib import cycler
from matplotlib.dates import WE, WeekdayLocator, AutoDateFormatter
from matplotlib.patches import Rectangle

plt.rcParams['savefig.dpi'] = 200
plt.rcParams['axes.prop_cycle'] = cycler(color=[
    'black', 'tab:brown', 'tab:gray', 'tab:blue', 'tab:pink', 'tab:cyan'])

TESTS_NEW_GUESSTIMATE = 0.95  # assume 95% of tests are new tests (not re-tests)
SRC_LINK = "https://github.com/tomaskrizek/covid19-pes/tree/v1.0.0"  # TODO release 1.0.0
DATA_FILEPATH = 'data/covid_orp.csv'
POPULATION_FILEPATH = 'data/obyvatele.csv'
DATA_URL = 'https://onemocneni-aktualne.mzcr.cz/api/account/verejne-distribuovana-data/file/dip%252Fweb_orp.csv'  # noqa
ALL_LABEL = 'Celá ČR'


AgeGroup = namedtuple('AgeGroup', ['all', 'senior'])


logger = logging.getLogger('PES')


class PesError(Exception):
    pass


class PesValueError(PesError):
    pass


class EpidemicData:
    def __init__(self, incidence7=0, incidence7_65=0, tests7=0):
        self.incidence7 = AgeGroup(incidence7, incidence7_65)
        self.tests7 = tests7

    @property
    def positivity(self):
        if self.tests7 == 0:
            return 0
        return self.incidence7.all / (self.tests7 * TESTS_NEW_GUESSTIMATE)

    def __add__(self, other):
        return EpidemicData(
            self.incidence7.all + other.incidence7.all,
            self.incidence7.senior + other.incidence7.senior,
            self.tests7 + other.tests7)

    def __str__(self):
        return (
            "incidence7: {s.incidence7.all:d}, "
            "incidence7_senior: {s.incidence7.senior:d}, "
            "tests7: {s.tests7:d}, "
            "positivity: {s.positivity:.2f}").format(s=self)


class Pes:
    def __init__(self, day, region_data, region_population):
        day_prev5 = day - timedelta(days=5)
        day_prev7 = day - timedelta(days=7)
        day_prev14 = day - timedelta(days=14)

        self.population = region_population

        self.incidence14 = (region_data[day] + region_data[day_prev7]).incidence7
        self.incidence14_prev7 = (region_data[day_prev7] + region_data[day_prev14]).incidence7

        self.score_incidence_all = self._score_incidence(
            self.incidence14.all / self.population.all * 100000)
        self.score_incidence_senior = self._score_incidence(
            self.incidence14.senior / self.population.senior * 100000)
        if self.incidence14.senior > self.incidence14_prev7.senior:
            self.score_incidence_senior += 2

        self.repro = region_data[day].incidence7.all / region_data[day_prev5].incidence7.all
        self.score_repro = self._score_repro(self.repro)

        self.score_positivity = self._score_positivity(region_data[day].positivity)
        if region_data[day].positivity > region_data[day_prev7].positivity:
            self.score_positivity += 2

    @property
    def score(self):
        return (
            self.score_incidence_all +
            self.score_incidence_senior +
            self.score_repro +
            self.score_positivity)

    @classmethod
    def _score_incidence(cls, incidence_per_100k):
        if incidence_per_100k < 10:
            return 0
        if incidence_per_100k < 25:
            return 2
        if incidence_per_100k < 50:
            return 4
        if incidence_per_100k < 120:
            return 7
        if incidence_per_100k < 240:
            return 10
        if incidence_per_100k < 480:
            return 13
        if incidence_per_100k < 960:
            return 16
        return 20

    @classmethod
    def _score_repro(cls, repro):
        if repro < 0.8:
            return 0
        if repro < 1.0:
            return 5
        if repro < 1.2:
            return 10
        if repro < 1.4:
            return 15
        if repro < 1.6:
            return 20
        if repro < 1.9:
            return 25
        return 30

    @classmethod
    def _score_positivity(cls, positivity):
        if positivity < 0.03:
            return 0
        if positivity < 0.07:
            return 3
        if positivity < 0.11:
            return 7
        if positivity < 0.15:
            return 11
        if positivity < 0.19:
            return 15
        if positivity < 0.23:
            return 20
        if positivity < 0.26:
            return 25
        return 30


def score_color(score):
    if score > 75:
        return "indigo"
    if score > 60:
        return "crimson"
    if score > 40:
        return "darkorange"
    if score > 10:
        return "gold"
    return "forestgreen"


def init_plot(x_vals):
    fig, ax = plt.subplots(1)

    plt.xlabel("datum")
    plt.ylabel("index rizika")

    min_x = min(x_vals)
    max_x = max(x_vals)

    if isinstance(min_x, date):
        # format only for dates
        interval = math.ceil((max_x - min_x).days / (13 * 7))
        locator = WeekdayLocator(byweekday=WE, interval=interval)
        formatter = AutoDateFormatter(locator)
        minor_locator = WeekdayLocator(byweekday=WE)

        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        ax.xaxis.set_minor_locator(minor_locator)
        ax.set_xlim(min_x, max_x)
        ax.grid(which='major', axis='x', linestyle=':', lw=.5)

    ax.set_ylim(0, 104)
    ax.margins(0)

    ax.set_yticks([0, 20, 40, 60, 75, 100])
    colors = ["black", "forestgreen", "gold", "darkorange", "crimson", "indigo"]
    for ytick, color in zip(ax.get_yticklabels(), colors):
        plt.setp(ytick, color=color)
    ax.set_yticks([10, 30, 50, 70, 80, 90], minor=True)

    # PES levels
    # ax.axhline(100, color='indigo', linestyle='--')
    ax.axhline(75, color='crimson', linestyle='--')
    ax.axhline(60, color='darkorange', linestyle='--')
    ax.axhline(40, color='gold', linestyle='--')
    ax.axhline(20, color='forestgreen', linestyle='--')

    fig.autofmt_xdate()
    fig.text(0.02, 0.02, "{:s}".format(SRC_LINK), fontsize='xx-small', color='gray')
    fig.text(0.95, 0.02, "CC0", fontsize='small', color='gray')

    return fig, ax


def line_plot(fpath, region_pes):
    x_vals = sorted(region_pes[list(region_pes.keys())[0]].keys())
    fig, ax = init_plot(x_vals)
    plt.title("PES (k {:s})".format(x_vals[-1].strftime("%d.%m.%Y")))

    for region, pes in region_pes.items():
        y = [pes[x].score for x in x_vals]
        ax.plot(x_vals, y, label=region)

    tr = ax.transAxes
    patches = [
        Rectangle((0, 0), 1, 20/104, transform=tr, facecolor="forestgreen", alpha=0.4),
        Rectangle((0, 20/104), 1, 20/104, transform=tr, facecolor="gold", alpha=0.4),
        Rectangle((0, 40/104), 1, 20/104, transform=tr, facecolor="darkorange", alpha=0.4),
        Rectangle((0, 60/104), 1, 15/104, transform=tr, facecolor="crimson", alpha=0.4),
        Rectangle((0, 75/104), 1, 29/104, transform=tr, facecolor="indigo", alpha=0.4),
    ]

    for patch in patches:
        ax.add_patch(patch)

    plt.legend(loc='upper left', fontsize='xx-small')

    logger.info('Plotting into file %s', fpath)
    plt.savefig(fpath)


def stacked_plot(fpath, pes, region):
    x_vals = sorted(pes.keys())
    fig, ax = init_plot(x_vals)

    y = [pes[x].score for x in x_vals]
    y0 = [pes[x].score_incidence_all for x in x_vals]
    y1 = [pes[x].score_incidence_senior for x in x_vals]
    y2 = [pes[x].score_repro for x in x_vals]
    y3 = [pes[x].score_positivity for x in x_vals]

    plt.title("PES ({:s} k {:s})".format(region, x_vals[-1].strftime("%d.%m.%Y")))

    plot_collection = ax.stackplot(
        x_vals,
        y0, y1, y2, y3,
        labels=(
            'Body za počet pozitivních',
            'Body za počet pozitivních seniorů',
            'Body za reprodukční číslo',
            'Body za pozitivitu testů'),
        colors=('mediumblue', 'royalblue', 'deepskyblue', 'cyan'),
    )
    cumulative_line = ax.plot(x_vals, y, color='black', label='Celkem')

    plt.legend(
        handles=(plot_collection + cumulative_line)[::-1],
        loc='upper left',
        fontsize='xx-small')

    logger.info('Plotting stacked plot into file %s', fpath)
    plt.savefig(fpath)


def bar_plot_regions(data, population, num=10, today=None, extra_regions=None):
    if extra_regions is None:
        extra_regions = []
    if today is None:
        today = max(data[list(data.keys())[0]].keys()) - timedelta(days=1)  # ignore last day

    def add_if_missing(list_, entry):
        if not any(val[0] == entry[0] for val in list_):
            list_.append(entry)

    def add_value_to_bars(bars):
        for bar in bars:
            bar_height = bar.get_height()
            ax.annotate(
                '{}'.format(bar_height),
                xy=(bar.get_x() + bar.get_width() * 0.5, bar_height),
                xytext=(0, 2),
                textcoords="offset points",
                ha='center',
                va='bottom',
                rotation=20,
                color=score_color(bar_height),
            )

    region_pes = [
        (region, Pes(today, data[region], population[region]))
        for region in data.keys()
    ]
    region_pes_sorted = sorted(region_pes, key=lambda x: x[1].score)

    fpath = "pes_podle_regionu_{}.png".format(today.strftime("%d.%m.%Y"))

    to_plot = region_pes_sorted[:num] + region_pes_sorted[-1*num:]
    extra_regions = set(extra_regions + [ALL_LABEL])
    for extra_region in extra_regions:
        extra_region_bar = list(filter(lambda x: x[0] == extra_region, region_pes_sorted))[0]
        add_if_missing(to_plot, extra_region_bar)

    to_plot.sort(key=lambda x: x[1].score)

    fig, ax = init_plot(region_pes)
    plt.title("PES podle regionu ({:s}; {} nejlepších a nejhorších) ".format(
        today.strftime("%d.%m.%Y"), num))

    for region, pes in to_plot:
        color = score_color(pes.score)
        edge_color = 'black' if region in extra_regions else None
        bars = ax.bar([region], [pes.score], color=color, edgecolor=edge_color)
        add_value_to_bars(bars)

    logger.info('Plotting regions plot into file %s', fpath)
    plt.savefig(fpath)


def load_population(fpath):
    population = {}
    with open(fpath) as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            population[row['misto']] = AgeGroup(
                int(row['obyvatele']), int(row['obyvatele_65']))
    population[ALL_LABEL] = AgeGroup(
        sum([pop.all for pop in population.values()]),
        sum([pop.senior for pop in population.values()]))
    return population


def load_epidemic_data(fpath):
    data = {}
    with open(fpath) as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            orp_data = data.setdefault(row['orp_nazev'], {})
            today = date.fromisoformat(row['datum'])
            orp_data[today] = EpidemicData(
                int(row['incidence_7']),
                int(row['incidence_65_7']),
                int(row['testy_7']))
    all_cr = {}
    for orp, orp_data in data.items():
        for today, today_orp in orp_data.items():
            today_cr = all_cr.get(today, EpidemicData())
            all_cr[today] = today_cr + today_orp
    data[ALL_LABEL] = all_cr
    return data


def fetch_epidemic_data(out_fpath):
    logger.info(f"Downloding {DATA_URL} to {out_fpath}")
    with urllib.request.urlopen(DATA_URL) as in_file:
        with open(out_fpath, 'b+w') as out_file:
            out_file.write(in_file.read())


def configure_logger():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")


def main():
    parser = ArgumentParser(description='generate PES score charts')
    parser.add_argument('days', type=int, default=0, nargs='?',
                        help='number of past days to plot')
    parser.add_argument('--region', type=str, default=[ALL_LABEL], nargs='*',
                        help='plot selected region(s)')
    parser.add_argument(
        '--fetch', action='store_true', help='download updated dataset')
    args = parser.parse_args()
    configure_logger()

    if args.fetch:
        fetch_epidemic_data(DATA_FILEPATH)
    data = load_epidemic_data(DATA_FILEPATH)
    population = load_population(POPULATION_FILEPATH)

    for region in args.region:
        if region not in data:
            raise PesValueError(
                f'"{args.region}" is not a valid region name. '
                f'Available regions: {", ".join(sorted(data))}'
            )

    region_pes = {}
    regions = args.region

    # assume all regions have the same min and max date
    until = max(data[regions[0]].keys()) - timedelta(days=1)  # ignore last (incomplete) day
    min_since = min(data[regions[0]].keys()) + timedelta(days=14)
    if args.days == 0:
        since = min_since
    else:
        since = until - timedelta(days=args.days)
        if since < min_since:
            raise PesValueError("Not enough historical data. Max days: {:d}".format(
                (until - min_since).days))

    for region in regions:
        pes = {}
        for i in range((until - since).days + 1):
            today = since + timedelta(days=i)
            try:
                pes[today] = Pes(today, data[region], population[region])
            except KeyError:
                raise PesValueError(
                    f'missing data from {today.strftime("%d.%m.%Y")} for region "{region}"')
        region_pes[region] = pes

    line_plot('pes_{:d}d_{:s}_{:s}.png'.format(
        args.days, '_'.join(regions), str(until)), region_pes)
    for region in regions:
        stacked_plot('pes_{:d}d_{:s}_{:s}_skladany.png'.format(
            args.days, region, str(until)), region_pes[region], region)

    bar_plot_regions(data, population, num=7, extra_regions=regions)


if __name__ == '__main__':
    try:
        main()
    except PesError as exc:
        logger.error(exc)
