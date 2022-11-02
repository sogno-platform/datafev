def departure_protocol(ts, fleet):
    """
    This protocol is executed for EVs leaving the charger clusters.

    :param ts:      Current time                datetime
    :param fleet:   EV fleet object             datahandling.fleet

    """

    outgoing_vehicles = fleet.outgoing_vehicles_at(ts)

    # Managing the leaving EVs
    for ev in outgoing_vehicles:

        if ev.admitted == True:

            if ev.reserved == True:

                cu = ev.connected_cu
                cu.disconnect(ts)

                cc = ev.connected_cc
                cc.unreserve(ts, ev.reservation_id)
                cc.enter_data_of_outgoing_vehicle(ts, ev)

                ev.reservation_id = None
