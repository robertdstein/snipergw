import pandas as pd
import os
from planobs.models import TooTarget
from snipergw.model import EventConfig
from planobs.api import Queue, APIError
import time

ZTF_FILTER_MAP = {"g": 1, "r": 2, "i": 3}

def submit_too_ztf(
        schedule: pd.DataFrame,
        event_config: EventConfig,
        subprogram: str = "EMGW",
        submit: bool = False,
        delete: bool = True
):
    """
    Submit a ToO to ZTF

    :param schedule: Schedule dataframe
    :param event_config: Event config
    :param subprogram: Subprogram name e.g EMGW
    :param submit: Submit the queue
    :param delete: Delete the queue
    :return: None
    """
    
    targets = []

    for i, row in schedule.iterrows():
        targets.append(TooTarget(
            request_id=i,
            field_id=row["field"],
            filter_id=ZTF_FILTER_MAP[row["filter"]],
            subprogram_name=f"ToO_{subprogram}",
            exposure_time=row["texp"],
        ))

    # get name of user from home directory
    user = os.path.basename(os.path.expanduser("~"))

    q = Queue(user=user)

    t_0 = min(schedule["tobs"])
    t_1 = max(schedule["tobs"])

    trigger_name = f"ToO_{subprogram}_{event_config.event}"
    
    q.add_trigger_to_queue(
        targets=targets,
        trigger_name=trigger_name,
        validity_window_start_mjd=t_0,
        validity_window_end_mjd=t_1,
    )

    expected_name = f"{trigger_name}_0"

    def in_queue() -> bool:
        current_too_queue = q.get_too_queues()

        print(
            f"Current Kowalski queue has "
            f"{len(current_too_queue['data'])} entries"
        )

        kowalski_list = [
            current_too_queue["data"][i]["queue_name"]
            for i in range(len(current_too_queue["data"]))
        ]

        return expected_name in kowalski_list


    if submit:

        try:
            q.delete_queue()
        except APIError:
            pass
    
        # Now we submit our triggers
        q.submit_queue()
    
        time.sleep(5)

        if not in_queue():
            raise RuntimeError("Trigger not added to queue")

    if delete:
        print("deleting queue")
        if not in_queue():
            raise RuntimeError("Trigger not in queue")
        # Now we delete our triggers
        q.delete_queue()
    
        current_too_queue = q.get_too_queues()
    
        print(
            f"Current Kowalski queue has {len(current_too_queue['data'])} entries (after deleting)"
        )

