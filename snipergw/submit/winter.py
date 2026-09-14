import os

import pandas as pd
from winterapi import WinterAPI
from winterapi.messenger import WinterFieldToO

from snipergw.model import PlanConfig

winter = WinterAPI()

MAX_EXPOSURE_TIME = 30
MIN_DITHER = 5


def submit_too_winter(
    schedule: pd.DataFrame,
    event_name: str,
    plan_config: PlanConfig,
    submit: bool = False,
    delete: bool = False,
):
    """
    Submit a ToO to Winter

    :param schedule: Schedule dataframe
    :param event_name: Event name
    :param plan_config: Plan config
    :param submit: Submit the queue
    :param delete: Delete the queue
    """

    if delete:
        raise NotImplementedError("Delete not implemented for Winter")

    try:
        print(f"User is {winter.get_user()}")
    except KeyError:
        print("No user credentials found. Please add these first!")
        winter.add_user_details(overwrite=True)

    program_name = os.getenv("WINTER_PROGRAM_NAME")
    program_key = os.getenv("WINTER_PROGRAM_KEY")

    if program_name not in winter.get_programs():
        winter.add_program(program_name, program_key)

    too_list = []

    t_start = min(schedule["tobs"])
    t_end = max(schedule["tobs"])

    n_dithers = int(max(plan_config.exposuretime / MAX_EXPOSURE_TIME, MIN_DITHER))

    print("n_dithers", n_dithers, "texp", plan_config.exposuretime)

    for _, row in schedule.iterrows():
        too_list.append(
            WinterFieldToO(
                target_name=f"{event_name}_{row['field']}",
                field_id=row["field"],
                filters=[row["filter"]],
                total_exposure_time=plan_config.exposuretime,
                start_time_mjd=t_start,
                end_time_mjd=t_end,
                n_dither=n_dithers,
            )
        )

    api_res, api_schedule = winter.submit_too(
        program_name=program_name, data=too_list, submit_trigger=submit
    )

    print("Submitted too:", api_res)
    print(api_schedule)
