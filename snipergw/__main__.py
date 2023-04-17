"""
This module contains the command line interface for snipergw.
"""
import argparse
import logging

from astropy.time import Time

from snipergw.model import EventConfig, PlanConfig, DEFAULT_TELESCOPE, DEFAULT_EXPOSURE, DEFAULT_FILTERS, DEFAULT_STARTTIME
from snipergw.run import run_snipergw

logging.getLogger("snipergw").setLevel(logging.DEBUG)

parser = argparse.ArgumentParser(
    prog='snipergw',
    description='Simple Nodal Interface for Planning '
                'Electromagnetic Reconnaissance of Gravitational Waves',
)
parser.add_argument("-e", '--event')
parser.add_argument('-r', '--rev')
parser.add_argument('-o', '--outputdir')
parser.add_argument('-t', '--telescope', default=DEFAULT_TELESCOPE)
parser.add_argument("-f", "--filters", default=DEFAULT_FILTERS)
parser.add_argument("--exposuretime", default=DEFAULT_EXPOSURE)
parser.add_argument("--subprogram", default="EMGW")
parser.add_argument("-c", "--cache", default=False, action="store_true")
parser.add_argument("-s", "--submit", default=False, action="store_true")
parser.add_argument("-d", "--delete", default=False, action="store_true")
parser.add_argument("-sg", "--use_both_grids", default=False, action="store_true")
parser.add_argument("-st", "--starttime", default=None)
args, gwemopt_args = parser.parse_known_args()

if args.starttime is not None:
    args.starttime = Time(args.starttime, format="isot", scale="utc")
else:
    args.starttime = DEFAULT_STARTTIME

event = EventConfig(**args.__dict__)
plan_config = PlanConfig(**args.__dict__)

run_snipergw(
    event=event,
    plan_config=plan_config,
    gwemopt_args=gwemopt_args,
    submit=args.submit,
    delete=args.delete
)
